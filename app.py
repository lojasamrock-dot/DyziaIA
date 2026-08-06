"""
app.py
Perfil Físico Corporal IA Premium — v1.0
Streamlit app: login, cadastro de medidas, índices automáticos, leitura por IA
(baseada em regras), radar corporal, evolução histórica, fotos, metas e
relatório em PDF.

Para rodar:
    pip install -r requirements.txt
    streamlit run app.py
"""

import os
from datetime import datetime
from io import BytesIO

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import database as db
import calculos
import analise_ia
import metas as metas_mod
from gerador_pdf import gerar_relatorio_pdf

# ----------------------------------------------------------------------------
# Configuração inicial
# ----------------------------------------------------------------------------

st.set_page_config(
    page_title="Perfil Físico Corporal IA",
    page_icon="💪",
    layout="wide",
)

db.init_db()

PASTA_FOTOS = os.path.join(os.path.dirname(__file__), "fotos_usuarios")
os.makedirs(PASTA_FOTOS, exist_ok=True)

CAMPOS_MEDIDAS = [
    ("peso_kg", "Peso (kg)"),
    ("pescoco_cm", "Pescoço (cm)"),
    ("ombros_cm", "Ombros (cm)"),
    ("peitoral_cm", "Peitoral (cm)"),
    ("cintura_cm", "Cintura (cm)"),
    ("abdomen_cm", "Abdômen (cm)"),
    ("quadril_cm", "Quadril (cm)"),
    ("braco_dir_cm", "Braço direito (cm)"),
    ("braco_esq_cm", "Braço esquerdo (cm)"),
    ("antebraco_cm", "Antebraço (cm)"),
    ("coxa_cm", "Coxa (cm)"),
    ("panturrilha_cm", "Panturrilha (cm)"),
]


# ----------------------------------------------------------------------------
# CSS - cards, gauges visuais
# ----------------------------------------------------------------------------

