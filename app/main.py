# app/main.py
from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse

from app.db import Base, engine
from app.deps import get_db

import app.db_models  # garante que models carregam (inclui UserDB)

from app.routes import (
    creditos,
    pagamentos,
    relatorios,
    atendentes,
    dashboard,
    admin_users,
    session,
    login_page,   # ✅ nova rota da página de login
)
from app.auth import get_login_route

# Cria as tabelas (inclui a tabela "users")
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ukamba Microcrédito")

# ==============================
# ROTA DE LOGIN (/token) - API
# ==============================

login_for_access_token = get_login_route()


@app.post("/token", tags=["Autenticação"])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Endpoint de login.
    Usa username + password e devolve um token JWT.
    (Usado pela tela de login HTML e pelo /docs.)
    """
    return await login_for_access_token(form_data, db)


# ==============================
# INCLUIR ROUTERS
# ==============================

app.include_router(creditos.router, prefix="/creditos", tags=["Créditos"])
app.include_router(pagamentos.router, prefix="/pagamentos", tags=["Pagamentos"])
app.include_router(relatorios.router, prefix="/relatorios", tags=["Relatórios"])
app.include_router(atendentes.router, prefix="/atendentes", tags=["Atendentes"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

# admin_users já tem prefix="/admin" lá dentro -> fica /admin/users
app.include_router(admin_users.router)

# rota de logout /logout
app.include_router(session.router)

# rota da página de login /login
app.include_router(login_page.router)


# ==============================
# ROTA RAIZ -> redireciona para /login
# ==============================

@app.get("/")
def home():
    """
    Quando alguém entra pela primeira vez na plataforma (raiz /),
    redirecionamos para a tela de login bonita.
    """
    return RedirectResponse(url="/login", status_code=307)
