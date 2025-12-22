# app/auth.py
import os
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.deps import get_db
from app import db_models

import hashlib


"""
Módulo de autenticação e autorização da plataforma de microcrédito.

Usuários e papéis (roles):
- admin  -> tudo (criar, editar, apagar, ver relatórios, gerir usuários)
- gestor -> criar créditos, registrar pagamentos, ver dashboards e relatórios
- leitor -> apenas leitura (dashboard, relatórios, lista de créditos)
"""

# 🔐 IMPORTANTE:
# Em produção a chave vem da variável de ambiente SECRET_KEY (Render, etc.).
# Em desenvolvimento local, se não existir, usa o default abaixo.
SECRET_KEY = os.getenv("SECRET_KEY", "COLOQUE_AQUI_UMA_CHAVE_BEM_SECRETA_E_GRANDE")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 horas

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# ==============================
# Utilitários de senha (SHA-256)
# ==============================
def _hash_sha256(password: str) -> str:
    """
    Gera um hash SHA-256 em formato hexadecimal.
    Sem limite de tamanho de senha.
    """
    if password is None:
        password = ""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha em texto simples corresponde ao hash armazenado.
    """
    return _hash_sha256(plain_password) == hashed_password


def get_password_hash(password: str) -> str:
    """
    Gera o hash da senha para ser guardado na base de dados.
    """
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
# Dependências
# ==============================
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> db_models.UserDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: db_models.UserDB = Depends(get_current_user),
) -> db_models.UserDB:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário inativo.",
        )
    return current_user


def require_roles(roles: List[db_models.UserRole]):
    def dependency(
        current_user: db_models.UserDB = Depends(get_current_active_user),
    ) -> db_models.UserDB:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissões insuficientes para esta operação.",
            )
        return current_user
    return dependency


# ==============================
# Atalhos de permissão por papel
# ==============================
# admin_only     -> apenas ADMIN
# admin_ou_gestor -> ADMIN ou GESTOR
admin_only = require_roles([db_models.UserRole.ADMIN])
admin_ou_gestor = require_roles([
    db_models.UserRole.ADMIN,
    db_models.UserRole.GESTOR,
])


# ==============================
# Login handler usado pelo main.py
# ==============================
def get_login_route():
    async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db),
    ):
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username ou senha incorretos.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token(
            data={"sub": user.username, "role": user.role.value}
        )
        return {"access_token": access_token, "token_type": "bearer"}

    return login_for_access_token
