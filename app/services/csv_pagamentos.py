from io import StringIO
import csv
from datetime import date
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from app.db import SessionLocal
from app.db_models import PagamentoDB


def _get_db() -> Session:
    return SessionLocal()


def _csv_response(buffer: StringIO, filename: str):
    buffer.seek(0)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "text/csv; charset=utf-8",
    }
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)


def exportar_pagamentos_csv() -> StreamingResponse:
    db = _get_db()
    try:
        output = StringIO()
        writer = csv.writer(output, delimiter=";")

        writer.writerow([
            "id_pagamento",
            "nr_comprovativo",
            "id_credito",
            "data_pagamento",
            "valor_pago_no_dia",
            "forma_pagamento",
            "observacao",
            "emitido_em",
        ])

        pagamentos = db.query(PagamentoDB).order_by(PagamentoDB.id_pagamento.asc()).all()

        for p in pagamentos:
            writer.writerow([
                p.id_pagamento,
                p.nr_comprovativo,
                p.id_credito,
                p.data_pagamento.isoformat() if p.data_pagamento else "",
                f"{p.valor_pago_no_dia:.2f}",
                p.forma_pagamento or "",
                (p.observacao or "").replace("\n", " ").replace(";", ","),
                p.emitido_em.isoformat() if p.emitido_em else "",
            ])

        filename = f"ukamba_pagamentos_{date.today().isoformat()}.csv"
        return _csv_response(output, filename)
    finally:
        db.close()
