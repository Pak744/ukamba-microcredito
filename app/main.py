# app/main.py
from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse

from app.db import Base, engine, SessionLocal
from app.deps import get_db
from app.db_models import UserDB

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
                password=get_password_hash("Ukamba123")
            )
            db.add(admin)
            db.commit()
            print("✅ Admin alberto_admin criado com sucesso")
        else:
            print("ℹ️ Admin já existe, nada a fazer")
    finally:
        db.close()

# executa uma vez no startup
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
    Endpoint de login.
    Usa username + password e devolve um token JWT.
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

# admin_users já tem prefix="/admin"
app.include_router(admin_users.router)

# logout
app.include_router(session.router)

# página de login
app.include_router(login_page.router)

# ==============================
# ROTA RAIZ -> /login
# ==============================
@app.get("/")
def home():
    return RedirectResponse(url="/login", status_code=307)
