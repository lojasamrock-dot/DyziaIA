"""
calculos.py
Todas as fórmulas de índices corporais do Perfil Físico Corporal IA.

Fontes das fórmulas:
- % de gordura: método da Marinha dos EUA (US Navy Method / Hodgdon & Beckett, 1984)
- FFMI (Fat-Free Mass Index): Kouri et al., 1995
- Demais índices (estético, hipertrofia, definição, simetria) são heurísticas
  próprias, calibradas por faixas de referência comuns em avaliação física,
  não substituem avaliação por profissional de educação física / nutrição.
"""

import math


def calcular_imc(peso_kg, altura_cm):
    altura_m = altura_cm / 100
    return round(peso_kg / (altura_m ** 2), 2)


def calcular_percentual_gordura(sexo, altura_cm, pescoco_cm, cintura_cm, quadril_cm=None):
    """Método da Marinha dos EUA. Medidas em cm."""
    if sexo == "M":
        if cintura_cm <= pescoco_cm:
            return None
        bf = (
            495
            / (
                1.0324
                - 0.19077 * math.log10(cintura_cm - pescoco_cm)
                + 0.15456 * math.log10(altura_cm)
            )
            - 450
        )
    else:
        if quadril_cm is None or (cintura_cm + quadril_cm) <= pescoco_cm:
            return None
        bf = (
            495
            / (
                1.29579
                - 0.35004 * math.log10(cintura_cm + quadril_cm - pescoco_cm)
                + 0.22100 * math.log10(altura_cm)
            )
            - 450
        )
    return round(max(bf, 3.0), 2)  # piso de 3% (fisiologicamente mínimo plausível)


def calcular_massa_gorda(peso_kg, percentual_gordura):
    if percentual_gordura is None:
        return None
    return round(peso_kg * percentual_gordura / 100, 2)


def calcular_massa_magra(peso_kg, massa_gorda_kg):
    if massa_gorda_kg is None:
        return None
    return round(peso_kg - massa_gorda_kg, 2)


def calcular_ffmi(massa_magra_kg, altura_cm):
    if massa_magra_kg is None:
        return None
    altura_m = altura_cm / 100
    ffmi = massa_magra_kg / (altura_m ** 2) + 6.1 * (1.8 - altura_m)
    return round(ffmi, 2)


def calcular_razao_ombro_cintura(ombros_cm, cintura_cm):
    if not cintura_cm:
        return None
    return round(ombros_cm / cintura_cm, 3)


def calcular_razao_cintura_altura(cintura_cm, altura_cm):
    if not altura_cm:
        return None
    return round(cintura_cm / altura_cm, 3)


def calcular_simetria(braco_dir_cm, braco_esq_cm):
    """Retorna % de simetria entre 0 e 100 (100 = perfeitamente simétrico)."""
    if not braco_dir_cm or not braco_esq_cm:
        return None
    media = (braco_dir_cm + braco_esq_cm) / 2
    diferenca = abs(braco_dir_cm - braco_esq_cm)
    simetria = 100 - (diferenca / media * 100)
    return round(max(simetria, 0), 1)


def _escala_linear(valor, minimo, maximo, inverter=False):
    """Mapeia 'valor' para uma nota de 0 a 10 dentro do intervalo [minimo, maximo]."""
    if valor is None:
        return None
    nota = (valor - minimo) / (maximo - minimo) * 10
    nota = max(0, min(10, nota))
    if inverter:
        nota = 10 - nota
    return round(nota, 1)


def calcular_indice_estetico(razao_ombro_cintura, simetria_pct):
    """
    Baseado na proximidade da razão ombro/cintura à 'proporção áurea' estética
    (~1.618, referência clássica de fisiculturismo/Adonis Index) combinada
    com a simetria entre os lados do corpo.
    """
    if razao_ombro_cintura is None:
        return None
    proximidade = 10 - min(abs(razao_ombro_cintura - 1.618) * 10, 10)
    nota_simetria = (simetria_pct / 100 * 10) if simetria_pct is not None else proximidade
    indice = round(proximidade * 0.7 + nota_simetria * 0.3, 1)
    return max(0, min(10, indice))


