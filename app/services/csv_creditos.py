from io import StringIO
import csv
from datetime import date
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from app.db import SessionLocal
from app.db_models import CreditoDB


def _get_db() -> Session:
    return SessionLocal()


def _csv_response(buffer: StringIO, filename: str):
    buffer.seek(0)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "text/csv; charset=utf-8",
    }
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)


def exportar_creditos_csv() -> StreamingResponse:
    db = _get_db()
    try:
        output = StringIO()
        writer = csv.writer(output, delimiter=";")

        writer.writerow([
            "id_credito",
            "nome",
            "telefone",
            "profissao",
            "salario_mensal",
            "valor_solicitado",
            "duracao_meses",
            "taxa_juros",
            "valor_total_reembolsar",
            "prestacao_mensal",
            "valor_pago",
            "saldo_em_aberto",
            "data_inicio",
            "data_fim",
            "estado",
            "comentario",
        ])

        creditos = db.query(CreditoDB).order_by(CreditoDB.id_credito.asc()).all()
        for c in creditos:
            writer.writerow([
                c.id_credito,
                c.nome,
                c.telefone,
                c.profissao,
                f"{c.salario_mensal:.2f}",
                f"{c.valor_solicitado:.2f}",
                c.duracao_meses,
                f"{c.taxa_juros:.4f}",
                f"{c.valor_total_reembolsar:.2f}",
                f"{c.prestacao_mensal:.2f}",
                f"{c.valor_pago:.2f}",
                f"{c.saldo_em_aberto:.2f}",
                c.data_inicio.isoformat() if c.data_inicio else "",
                c.data_fim.isoformat() if c.data_fim else "",
                c.estado or "",
                (c.comentario or "").replace("\n", " ").replace(";", ","),
            ])

        filename = f"ukamba_creditos_{date.today().isoformat()}.csv"
        return _csv_response(output, filename)
    finally:
        db.close()
