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

# Usa o mesmo diretório gravável que o banco resolveu (ver database.py).
# getattr com fallback: se por algum motivo estiver rodando uma versão de
# database.py sem esse atributo (ex.: deploy não atualizou o arquivo todo),
# o app não quebra — recalcula um diretório gravável localmente.
def _diretorio_dados_fallback():
    preferido = os.path.dirname(os.path.abspath(__file__))
    try:
        teste = os.path.join(preferido, ".write_test_app")
        with open(teste, "w") as f:
            f.write("ok")
        os.remove(teste)
        return preferido
    except Exception:
        import tempfile
        alternativo = os.path.join(tempfile.gettempdir(), "perfil_fisico_ia_dados")
        os.makedirs(alternativo, exist_ok=True)
        return alternativo


DIRETORIO_DADOS = getattr(db, "DIRETORIO_DADOS", None) or _diretorio_dados_fallback()

PASTA_FOTOS = os.path.join(DIRETORIO_DADOS, "fotos_usuarios")
os.makedirs(PASTA_FOTOS, exist_ok=True)

PASTA_FOTOS_PERFIL = os.path.join(DIRETORIO_DADOS, "fotos_perfil")
os.makedirs(PASTA_FOTOS_PERFIL, exist_ok=True)

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
# CSS - identidade visual premium (cabeçalhos centralizados, cards, tabs)
# ----------------------------------------------------------------------------

