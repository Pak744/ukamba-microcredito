# app/services/pdf.py
from io import BytesIO
from pathlib import Path

from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm


PROJECT_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = PROJECT_DIR / "static"


def _achar_imagem(nome_base: str) -> Path | None:
    for ext in ("png", "jpeg", "jpg"):
        p = STATIC_DIR / f"{nome_base}.{ext}"
        if p.exists():
            return p
    return None


def _fmt_kz(valor) -> str:
    try:
        v = float(valor)
    except Exception:
        v = 0.0
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")
    return f"{s} Kz"


def _desenhar_logo(c: canvas.Canvas):
    logo = _achar_imagem("logo")
    if not logo:
        return
    w = 28 * mm
    h = 28 * mm
    x = 18 * mm
    y = A4[1] - 18 * mm - h
    try:
        c.drawImage(str(logo), x, y, width=w, height=h, mask="auto")
    except Exception:
        pass


def _desenhar_carimbo(c: canvas.Canvas):
    carimbo = _achar_imagem("carimbo")
    if not carimbo:
        return
    w = 45 * mm
    h = 45 * mm
    x = A4[0] - (20 * mm) - w
    y = 18 * mm
    try:
        c.drawImage(str(carimbo), x, y, width=w, height=h, mask="auto")
    except Exception:
        pass


def gerar_comprovativo_pagamento_pdf(pagamento: dict, credito: dict, responsavel: str | None = None):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    margem_x = 18 * mm
    y = altura - 20 * mm

    _desenhar_logo(c)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(margem_x + 32 * mm, y, "Ukamba Africa - Comprovativo de Pagamento")
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    c.drawString(margem_x, y, f"Nº Comprovativo: {pagamento.get('nr_comprovativo')}")
    y -= 6 * mm
    c.drawString(margem_x, y, f"Data do pagamento: {pagamento.get('data_pagamento')}")
    y -= 6 * mm
    if responsavel:
        c.drawString(margem_x, y, f"Responsável/Atendente: {responsavel}")
        y -= 10 * mm
    else:
        y -= 4 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margem_x, y, "Dados do Crédito")
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    c.drawString(margem_x, y, f"Crédito ID: {credito.get('id_credito')}")
    y -= 6 * mm
    c.drawString(margem_x, y, f"Nome: {credito.get('nome')}")
    y -= 6 * mm
    c.drawString(margem_x, y, f"Telefone: {credito.get('telefone')}")
    y -= 6 * mm
    c.drawString(margem_x, y, f"Profissão: {credito.get('profissao')}")
    y -= 10 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margem_x, y, "Detalhes do Pagamento")
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    c.drawString(margem_x, y, f"Valor pago hoje: {_fmt_kz(pagamento.get('valor_pago_no_dia'))}")
    y -= 6 * mm
    c.drawString(margem_x, y, f"Forma de pagamento: {pagamento.get('forma_pagamento')}")
    y -= 6 * mm
    c.drawString(margem_x, y, f"Total já pago: {_fmt_kz(credito.get('valor_pago'))}")
    y -= 6 * mm
    c.drawString(margem_x, y, f"Total a reembolsar: {_fmt_kz(credito.get('valor_total_reembolsar'))}")
    y -= 6 * mm
    c.drawString(margem_x, y, f"Falta pagar (saldo): {_fmt_kz(credito.get('saldo_em_aberto'))}")

    _desenhar_carimbo(c)

    c.setFont("Helvetica-Oblique", 8)
    c.drawRightString(largura - margem_x, 10 * mm, "Documento oficial - Ukamba Microcrédito")

    c.save()
    buffer.seek(0)

    filename = f"comprovativo_{pagamento.get('nr_comprovativo','pagamento')}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)
