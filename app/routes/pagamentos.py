from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.db_models import PagamentoDB, CreditoDB
from app.services.juros import calcular_estado
from app.services.pdf import gerar_comprovativo_pagamento_pdf

router = APIRouter()


# =========================
# DB dependency
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# Helpers
# =========================
def _pagamento_to_dict(p: PagamentoDB) -> dict:
    atendente_nome: Optional[str] = None
    try:
        if getattr(p, "atendente", None) is not None:
            atendente_nome = p.atendente.nome
    except Exception:
        atendente_nome = None

    return {
        "id_pagamento": p.id_pagamento,
        "nr_comprovativo": p.nr_comprovativo,
        "id_credito": p.id_credito,
        "data_pagamento": p.data_pagamento,
        "valor_pago_no_dia": float(p.valor_pago_no_dia or 0),
        "forma_pagamento": p.forma_pagamento,
        "observacao": p.observacao,
        "emitido_em": p.emitido_em,
        "id_atendente": p.id_atendente,
        "atendente_nome": atendente_nome,
    }


def _recalcular_credito(credito: CreditoDB, db: Session):
    pagamentos = (
        db.query(PagamentoDB)
        .filter(PagamentoDB.id_credito == credito.id_credito)
        .all()
    )

    total_pago = sum(float(p.valor_pago_no_dia or 0) for p in pagamentos)
    credito.valor_pago = total_pago

    if credito.valor_total_reembolsar is None:
        credito.valor_total_reembolsar = credito.valor_pago

    credito.saldo_em_aberto = max(
        0.0,
        float(credito.valor_total_reembolsar) - float(credito.valor_pago),
    )

    credito.estado = calcular_estado(
        credito.data_fim,
        credito.saldo_em_aberto,
        hoje=date.today(),
    )


def _parse_data_pagamento(value):
    # Aceita date, "YYYY-MM-DD" ou "DD/MM/YYYY"
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("data_pagamento inválida")

    value = value.strip()

    # Tenta formato ISO: 2025-12-29
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        pass

    # Tenta formato BR/PT: 29/12/2025
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except Exception:
        pass

    raise ValueError("data_pagamento inválida (esperado YYYY-MM-DD ou DD/MM/YYYY)")


# =========================
# Rotas (SEM AUTENTICAÇÃO)
# =========================

@router.get("/credito/{id_credito}")
def listar_pagamentos_credito(id_credito: int, db: Session = Depends(get_db)):
    pagamentos = (
        db.query(PagamentoDB)
        .filter(PagamentoDB.id_credito == id_credito)
        .order_by(PagamentoDB.data_pagamento.asc(), PagamentoDB.id_pagamento.asc())
        .all()
    )
    return [_pagamento_to_dict(p) for p in pagamentos]


@router.post("")
def registrar_pagamento(data = Body(...), db: Session = Depends(get_db)):
    # data = dict enviado pelo frontend
    try:
        id_credito = int(data.get("id_credito"))
    except Exception:
        raise HTTPException(status_code=400, detail="id_credito inválido")

    credito = (
        db.query(CreditoDB)
        .filter(CreditoDB.id_credito == id_credito)
        .first()
    )
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito não encontrado")

    # Data do pagamento
    try:
        data_pagamento = _parse_data_pagamento(data.get("data_pagamento"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Valor pago
    try:
        valor_str = str(data.get("valor_pago_no_dia"))
        valor_pago = float(valor_str.replace(",", "."))
    except Exception:
        raise HTTPException(status_code=400, detail="valor_pago_no_dia inválido")

    pagamento = PagamentoDB(
        id_credito=id_credito,
        nr_comprovativo=data.get("nr_comprovativo"),
        data_pagamento=data_pagamento,
        valor_pago_no_dia=valor_pago,
        forma_pagamento=data.get("forma_pagamento"),
        observacao=data.get("observacao"),
        emitido_em=datetime.utcnow(),
        id_atendente=data.get("id_atendente"),
    )
    db.add(pagamento)

    _recalcular_credito(credito, db)

    db.commit()
    db.refresh(pagamento)
    db.refresh(credito)

    return _pagamento_to_dict(pagamento)


@router.put("/{id_pagamento}")
def atualizar_pagamento(id_pagamento: int, data = Body(...), db: Session = Depends(get_db)):
    pagamento = (
        db.query(PagamentoDB)
        .filter(PagamentoDB.id_pagamento == id_pagamento)
        .first()
    )
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    credito = (
        db.query(CreditoDB)
        .filter(CreditoDB.id_credito == pagamento.id_credito)
        .first()
    )
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito não encontrado")

    if "nr_comprovativo" in data:
        pagamento.nr_comprovativo = data.get("nr_comprovativo")

    if "data_pagamento" in data:
        try:
            pagamento.data_pagamento = _parse_data_pagamento(data.get("data_pagamento"))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    if "valor_pago_no_dia" in data:
        try:
            valor_str = str(data.get("valor_pago_no_dia"))
            pagamento.valor_pago_no_dia = float(valor_str.replace(",", "."))
        except Exception:
            raise HTTPException(status_code=400, detail="valor_pago_no_dia inválido")

    if "forma_pagamento" in data:
        pagamento.forma_pagamento = data.get("forma_pagamento")

    if "observacao" in data:
        pagamento.observacao = data.get("observacao")

    _recalcular_credito(credito, db)

    db.commit()
    db.refresh(pagamento)
    db.refresh(credito)

    return _pagamento_to_dict(pagamento)


@router.delete("/{id_pagamento}")
def apagar_pagamento(id_pagamento: int, db: Session = Depends(get_db)):
    pagamento = (
        db.query(PagamentoDB)
        .filter(PagamentoDB.id_pagamento == id_pagamento)
        .first()
    )
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    credito = (
        db.query(CreditoDB)
        .filter(CreditoDB.id_credito == pagamento.id_credito)
        .first()
    )
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito não encontrado")

    db.delete(pagamento)
    _recalcular_credito(credito, db)

    db.commit()
    db.refresh(credito)

    return {"ok": True, "msg": "Pagamento apagado com sucesso"}


@router.get("/{id_pagamento}/comprovativo")
def gerar_comprovativo(id_pagamento: int, db: Session = Depends(get_db)):
    pagamento = (
        db.query(PagamentoDB)
        .filter(PagamentoDB.id_pagamento == id_pagamento)
        .first()
    )
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    credito = (
        db.query(CreditoDB)
        .filter(CreditoDB.id_credito == pagamento.id_credito)
        .first()
    )
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito não encontrado")

    return gerar_comprovativo_pagamento_pdf(
        pagamento=_pagamento_to_dict(pagamento),
        credito={
            "id_credito": credito.id_credito,
            "nome": credito.nome,
            "telefone": credito.telefone,
            "profissao": credito.profissao,
            "valor_pago": credito.valor_pago,
            "saldo_em_aberto": credito.saldo_em_aberto,
            "valor_total_reembolsar": credito.valor_total_reembolsar,
        },
        responsavel="sistema",
    )
