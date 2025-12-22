from datetime import date


def obter_taxa_por_meses(duracao_meses: int) -> float:
    tabela = {
        1: 0.09,
        2: 0.19,
        3: 0.30,
        4: 0.41,
        5: 0.54,
        6: 0.68,
    }
    if duracao_meses not in tabela:
        raise ValueError("Duração inválida. Permitido apenas 1 a 6 meses.")
    return tabela[duracao_meses]


def calcular_total_reembolsar(valor_solicitado: float, duracao_meses: int) -> tuple[float, float]:
    taxa = obter_taxa_por_meses(duracao_meses)
    total = valor_solicitado * (1 + taxa)
    return taxa, total


def calcular_prestacao_mensal(total_reembolsar: float, duracao_meses: int) -> float:
    if duracao_meses <= 0:
        raise ValueError("Duração inválida.")
    return total_reembolsar / duracao_meses


def adicionar_meses(data_inicio: date, meses: int) -> date:
    # Soma meses sem libs externas (seguro e suficiente para o nosso uso inicial)
    ano = data_inicio.year
    mes = data_inicio.month + meses
    dia = data_inicio.day

    while mes > 12:
        mes -= 12
        ano += 1

    # Ajuste de dia para meses menores (ex: 31 -> 30/28)
    # Regra simples: vai descendo até achar um dia válido.
    while True:
        try:
            return date(ano, mes, dia)
        except ValueError:
            dia -= 1


def calcular_data_fim(data_inicio: date, duracao_meses: int) -> date:
    return adicionar_meses(data_inicio, duracao_meses)


def calcular_estado(data_fim: date, saldo_em_aberto: float, hoje: date | None = None) -> str:
    if hoje is None:
        hoje = date.today()

    if saldo_em_aberto <= 0:
        return "Concluído"
    if hoje <= data_fim:
        return "Ativo"
    return "Devedor"
