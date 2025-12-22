# app/services/pdf_relatorios.py
from datetime import date, datetime, timedelta
from io import BytesIO
import calendar

from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.db_models import CreditoDB, PagamentoDB


def _fmt_kz(v) -> str:
    try:
        v = float(v or 0)
    except Exception:
        v = 0.0
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")
    return f"{s} Kz"


def _titulo(c: canvas.Canvas, texto: str, y: float) -> float:
    c.setFont("Helvetica-Bold", 13)
    c.drawString(25, y, texto)
    return y - 18


def _linha(c: canvas.Canvas, y: float) -> float:
    c.setLineWidth(0.5)
    c.line(25, y, A4[0] - 25, y)
    return y - 8


def gerar_relatorio_mensal_pdf(
    ano: int,
    mes: int,
    dias_alerta: int = 7,
    limite_top: int = 10,
    responsavel: str | None = None,
):
    """
    Gera um PDF mensal consolidando:
      - Créditos criados no mês
      - Pagamentos do mês
      - Top devedores
      - Créditos a vencer nos próximos X dias
    É escrito para funcionar mesmo se não houver dados (não deve dar erro 500).
    """

    # --- Garantir ano/mês válidos ---
    if mes < 1 or mes > 12:
        # Em vez de explodir, devolvemos um PDF simples explicando o erro
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, A4[1] - 60, "Relatório Mensal - Erro nos parâmetros")
        c.setFont("Helvetica", 11)
        c.drawString(50, A4[1] - 90, f"Mês inválido: {mes}. Use valores entre 1 e 12.")
        c.save()
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="relatorio_erro.pdf"'},
        )

    # --- Intervalo do mês ---
    primeiro_dia = date(ano, mes, 1)
    ultimo_dia = date(ano, mes, calendar.monthrange(ano, mes)[1])

    hoje = date.today()
    limite_venc = hoje + timedelta(days=dias_alerta)

    db: Session = SessionLocal()
    try:
        # Créditos criados no mês
        creditos_mes = (
            db.query(CreditoDB)
            .filter(
                CreditoDB.data_inicio >= primeiro_dia,
                CreditoDB.data_inicio <= ultimo_dia,
            )
            .order_by(CreditoDB.data_inicio.asc())
            .all()
        )

        # Pagamentos do mês
        pagamentos_mes = (
            db.query(PagamentoDB)
            .filter(
                PagamentoDB.data_pagamento >= primeiro_dia,
                PagamentoDB.data_pagamento <= ultimo_dia,
            )
            .order_by(PagamentoDB.data_pagamento.asc())
            .all()
        )

        # Top devedores (independente do mês)
        top_devedores = (
            db.query(CreditoDB)
            .filter(CreditoDB.saldo_em_aberto > 0)
            .order_by(CreditoDB.saldo_em_aberto.desc())
            .limit(limite_top)
            .all()
        )

        # Próximos vencimentos
        proximos_vencimentos = (
            db.query(CreditoDB)
            .filter(
                CreditoDB.saldo_em_aberto > 0,
                CreditoDB.data_fim >= hoje,
                CreditoDB.data_fim <= limite_venc,
            )
            .order_by(CreditoDB.data_fim.asc())
            .all()
        )

        # --- Montagem do PDF ---
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        largura, altura = A4

        y = altura - 40
        c.setFont("Helvetica-Bold", 15)
        c.drawString(25, y, f"Ukamba Microcrédito - Relatório Mensal")
        y -= 18
        c.setFont("Helvetica", 11)
        c.drawString(25, y, f"Mês/Ano: {mes:02d}/{ano}")
        y -= 14
        c.drawString(25, y, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        y -= 14
        if responsavel:
            c.drawString(25, y, f"Responsável: {responsavel}")
            y -= 18
        else:
            y -= 10

        y = _linha(c, y)

        # 1) Créditos criados no mês
        y = _titulo(c, "1. Créditos criados no mês", y)
        c.setFont("Helvetica", 9)
        if not creditos_mes:
            c.drawString(30, y, "Nenhum crédito criado neste mês.")
            y -= 14
        else:
            c.drawString(30, y, "ID")
            c.drawString(70, y, "Nome")
            c.drawString(250, y, "Data início")
            c.drawString(320, y, "Valor")
            c.drawString(420, y, "Estado")
            y -= 12
            for cred in creditos_mes:
                if y < 70:
                    c.showPage()
                    y = altura - 40
                c.drawString(30, y, str(cred.id_credito))
                c.drawString(70, y, (cred.nome or "")[:26])
                c.drawString(
                    250, y, cred.data_inicio.strftime("%d/%m/%Y") if cred.data_inicio else ""
                )
                c.drawRightString(400, y, _fmt_kz(cred.valor_solicitado))
                c.drawString(420, y, cred.estado or "")
                y -= 12

        y = _linha(c, y)

        # 2) Pagamentos do mês
        y = _titulo(c, "2. Pagamentos do mês", y)
        c.setFont("Helvetica", 9)
        if not pagamentos_mes:
            c.drawString(30, y, "Nenhum pagamento lançado neste mês.")
            y -= 14
        else:
            c.drawString(30, y, "Data")
            c.drawString(90, y, "Crédito")
            c.drawString(160, y, "Valor")
            c.drawString(260, y, "Forma")
            y -= 12
            for p in pagamentos_mes:
                if y < 70:
                    c.showPage()
                    y = altura - 40
                c.drawString(
                    30, y, p.data_pagamento.strftime("%d/%m/%Y") if p.data_pagamento else ""
                )
                c.drawString(90, y, f"#{p.id_credito}")
                c.drawRightString(220, y, _fmt_kz(p.valor_pago_no_dia))
                c.drawString(260, y, (p.forma_pagamento or "")[:25])
                y -= 12

        y = _linha(c, y)

        # 3) Top devedores
        y = _titulo(c, "3. Top devedores (maior saldo em aberto)", y)
        c.setFont("Helvetica", 9)
        if not top_devedores:
            c.drawString(30, y, "Não há devedores com saldo em aberto.")
            y -= 14
        else:
            c.drawString(30, y, "ID")
            c.drawString(70, y, "Nome")
            c.drawString(260, y, "Saldo em aberto")
            y -= 12
            for d in top_devedores:
                if y < 70:
                    c.showPage()
                    y = altura - 40
                c.drawString(30, y, str(d.id_credito))
                c.drawString(70, y, (d.nome or "")[:30])
                c.drawRightString(360, y, _fmt_kz(d.saldo_em_aberto))
                y -= 12

        y = _linha(c, y)

        # 4) Próximos vencimentos
        y = _titulo(c, f"4. Próximos vencimentos (próximos {dias_alerta} dias)", y)
        c.setFont("Helvetica", 9)
        if not proximos_vencimentos:
            c.drawString(30, y, "Nenhum crédito com vencimento iminente.")
            y -= 14
        else:
            c.drawString(30, y, "ID")
            c.drawString(70, y, "Nome")
            c.drawString(260, y, "Data fim")
            c.drawString(340, y, "Saldo")
            y -= 12
            for v in proximos_vencimentos:
                if y < 70:
                    c.showPage()
                    y = altura - 40
                c.drawString(30, y, str(v.id_credito))
                c.drawString(70, y, (v.nome or "")[:30])
                c.drawString(
                    260, y, v.data_fim.strftime("%d/%m/%Y") if v.data_fim else ""
                )
                c.drawRightString(420, y, _fmt_kz(v.saldo_em_aberto))
                y -= 12

        c.showPage()
        c.save()
        buffer.seek(0)

        filename = f"relatorio_mensal_{ano}_{mes:02d}.pdf"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)

    finally:
        db.close()
