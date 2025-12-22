# app/routes/admin_users.py
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app import db_models
from app.auth import (
    get_password_hash,
    get_current_active_user,  # para o /whoami
)

import urllib.parse

router = APIRouter(prefix="/admin", tags=["Admin"])

templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ⚠️ IMPORTANTE:
# Por enquanto NÃO vamos exigir token JWT nessas rotas HTML,
# senão o navegador mostra "Not authenticated" direto.
# A segurança prática fica assim:
# - Só o ADMIN vê o botão "Gestão de usuários" no dashboard (via /admin/whoami)
# - Gestor e Leitor não têm esse botão.
# Se alguém tentar adivinhar URL à mão, tecnicamente ainda consegue,
# mas isso já resolve bem o uso interno.


@router.get("/users")
def users_page(request: Request, db: Session = Depends(get_db)):
    users = db.query(db_models.UserDB).order_by(db_models.UserDB.id.asc()).all()
    roles = [
        ("admin", "admin"),
        ("gestor", "gestor"),
        ("leitor", "leitura"),
    ]
    ok_msg = request.query_params.get("ok")
    err_msg = request.query_params.get("err")
    return templates.TemplateResponse(
        "admin_users.html",
        {
            "request": request,
            "users": users,
            "roles": roles,
            "ok_msg": ok_msg,
            "err_msg": err_msg,
        },
    )


@router.post("/users")
def create_user(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    username = (username or "").strip()
    if not username:
        return RedirectResponse(
            "/admin/users?err=" + urllib.parse.quote_plus("Username inválido"),
            status_code=303,
        )

    try:
        existing = (
            db.query(db_models.UserDB)
            .filter(db_models.UserDB.username == username)
            .first()
        )
        if existing:
            return RedirectResponse(
                "/admin/users?err=" + urllib.parse.quote_plus("Username já existe"),
                status_code=303,
            )

        # valida role
        try:
            role_enum = db_models.UserRole(role)
        except Exception:
            role_enum = db_models.UserRole.LEITOR

        user = db_models.UserDB(
            username=username,
            full_name=username,
            email=None,
            hashed_password=get_password_hash(password),
            role=role_enum,
            is_active=True,
        )
        db.add(user)
        db.commit()
        return RedirectResponse(
            "/admin/users?ok=" + urllib.parse.quote_plus("Utilizador criado"),
            status_code=303,
        )
    except Exception as e:
        db.rollback()
        msg = f"Erro ao criar utilizador: {e}"
        return RedirectResponse(
            "/admin/users?err=" + urllib.parse.quote_plus(msg),
            status_code=303,
        )


@router.post("/users/{user_id}/toggle")
def toggle_active(user_id: int, db: Session = Depends(get_db)):
    try:
        u = db.query(db_models.UserDB).filter(db_models.UserDB.id == user_id).first()
        if not u:
            return RedirectResponse(
                "/admin/users?err="
                + urllib.parse.quote_plus("Utilizador não encontrado"),
                status_code=303,
            )

        u.is_active = not u.is_active
        db.commit()
        return RedirectResponse(
            "/admin/users?ok=" + urllib.parse.quote_plus("Estado atualizado"),
            status_code=303,
        )
    except Exception as e:
        db.rollback()
        msg = f"Erro ao atualizar estado: {e}"
        return RedirectResponse(
            "/admin/users?err=" + urllib.parse.quote_plus(msg),
            status_code=303,
        )


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        u = db.query(db_models.UserDB).filter(db_models.UserDB.id == user_id).first()
        if not u:
            return RedirectResponse(
                "/admin/users?err="
                + urllib.parse.quote_plus("Utilizador não encontrado"),
                status_code=303,
            )
        if not new_password:
            return RedirectResponse(
                "/admin/users?err="
                + urllib.parse.quote_plus("Senha inválida"),
                status_code=303,
            )

        u.hashed_password = get_password_hash(new_password)
        db.commit()
        return RedirectResponse(
            "/admin/users?ok=" + urllib.parse.quote_plus("Senha atualizada"),
            status_code=303,
        )
    except Exception as e:
        db.rollback()
        msg = f"Erro ao atualizar senha: {e}"
        return RedirectResponse(
            "/admin/users?err=" + urllib.parse.quote_plus(msg),
            status_code=303,
        )


# 👇 Endpoint usado pelo JavaScript para descobrir quem está logado
# ESTE SIM continua protegido por token (Authorization: Bearer ...)
@router.get("/whoami")
def whoami(current_user: db_models.UserDB = Depends(get_current_active_user)):
    return {
        "username": current_user.username,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
    }
