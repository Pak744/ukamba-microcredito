from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors

from app.services.dashboard_service import dashboard_data


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


def _truncate(txt: str | None, max_len: int) -> str:
    t = (txt or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _draw_header(c: canvas.Canvas, titulo: str, subtitulo: str):
    w, h = A4
    # Faixa azul
    c.setFillColor(colors.HexColor("#0D47A1"))
    c.rect(0, h - 22 * mm, w, 22 * mm, stroke=0, fill=1)

    # Logo (opcional)
    logo = _achar_imagem("logo")
    if logo:
        try:
            c.drawImage(str(logo), 10 * mm, h - 20 * mm, width=16 * mm, height=16 * mm, mask="auto")
        except Exception:
            pass

    # Texto
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(30 * mm, h - 14.5 * mm, titulo)

    c.setFont("Helvetica", 8.8)
    c.drawString(30 * mm, h - 19 * mm, subtitulo)


def _card(c: canvas.Canvas, x: float, y: float, w: float, h: float, k: str, v: str):
    # Caixa
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#E6EAF2"))
    c.roundRect(x, y, w, h, 5, stroke=1, fill=1)

    # Título
    c.setFillColor(colors.HexColor("#667085"))
    c.setFont("Helvetica", 8.5)
    c.drawString(x + 6 * mm, y + h - 8 * mm, k)

    # Valor
    c.setFillColor(colors.HexColor("#101828"))
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(x + 6 * mm, y + 6.5 * mm, v)


def _table_header(c: canvas.Canvas, x: float, y: float, w: float, title: str):
    c.setFillColor(colors.HexColor("#101828"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, title)
    c.setStrokeColor(colors.HexColor("#E6EAF2"))
    c.line(x, y - 2.5 * mm, x + w, y - 2.5 * mm)


def _draw_table(
    c: canvas.Canvas,
    x: float,
    y: float,
    col_widths: list[float],
    headers: list[str],
    rows: list[list[str]],
    row_h: float = 6.3 * mm,
):
    """
    Desenha tabela simples com cabeçalho cinza claro e linhas.
    Retorna o novo y após desenhar.
    """
    total_w = sum(col_widths)

    # Header background
    c.setFillColor(colors.HexColor("#F2F4F7"))
    c.setStrokeColor(colors.HexColor("#E6EAF2"))
    c.rect(x, y - row_h, total_w, row_h, stroke=1, fill=1)

    # Header text
    c.setFillColor(colors.HexColor("#344054"))
    c.setFont("Helvetica-Bold", 8.7)
    cx = x
    for i, htxt in enumerate(headers):
        c.drawString(cx + 2.2 * mm, y - row_h + 2.1 * mm, _truncate(htxt, 30))
        cx += col_widths[i]

    # Rows
    c.setFont("Helvetica", 8.2)
    cy = y - row_h
    for r in rows:
        cy -= row_h
        # row line
        c.setFillColor(colors.white)
        c.rect(x, cy, total_w, row_h, stroke=1, fill=1)

        c.setFillColor(colors.HexColor("#101828"))
        cx = x
        for i, cell in enumerate(r):
            c.drawString(cx + 2.2 * mm, cy + 2.1 * mm, _truncate(str(cell), 38))
            cx += col_widths[i]

        if cy < 25 * mm:
            return cy  # sinaliza falta de espaço

    return cy


def gerar_dashboard_pdf(
    mes: Optional[str] = None,
    estado: Optional[str] = None,
    atendente_id: Optional[int] = None,
):
    data = dashboard_data(mes=mes, estado=estado, atendente_id=atendente_id)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    margem_x = 14 * mm
    y = h - 26 * mm  # abaixo do header
    usable_w = w - 2 * margem_x

    filtros = data.get("filters", {})
    subtitulo = (
        f"Gerado em: {data.get('gerado_em')}  |  "
        f"mes={filtros.get('mes') or '-'}  "
        f"estado={filtros.get('estado') or '-'}  "
        f"atendente_id={filtros.get('atendente_id') or '-'}"
    )

    _draw_header(c, "Ukamba Microcrédito — Dashboard (PDF)", subtitulo)

    # =========================
    # Cards
    # =========================
    cards = data.get("cards", {})
    blocos = [
        ("Total concedido", _fmt_kz(cards.get("total_concedido"))),
        ("Total a receber", _fmt_kz(cards.get("total_a_receber"))),
        ("Total pago", _fmt_kz(cards.get("total_pago"))),
        ("Total em aberto", _fmt_kz(cards.get("total_em_aberto"))),
        ("Créditos", str(cards.get("total_creditos", 0))),
        ("Ativos", str(cards.get("ativos", 0))),
        ("Devedores", str(cards.get("devedores", 0))),
        ("Concluídos", str(cards.get("concluidos", 0))),
    ]

    card_w = (usable_w - 3 * 6 * mm) / 4
    card_h = 18 * mm
    gap = 6 * mm

    # 2 linhas de cards (4 por linha)
    y_cards_top = y - 4 * mm
    for i, (k, v) in enumerate(blocos):
        row = i // 4
        col = i % 4
        cx = margem_x + col * (card_w + gap)
        cy = y_cards_top - row * (card_h + gap) - card_h
        _card(c, cx, cy, card_w, card_h, k, v)

    y = y_cards_top - 2 * (card_h + gap) - 6 * mm

    def new_page():
        nonlocal y
        c.showPage()
        _draw_header(c, "Ukamba Microcrédito — Dashboard (PDF)", subtitulo)
        y = h - 26 * mm

    # =========================
    # Pagamentos recentes
    # =========================
    if y < 80 * mm:
        new_page()

    _table_header(c, margem_x, y, usable_w, "Pagamentos recentes")
    y -= 8 * mm

    pr = data.get("pagamentos_recentes", [])[:12]
    rows = []
    for p in pr:
        rows.append([
            str(p.get("data_pagamento", ""))[:10],
            f"#{p.get('id_credito','')}",
            _fmt_kz(p.get("valor_pago_no_dia", 0)),
            p.get("forma_pagamento") or "",
            p.get("atendente_nome") or "-",
        ])

    if not rows:
        rows = [["-", "-", "-", "-", "Sem pagamentos recentes."]]

    col_widths = [22 * mm, 20 * mm, 28 * mm, 42 * mm, usable_w - (22 + 20 + 28 + 42) * mm]
    headers = ["Data", "Crédito", "Valor", "Forma", "Atendente"]
    y_after = _draw_table(c, margem_x, y, col_widths, headers, rows, row_h=6.2 * mm)
    if y_after < 25 * mm:
        new_page()
        _table_header(c, margem_x, y, usable_w, "Pagamentos recentes (continuação)")
        y -= 8 * mm
        _draw_table(c, margem_x, y, col_widths, headers, rows, row_h=6.2 * mm)
        y = h - 26 * mm - 110 * mm
    else:
        y = y_after - 10 * mm

    # =========================
    # Top devedores
    # =========================
    if y < 70 * mm:
        new_page()

    _table_header(c, margem_x, y, usable_w, "Top devedores")
    y -= 8 * mm

    td = data.get("top_devedores", [])[:10]
    rows = []
    for d in td:
        rows.append([
            f"#{d.get('id_credito','')}",
            d.get("nome") or "",
            _fmt_kz(d.get("saldo_em_aberto", 0)),
        ])
    if not rows:
        rows = [["-", "Sem devedores.", "-"]]

    col_widths = [20 * mm, usable_w - 20 * mm - 35 * mm, 35 * mm]
    headers = ["ID", "Nome", "Saldo"]
    y_after = _draw_table(c, margem_x, y, col_widths, headers, rows)
    if y_after < 25 * mm:
        new_page()
        _table_header(c, margem_x, y, usable_w, "Top devedores (continuação)")
        y -= 8 * mm
        y_after = _draw_table(c, margem_x, y, col_widths, headers, rows)
    y = y_after - 10 * mm

    # =========================
    # Totais por forma de pagamento
    # =========================
    if y < 75 * mm:
        new_page()

    _table_header(c, margem_x, y, usable_w, "Totais por forma de pagamento")
    y -= 8 * mm

    tf = data.get("totais_por_forma_pagamento", [])[:12]
    rows = []
    for t in tf:
        rows.append([
            t.get("forma_pagamento") or "-",
            str(t.get("qtd", 0)),
            _fmt_kz(t.get("total", 0)),
        ])
    if not rows:
        rows = [["-", "0", _fmt_kz(0)]]

    col_widths = [usable_w - 22 * mm - 40 * mm, 22 * mm, 40 * mm]
    headers = ["Forma", "Qtd", "Total"]
    y_after = _draw_table(c, margem_x, y, col_widths, headers, rows)
    if y_after < 25 * mm:
        new_page()
        _table_header(c, margem_x, y, usable_w, "Totais por forma (continuação)")
        y -= 8 * mm
        y_after = _draw_table(c, margem_x, y, col_widths, headers, rows)
    y = y_after - 10 * mm

    # =========================
    # ✅ Totais por atendente (NOVO)
    # =========================
    if y < 75 * mm:
        new_page()

    _table_header(c, margem_x, y, usable_w, "Totais por atendente")
    y -= 8 * mm

    ta = data.get("totais_por_atendente", [])[:15]
    rows = []
    for t in ta:
        rows.append([
            str(t.get("id_atendente") or "-"),
            t.get("atendente_nome") or "-",
            str(t.get("qtd", 0)),
            _fmt_kz(t.get("total", 0)),
        ])
    if not rows:
        rows = [["-", "Sem dados.", "0", _fmt_kz(0)]]

    col_widths = [18 * mm, usable_w - 18 * mm - 18 * mm - 40 * mm, 18 * mm, 40 * mm]
    headers = ["ID", "Atendente", "Qtd", "Total"]
    y_after = _draw_table(c, margem_x, y, col_widths, headers, rows)
    if y_after < 25 * mm:
        new_page()
        _table_header(c, margem_x, y, usable_w, "Totais por atendente (continuação)")
        y -= 8 * mm
        _draw_table(c, margem_x, y, col_widths, headers, rows)

    # Rodapé
    c.setFillColor(colors.HexColor("#667085"))
    c.setFont("Helvetica-Oblique", 8)
    c.drawRightString(w - margem_x, 10 * mm, "Documento gerado automaticamente — Ukamba Microcrédito")

    c.save()
    buf.seek(0)

    filename = "dashboard.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(buf, media_type="application/pdf", headers=headers)
