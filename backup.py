"""
Script de backup diário da base de dados Ukamba Microcrédito.

- Usa pg_dump para gerar um ficheiro .sql
- Mantém apenas os 7 backups mais recentes
- Envia o backup por email usando SendGrid (SMTP)

Este script é pensado para correr num Cron Job na Render
com o comando:  python backup.py
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
import smtplib
from email.message import EmailMessage
import traceback


def run_backup():
    # ==========================
    # 1) Ler variáveis de ambiente
    # ==========================
    db_url = os.getenv("DATABASE_URL")
    sendgrid_key = os.getenv("SENDGRID_API_KEY")
    email_to = os.getenv("BACKUP_EMAIL_TO")
    email_from = os.getenv("BACKUP_EMAIL_FROM", email_to)

    if not db_url:
        raise RuntimeError("DATABASE_URL não definida nas variáveis de ambiente.")
    if not sendgrid_key:
        raise RuntimeError("SENDGRID_API_KEY não definida nas variáveis de ambiente.")
    if not email_to:
        raise RuntimeError("BACKUP_EMAIL_TO não definida nas variáveis de ambiente.")

    # ==========================
    # 2) Criar pasta de backups
    # ==========================
    backups_dir = Path("backups")
    backups_dir.mkdir(exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"ukamba_backup_{timestamp}.sql"
    backup_path = backups_dir / backup_filename

    # ==========================
    # 3) Rodar pg_dump
    # ==========================
    # OBS: isto assume que o binário pg_dump está disponível no ambiente da Render.
    # Se nos logs aparecer "pg_dump: command not found", depois ajustamos a estratégia.
    print(f"🔵 A executar pg_dump para {backup_path} ...")
    result = subprocess.run(
        ["pg_dump", db_url, "-f", str(backup_path)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("❌ pg_dump falhou:")
        print(result.stderr)
        raise RuntimeError(f"pg_dump falhou: {result.stderr}")

    print("✅ pg_dump concluído com sucesso.")

    # ==========================
    # 4) Manter só os 7 últimos backups
    # ==========================
    backups = sorted(
        backups_dir.glob("ukamba_backup_*.sql"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    print(f"Encontrados {len(backups)} ficheiros de backup.")
    for old in backups[7:]:
        try:
            print(f"🧹 Apagando backup antigo: {old.name}")
            old.unlink()
        except Exception as e:
            print(f"⚠️ Não foi possível apagar {old}: {e}")

    # ==========================
    # 5) Enviar email com o backup em anexo (SendGrid SMTP)
    # ==========================
    msg = EmailMessage()
    msg["Subject"] = f"Backup Ukamba Microcrédito – {timestamp} (UTC)"
    msg["From"] = email_from
    msg["To"] = email_to

    msg.set_content(
        f"""Olá,

Segue em anexo o backup da base de dados Ukamba Microcrédito.

Data (UTC): {timestamp}
Ficheiro: {backup_filename}

Apenas os 7 backups mais recentes são mantidos no servidor.

Atenciosamente,
Sistema automático de backup Ukamba Africa
"""
    )

    with open(backup_path, "rb") as f:
        data = f.read()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="sql",
            filename=backup_filename,
        )

    print("📧 Enviando email de backup via SendGrid (SMTP)...")

    # Configuração padrão do SMTP do SendGrid
    smtp_server = "smtp.sendgrid.net"
    smtp_port = 587
    smtp_user = "apikey"  # literal mesmo, a SendGrid usa "apikey" como utilizador
    smtp_password = sendgrid_key

    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)

    print("✅ Email enviado com sucesso para", email_to)


if __name__ == "__main__":
    try:
        run_backup()
        print("✅ Backup concluído sem erros.")
    except Exception as e:
        print("❌ Erro durante o backup:")
        print(e)
        traceback.print_exc()
        # Aqui poderíamos opcionalmente tentar enviar um email de erro,
        # mas por enquanto deixamos só nos logs do Cron Job.
