# app/main.py
from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse, JSONResponse  # 👈 adicionámos JSONResponse
from fastapi import APIRouter

from app.db import Base, engine, SessionLocal
from app.deps import get_db
from app.db_models import UserDB, UserRole

from app.routes import (
    creditos,
    pagamentos,
    relatorios,
    atendentes,
    dashboard,
    admin_users,
    session,
    login_page,
)

from app.auth import get_login_route, get_password_hash

# ==============================
# CRIA TABELAS
# ==============================
Base.metadata.create_all(bind=engine)

# ==============================
# FASTAPI APP
# ==============================
app = FastAPI(title="Ukamba Microcrédito")

# ==============================
# CRIA ADMIN PADRÃO (SE NÃO EXISTIR)
# ==============================
def create_default_admin():
    db = SessionLocal()
    try:
        admin = db.query(UserDB).filter(
            UserDB.username == "alberto_admin"
        ).first()

        if not admin:
            admin = UserDB(
                username="alberto_admin",
                full_name="Administrador Geral",
                email=None,
                hashed_password=get_password_hash("Ukamba123"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print("✅ Admin alberto_admin criado com sucesso")
        else:
            print("ℹ️ Admin já existe, nada a fazer")
    finally:
        db.close()

create_default_admin()

# ==============================
# ROTA DE LOGIN (/token)
# ==============================
login_for_access_token = get_login_route()

@app.post("/token", tags=["Autenticação"])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Faz login, devolve JSON com o token
    E também grava o token em cookies:
      - Authorization = Bearer <token>
      - access_token = <token>
    """
    data = await login_for_access_token(form_data, db)

    access_token = data["access_token"]

    resp = JSONResponse(content=data)
    # Cookie completo (para debug/frontends que usam "Bearer ...")
    resp.set_cookie(
        key="Authorization",
        value=f"Bearer {access_token}",
        httponly=True,
        samesite="lax",
    )
    # Cookie apenas com o token cru
    resp.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
    )
    return resp

# ==============================
# ROTA PARA RESET DO ADMIN
# ==============================
reset_router = APIRouter()

@reset_router.post("/reset-admin-password", tags=["Admin"])
def reset_admin_password(db: Session = Depends(get_db)):
    """
    Reseta ou cria o usuário 'alberto_admin' com senha Ukamba123
    """
    user = db.query(UserDB).filter(UserDB.username == "alberto_admin").first()

    if not user:
        user = UserDB(
            username="alberto_admin",
            full_name="Administrador Geral",
            email=None,
            hashed_password=get_password_hash("Ukamba123"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
        return {
            "status": "ok",
            "mensagem": "Usuário alberto_admin criado com senha Ukamba123"
        }

    user.hashed_password = get_password_hash("Ukamba123")
    db.commit()

    return {
        "status": "ok",
        "mensagem": "Senha do alberto_admin resetada para Ukamba123"
    }

app.include_router(reset_router)

# ==============================
# INCLUIR ROUTERS
# ==============================
app.include_router(creditos.router, prefix="/creditos", tags=["Créditos"])
app.include_router(pagamentos.router, prefix="/pagamentos", tags=["Pagamentos"])
app.include_router(relatorios.router, prefix="/relatorios", tags=["Relatórios"])
app.include_router(atendentes.router, prefix="/atendentes", tags=["Atendentes"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(admin_users.router)
app.include_router(session.router)
app.include_router(login_page.router)

# ==============================
# ROTA RAIZ -> /login
# ==============================
@app.get("/")
def home():
    return RedirectResponse(url="/login", status_code=307)
