"""
analise_ia.py
Motor de leitura corporal "estilo personal trainer".

IMPORTANTE: isto é um sistema baseado em regras (heurísticas com faixas de
referência), não um modelo de machine learning treinado. Está isolado neste
módulo justamente para que, no futuro, a função `gerar_leitura_corporal`
possa ser substituída por uma chamada a um modelo real (ex.: um classificador
treinado com dados de várias avaliações) sem mudar o resto do app.
"""

CORES = {
    "excelente": "🟢",
    "bom": "🟡",
    "regular": "🟠",
    "melhorar": "🔴",
}


def _classificar(valor, faixas):
    """
    faixas: lista de tuplas (limite_superior, rotulo) em ORDEM CRESCENTE.
    Retorna o primeiro rótulo cujo limite_superior >= valor.
    """
    for limite, rotulo in faixas:
        if valor <= limite:
            return rotulo
    return faixas[-1][1]


def _rotulo_estrutura_ossea(altura_cm, punho_estimado=None):
    # Sem medida de punho no formulário -> classificação neutra por altura
    if altura_cm < 165:
        return "Pequena"
    if altura_cm < 180:
        return "Média"
    return "Grande"


def _nivel_treino(tempo_treino_meses):
    if tempo_treino_meses is None:
        return "Não informado"
    if tempo_treino_meses < 6:
        return "Iniciante"
    if tempo_treino_meses < 24:
        return "Intermediário"
    if tempo_treino_meses < 60:
        return "Avançado"
    return "Elite"


def _avaliar_grupo(nota_0_a_10):
    if nota_0_a_10 is None:
        return "Não avaliado", CORES["regular"]
    if nota_0_a_10 >= 8.5:
        return "Excelente", CORES["excelente"]
    if nota_0_a_10 >= 7:
        return "Muito Bom", CORES["excelente"]
    if nota_0_a_10 >= 5.5:
        return "Bom", CORES["bom"]
    if nota_0_a_10 >= 4:
        return "Regular", CORES["regular"]
    return "Necessita prioridade", CORES["melhorar"]


def _nota_relativa_a_altura(medida_cm, altura_cm, razao_ref, tolerancia=0.06):
    """
    Estima uma nota 0-10 comparando (medida/altura) com uma razão de
    referência típica de bom desenvolvimento daquele grupamento.
    """
    if not medida_cm or not altura_cm:
        return None
    razao = medida_cm / altura_cm
    desvio = (razao - razao_ref) / razao_ref
    nota = 5 + (desvio / tolerancia) * 5
    return max(0, min(10, round(nota, 1)))


def gerar_leitura_corporal(dados_pessoais: dict, medidas: dict, indices: dict) -> dict:
    """
    Retorna um dicionário estruturado com a leitura completa do perfil,
    pronto para renderizar na interface (texto + cor por grupo).
    """
    altura_cm = dados_pessoais["altura_cm"]
    sexo = dados_pessoais["sexo"]

    # Razões de referência (medida_cm / altura_cm) aproximadas para físico
    # "muito bom" natural — usadas apenas como heurística de leitura.
    ref = {
        "peitoral": 0.56 if sexo == "M" else 0.52,
        "costas": 0.575 if sexo == "M" else 0.53,  # aproximado via 'ombros'
        "braco": 0.185 if sexo == "M" else 0.155,
        "antebraco": 0.155 if sexo == "M" else 0.135,
        "coxa": 0.335 if sexo == "M" else 0.335,
        "panturrilha": 0.215 if sexo == "M" else 0.205,
    }

    nota_peitoral = _nota_relativa_a_altura(medidas.get("peitoral_cm"), altura_cm, ref["peitoral"])
    nota_costas = _nota_relativa_a_altura(medidas.get("ombros_cm"), altura_cm, ref["costas"])
    braco_medio = None
    if medidas.get("braco_dir_cm") and medidas.get("braco_esq_cm"):
        braco_medio = (medidas["braco_dir_cm"] + medidas["braco_esq_cm"]) / 2
    nota_braco = _nota_relativa_a_altura(braco_medio, altura_cm, ref["braco"])
    nota_antebraco = _nota_relativa_a_altura(medidas.get("antebraco_cm"), altura_cm, ref["antebraco"])
    nota_coxa = _nota_relativa_a_altura(medidas.get("coxa_cm"), altura_cm, ref["coxa"])
    nota_panturrilha = _nota_relativa_a_altura(medidas.get("panturrilha_cm"), altura_cm, ref["panturrilha"])

    grupos = {}
    for nome, nota in [
        ("Peitoral", nota_peitoral),
        ("Costas", nota_costas),
        ("Braços", nota_braco),
        ("Antebraços", nota_antebraco),
        ("Pernas (coxa)", nota_coxa),
        ("Panturrilhas", nota_panturrilha),
    ]:
        rotulo, cor = _avaliar_grupo(nota)
        grupos[nome] = {"nota": nota, "rotulo": rotulo, "cor": cor}

    # Prioridade de treino = grupo(s) com pior nota
    grupos_validos = {k: v for k, v in grupos.items() if v["nota"] is not None}
    prioridade = None
    if grupos_validos:
        prioridade = min(grupos_validos.items(), key=lambda kv: kv[1]["nota"])[0]

    resultado = {
        "estrutura_ossea": _rotulo_estrutura_ossea(altura_cm),
        "nivel_muscular": _nivel_treino(dados_pessoais.get("tempo_treino_meses")),
        "grupos": grupos,
        "prioridade_treino": prioridade,
        "estimativa_gordura": indices.get("percentual_gordura"),
        "nota_geral": indices.get("nota_geral"),
        "pontos_fortes": [
            nome for nome, v in grupos.items()
            if v["nota"] is not None and v["nota"] >= 7
        ],
        "pontos_fracos": [
            nome for nome, v in grupos.items()
            if v["nota"] is not None and v["nota"] < 5.5
        ],
    }
    return resultado


def cor_por_nota(nota_0_a_10):
    """Utilitário para a UI: devolve o emoji de cor para qualquer nota 0-10."""
    _, cor = _avaliar_grupo(nota_0_a_10)
    return cor
