from fastapi import APIRouter, HTTPException, Body, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, datetime

from app.db import SessionLocal
from app.db_models import PagamentoDB, CreditoDB, AtendenteDB
from app.models.schemas import PagamentoCreate, PagamentoUpdate, PagamentoOut
from app.services.juros import calcular_estado
from app.services.pdf import gerar_comprovativo_pagamento_pdf

from app import db_models
from app.auth import admin_only, admin_ou_gestor, get_current_active_user

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
    atendente_nome = p.atendente.nome if p.atendente else None

    return {
        "id_pagamento": p.id_pagamento,
        "nr_comprovativo": p.nr_comprovativo,
        "id_credito": p.id_credito,
        "data_pagamento": p.data_pagamento,
        "valor_pago_no_dia": float(p.valor_pago_no_dia),
        "forma_pagamento": p.forma_pagamento,
        "observacao": p.observacao,
        "emitido_em": p.emitido_em,
        "id_atendente": p.id_atendente,
        "atendente_nome": atendente_nome,
    }


def _recalcular_credito(credito: CreditoDB):
    credito.valor_pago = round(float(credito.valor_pago), 2)
    credito.saldo_em_aberto = round(
        float(credito.valor_total_reembolsar) - float(credito.valor_pago), 2
    )

    if credito.saldo_em_aberto < 0:
        credito.saldo_em_aberto = 0.0

    credito.estado = calcular_estado(
        credito.data_fim,
        credito.saldo_em_aberto,
        hoje=date.today(),
    )


# =========================
# ROTAS
# =========================

@router.post(
    "",
    response_model=PagamentoOut,
    summary="Registrar Pagamento",
)
def registrar_pagamento(
    payload: PagamentoCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(admin_ou_gestor),
):
    credito = db.query(CreditoDB).filter(
        CreditoDB.id_credito == payload.id_credito
    ).first()
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito não encontrado")

    if float(payload.valor_pago_no_dia) <= 0:
        raise HTTPException(status_code=400, detail="O valor pago deve ser maior que 0")

    existe = db.query(PagamentoDB).filter(
        PagamentoDB.nr_comprovativo == payload.nr_comprovativo
    ).first()
    if existe:
        raise HTTPException(status_code=409, detail="nr_comprovativo já existe")

    pagamento = PagamentoDB(
        nr_comprovativo=payload.nr_comprovativo,
        id_credito=payload.id_credito,
        data_pagamento=payload.data_pagamento,
        valor_pago_no_dia=float(payload.valor_pago_no_dia),
        forma_pagamento=payload.forma_pagamento,
        observacao=payload.observacao,
        id_atendente=payload.id_atendente,
        emitido_em=datetime.utcnow(),
    )

    credito.valor_pago += float(payload.valor_pago_no_dia)
    _recalcular_credito(credito)

    db.add(pagamento)
    db.commit()
    db.refresh(pagamento)

    return _pagamento_to_dict(pagamento)


@router.get(
    "",
    response_model=list[PagamentoOut],
    summary="Listar Pagamentos",
)
def listar_pagamentos(
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(get_current_active_user),
):
    pagamentos = db.query(PagamentoDB).order_by(
        PagamentoDB.id_pagamento.desc()
    ).all()
    return [_pagamento_to_dict(p) for p in pagamentos]


@router.patch(
    "/{id_pagamento}",
    response_model=PagamentoOut,
    summary="Atualizar Pagamento",
)
def atualizar_pagamento(
    id_pagamento: int,
    payload: PagamentoUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(admin_ou_gestor),
):
    pagamento = db.query(PagamentoDB).filter(
        PagamentoDB.id_pagamento == id_pagamento
    ).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(pagamento, k, v)

    db.commit()
    db.refresh(pagamento)
    return _pagamento_to_dict(pagamento)


@router.delete(
    "/{id_pagamento}",
    summary="Apagar Pagamento (ADMIN)",
)
def apagar_pagamento(
    id_pagamento: int,
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(admin_only),
):
    pagamento = db.query(PagamentoDB).filter(
        PagamentoDB.id_pagamento == id_pagamento
    ).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    db.delete(pagamento)
    db.commit()
    return {"ok": True}


@router.get(
    "/{id_pagamento}/comprovativo.pdf",
    summary="Baixar comprovativo",
)
def baixar_comprovativo(
    id_pagamento: int,
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(get_current_active_user),
):
    pagamento = db.query(PagamentoDB).filter(
        PagamentoDB.id_pagamento == id_pagamento
    ).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    credito = db.query(CreditoDB).filter(
        CreditoDB.id_credito == pagamento.id_credito
    ).first()

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
        responsavel=None,
    )