def calcular_indice_hipertrofia(ffmi):
    """
    Referência aproximada (natural, sem uso de hormônios exógenos):
      FFMI ~16-17  -> iniciante
      FFMI ~19-20  -> intermediário
      FFMI ~22-23  -> avançado
      FFMI ~25+    -> teto natural / elite
    """
    if ffmi is None:
        return None
    return _escala_linear(ffmi, 15, 25)


def calcular_indice_definicao(percentual_gordura, sexo):
    """Quanto menor o %gordura (dentro de faixas saudáveis), maior a nota."""
    if percentual_gordura is None:
        return None
    if sexo == "M":
        return _escala_linear(percentual_gordura, 6, 25, inverter=True)
    return _escala_linear(percentual_gordura, 14, 32, inverter=True)


def calcular_nota_geral(indice_estetico, indice_hipertrofia, indice_definicao, simetria_pct):
    """Média ponderada dos índices principais -> nota geral de 0 a 10."""
    notas_pesos = []
    if indice_estetico is not None:
        notas_pesos.append((indice_estetico, 0.30))
    if indice_hipertrofia is not None:
        notas_pesos.append((indice_hipertrofia, 0.30))
    if indice_definicao is not None:
        notas_pesos.append((indice_definicao, 0.25))
    if simetria_pct is not None:
        notas_pesos.append((simetria_pct / 10, 0.15))

    if not notas_pesos:
        return None
    soma_pesos = sum(p for _, p in notas_pesos)
    nota = sum(n * p for n, p in notas_pesos) / soma_pesos
    return round(nota, 1)


def calcular_todos_indices(dados_pessoais: dict, medidas: dict) -> dict:
    """
    dados_pessoais: {sexo, altura_cm}
    medidas: {peso_kg, pescoco_cm, ombros_cm, cintura_cm, quadril_cm,
              braco_dir_cm, braco_esq_cm, ...}
    Retorna dict pronto para salvar em 'avaliacoes'.
    """
    sexo = dados_pessoais["sexo"]
    altura_cm = dados_pessoais["altura_cm"]

    imc = calcular_imc(medidas["peso_kg"], altura_cm)
    pct_gordura = calcular_percentual_gordura(
        sexo, altura_cm, medidas["pescoco_cm"], medidas["cintura_cm"],
        medidas.get("quadril_cm"),
    )
    massa_gorda = calcular_massa_gorda(medidas["peso_kg"], pct_gordura)
    massa_magra = calcular_massa_magra(medidas["peso_kg"], massa_gorda)
    ffmi = calcular_ffmi(massa_magra, altura_cm)
    razao_oc = calcular_razao_ombro_cintura(medidas["ombros_cm"], medidas["cintura_cm"])
    razao_ca = calcular_razao_cintura_altura(medidas["cintura_cm"], altura_cm)
    simetria = calcular_simetria(medidas["braco_dir_cm"], medidas["braco_esq_cm"])
    indice_estetico = calcular_indice_estetico(razao_oc, simetria)
    indice_hipertrofia = calcular_indice_hipertrofia(ffmi)
    indice_definicao = calcular_indice_definicao(pct_gordura, sexo)
    nota_geral = calcular_nota_geral(
        indice_estetico, indice_hipertrofia, indice_definicao, simetria
    )

    return {
        "imc": imc,
        "percentual_gordura": pct_gordura,
        "massa_gorda_kg": massa_gorda,
        "massa_magra_kg": massa_magra,
        "ffmi": ffmi,
        "razao_ombro_cintura": razao_oc,
        "razao_cintura_altura": razao_ca,
        "simetria_pct": simetria,
        "indice_estetico": indice_estetico,
        "indice_hipertrofia": indice_hipertrofia,
        "indice_definicao": indice_definicao,
        "nota_geral": nota_geral,
    }
