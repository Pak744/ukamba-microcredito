from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional


# =========================================================
# Base comum (Pydantic v2) - evita "Config" + "model_config"
# =========================================================
class _BaseSchema(BaseModel):
    model_config = {"from_attributes": True}


# =======================
# CRÉDITOS
# =======================
class CreditoCreate(_BaseSchema):
    nome: str = Field(..., min_length=2)
    telefone: str = Field(..., min_length=6)
    profissao: str = Field(..., min_length=2)
    salario_mensal: float = Field(..., gt=0)

    valor_solicitado: float = Field(..., gt=0)
    duracao_meses: int = Field(..., ge=1, le=6)  # alinhado com juros.py (1..6)
    data_inicio: date

    comentario: Optional[str] = None


class CreditoUpdate(_BaseSchema):
    nome: Optional[str] = Field(None, min_length=2)
    telefone: Optional[str] = Field(None, min_length=6)
    profissao: Optional[str] = Field(None, min_length=2)
    salario_mensal: Optional[float] = Field(None, gt=0)

    valor_solicitado: Optional[float] = Field(None, gt=0)
    duracao_meses: Optional[int] = Field(None, ge=1, le=6)
    data_inicio: Optional[date] = None

    comentario: Optional[str] = None


class CreditoOut(_BaseSchema):
    id_credito: int

    nome: str
    telefone: str
    profissao: str
    salario_mensal: float

    valor_solicitado: float
    duracao_meses: int
    taxa_juros: float
    valor_total_reembolsar: float
    prestacao_mensal: float

    valor_pago: float
    saldo_em_aberto: float

    data_inicio: date
    data_fim: date

    estado: str
    comentario: Optional[str] = None


# =======================
# PAGAMENTOS
# =======================
class PagamentoCreate(_BaseSchema):
    id_credito: int = Field(..., gt=0)
    nr_comprovativo: str = Field(..., min_length=5)
    data_pagamento: date
    valor_pago_no_dia: float = Field(..., gt=0)
    forma_pagamento: str = Field(..., min_length=2)
    observacao: Optional[str] = None

    id_atendente: Optional[int] = Field(None, gt=0)


class PagamentoUpdate(_BaseSchema):
    nr_comprovativo: Optional[str] = Field(None, min_length=5)
    data_pagamento: Optional[date] = None
    valor_pago_no_dia: Optional[float] = Field(None, gt=0)
    forma_pagamento: Optional[str] = Field(None, min_length=2)
    observacao: Optional[str] = None

    id_atendente: Optional[int] = Field(None, gt=0)


class PagamentoOut(_BaseSchema):
    id_pagamento: int
    nr_comprovativo: str
    id_credito: int
    data_pagamento: date
    valor_pago_no_dia: float
    forma_pagamento: str
    observacao: Optional[str] = None
    emitido_em: datetime

    id_atendente: Optional[int] = None
    atendente_nome: Optional[str] = None


# ✅ ISTO É O QUE ESTAVA A FALTAR (e dava ImportError)
class CreditoPagamentosOut(_BaseSchema):
    credito: CreditoOut
    pagamentos: list[PagamentoOut]


# =======================
# ATENDENTES
# =======================
class AtendenteCreate(_BaseSchema):
    nome: str = Field(..., min_length=2)
    email: Optional[str] = Field(None, min_length=5)
    ativo: bool = True


class AtendenteUpdate(_BaseSchema):
    nome: Optional[str] = Field(None, min_length=2)
    email: Optional[str] = Field(None, min_length=5)
    ativo: Optional[bool] = None


class AtendenteOut(_BaseSchema):
    id_atendente: int
    nome: str
    email: Optional[str] = None
    ativo: bool
    criado_em: datetime
