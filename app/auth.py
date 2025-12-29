# app/auth.py
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.deps import get_db
from app import db_models

# ==============================
# Configurações JWT
# ==============================
SECRET_KEY = os.getenv("SECRET_KEY", "COLOQUE_AQUI_UMA_CHAVE_BEM_SECRETA_E_GRANDE")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 horas


# ==============================
# Utilitários de senha (SHA-256)
# ==============================
def _hash_sha256(password: str) -> str:
    if password is None:
        password = ""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _hash_sha256(plain_password) == hashed_password


def get_password_hash(password: str) -> str:
    return _hash_sha256(password)


# ==============================
# Utilitários de utilizador
# ==============================
def get_user_by_username(db: Session, username: str) -> Optional[db_models.UserDB]:
    return (
        db.query(db_models.UserDB)
        .filter(db_models.UserDB.username == username)
        .first()
    )


def authenticate_user(db: Session, username: str, password: str) -> Optional[db_models.UserDB]:
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


# ==============================
# JWT
# ==============================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ==============================
# Dependências de autenticação
# ==============================
def _get_token_from_request(request: Request) -> Optional[str]:
    """
    Tenta obter o token nesta ordem:
    1) Header Authorization: Bearer xxx
    2) Cookie "Authorization" (aceita "Bearer xxx" ou só o token)
    3) Cookie "access_token"
    """
    # 1) Header
    auth_header = request.headers.get("Authorization")
    if auth_header:
        token = auth_header.strip()
        if token.lower().startswith("bearer "):
            return token[7:].strip()
        return token

    # 2) Cookie Authorization
    auth_cookie = request.cookies.get("Authorization")
    if auth_cookie:
        token = auth_cookie.strip()
        if token.lower().startswith("bearer "):
            return token[7:].strip()
        return token

    # 3) Cookie access_token
    access_cookie = request.cookies.get("access_token")
    if access_cookie:
        return access_cookie.strip()

    return None


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> db_models.UserDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = _get_token_from_request(request)
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_username(db, username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: db_models.UserDB = Depends(get_current_user),
) -> db_models.UserDB:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )
    return current_user


# ==============================
# Controle de permissões por role
# ==============================
def require_roles(roles: List[db_models.UserRole]):
    """
    Cria uma dependência que obriga o usuário a ter uma das roles especificadas.
    Usa Enum UserRole (ADMIN, GESTOR, LEITOR).
    """
    def dependency(
        current_user: db_models.UserDB = Depends(get_current_active_user),
    ) -> db_models.UserDB:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissões insuficientes",
            )
        return current_user
    return dependency


# ==============================
# Atalhos de permissão
# ==============================
admin_only = require_roles([db_models.UserRole.ADMIN])

admin_ou_gestor = require_roles([
    db_models.UserRole.ADMIN,
    db_models.UserRole.GESTOR,
])


# ==============================
# Login handler (usado em /token)
# ==============================
from fastapi.security import OAuth2PasswordRequestForm  # import aqui para evitar ciclo

def get_login_route():
    async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db),
    ):
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username ou senha incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token(
            data={"sub": user.username, "role": user.role.value}
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    return login_for_access_token
