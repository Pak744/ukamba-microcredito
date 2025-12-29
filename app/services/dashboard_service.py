# app/services/dashboard_service.py

from datetime import date, datetime
from typing import Dict, Any, List, Optional

from app.db import SessionLocal
from app.db_models import CreditoDB, PagamentoDB


def _float(value) -> float:
    """Converte valores para float sem rebentar se vier None ou string."""
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def dashboard_data() -> Dict[str, Any]:
    """
    Consolida os dados principais para o painel:
    - totais (concedido, a receber, pago, em aberto)
    - contagem de créditos (ativos, devedores, concluídos)
    - lista de pagamentos recentes
    - (outros blocos ficam por enquanto vazios, mas já com chave criada)
    """
    db = SessionLocal()
    try:
        creditos: List[CreditoDB] = db.query(CreditoDB).all()
        pagamentos: List[PagamentoDB] = db.query(PagamentoDB).all()

        # ----- Totais principais -----
        total_concedido = sum(_float(c.valor_solicitado) for c in creditos)
        total_a_receber = sum(_float(c.valor_total_reembolsar) for c in creditos)
        total_pago = sum(_float(c.valor_pago) for c in creditos)
        total_em_aberto = sum(_float(c.saldo_em_aberto) for c in creditos)

        total_creditos = len(creditos)
        ativos = sum(1 for c in creditos if c.estado == "Ativo")
        devedores = sum(1 for c in creditos if c.estado == "Devedor")
        concluidos = sum(1 for c in creditos if c.estado == "Concluído")

        cards = {
            "total_concedido": total_concedido,
            "total_a_receber": total_a_receber,
            "total_pago": total_pago,
            "total_em_aberto": total_em_aberto,
            # 👇 mesma chave que o teu dashboard antigo usa
            "total_creditos": total_creditos,
            "ativos": ativos,
            "devedores": devedores,
            "concluidos": concluidos,
        }

        # ----- Pagamentos recentes (máx. 10) -----
        pagamentos_ord = sorted(
            pagamentos,
            key=lambda p: (
                p.data_pagamento or date.min,
                p.id_pagamento,
            ),
            reverse=True,
        )[:10]

        pagamentos_recentes: List[Dict[str, Any]] = []
        for p in pagamentos_ord:
            try:
                nome_cliente: Optional[str] = None
                if getattr(p, "credito", None) is not None:
                    nome_cliente = p.credito.nome
            except Exception:
                nome_cliente = None

            data_fmt = ""
            raw_data = None
            if p.data_pagamento:
                try:
                    data_fmt = p.data_pagamento.strftime("%Y-%m-%d")
                    raw_data = p.data_pagamento.isoformat()
                except Exception:
                    data_fmt = str(p.data_pagamento)

            pagamentos_recentes.append(
                {
                    "id_pagamento": p.id_pagamento,
                    "data": raw_data or data_fmt,
                    "valor": _float(p.valor_pago_no_dia),
                    "forma": p.forma_pagamento,
                    "credito": p.id_credito,
                    "atendente": p.atendente.nome if p.atendente else None,
                }
            )

        return {
            "cards": cards,
            "pagamentos_recentes": pagamentos_recentes,
            # por enquanto vazios, mas com as chaves esperadas pelo dashboard antigo
            "top_devedores": [],
            "totais_por_forma_pagamento": [],
            "totais_por_atendente": [],
            "pagamentos_por_mes": [],
            "gerado_em": datetime.utcnow().isoformat(),
        }

    finally:
        db.close()
