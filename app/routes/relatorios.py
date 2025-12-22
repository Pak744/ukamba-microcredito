from fastapi import APIRouter

from app.services.relatorios import (
    resumo_geral,
    lista_devedores,
    lista_ativos,
    lista_concluidos,
    gerar_resumo_excel,
    gerar_exportacao_completa_excel,
    top_devedores,
    alertas,
    relatorio_mensal_pdf,
    extrato_credito_pdf,
)

from app.services.csv_creditos import exportar_creditos_csv
from app.services.csv_pagamentos import exportar_pagamentos_csv
from app.services.csv_extrato_credito import exportar_credito_unico_csv

router = APIRouter()


@router.get("/resumo")
def relatorio_resumo():
    return resumo_geral()


@router.get("/resumo.xlsx")
def relatorio_resumo_excel():
    return gerar_resumo_excel()


@router.get("/exportar.xlsx")
def relatorio_exportar_excel():
    return gerar_exportacao_completa_excel()


@router.get("/exportar/creditos.csv")
def relatorio_exportar_creditos_csv():
    return exportar_creditos_csv()


@router.get("/exportar/pagamentos.csv")
def relatorio_exportar_pagamentos_csv():
    return exportar_pagamentos_csv()


@router.get("/creditos/{id_credito}/extrato.csv")
def relatorio_exportar_credito_unico_csv(id_credito: int):
    return exportar_credito_unico_csv(id_credito)


@router.get("/creditos/{id_credito}/extrato.pdf")
def relatorio_extrato_credito_pdf(id_credito: int, responsavel: str | None = None):
    return extrato_credito_pdf(id_credito=id_credito, responsavel=responsavel)


@router.get("/top-devedores")
def relatorio_top_devedores(limite: int = 10):
    return top_devedores(limite=limite)


@router.get("/alertas")
def relatorio_alertas(dias: int = 7):
    return alertas(dias=dias)


@router.get("/mensal.pdf")
def baixar_relatorio_mensal_pdf(
    ano: int,
    mes: int,
    dias_alerta: int = 7,
    limite_top: int = 10,
    responsavel: str | None = None,
):
    return relatorio_mensal_pdf(
        ano=ano,
        mes=mes,
        dias_alerta=dias_alerta,
        limite_top=limite_top,
        responsavel=responsavel,
    )
