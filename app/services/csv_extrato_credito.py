from io import StringIO
import csv
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from app.db import SessionLocal
from app.db_models import CreditoDB, PagamentoDB


def _get_db() -> Session:
    return SessionLocal()


def _csv_response(buffer: StringIO, filename: str):
    buffer.seek(0)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "text/csv; charset=utf-8",
    }
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)


def exportar_credito_unico_csv(id_credito: int) -> StreamingResponse:
    db = _get_db()
    try:
        credito = (
            db.query(CreditoDB)
            .filter(CreditoDB.id_credito == id_credito)
            .first()
        )

        if not credito:
            output = StringIO()
            writer = csv.writer(output, delimiter=";")
            writer.writerow(["erro"])
            writer.writerow([f"Crédito {id_credito} não encontrado"])
            return _csv_response(output, f"ukamba_credito_{id_credito}_erro.csv")

        pagamentos = (
            db.query(PagamentoDB)
            .filter(PagamentoDB.id_credito == id_credito)
            .order_by(PagamentoDB.data_pagamento.asc())
            .all()
        )

        output = StringIO()
        writer = csv.writer(output, delimiter=";")

        # Cabeçalho do crédito
        writer.writerow(["Crédito", id_credito])
        writer.writerow(["Nome", credito.nome])
        writer.writerow(["Telefone", credito.telefone])
        writer.writerow(["Profissão", credito.profissao])
        writer.writerow(["Valor solicitado", f"{credito.valor_solicitado:.2f}"])
        writer.writerow(["Taxa juros", f"{credito.taxa_juros:.4f}"])
        writer.writerow(["Total reembolsar", f"{credito.valor_total_reembolsar:.2f}"])
        writer.writerow(["Pago", f"{credito.valor_pago:.2f}"])
        writer.writerow(["Saldo", f"{credito.saldo_em_aberto:.2f}"])
        writer.writerow(["Estado", credito.estado or ""])
        writer.writerow([])

        # Tabela de pagamentos
        writer.writerow([
            "id_pagamento",
            "nr_comprovativo",
            "data_pagamento",
            "valor_pago_no_dia",
            "forma_pagamento",
            "observacao",
            "emitido_em",
        ])

        for p in pagamentos:
            writer.writerow([
                p.id_pagamento,
                p.nr_comprovativo,
                p.data_pagamento.isoformat() if p.data_pagamento else "",
                f"{p.valor_pago_no_dia:.2f}",
                p.forma_pagamento or "",
                (p.observacao or "").replace("\n", " ").replace(";", ","),
                p.emitido_em.isoformat() if p.emitido_em else "",
            ])

        filename = f"ukamba_credito_{id_credito}_extrato.csv"
        return _csv_response(output, filename)

    finally:
        db.close()
