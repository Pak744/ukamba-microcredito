# app/db.py
import os
import logging
from urllib.parse import urlparse

from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base

# --------------------------------------------------------------------
# Escolha da DATABASE_URL
# --------------------------------------------------------------------
# Se existir DATABASE_URL (Render), usa Postgres.
# Se não existir, usa o SQLite local (ukamba.db).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ukamba.db")

# Descobrir se estamos em SQLite ou Postgres (sem vazar senha)
parsed = urlparse(DATABASE_URL)

if DATABASE_URL.startswith("sqlite"):
    logging.warning("DB BACKEND: usando SQLite em %s", DATABASE_URL)
else:
    # Não logamos senha; só host e nome da base
    host = parsed.hostname
    db_name = (parsed.path or "").lstrip("/")
    logging.warning(
        "DB BACKEND: usando Postgres host=%s db=%s (schema microcredito)",
        host,
        db_name,
    )

# --------------------------------------------------------------------
# Parâmetros extra apenas para SQLite
# --------------------------------------------------------------------
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Cria o engine
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Se for Postgres, cria o schema "microcredito" (se ainda não existir)
if not DATABASE_URL.startswith("sqlite"):
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS microcredito"))

# Define o metadata:
# - SQLite: schema padrão
# - Postgres: usa schema "microcredito"
if DATABASE_URL.startswith("sqlite"):
    metadata = MetaData()
else:
    metadata = MetaData(schema="microcredito")

# Base para todos os modelos
Base = declarative_base(metadata=metadata)

# Sessões de BD
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
