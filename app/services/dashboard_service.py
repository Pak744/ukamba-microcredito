# app/services/dashboard_service.py
from datetime import date
from typing import List, Dict, Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.db_models import CreditoDB, PagamentoDB


def _to_float(v) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def _estrutura_vazia(erro: str | None = None) -> Dict[str, Any]:
    """
    Estrutura completa do dashboard com tudo zerado.
    Devolvemos isto em vez de levantar exceção, para nunca gerar "Internal Server Error".
    """
    base: Dict[str, Any] = {
        "cards": {
            "total_concedido": 0.0,
            "total_a_receber": 0.0,
            "total_pago": 0.0,
            "total_em_aberto": 0.0,
            "total_creditos": 0,
            "ativos": 0,
            "devedores": 0,
            "concluidos": 0,
        },
        "pagamentos_recentes": [],
        "top_devedores": [],
        "totais_por_forma_pagamento": [],
        "totais_por_atendente": [],
        "pagamentos_por_mes": [],
        "proximos_vencimentos": [],
        "creditos_mes": [],
        "gerado_em": date.today().isoformat(),
    }
    if erro:
        base["erro"] = erro
    return base


def dashboard_data() -> Dict[str, Any]:
    """
    Versão simplificada e SEGURA do serviço do dashboard.
    Qualquer erro interno devolve um JSON vazio + campo "erro",
    nunca "Internal Server Error".
    """
    db: Session = SessionLocal()
    try:
        hoje = date.today()

        # 1) CARDS PRINCIPAIS
        try:
            total_creditos = db.query(CreditoDB).count()
            ativos = db.query(CreditoDB).filter(CreditoDB.estado == "Ativo").count()
            devedores = db.query(CreditoDB).filter(CreditoDB.estado == "Devedor").count()
            concluidos = (
                db.query(CreditoDB).filter(CreditoDB.estado == "Concluído").count()
            )

            total_concedido = sum(
                _to_float(x[0]) for x in db.query(CreditoDB.valor_solicitado).all()
            )
            total_a_receber = sum(
                _to_float(x[0])
                for x in db.query(CreditoDB.valor_total_reembolsar).all()
            )
            total_pago = sum(
                _to_float(x[0]) for x in db.query(CreditoDB.valor_pago).all()
            )
            total_em_aberto = sum(
                _to_float(x[0]) for x in db.query(CreditoDB.saldo_em_aberto).all()
            )

            cards = {
                "total_concedido": round(total_concedido, 2),
                "total_a_receber": round(total_a_receber, 2),
                "total_pago": round(total_pago, 2),
                "total_em_aberto": round(total_em_aberto, 2),
                "total_creditos": total_creditos,
                "ativos": ativos,
                "devedores": devedores,
                "concluidos": concluidos,
            }
        except Exception as e:
            return _estrutura_vazia(erro=f"erro nos cards: {e}")

        # 2) PAGAMENTOS RECENTES (10 últimos)
        pagamentos_recentes: List[Dict[str, Any]] = []
        try:
            rows = (
                db.query(PagamentoDB)
                .order_by(
                    PagamentoDB.data_pagamento.desc(),
                    PagamentoDB.id_pagamento.desc(),
                )
                .limit(10)
                .all()
            )
            for p in rows:
                atendente_nome = getattr(getattr(p, "atendente", None), "nome", "-")
                pagamentos_recentes.append(
                    {
                        "data": p.data_pagamento.isoformat()
                        if p.data_pagamento
                        else "",
                        "credito": p.id_credito,
                        "valor": _to_float(p.valor_pago_no_dia),
                        "forma": p.forma_pagamento,
                        "atendente": atendente_nome,
                    }
                )
        except Exception:
            pagamentos_recentes = []

        # 3) TOP DEVEDORES
        top_devedores: List[Dict[str, Any]] = []
        try:
            rows = (
                db.query(CreditoDB)
                .filter(CreditoDB.estado == "Devedor")
                .order_by(CreditoDB.saldo_em_aberto.desc())
                .limit(10)
                .all()
            )
            for c in rows:
                top_devedores.append(
                    {
                        "nome": c.nome,
                        "saldo": _to_float(c.saldo_em_aberto),
                        "id_credito": c.id_credito,
                    }
                )
        except Exception:
            top_devedores = []

        # 4) TOTAIS POR FORMA DE PAGAMENTO
        totais_por_forma_pagamento: List[Dict[str, Any]] = []
        try:
            rows = (
                db.query(
                    PagamentoDB.forma_pagamento,
                    func.sum(PagamentoDB.valor_pago_no_dia),
                )
                .group_by(PagamentoDB.forma_pagamento)
                .all()
            )
            for forma, total in rows:
                totais_por_forma_pagamento.append(
                    {"forma": forma or "(sem forma)", "total": _to_float(total)}
                )
        except Exception:
            totais_por_forma_pagamento = []

        # Retorno final (parte avançada fica vazia por enquanto)
        return {
            "cards": cards,
            "pagamentos_recentes": pagamentos_recentes,
            "top_devedores": top_devedores,
            "totais_por_forma_pagamento": totais_por_forma_pagamento,
            "totais_por_atendente": [],
            "pagamentos_por_mes": [],
            "proximos_vencimentos": [],
            "creditos_mes": [],
            "gerado_em": hoje.isoformat(),
        }

    except Exception as e:
        # Qualquer erro inesperado -> JSON vazio, nunca HTML 500
        return _estrutura_vazia(erro=f"erro inesperado: {e}")
    finally:
        db.close()
