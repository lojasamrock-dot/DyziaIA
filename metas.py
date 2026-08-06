"""
metas.py
Sistema inteligente de metas: dado um valor atual e um valor alvo,
estima o tempo necessário com base em taxas de progresso realistas
(referências gerais de ganho/perda por mês em treino natural).
"""

# Taxa mensal aproximada de mudança "saudável/sustentável" por tipo de medida.
# Valores conservadores, pensados para atletas naturais.
TAXA_MENSAL_CM = {
    "peitoral_cm": 0.4,
    "ombros_cm": 0.3,
    "braco_dir_cm": 0.3,
    "braco_esq_cm": 0.3,
    "antebraco_cm": 0.2,
    "coxa_cm": 0.4,
    "panturrilha_cm": 0.25,
    "cintura_cm": -0.6,  # redução de cintura (emagrecimento)
    "abdomen_cm": -0.6,
    "quadril_cm": 0.3,
    "pescoco_cm": 0.15,
}

TAXA_MENSAL_PESO_KG = 0.5  # ganho de massa magra líquida/mês, natural, conservador


def estimar_tempo_meses(campo, valor_atual, valor_meta):
    if valor_atual is None or valor_meta is None:
        return None
    diferenca = valor_meta - valor_atual
    if abs(diferenca) < 0.01:
        return 0

    if campo == "peso_kg":
        taxa = TAXA_MENSAL_PESO_KG if diferenca > 0 else -TAXA_MENSAL_PESO_KG
    else:
        taxa = TAXA_MENSAL_CM.get(campo)
        if taxa is None:
            return None
        # se a direção pedida for oposta à taxa de referência, inverte o sinal
        if (diferenca > 0) != (taxa > 0):
            taxa = -taxa

    if taxa == 0:
        return None
    meses = diferenca / taxa
    return round(abs(meses), 1)


def montar_plano_metas(metas: list) -> list:
    """
    metas: lista de dicts {campo, valor_atual, valor_meta}
    Retorna a mesma lista com 'prazo_meses' preenchido e um rótulo amigável.
    """
    NOMES_AMIGAVEIS = {
        "peso_kg": "Peso",
        "peitoral_cm": "Peitoral",
        "ombros_cm": "Ombros",
        "braco_dir_cm": "Braço direito",
        "braco_esq_cm": "Braço esquerdo",
        "antebraco_cm": "Antebraço",
        "coxa_cm": "Coxa",
        "panturrilha_cm": "Panturrilha",
        "cintura_cm": "Cintura",
        "abdomen_cm": "Abdômen",
        "quadril_cm": "Quadril",
        "pescoco_cm": "Pescoço",
    }
    plano = []
    for m in metas:
        prazo = estimar_tempo_meses(m["campo"], m["valor_atual"], m["valor_meta"])
        plano.append({
            **m,
            "nome_amigavel": NOMES_AMIGAVEIS.get(m["campo"], m["campo"]),
            "prazo_meses": prazo,
        })
    return plano


def prazo_geral(plano: list):
    """Prazo estimado do plano completo = maior prazo individual (o gargalo)."""
    prazos = [p["prazo_meses"] for p in plano if p.get("prazo_meses")]
    return max(prazos) if prazos else None
