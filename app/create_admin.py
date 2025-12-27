# app/create_admin.py
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.db_models import UserDB  # ou User
from passlib.context import CryptContext

# Cria contexto bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin():
    db: Session = SessionLocal()
    try:
        # Senha com menos de 72 caracteres
        raw_password = "Ukamba123"
        hashed_password = pwd_context.hash(raw_password)  # passa string diretamente
        user = UserDB(username="alberto_admin", password=hashed_password)
        db.add(user)
        db.commit()
        print("✅ Usuário alberto_admin criado com senha Ukamba123")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
