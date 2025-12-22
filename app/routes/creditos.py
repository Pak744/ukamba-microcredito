from fastapi import APIRouter, HTTPException, Body, Depends
from sqlalchemy.orm import Session
from datetime import date

from app.db import SessionLocal
from app.db_models import CreditoDB, PagamentoDB
from app import db_models
from app.auth import require_roles, admin_only, admin_ou_gestor  # ✅ agora com atalhos

from app.models.schemas import (
    CreditoCreate,
    CreditoUpdate,
    CreditoOut,
    PagamentoOut,
    CreditoPagamentosOut,
)

from app.services.juros import (
    calcular_total_reembolsar,
    calcular_prestacao_mensal,
    calcular_data_fim,
    calcular_estado,
)

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
def _credito_to_dict(c: CreditoDB) -> dict:
    return {
        "id_credito": c.id_credito,
        "nome": c.nome,
        "telefone": c.telefone,
        "profissao": c.profissao,
        "salario_mensal": float(c.salario_mensal),
        "valor_solicitado": float(c.valor_solicitado),
        "duracao_meses": int(c.duracao_meses),
        "taxa_juros": float(c.taxa_juros),
        "valor_total_reembolsar": float(c.valor_total_reembolsar),
        "prestacao_mensal": float(c.prestacao_mensal),
        "valor_pago": float(c.valor_pago),
        "saldo_em_aberto": float(c.saldo_em_aberto),
        "data_inicio": c.data_inicio,
        "data_fim": c.data_fim,
        "estado": c.estado,
        "comentario": c.comentario,
    }


def _pagamento_to_dict(p: PagamentoDB) -> dict:
    atendente_nome = None
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
        "valor_pago_no_dia": float(p.valor_pago_no_dia),
        "forma_pagamento": p.forma_pagamento,
        "observacao": p.observacao,
        "emitido_em": p.emitido_em,
        "id_atendente": p.id_atendente,
        "atendente_nome": atendente_nome,
    }


# =========================
# Rotas
# =========================
@router.get("/simular", summary="Simular Crédito")
def simular_credito(valor_solicitado: float, duracao_meses: int):
    try:
        taxa, total = calcular_total_reembolsar(valor_solicitado, duracao_meses)
        prestacao = calcular_prestacao_mensal(total, duracao_meses)
        return {
            "valor_solicitado": float(valor_solicitado),
            "duracao_meses": int(duracao_meses),
            "taxa": float(taxa),
            "taxa_percentual": round(float(taxa) * 100, 2),
            "total_reembolsar": round(float(total), 2),
            "prestacao_mensal": round(float(prestacao), 2),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", response_model=CreditoOut, summary="Criar Crédito")
def criar_credito(
    payload: CreditoCreate = Body(
        ...,
        examples={
            "exemplo_1": {
                "summary": "Exemplo de criação de crédito",
                "value": {
                    "nome": "João Manuel",
                    "telefone": "923456789",
                    "profissao": "Técnico Administrativo",
                    "salario_mensal": 180000,
                    "valor_solicitado": 300000,
                    "duracao_meses": 6,
                    "data_inicio": "2025-01-10",
                    "comentario": "Crédito para despesas escolares",
                },
            }
        },
    ),
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(admin_ou_gestor),  # ✅ só ADMIN ou GESTOR
):
    try:
        taxa, total = calcular_total_reembolsar(float(payload.valor_solicitado), int(payload.duracao_meses))
        prestacao = calcular_prestacao_mensal(float(total), int(payload.duracao_meses))
        data_fim = calcular_data_fim(payload.data_inicio, int(payload.duracao_meses))

        valor_pago = 0.0
        saldo = round(float(total) - valor_pago, 2)
        estado = calcular_estado(data_fim, saldo, hoje=date.today())

        c = CreditoDB(
            nome=payload.nome,
            telefone=payload.telefone,
            profissao=payload.profissao,
            salario_mensal=float(payload.salario_mensal),
            valor_solicitado=float(payload.valor_solicitado),
            duracao_meses=int(payload.duracao_meses),
            taxa_juros=float(taxa),
            valor_total_reembolsar=round(float(total), 2),
            prestacao_mensal=round(float(prestacao), 2),
            valor_pago=0.0,
            saldo_em_aberto=saldo,
            data_inicio=payload.data_inicio,
            data_fim=data_fim,
            estado=estado,
            comentario=payload.comentario,
        )

        db.add(c)
        db.commit()
        db.refresh(c)
        return _credito_to_dict(c)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[CreditoOut], summary="Listar Créditos")
