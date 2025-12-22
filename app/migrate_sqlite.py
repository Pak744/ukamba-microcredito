from sqlalchemy import text
from app.db import engine

def run():
    with engine.begin() as conn:
        # 1) criar tabela atendentes se não existir
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS atendentes (
            id_atendente INTEGER PRIMARY KEY,
            nome VARCHAR(120) NOT NULL,
            email VARCHAR(120) UNIQUE,
            ativo BOOLEAN NOT NULL DEFAULT 1,
            criado_em DATETIME NOT NULL
        );
        """))

        # 2) adicionar coluna id_atendente em pagamentos (se ainda não existir)
        cols = conn.execute(text("PRAGMA table_info(pagamentos);")).fetchall()
        nomes = {c[1] for c in cols}  # c[1] = nome da coluna

        if "id_atendente" not in nomes:
            conn.execute(text("ALTER TABLE pagamentos ADD COLUMN id_atendente INTEGER;"))

    print("✅ Migração concluída com sucesso!")

if __name__ == "__main__":
    run()
