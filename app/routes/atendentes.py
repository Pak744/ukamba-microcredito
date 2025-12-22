from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.db_models import AtendenteDB, PagamentoDB
from app.models.schemas import AtendenteCreate, AtendenteUpdate, AtendenteOut

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _to_out(a: AtendenteDB) -> dict:
    return {
        "id_atendente": a.id_atendente,
        "nome": a.nome,
        "email": a.email,
        "ativo": a.ativo,
        "criado_em": a.criado_em,
    }


@router.post("", response_model=AtendenteOut, summary="Criar atendente")
def criar_atendente(payload: AtendenteCreate, db: Session = Depends(get_db)):
    if payload.email:
        existe = db.query(AtendenteDB).filter(AtendenteDB.email == payload.email).first()
        if existe:
            raise HTTPException(status_code=409, detail="email já existe")

    a = AtendenteDB(nome=payload.nome, email=payload.email, ativo=payload.ativo)
    db.add(a)
    db.commit()
    db.refresh(a)
    return _to_out(a)


@router.get("", response_model=list[AtendenteOut], summary="Listar atendentes")
def listar_atendentes(db: Session = Depends(get_db)):
    itens = db.query(AtendenteDB).order_by(AtendenteDB.id_atendente.desc()).all()
    return [_to_out(i) for i in itens]


@router.get("/{id_atendente}", response_model=AtendenteOut, summary="Obter atendente por ID")
def obter_atendente(id_atendente: int, db: Session = Depends(get_db)):
    a = db.query(AtendenteDB).filter(AtendenteDB.id_atendente == id_atendente).first()
    if not a:
        raise HTTPException(status_code=404, detail="Atendente não encontrado")
    return _to_out(a)


@router.patch("/{id_atendente}", response_model=AtendenteOut, summary="Atualizar atendente (PATCH)")
def atualizar_atendente(id_atendente: int, payload: AtendenteUpdate, db: Session = Depends(get_db)):
    a = db.query(AtendenteDB).filter(AtendenteDB.id_atendente == id_atendente).first()
    if not a:
        raise HTTPException(status_code=404, detail="Atendente não encontrado")

    if payload.email and payload.email != a.email:
        existe = db.query(AtendenteDB).filter(AtendenteDB.email == payload.email).first()
        if existe:
            raise HTTPException(status_code=409, detail="email já existe")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(a, k, v)

    db.commit()
    db.refresh(a)
    return _to_out(a)


@router.delete("/{id_atendente}", summary="Excluir atendente (bloqueia se tiver pagamentos)")
def excluir_atendente(id_atendente: int, db: Session = Depends(get_db)):
    a = db.query(AtendenteDB).filter(AtendenteDB.id_atendente == id_atendente).first()
    if not a:
        raise HTTPException(status_code=404, detail="Atendente não encontrado")

    # ✅ BLOQUEIO SE TIVER PAGAMENTOS (mais seguro que a.pagamentos)
    existe_pag = db.query(PagamentoDB).filter(PagamentoDB.id_atendente == id_atendente).first()
    if existe_pag:
        raise HTTPException(status_code=409, detail="Não pode apagar: atendente tem pagamentos associados")

    db.delete(a)
    db.commit()
    return {"ok": True}