def listar_creditos(db: Session = Depends(get_db)):
    itens = db.query(CreditoDB).order_by(CreditoDB.id_credito.desc()).all()
    return [_credito_to_dict(i) for i in itens]


@router.get("/{id_credito}", response_model=CreditoOut, summary="Obter Crédito por ID")
def obter_credito(id_credito: int, db: Session = Depends(get_db)):
    c = db.query(CreditoDB).filter(CreditoDB.id_credito == id_credito).first()
    if not c:
        raise HTTPException(status_code=404, detail="Crédito não encontrado")
    return _credito_to_dict(c)


@router.patch("/{id_credito}", response_model=CreditoOut, summary="Atualizar Crédito (PATCH)")
def atualizar_credito(
    id_credito: int,
    payload: CreditoUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.UserDB = Depends(admin_ou_gestor),  # ✅ só ADMIN ou GESTOR
):
    c = db.query(CreditoDB).filter(CreditoDB.id_credito == id_credito).first()
    if not c:
        raise HTTPException(status_code=404, detail="Crédito não encontrado")

    data = payload.model_dump(exclude_unset=True)

    # Se mexer em valor_solicitado/duracao/data_inicio, recalcula tudo
    vai_recalcular = any(k in data for k in ("valor_solicitado", "duracao_meses", "data_inicio"))

    for k, v in data.items():
        setattr(c, k, v)

    if vai_recalcular:
        try:
            taxa, total = calcular_total_reembolsar(float(c.valor_solicitado), int(c.duracao_meses))
            prestacao = calcular_prestacao_mensal(float(total), int(c.duracao_meses))
            data_fim = calcular_data_fim(c.data_inicio, int(c.duracao_meses))

            c.taxa_juros = float(taxa)
            c.valor_total_reembolsar = round(float(total), 2)
            c.prestacao_mensal = round(float(prestacao), 2)
            c.data_fim = data_fim

            # Mantém valor_pago existente e recalcula saldo/estado
            c.saldo_em_aberto = round(float(c.valor_total_reembolsar) - float(c.valor_pago), 2)
            if c.saldo_em_aberto < 0:
                c.saldo_em_aberto = 0.0
            c.estado = calcular_estado(c.data_fim, c.saldo_em_aberto, hoje=date.today())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # Sempre garante estado coerente
        c.estado = calcular_estado(c.data_fim, float(c.saldo_em_aberto), hoje=date.today())

    db.commit()
    db.refresh(c)
    return _credito_to_dict(c)


@router.delete("/{id_credito}", summary="Apagar crédito (bloqueado se tiver pagamentos)")
def apagar_credito(
    id_credito: int,
    db: Session = Depends(get_db),
    # ❌ removido current_user: db_models.UserDB = Depends(admin_only)
):
    c = db.query(CreditoDB).filter(CreditoDB.id_credito == id_credito).first()
    if not c:
        raise HTTPException(status_code=404, detail="Crédito não encontrado")

    # ✅ BLOQUEIO: se houver pagamentos, não apaga
    existe_pagamento = db.query(PagamentoDB).filter(PagamentoDB.id_credito == id_credito).first()
    if existe_pagamento:
        raise HTTPException(
            status_code=409,
            detail="Não é possível apagar: este crédito já tem pagamentos registrados.",
        )

    db.delete(c)
    db.commit()
    return {"ok": True, "msg": f"Crédito {id_credito} apagado com sucesso"}


@router.get("/{id_credito}/pagamentos", response_model=CreditoPagamentosOut, summary="Obter crédito + pagamentos")
def obter_credito_com_pagamentos(id_credito: int, db: Session = Depends(get_db)):
    c = db.query(CreditoDB).filter(CreditoDB.id_credito == id_credito).first()
    if not c:
        raise HTTPException(status_code=404, detail="Crédito não encontrado")

    pagamentos = (
        db.query(PagamentoDB)
        .filter(PagamentoDB.id_credito == id_credito)
        .order_by(PagamentoDB.data_pagamento.desc(), PagamentoDB.id_pagamento.desc())
        .all()
    )

    return {
        "credito": _credito_to_dict(c),
        "pagamentos": [_pagamento_to_dict(p) for p in pagamentos],
    }
