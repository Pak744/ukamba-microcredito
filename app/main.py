# adicione no final do main.py

from fastapi import APIRouter, Depends
from app.db_models import UserDB
from sqlalchemy.orm import Session
from app.deps import get_db
from app.auth import get_password_hash

reset_router = APIRouter()

@reset_router.post("/reset-admin-password", tags=["Admin"])
def reset_admin_password(db: Session = Depends(get_db)):
    """
    Reseta a senha do usuário 'alberto_admin' para Ukamba123
    """
    user = db.query(UserDB).filter(UserDB.username == "alberto_admin").first()
    if not user:
        # Se não existir, cria
        from app.db_models import UserDB
        user = UserDB(username="alberto_admin", password=get_password_hash("Ukamba123"))
        db.add(user)
        db.commit()
        return {"status": "ok", "mensagem": "Usuário alberto_admin criado com senha Ukamba123"}
    
    # Se existir, apenas reseta a senha
    user.password = get_password_hash("Ukamba123")
    db.commit()
    return {"status": "ok", "mensagem": "Senha do alberto_admin resetada para Ukamba123"}

# Inclua a rota
app.include_router(reset_router)
