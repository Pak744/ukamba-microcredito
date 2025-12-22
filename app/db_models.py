# app/db_models.py
from datetime import datetime
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    Enum,
)
from sqlalchemy.orm import relationship

from app.db import Base


# ==============================
# USUÁRIOS E PERMISSÕES
# ==============================

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    GESTOR = "gestor"
    LEITOR = "leitor"


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # login
    username = Column(String(80), unique=True, index=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=True)

    hashed_password = Column(String(255), nullable=False)

    role = Column(
        Enum(UserRole, name="user_role_enum"),
        nullable=False,
        default=UserRole.LEITOR,
    )

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ==============================
# CRÉDITOS / PAGAMENTOS
# ==============================

class CreditoDB(Base):
    __tablename__ = "creditos"

    id_credito = Column(Integer, primary_key=True, index=True)

    nome = Column(String(120), nullable=False)
    telefone = Column(String(50), nullable=False)
    profissao = Column(String(120), nullable=False)
    salario_mensal = Column(Float, nullable=False)

    valor_solicitado = Column(Float, nullable=False)
    duracao_meses = Column(Integer, nullable=False)
    taxa_juros = Column(Float, nullable=False)

    valor_total_reembolsar = Column(Float, nullable=False)
    prestacao_mensal = Column(Float, nullable=False)

    valor_pago = Column(Float, nullable=False, default=0.0)
    saldo_em_aberto = Column(Float, nullable=False)

    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)

    # Ativo / Devedor / Concluído
    estado = Column(String(30), nullable=False)
    comentario = Column(Text, nullable=True)

    pagamentos = relationship(
        "PagamentoDB",
        back_populates="credito",
        cascade="all, delete-orphan",
    )


class AtendenteDB(Base):
    __tablename__ = "atendentes"

    id_atendente = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(120), nullable=True, unique=True, index=True)
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)

    pagamentos = relationship("PagamentoDB", back_populates="atendente")


class PagamentoDB(Base):
    __tablename__ = "pagamentos"

    id_pagamento = Column(Integer, primary_key=True, index=True)
    nr_comprovativo = Column(String(50), nullable=False, unique=True, index=True)

    id_credito = Column(
        Integer,
        ForeignKey("creditos.id_credito"),
        nullable=False,
        index=True,
    )
    data_pagamento = Column(Date, nullable=False)

    valor_pago_no_dia = Column(Float, nullable=False)
    forma_pagamento = Column(String(80), nullable=False)
    observacao = Column(Text, nullable=True)

    # quem atendeu / imprimiu
    id_atendente = Column(
        Integer,
        ForeignKey("atendentes.id_atendente"),
        nullable=True,
        index=True,
    )

    emitido_em = Column(DateTime, nullable=False, default=datetime.utcnow)

    credito = relationship("CreditoDB", back_populates="pagamentos")
    atendente = relationship("AtendenteDB", back_populates="pagamentos")