def injetar_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }

        /* Fundo geral com leve gradiente radial para dar profundidade */
        .stApp {
            background:
                radial-gradient(circle at 15% 0%, rgba(31,111,235,0.10) 0%, rgba(11,15,25,0) 45%),
                radial-gradient(circle at 85% 0%, rgba(31,111,235,0.06) 0%, rgba(11,15,25,0) 40%),
                #0B0F19;
        }

        /* Esconde o menu hambúrguer / rodapé padrão do Streamlit para visual mais limpo */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* ---------- Cabeçalho de página / seção, sempre centralizado ---------- */
        .header-wrap {
            text-align: center;
            padding: 6px 0 22px 0;
            margin-bottom: 18px;
            border-bottom: 1px solid rgba(31,42,68,0.7);
        }
        .header-eyebrow {
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: .14em;
            text-transform: uppercase;
            color: #7FA8F5;
            background: rgba(31,111,235,0.12);
            border: 1px solid rgba(31,111,235,0.35);
            border-radius: 999px;
            padding: 4px 14px;
            margin-bottom: 10px;
        }
        .header-title {
            font-size: 2.1rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #F3F6FC;
            margin: 4px 0 6px 0;
        }
        .header-subtitle {
            font-size: 0.98rem;
            color: #93A2C2;
            font-weight: 400;
            max-width: 640px;
            margin: 0 auto;
        }

        /* Cabeçalho principal (hero) da tela de login */
        .hero-wrap {
            text-align: center;
            padding: 34px 20px 26px 20px;
            margin-bottom: 8px;
        }
        .hero-logo {
            font-size: 2.6rem;
            margin-bottom: 4px;
        }
        .hero-title {
            font-size: 2.6rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(90deg, #E5E7EB, #7FA8F5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0 0 8px 0;
        }
        .hero-subtitle {
            font-size: 1.05rem;
            color: #93A2C2;
            max-width: 560px;
            margin: 0 auto 6px auto;
        }
        .hero-badge {
            display: inline-block;
            margin-top: 12px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: .12em;
            text-transform: uppercase;
            color: #0B0F19;
            background: linear-gradient(90deg, #1F6FEB, #7FA8F5);
            border-radius: 999px;
            padding: 6px 16px;
        }

        /* ---------- Cards de índices ---------- */
        .card {
            background: linear-gradient(160deg, #131A2C 0%, #0D111C 100%);
            border: 1px solid #1F2A44;
            border-radius: 16px;
            padding: 18px 20px;
            margin-bottom: 14px;
            box-shadow: 0 4px 22px rgba(0,0,0,0.25);
            transition: border-color .15s ease;
        }
        .card:hover { border-color: #1F6FEB; }
        .card h4 {
            margin: 0 0 8px 0; color: #8DA3D0; font-size: 0.72rem;
            text-transform: uppercase; letter-spacing: .09em; font-weight: 600;
        }
        .card .valor { font-size: 1.75rem; font-weight: 800; color: #F3F6FC; line-height: 1.1; }
        .card .valor .unidade { font-size: 0.95rem; font-weight: 500; color: #8DA3D0; margin-left: 3px; }

        /* ---------- Bloco de conteúdo (envolve seções, tipo "painel") ---------- */
        .panel {
            background: rgba(17,24,39,0.55);
            border: 1px solid #1F2A44;
            border-radius: 18px;
            padding: 24px 26px;
            margin-bottom: 18px;
        }
        .panel-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #F3F6FC;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* ---------- Linhas de leitura IA (grupo muscular) ---------- */
        .grupo-linha {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 14px;
            border-radius: 10px;
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(31,42,68,0.6);
            margin-bottom: 8px;
        }
        .grupo-nome { color: #C7D2E8; font-weight: 500; font-size: 0.92rem; }
        .grupo-status { font-weight: 700; font-size: 0.88rem; }
        .st-excelente { color: #22C55E; }
        .st-bom { color: #EAB308; }
        .st-regular { color: #F97316; }
        .st-melhorar { color: #EF4444; }

        .legenda-cores {
            display: flex; justify-content: center; gap: 22px; flex-wrap: wrap;
            font-size: 0.85rem; color: #93A2C2; margin-top: 10px;
        }

        /* ---------- Tabs premium ---------- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            border-bottom: 1px solid #1F2A44;
            justify-content: center;
        }
        .stTabs [data-baseweb="tab"] {
            height: 42px;
            border-radius: 10px 10px 0 0;
            color: #93A2C2;
            font-weight: 600;
            font-size: 0.92rem;
            padding: 0 18px;
        }
        .stTabs [aria-selected="true"] {
            color: #F3F6FC !important;
            background: rgba(31,111,235,0.12) !important;
            border-bottom: 2px solid #1F6FEB !important;
        }

        /* ---------- Botões ---------- */
        .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
            border-radius: 10px;
            font-weight: 600;
            border: 1px solid #1F6FEB;
        }
        .stButton > button[kind="primary"], .stFormSubmitButton > button {
            background: linear-gradient(90deg, #1F6FEB, #1257C4);
        }

        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {
            background: #0D111C;
            border-right: 1px solid #1F2A44;
        }
        .sidebar-card {
            text-align: center;
            padding: 18px 10px 20px 10px;
            border-bottom: 1px solid #1F2A44;
            margin-bottom: 16px;
        }
        .sidebar-avatar {
            width: 58px; height: 58px; border-radius: 50%;
            background: linear-gradient(135deg, #1F6FEB, #7FA8F5);
            display: flex; align-items: center; justify-content: center;
            font-size: 1.4rem; font-weight: 800; color: #0B0F19;
            margin: 0 auto 10px auto;
        }
        .sidebar-name { font-weight: 700; color: #F3F6FC; font-size: 1rem; }
        .sidebar-user { color: #7FA8F5; font-size: 0.82rem; }

        /* ---------- Tabelas / dataframes ---------- */
        [data-testid="stDataFrame"], .stTable {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #1F2A44;
        }

        /* ---------- Foto de perfil ---------- */
        .foto-perfil-box {
            background: rgba(255,255,255,0.02);
            border: 1px dashed #2A3B5C;
            border-radius: 14px;
            padding: 14px 16px;
            margin-bottom: 6px;
        }
        .foto-placeholder {
            width: 110px; height: 110px;
            border-radius: 50%;
            background: #131A2C;
            border: 1px solid #1F2A44;
            display: flex; align-items: center; justify-content: center;
            color: #6B7A9E; font-size: 0.72rem; text-align: center;
        }
        .sidebar-avatar-foto {
            width: 58px; height: 58px; border-radius: 50%;
            object-fit: cover;
            display: block; margin: 0 auto 10px auto;
            border: 2px solid #1F6FEB;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def cabecalho(titulo, subtitulo="", eyebrow=""):
    """Cabeçalho de seção, sempre centralizado — usar no topo de cada aba."""
    eyebrow_html = f'<div class="header-eyebrow">{eyebrow}</div>' if eyebrow else ""
    subtitulo_html = f'<div class="header-subtitle">{subtitulo}</div>' if subtitulo else ""
    st.markdown(
        f"""
        <div class="header-wrap">
            {eyebrow_html}
            <div class="header-title">{titulo}</div>
            {subtitulo_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def abrir_painel(titulo=""):
    if titulo:
        st.markdown(f'<div class="panel-title">{titulo}</div>', unsafe_allow_html=True)


def card(titulo, valor, sufixo=""):
    st.markdown(
        f'<div class="card"><h4>{titulo}</h4>'
        f'<div class="valor">{valor}<span class="unidade">{sufixo}</span></div></div>',
        unsafe_allow_html=True,
    )


def capturar_foto_perfil(key_prefix, foto_atual_path=None):
    """
    Widget reutilizável de foto de perfil: permite tirar foto pela câmera
    do dispositivo ou enviar um arquivo da galeria/computador.
    Retorna os bytes da nova foto escolhida (ou None se nada foi trocado).
    Mostra também uma prévia da foto atual, se houver.
    """
    st.markdown('<div class="foto-perfil-box">', unsafe_allow_html=True)
    st.markdown("**Foto de perfil**")

    col_preview, col_widget = st.columns([1, 2])
    with col_preview:
        if foto_atual_path and os.path.exists(foto_atual_path):
            st.image(foto_atual_path, width=110, caption="Atual")
        else:
            st.markdown(
                '<div class="foto-placeholder">Sem foto</div>',
                unsafe_allow_html=True,
            )

    with col_widget:
        modo = st.radio(
            "Origem da foto",
            ["Não alterar", "📷 Tirar foto agora", "📁 Enviar arquivo"],
            horizontal=True, key=f"{key_prefix}_modo",
            label_visibility="collapsed",
        )

        foto_bytes = None
        if modo == "📷 Tirar foto agora":
            captura = st.camera_input("Use a câmera do celular ou computador", key=f"{key_prefix}_camera")
            if captura:
                foto_bytes = captura.getvalue()
        elif modo == "📁 Enviar arquivo":
            arquivo = st.file_uploader(
                "Selecione uma imagem (jpg, jpeg ou png)",
                type=["jpg", "jpeg", "png"], key=f"{key_prefix}_upload",
            )
            if arquivo:
                foto_bytes = arquivo.getvalue()

    st.markdown('</div>', unsafe_allow_html=True)
    return foto_bytes


def salvar_arquivo_foto_perfil(usuario_id, foto_bytes):
    """Salva os bytes da foto em disco e devolve o caminho salvo."""
    caminho = os.path.join(PASTA_FOTOS_PERFIL, f"perfil_{usuario_id}.jpg")
    with open(caminho, "wb") as f:
        f.write(foto_bytes)
    return caminho


def _foto_base64(caminho):
    import base64
    with open(caminho, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ----------------------------------------------------------------------------
# Login / Cadastro
# ----------------------------------------------------------------------------

def tela_login():
    injetar_css()

    st.markdown(
        """
        <div class="hero-wrap">
            <div class="hero-logo">💪</div>
            <div class="hero-title">Perfil Físico Corporal IA</div>
            <div class="hero-subtitle">
                Seu personal trainer digital: medidas, índices automáticos, leitura por IA,
                radar corporal e evolução completa em um único lugar.
            </div>
            <div class="hero-badge">Premium · v1.0</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not getattr(db, "ARMAZENAMENTO_PERMANENTE", True):
        st.warning(
            "⚠️ Este servidor não permite gravação permanente na pasta do app "
            "(comum em hospedagens gratuitas). Os dados estão sendo salvos em "
            "modo temporário e podem ser perdidos quando o app reiniciar. "
            "Para persistência permanente, hospede em um servidor próprio "
            "(VPS/Docker) com um volume gravável."
        )

    _, col_centro, _ = st.columns([1, 1.3, 1])
    with col_centro:
        aba_login, aba_cadastro = st.tabs(["Entrar", "Criar conta"])

        with aba_login:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)

        with aba_cadastro:
            st.markdown('<div class="panel">', unsafe_allow_html=True)

            foto_cadastro_bytes = capturar_foto_perfil("cadastro")

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
                            novo_id = db.criar_usuario(
                                novo_username, nova_senha, nome, int(idade), sexo,
                                float(altura_cm), int(tempo_treino), natural, objetivo,
                            )
                            if foto_cadastro_bytes:
                                caminho_foto = salvar_arquivo_foto_perfil(novo_id, foto_cadastro_bytes)
                                db.atualizar_usuario(novo_id, foto_perfil=caminho_foto)
                            st.success("Conta criada! Vá para a aba 'Entrar'.")
                        except Exception as e:
                            st.error(f"Não foi possível criar a conta: {e}")
            st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Nova avaliação
# ----------------------------------------------------------------------------

def secao_nova_avaliacao(usuario):
    cabecalho(
        "Nova Avaliação",
        "Registre as medidas corporais atuais para gerar índices, leitura por IA e radar.",
        eyebrow="📏 Medidas Corporais",
    )

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    with st.form("form_medidas"):
        cols = st.columns(3)
        valores = {}
        for i, (campo, rotulo) in enumerate(CAMPOS_MEDIDAS):
            with cols[i % 3]:
                valores[campo] = st.number_input(rotulo, min_value=0.0, max_value=250.0,
                                                   value=0.0, step=0.1, key=f"med_{campo}")
        salvar = st.form_submit_button("Calcular e Salvar Avaliação", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if salvar:
        faltando = [rotulo for campo, rotulo in CAMPOS_MEDIDAS if valores[campo] == 0.0]
        if faltando:
            st.warning(f"Preencha todas as medidas antes de salvar: {', '.join(faltando)}")
            return

        dados_pessoais = {"sexo": usuario["sexo"], "altura_cm": usuario["altura_cm"],
                           "tempo_treino_meses": usuario["tempo_treino_meses"]}
        indices = calculos.calcular_todos_indices(dados_pessoais, valores)
        try:
            avaliacao_id = db.salvar_avaliacao(usuario["id"], valores, indices)
            st.session_state["ultima_avaliacao_id"] = avaliacao_id
            st.success("Avaliação salva com sucesso! Veja os resultados na aba 'Dashboard'.")
        except Exception as e:
            st.error(f"Não foi possível salvar a avaliação agora. Detalhe técnico: {e}")


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

    cabecalho(
        "Dashboard",
        f"Avaliação registrada em {avaliacao['data_avaliacao'][:10]} — visão completa de índices e leitura por IA.",
        eyebrow="📊 Resultados",
    )

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

    st.write("")
    col_esq, col_dir = st.columns([1, 1])

    ROTULO_CLASSE = {
        "Excelente": "st-excelente", "Muito Bom": "st-excelente",
        "Bom": "st-bom", "Regular": "st-regular",
        "Necessita prioridade": "st-melhorar", "Não avaliado": "st-regular",
    }

    with col_esq:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        abrir_painel("🧠 Leitura do Perfil Corporal (IA)")

        m1, m2 = st.columns(2)
        with m1: card("Estrutura óssea", leitura["estrutura_ossea"])
        with m2: card("Nível muscular", leitura["nivel_muscular"])

        for grupo, info in leitura["grupos"].items():
            classe = ROTULO_CLASSE.get(info["rotulo"], "st-regular")
            st.markdown(
                f'<div class="grupo-linha">'
                f'<span class="grupo-nome">{grupo}</span>'
                f'<span class="grupo-status {classe}">{info["cor"]} {info["rotulo"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if leitura["prioridade_treino"]:
            st.warning(f'🎯 Prioridade de treino sugerida: **{leitura["prioridade_treino"]}**')

        st.markdown(
            '<div class="legenda-cores">'
            '<span>🟢 Excelente</span><span>🟡 Bom</span>'
            '<span>🟠 Regular</span><span>🔴 Necessita melhorar</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_dir:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        abrir_painel("🕸️ Radar Corporal")
        st.plotly_chart(montar_radar(leitura, indices), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    abrir_painel("⏱️ Medidores")
    g1, g2, g3 = st.columns(3)
    with g1:
        st.plotly_chart(montar_gauge("Índice Estético", indices["indice_estetico"], 0, 10), use_container_width=True)
    with g2:
        st.plotly_chart(montar_gauge("Índice de Hipertrofia", indices["indice_hipertrofia"], 0, 10), use_container_width=True)
    with g3:
        st.plotly_chart(montar_gauge("Índice de Definição", indices["indice_definicao"], 0, 10), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Evolução
# ----------------------------------------------------------------------------

def secao_evolucao(usuario):
    cabecalho(
        "Evolução",
        "Acompanhe a variação das suas medidas e índices ao longo do tempo.",
        eyebrow="📈 Histórico",
    )

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    periodo = st.selectbox("Período", ["Hoje", "30 dias", "90 dias", "180 dias", "1 ano", "Tudo"])
    mapa_dias = {"Hoje": 1, "30 dias": 30, "90 dias": 90, "180 dias": 180, "1 ano": 365, "Tudo": None}
    avaliacoes = db.listar_avaliacoes(usuario["id"], dias=mapa_dias[periodo])

    if not avaliacoes:
        st.info("Sem avaliações no período selecionado.")
        st.markdown('</div>', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    abrir_painel("Histórico completo")
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
    st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Fotos
# ----------------------------------------------------------------------------

def secao_fotos(usuario):
    cabecalho(
        "Fotos — Antes / Depois",
        "Registre fotos de acompanhamento e veja o resumo automático da evolução.",
        eyebrow="📸 Registro Visual",
    )

    avaliacao = db.ultima_avaliacao(usuario["id"])
    if not avaliacao:
        st.info("Salve uma avaliação antes de anexar fotos.")
        return

    st.markdown('<div class="panel">', unsafe_allow_html=True)
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
            try:
                for arquivo, tipo in [(foto_antes, "antes"), (foto_depois, "depois")]:
                    if arquivo:
                        nome_arquivo = f"{usuario['id']}_{avaliacao['id']}_{tipo}_{arquivo.name}"
                        caminho = os.path.join(PASTA_FOTOS, nome_arquivo)
                        with open(caminho, "wb") as f:
                            f.write(arquivo.getbuffer())
                        db.salvar_foto(avaliacao["id"], tipo, caminho)
                st.success("Fotos salvas.")
            except Exception as e:
                st.error(f"Não foi possível salvar as fotos agora. Detalhe técnico: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

    # Comparação automática (heurística baseada nas medidas salvas, não em
    # visão computacional real — compara a avaliação atual com a anterior)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    abrir_painel("🔍 Comparação automática (baseada nas medidas)")
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
    st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Metas
# ----------------------------------------------------------------------------

def secao_metas(usuario):
    cabecalho(
        "Sistema Inteligente de Metas",
        "Defina metas de medidas e peso — o sistema estima o prazo com base em taxas de progresso realistas.",
        eyebrow="🎯 Metas",
    )
    avaliacao = db.ultima_avaliacao(usuario["id"])
    if not avaliacao:
        st.info("Salve uma avaliação para definir metas.")
        return

    campos_meta = [("peso_kg", "Peso (kg)")] + CAMPOS_MEDIDAS[1:]  # inclui peso + medidas
    st.markdown('<div class="panel">', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)

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
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        abrir_painel("📋 Plano de metas")
        st.table(pd.DataFrame(dados_tabela))

        prazo_total = metas_mod.prazo_geral(plano)
        if prazo_total:
            st.info(f"⏳ Tempo estimado para atingir todas as metas: **{prazo_total} meses**")
        st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Relatório PDF
# ----------------------------------------------------------------------------

def secao_relatorio(usuario):
    cabecalho(
        "Relatório Premium",
        "Gere um PDF completo com medidas, índices, leitura por IA e plano de metas.",
        eyebrow="📄 Exportação",
    )
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

    _, col_centro, _ = st.columns([1, 1.2, 1])
    with col_centro:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Dados pessoais (edição)
# ----------------------------------------------------------------------------

def secao_dados_pessoais(usuario):
    cabecalho(
        "Dados Pessoais",
        "Essas informações alimentam as fórmulas de composição corporal e a leitura por IA.",
        eyebrow="🙋 Perfil",
    )
    _, col_centro, _ = st.columns([1, 1.4, 1])
    with col_centro:
        st.markdown('<div class="panel">', unsafe_allow_html=True)

        foto_perfil_bytes = capturar_foto_perfil(
            "perfil_edicao", foto_atual_path=usuario.get("foto_perfil")
        )

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
            atualizar = st.form_submit_button("Salvar alterações", use_container_width=True)
            if atualizar:
                campos_atualizados = dict(
                    nome=nome, idade=int(idade), sexo=sexo,
                    altura_cm=float(altura_cm), tempo_treino_meses=int(tempo_treino),
                    natural_hormonizado=natural, objetivo=objetivo,
                )
                try:
                    if foto_perfil_bytes:
                        campos_atualizados["foto_perfil"] = salvar_arquivo_foto_perfil(
                            usuario["id"], foto_perfil_bytes
                        )
                    db.atualizar_usuario(usuario["id"], **campos_atualizados)
                    st.session_state["usuario"] = db.get_usuario(usuario["id"])
                    st.success("Dados atualizados.")
                    st.rerun()
                except Exception as e:
                    st.error(
                        "Não foi possível salvar as alterações agora. "
                        "Se você acabou de trocar a foto, tente novamente — "
                        f"detalhe técnico: {e}"
                    )
        st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# App principal
# ----------------------------------------------------------------------------

def app_principal():
    usuario = st.session_state["usuario"]
    injetar_css()

    inicial = (usuario["nome"] or "?").strip()[0].upper()
    foto_path = usuario.get("foto_perfil")
    if foto_path and os.path.exists(foto_path):
        avatar_html = f'<img class="sidebar-avatar-foto" src="data:image/jpeg;base64,{_foto_base64(foto_path)}" />'
    else:
        avatar_html = f'<div class="sidebar-avatar">{inicial}</div>'

    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-card">
                {avatar_html}
                <div class="sidebar-name">{usuario['nome']}</div>
                <div class="sidebar-user">@{usuario['username']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
