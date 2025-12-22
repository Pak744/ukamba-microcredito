# app/routes/dashboard.py
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.db import SessionLocal
from app.db_models import CreditoDB, PagamentoDB
from app.services.dashboard_service import dashboard_data

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ==========================
# Dashboard principal
# ==========================
@router.get("", response_class=HTMLResponse, summary="Página do Dashboard (HTML)")
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/data", summary="Dados do Dashboard (JSON)")
def dashboard_json():
    """
    Mesmo que dashboard_data dê erro,
    nunca devolvemos Internal Server Error.
    """
    try:
        data = dashboard_data()

        if not isinstance(data, dict):
            return {
                "erro": "dashboard_data não retornou dict",
                "cards": {},
                "pagamentos_recentes": [],
                "top_devedores": [],
                "totais_por_forma_pagamento": [],
                "totais_por_atendente": [],
                "pagamentos_por_mes": [],
                "proximos_vencimentos": [],
                "creditos_mes": [],
                "gerado_em": "",
            }

        return data
    except Exception as e:
        return {
            "erro": f"falha na rota /dashboard/data: {e}",
            "cards": {},
            "pagamentos_recentes": [],
            "top_devedores": [],
            "totais_por_forma_pagamento": [],
            "totais_por_atendente": [],
            "pagamentos_por_mes": [],
            "proximos_vencimentos": [],
            "creditos_mes": [],
            "gerado_em": "",
        }


# ==========================
# Lista de créditos
# ==========================
@router.get(
    "/creditos",
    response_class=HTMLResponse,
    summary="Lista completa de créditos",
)
def dashboard_creditos_page(request: Request):
    """
    Tela separada para listar todos os créditos.
    URL: /dashboard/creditos
    """
    db = SessionLocal()
    try:
        creditos_db = (
            db.query(CreditoDB)
            .order_by(CreditoDB.id_credito.desc())
            .all()
        )

        creditos = []
        for c in creditos_db:
            creditos.append(
                {
                    "id_credito": c.id_credito,
                    "nome": c.nome,
                    "telefone": c.telefone,
                    "valor_solicitado": float(c.valor_solicitado or 0),
                    "valor_pago": float(c.valor_pago or 0),
                    "saldo_em_aberto": float(c.saldo_em_aberto or 0),
                    "estado": c.estado,
                }
            )

        total = len(creditos)
        ativos = sum(1 for i in creditos if i["estado"] == "Ativo")
        devedores = sum(1 for i in creditos if i["estado"] == "Devedor")
        concluidos = sum(1 for i in creditos if i["estado"] == "Concluído")

    finally:
        db.close()

    return templates.TemplateResponse(
        "creditos_lista.html",
        {
            "request": request,
            "creditos": creditos,
            "stats": {
                "total": total,
                "ativos": ativos,
                "devedores": devedores,
                "concluidos": concluidos,
            },
        },
    )


# ==========================
# Detalhe de um crédito
# ==========================
@router.get(
    "/creditos/{id_credito}",
    response_class=HTMLResponse,
    summary="Detalhe completo de um crédito",
)
def dashboard_credito_detalhe(id_credito: int, request: Request):
    db = SessionLocal()
    try:
        credito = (
            db.query(CreditoDB)
            .filter(CreditoDB.id_credito == id_credito)
            .first()
        )
        if not credito:
            raise HTTPException(status_code=404, detail="Crédito não encontrado")

        pagamentos_db = (
            db.query(PagamentoDB)
            .filter(PagamentoDB.id_credito == id_credito)
            .order_by(PagamentoDB.data_pagamento.desc())
            .all()
        )

        credito_dict = {
            "id_credito": credito.id_credito,
            "nome": credito.nome,
            "telefone": credito.telefone,
            "profissao": credito.profissao,
            "salario_mensal": float(credito.salario_mensal or 0),
            "valor_solicitado": float(credito.valor_solicitado or 0),
            "duracao_meses": credito.duracao_meses,
            "taxa_juros": float(credito.taxa_juros or 0),
            "valor_total_reembolsar": float(credito.valor_total_reembolsar or 0),
            "prestacao_mensal": float(credito.prestacao_mensal or 0),
            "valor_pago": float(credito.valor_pago or 0),
            "saldo_em_aberto": float(credito.saldo_em_aberto or 0),
            "data_inicio": credito.data_inicio,
            "data_fim": credito.data_fim,
            "estado": credito.estado,
            "comentario": credito.comentario,
        }

        pagamentos = []
        for p in pagamentos_db:
            pagamentos.append(
                {
                    "id_pagamento": p.id_pagamento,
                    "data_pagamento": p.data_pagamento,
                    "nr_comprovativo": p.nr_comprovativo,
                    "valor_pago_no_dia": float(p.valor_pago_no_dia or 0),
                    "forma_pagamento": p.forma_pagamento,
                    "atendente_nome": p.atendente.nome if p.atendente else "",
                }
            )

    finally:
        db.close()

    return templates.TemplateResponse(
        "credito_detalhe.html",
        {
            "request": request,
            "credito": credito_dict,
            "pagamentos": pagamentos,
        },
    )