def injetar_css():
    st.markdown(
        """
        <style>
        .card {
            background: linear-gradient(145deg, #111827, #0B0F19);
            border: 1px solid #1F2A44;
            border-radius: 14px;
            padding: 18px 20px;
            margin-bottom: 14px;
            box-shadow: 0 0 18px rgba(31,111,235,0.08);
        }
        .card h4 { margin: 0 0 6px 0; color: #9CB4E8; font-size: 0.85rem;
                    text-transform: uppercase; letter-spacing: .05em;}
        .card .valor { font-size: 1.6rem; font-weight: 700; color: #E5E7EB; }
        .badge-verde {color:#22C55E; font-weight:600;}
        .badge-amarelo {color:#EAB308; font-weight:600;}
        .badge-laranja {color:#F97316; font-weight:600;}
        .badge-vermelho {color:#EF4444; font-weight:600;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def card(titulo, valor, sufixo=""):
    st.markdown(
        f'<div class="card"><h4>{titulo}</h4>'
        f'<div class="valor">{valor}{sufixo}</div></div>',
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------------
# Login / Cadastro
# ----------------------------------------------------------------------------

def tela_login():
    st.title("💪 Perfil Físico Corporal IA — Premium")
    st.caption("Seu personal trainer digital: medidas, índices, IA e evolução em um só lugar.")

    aba_login, aba_cadastro = st.tabs(["Entrar", "Criar conta"])

    with aba_login:
        with st.form("form_login"):
            username = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            enviar = st.form_submit_button("Entrar", use_container_width=True)
            if enviar:
                usuario = db.autenticar(username, senha)
                if usuario:
                    st.session_state["usuario"] = usuario
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")

    with aba_cadastro:
        with st.form("form_cadastro"):
            c1, c2 = st.columns(2)
            with c1:
                novo_username = st.text_input("Usuário (login)")
                nova_senha = st.text_input("Senha", type="password")
                nome = st.text_input("Nome completo")
                idade = st.number_input("Idade", min_value=10, max_value=100, value=25)
            with c2:
                sexo = st.selectbox("Sexo (para as fórmulas de composição corporal)", ["M", "F"])
                altura_cm = st.number_input("Altura (cm)", min_value=100.0, max_value=230.0, value=175.0)
                tempo_treino = st.number_input("Tempo de treino (meses)", min_value=0, max_value=600, value=12)
                natural = st.selectbox("Natural ou hormonizado", ["Natural", "Hormonizado"])
            objetivo = st.text_input("Objetivo (ex: hipertrofia, definição, saúde geral)")
            criar = st.form_submit_button("Criar conta", use_container_width=True)
            if criar:
                if not novo_username or not nova_senha or not nome:
                    st.error("Preencha usuário, senha e nome.")
                else:
                    try:
                        db.criar_usuario(
                            novo_username, nova_senha, nome, int(idade), sexo,
                            float(altura_cm), int(tempo_treino), natural, objetivo,
                        )
                        st.success("Conta criada! Vá para a aba 'Entrar'.")
                    except Exception as e:
                        st.error(f"Não foi possível criar a conta: {e}")


# ----------------------------------------------------------------------------
# Nova avaliação
# ----------------------------------------------------------------------------

def secao_nova_avaliacao(usuario):
    st.subheader("📏 Nova Avaliação — Medidas Corporais")

    with st.form("form_medidas"):
        cols = st.columns(3)
        valores = {}
        for i, (campo, rotulo) in enumerate(CAMPOS_MEDIDAS):
            with cols[i % 3]:
                valores[campo] = st.number_input(rotulo, min_value=0.0, max_value=250.0,
                                                   value=0.0, step=0.1, key=f"med_{campo}")
        salvar = st.form_submit_button("Calcular e Salvar Avaliação", use_container_width=True)

    if salvar:
        faltando = [rotulo for campo, rotulo in CAMPOS_MEDIDAS if valores[campo] == 0.0]
        if faltando:
            st.warning(f"Preencha todas as medidas antes de salvar: {', '.join(faltando)}")
            return

        dados_pessoais = {"sexo": usuario["sexo"], "altura_cm": usuario["altura_cm"],
                           "tempo_treino_meses": usuario["tempo_treino_meses"]}
        indices = calculos.calcular_todos_indices(dados_pessoais, valores)
        avaliacao_id = db.salvar_avaliacao(usuario["id"], valores, indices)
        st.session_state["ultima_avaliacao_id"] = avaliacao_id
        st.success("Avaliação salva com sucesso! Veja os resultados na aba 'Dashboard'.")


# ----------------------------------------------------------------------------
# Radar chart
# ----------------------------------------------------------------------------

def montar_radar(leitura_ia: dict, indices: dict):
    categorias = list(leitura_ia["grupos"].keys()) + ["Simetria"]
    valores = [
        (v["nota"] if v["nota"] is not None else 0) for v in leitura_ia["grupos"].values()
    ] + [((indices.get("simetria_pct") or 0) / 10)]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=valores, theta=categorias, fill="toself",
        line=dict(color="#1F6FEB"), fillcolor="rgba(31,111,235,0.35)",
        name="Perfil atual",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="#0B0F19",
            radialaxis=dict(visible=True, range=[0, 10], color="#9CB4E8"),
            angularaxis=dict(color="#E5E7EB"),
        ),
        showlegend=False,
        paper_bgcolor="#0B0F19",
        font=dict(color="#E5E7EB"),
        margin=dict(l=40, r=40, t=30, b=30),
        height=480,
    )
    return fig


def montar_gauge(titulo, valor, minimo, maximo, sufixo=""):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor if valor is not None else 0,
        number={"suffix": sufixo},
        title={"text": titulo, "font": {"size": 14, "color": "#9CB4E8"}},
        gauge={
            "axis": {"range": [minimo, maximo], "tickcolor": "#9CB4E8"},
            "bar": {"color": "#1F6FEB"},
            "bgcolor": "#111827",
            "borderwidth": 0,
        },
    ))
    fig.update_layout(
        paper_bgcolor="#0B0F19", font=dict(color="#E5E7EB"),
        height=220, margin=dict(l=20, r=20, t=40, b=10),
    )
    return fig


# ----------------------------------------------------------------------------
# Dashboard (índices, leitura IA, cores, radar, gauges)
# ----------------------------------------------------------------------------

def secao_dashboard(usuario):
    avaliacao = db.ultima_avaliacao(usuario["id"])
    if not avaliacao:
        st.info("Ainda não há avaliações salvas. Vá para 'Nova Avaliação' para começar.")
        return

    dados_pessoais = {"sexo": usuario["sexo"], "altura_cm": usuario["altura_cm"],
                       "tempo_treino_meses": usuario["tempo_treino_meses"]}
    medidas = {campo: avaliacao[campo] for campo, _ in CAMPOS_MEDIDAS}
    indices = {k: avaliacao[k] for k in [
        "imc", "percentual_gordura", "massa_gorda_kg", "massa_magra_kg", "ffmi",
        "razao_ombro_cintura", "razao_cintura_altura", "simetria_pct",
        "indice_estetico", "indice_hipertrofia", "indice_definicao", "nota_geral",
    ]}
    leitura = analise_ia.gerar_leitura_corporal(dados_pessoais, medidas, indices)
    st.session_state["_leitura_atual"] = leitura
    st.session_state["_indices_atual"] = indices
    st.session_state["_medidas_atual"] = medidas
    st.session_state["_avaliacao_atual"] = avaliacao

    st.subheader(f"📊 Dashboard — avaliação de {avaliacao['data_avaliacao'][:10]}")

    # Cards de índices principais
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: card("IMC", f'{indices["imc"]:.1f}')
    with c2: card("% Gordura", f'{indices["percentual_gordura"]:.1f}', "%")
    with c3: card("Massa Magra", f'{indices["massa_magra_kg"]:.1f}', " kg")
    with c4: card("FFMI", f'{indices["ffmi"]:.1f}')
    with c5: card("Nota Geral", f'{indices["nota_geral"]:.1f}', " /10")

    c6, c7, c8 = st.columns(3)
    with c6: card("Ombro/Cintura", f'{indices["razao_ombro_cintura"]:.2f}')
    with c7: card("Cintura/Altura", f'{indices["razao_cintura_altura"]:.2f}')
    with c8: card("Simetria", f'{indices["simetria_pct"]:.1f}', "%")

    st.divider()

    col_esq, col_dir = st.columns([1, 1])

    with col_esq:
        st.markdown("#### 🧠 Leitura do Perfil Corporal (IA)")
        st.write(f'**Estrutura óssea:** {leitura["estrutura_ossea"]}')
        st.write(f'**Nível muscular:** {leitura["nivel_muscular"]}')
        for grupo, info in leitura["grupos"].items():
            st.write(f'{info["cor"]} **{grupo}:** {info["rotulo"]}')
        st.write(f'**Estimativa de gordura:** {leitura["estimativa_gordura"]:.1f}%')
        st.write(f'**Nota Geral:** {leitura["nota_geral"]:.1f} / 10')

        if leitura["prioridade_treino"]:
            st.warning(f'🎯 Prioridade de treino sugerida: **{leitura["prioridade_treino"]}**')

        st.markdown("##### Legenda de cores")
        st.markdown(
            "🟢 Excelente &nbsp;&nbsp; 🟡 Bom &nbsp;&nbsp; 🟠 Regular &nbsp;&nbsp; 🔴 Necessita melhorar"
        )

    with col_dir:
        st.markdown("#### 🕸️ Radar Corporal")
        st.plotly_chart(montar_radar(leitura, indices), use_container_width=True)

    st.divider()
    st.markdown("#### ⏱️ Medidores")
    g1, g2, g3 = st.columns(3)
    with g1:
        st.plotly_chart(montar_gauge("Índice Estético", indices["indice_estetico"], 0, 10), use_container_width=True)
    with g2:
        st.plotly_chart(montar_gauge("Índice de Hipertrofia", indices["indice_hipertrofia"], 0, 10), use_container_width=True)
    with g3:
        st.plotly_chart(montar_gauge("Índice de Definição", indices["indice_definicao"], 0, 10), use_container_width=True)


# ----------------------------------------------------------------------------
# Evolução
# ----------------------------------------------------------------------------

def secao_evolucao(usuario):
    st.subheader("📈 Evolução")
    periodo = st.selectbox("Período", ["Hoje", "30 dias", "90 dias", "180 dias", "1 ano", "Tudo"])
    mapa_dias = {"Hoje": 1, "30 dias": 30, "90 dias": 90, "180 dias": 180, "1 ano": 365, "Tudo": None}
    avaliacoes = db.listar_avaliacoes(usuario["id"], dias=mapa_dias[periodo])

    if not avaliacoes:
        st.info("Sem avaliações no período selecionado.")
        return

    df = pd.DataFrame(avaliacoes)
    df["data_avaliacao"] = pd.to_datetime(df["data_avaliacao"])

    metricas = st.multiselect(
        "Métricas para comparar",
        options=["peso_kg", "percentual_gordura", "massa_magra_kg", "ffmi",
                 "nota_geral", "cintura_cm", "peitoral_cm", "braco_dir_cm"],
        default=["peso_kg", "percentual_gordura", "nota_geral"],
    )

    if metricas:
        fig = go.Figure()
        for m in metricas:
            fig.add_trace(go.Scatter(x=df["data_avaliacao"], y=df[m], mode="lines+markers", name=m))
        fig.update_layout(
            paper_bgcolor="#0B0F19", plot_bgcolor="#0B0F19", font=dict(color="#E5E7EB"),
            legend=dict(orientation="h"), height=450, margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Histórico completo")
    st.dataframe(df.drop(columns=["usuario_id"]), use_container_width=True)

    # Exportação Excel
    buffer_excel = BytesIO()
    with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Evolucao")
    st.download_button(
        "⬇️ Exportar Excel", data=buffer_excel.getvalue(),
        file_name=f"evolucao_{usuario['username']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ----------------------------------------------------------------------------
# Fotos
# ----------------------------------------------------------------------------

def secao_fotos(usuario):
    st.subheader("📸 Fotos — Antes / Depois")
    avaliacao = db.ultima_avaliacao(usuario["id"])
    if not avaliacao:
        st.info("Salve uma avaliação antes de anexar fotos.")
        return

    c1, c2 = st.columns(2)
    with c1:
        foto_antes = st.file_uploader("Foto 'Antes'", type=["jpg", "jpeg", "png"], key="foto_antes")
        if foto_antes:
            st.image(foto_antes, caption="Antes", use_container_width=True)
    with c2:
        foto_depois = st.file_uploader("Foto 'Depois'", type=["jpg", "jpeg", "png"], key="foto_depois")
        if foto_depois:
            st.image(foto_depois, caption="Depois", use_container_width=True)

    if st.button("Salvar fotos na avaliação atual"):
        if not foto_antes and not foto_depois:
            st.warning("Envie ao menos uma foto.")
        else:
            for arquivo, tipo in [(foto_antes, "antes"), (foto_depois, "depois")]:
                if arquivo:
                    nome_arquivo = f"{usuario['id']}_{avaliacao['id']}_{tipo}_{arquivo.name}"
                    caminho = os.path.join(PASTA_FOTOS, nome_arquivo)
                    with open(caminho, "wb") as f:
                        f.write(arquivo.getbuffer())
                    db.salvar_foto(avaliacao["id"], tipo, caminho)
            st.success("Fotos salvas.")

    # Comparação automática (heurística baseada nas medidas salvas, não em
    # visão computacional real — compara a avaliação atual com a anterior)
    st.markdown("#### 🔍 Comparação automática (baseada nas medidas)")
    avaliacoes = db.listar_avaliacoes(usuario["id"])
    if len(avaliacoes) >= 2:
        anterior, atual = avaliacoes[-2], avaliacoes[-1]
        diffs = []
        if atual["massa_magra_kg"] is not None and anterior["massa_magra_kg"] is not None:
            delta_magra = atual["massa_magra_kg"] - anterior["massa_magra_kg"]
            if delta_magra > 0.3:
                diffs.append(f"✅ Aumento de massa muscular: +{delta_magra:.1f} kg")
        if atual["percentual_gordura"] is not None and anterior["percentual_gordura"] is not None:
            delta_gordura = atual["percentual_gordura"] - anterior["percentual_gordura"]
            if delta_gordura < -0.3:
                diffs.append(f"✅ Redução de gordura corporal: {delta_gordura:.1f} p.p.")
        if atual["simetria_pct"] is not None and anterior["simetria_pct"] is not None:
            delta_simetria = atual["simetria_pct"] - anterior["simetria_pct"]
            if delta_simetria > 0.5:
                diffs.append(f"✅ Melhora na simetria corporal: +{delta_simetria:.1f}%")
        if not diffs:
            diffs.append("Sem mudanças relevantes detectadas entre as duas últimas avaliações.")
        for d in diffs:
            st.write(d)
        st.caption(
            "Nota: esta comparação usa as medidas numéricas registradas, não análise de "
            "imagem. Para postura, o ideal é observação visual das fotos lado a lado acima."
        )
    else:
        st.info("Salve pelo menos duas avaliações para ver a comparação automática.")


# ----------------------------------------------------------------------------
# Metas
# ----------------------------------------------------------------------------

def secao_metas(usuario):
    st.subheader("🎯 Sistema Inteligente de Metas")
    avaliacao = db.ultima_avaliacao(usuario["id"])
    if not avaliacao:
        st.info("Salve uma avaliação para definir metas.")
        return

    campos_meta = [("peso_kg", "Peso (kg)")] + CAMPOS_MEDIDAS[1:]  # inclui peso + medidas
    with st.form("form_metas"):
        selecionados = st.multiselect(
            "Quais medidas você quer definir metas?",
            options=[c for c, _ in campos_meta],
            format_func=lambda c: dict(campos_meta)[c],
        )
        alvos = {}
        for campo in selecionados:
            rotulo = dict(campos_meta)[campo]
            atual = avaliacao[campo]
            alvos[campo] = st.number_input(
                f"Meta para {rotulo} (atual: {atual:.1f})",
                value=float(atual), key=f"meta_{campo}",
            )
        salvar_metas = st.form_submit_button("Salvar metas e calcular prazo")

    if salvar_metas and selecionados:
        db.limpar_metas(usuario["id"])
        for campo in selecionados:
            atual = avaliacao[campo]
            meta_valor = alvos[campo]
            prazo = metas_mod.estimar_tempo_meses(campo, atual, meta_valor)
            db.salvar_meta(usuario["id"], campo, atual, meta_valor, prazo)
        st.success("Metas salvas!")

    lista_metas = db.listar_metas(usuario["id"])
    if lista_metas:
        plano = metas_mod.montar_plano_metas([
            {"campo": m["campo"], "valor_atual": m["valor_atual"], "valor_meta": m["valor_meta"]}
            for m in lista_metas
        ])
        st.session_state["_plano_metas"] = plano

        dados_tabela = []
        for p in plano:
            dados_tabela.append({
                "Item": p["nome_amigavel"],
                "Atual": f'{p["valor_atual"]:.1f}',
                "Meta": f'{p["valor_meta"]:.1f}',
                "Prazo estimado": f'{p["prazo_meses"]} meses' if p["prazo_meses"] else "-",
            })
        st.table(pd.DataFrame(dados_tabela))

        prazo_total = metas_mod.prazo_geral(plano)
        if prazo_total:
            st.info(f"⏳ Tempo estimado para atingir todas as metas: **{prazo_total} meses**")


# ----------------------------------------------------------------------------
# Relatório PDF
# ----------------------------------------------------------------------------

def secao_relatorio(usuario):
    st.subheader("📄 Relatório Premium (PDF)")
    if "_avaliacao_atual" not in st.session_state:
        st.info("Abra a aba 'Dashboard' primeiro para carregar a avaliação mais recente.")
        return

    indices = st.session_state["_indices_atual"]
    medidas = st.session_state["_medidas_atual"]
    leitura = st.session_state["_leitura_atual"]
    plano_metas = st.session_state.get("_plano_metas")

    radar_png = None
    try:
        fig_radar = montar_radar(leitura, indices)
        radar_png = fig_radar.to_image(format="png", width=900, height=900, scale=2)
    except Exception:
        st.caption(
            "⚠️ Para incluir o radar no PDF, instale o pacote 'kaleido' "
            "(pip install -U kaleido). O relatório será gerado sem o gráfico."
        )

    if st.button("Gerar Relatório PDF", use_container_width=True):
        pdf_bytes = gerar_relatorio_pdf(
            usuario=usuario, medidas=medidas, indices=indices,
            leitura_ia=leitura, plano_metas=plano_metas,
            grafico_radar_png=radar_png,
        )
        st.download_button(
            "⬇️ Baixar PDF", data=pdf_bytes,
            file_name=f"relatorio_{usuario['username']}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf", use_container_width=True,
        )


# ----------------------------------------------------------------------------
# Dados pessoais (edição)
# ----------------------------------------------------------------------------

def secao_dados_pessoais(usuario):
    st.subheader("🙋 Dados Pessoais")
    with st.form("form_dados_pessoais"):
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome", value=usuario["nome"])
            idade = st.number_input("Idade", value=usuario["idade"], min_value=10, max_value=100)
            sexo = st.selectbox("Sexo", ["M", "F"], index=0 if usuario["sexo"] == "M" else 1)
            altura_cm = st.number_input("Altura (cm)", value=float(usuario["altura_cm"]))
        with c2:
            tempo_treino = st.number_input("Tempo de treino (meses)", value=usuario["tempo_treino_meses"], min_value=0)
            natural = st.selectbox("Natural ou hormonizado", ["Natural", "Hormonizado"],
                                    index=0 if usuario["natural_hormonizado"] == "Natural" else 1)
            objetivo = st.text_input("Objetivo", value=usuario["objetivo"] or "")
        atualizar = st.form_submit_button("Salvar alterações")
        if atualizar:
            db.atualizar_usuario(
                usuario["id"], nome=nome, idade=int(idade), sexo=sexo,
                altura_cm=float(altura_cm), tempo_treino_meses=int(tempo_treino),
                natural_hormonizado=natural, objetivo=objetivo,
            )
            st.session_state["usuario"] = db.get_usuario(usuario["id"])
            st.success("Dados atualizados.")
            st.rerun()


# ----------------------------------------------------------------------------
# App principal
# ----------------------------------------------------------------------------

def app_principal():
    usuario = st.session_state["usuario"]
    injetar_css()

    with st.sidebar:
        st.markdown(f"### 👤 {usuario['nome']}")
        st.caption(f"@{usuario['username']}")
        if st.button("Sair", use_container_width=True):
            del st.session_state["usuario"]
            st.rerun()

    abas = st.tabs([
        "🙋 Dados Pessoais", "📏 Nova Avaliação", "📊 Dashboard",
        "📈 Evolução", "📸 Fotos", "🎯 Metas", "📄 Relatório PDF",
    ])

    with abas[0]:
        secao_dados_pessoais(usuario)
    with abas[1]:
        secao_nova_avaliacao(usuario)
    with abas[2]:
        secao_dashboard(usuario)
    with abas[3]:
        secao_evolucao(usuario)
    with abas[4]:
        secao_fotos(usuario)
    with abas[5]:
        secao_metas(usuario)
    with abas[6]:
        secao_relatorio(usuario)


# ----------------------------------------------------------------------------
# Ponto de entrada
# ----------------------------------------------------------------------------

if "usuario" not in st.session_state:
    tela_login()
else:
    app_principal()
