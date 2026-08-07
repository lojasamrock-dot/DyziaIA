"""
gerador_pdf.py
Gera o Relatório Premium em PDF usando ReportLab.
"""

import os
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib.enums import TA_CENTER

AZUL = colors.HexColor("#0B1F3A")
AZUL_CLARO = colors.HexColor("#1F6FEB")
CINZA = colors.HexColor("#333333")


def _foto_perfil_circular(caminho, tamanho_px=500):
    """
    Recorta a foto de perfil em um círculo (fundo transparente) para uso
    no cabeçalho do relatório. Retorna BytesIO com um PNG, ou None se a
    foto não existir / não puder ser processada.
    """
    if not caminho or not os.path.exists(caminho):
        return None
    try:
        from PIL import Image as PILImage, ImageDraw, ImageOps
    except ImportError:
        return None

    try:
        img = PILImage.open(caminho).convert("RGBA")
        img = ImageOps.fit(img, (tamanho_px, tamanho_px), PILImage.LANCZOS)

        mascara = PILImage.new("L", (tamanho_px, tamanho_px), 0)
        desenho = ImageDraw.Draw(mascara)
        desenho.ellipse((0, 0, tamanho_px, tamanho_px), fill=255)

        saida = PILImage.new("RGBA", (tamanho_px, tamanho_px))
        saida.paste(img, (0, 0), mascara)

        buffer = BytesIO()
        saida.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
    except Exception:
        return None


def _estilos():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(
        name="TituloCapa", fontSize=26, leading=30, textColor=AZUL,
        alignment=TA_CENTER, spaceAfter=6, fontName="Helvetica-Bold",
    ))
    base.add(ParagraphStyle(
        name="SubtituloCapa", fontSize=13, leading=16, textColor=CINZA,
        alignment=TA_CENTER, spaceAfter=20,
    ))
    base.add(ParagraphStyle(
        name="SecaoTitulo", fontSize=15, leading=18, textColor=AZUL,
        spaceBefore=14, spaceAfter=8, fontName="Helvetica-Bold",
    ))
    base.add(ParagraphStyle(
        name="TextoNormal", fontSize=10.5, leading=15, textColor=CINZA,
    ))
    return base


def _tabela_medidas(medidas: dict):
    rotulos = {
        "peso_kg": "Peso (kg)", "pescoco_cm": "Pescoço (cm)",
        "ombros_cm": "Ombros (cm)", "peitoral_cm": "Peitoral (cm)",
        "cintura_cm": "Cintura (cm)", "abdomen_cm": "Abdômen (cm)",
        "quadril_cm": "Quadril (cm)", "braco_dir_cm": "Braço direito (cm)",
        "braco_esq_cm": "Braço esquerdo (cm)", "antebraco_cm": "Antebraço (cm)",
        "coxa_cm": "Coxa (cm)", "panturrilha_cm": "Panturrilha (cm)",
    }
    dados = [["Medida", "Valor"]]
    for chave, rotulo in rotulos.items():
        if medidas.get(chave) is not None:
            dados.append([rotulo, f'{medidas[chave]:.1f}'])
    return _estilizar_tabela(dados)


def _tabela_indices(indices: dict):
    rotulos = {
        "imc": "IMC", "percentual_gordura": "% Gordura",
        "massa_gorda_kg": "Massa Gorda (kg)", "massa_magra_kg": "Massa Magra (kg)",
        "ffmi": "FFMI", "razao_ombro_cintura": "Ombro/Cintura",
        "razao_cintura_altura": "Cintura/Altura", "simetria_pct": "Simetria (%)",
        "indice_estetico": "Índice Estético (0-10)",
        "indice_hipertrofia": "Índice de Hipertrofia (0-10)",
        "indice_definicao": "Índice de Definição (0-10)",
        "nota_geral": "Nota Geral (0-10)",
    }
    dados = [["Índice", "Valor"]]
    for chave, rotulo in rotulos.items():
        if indices.get(chave) is not None:
            dados.append([rotulo, f'{indices[chave]:.2f}'])
    return _estilizar_tabela(dados)


def _estilizar_tabela(dados):
    t = Table(dados, colWidths=[8 * cm, 6 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4FA")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def gerar_relatorio_pdf(usuario: dict, medidas: dict, indices: dict,
                         leitura_ia: dict, plano_metas: list = None,
                         grafico_radar_png: bytes = None) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    estilos = _estilos()
    story = []

    # Capa
    story.append(Spacer(1, 2 * cm))

    foto_circular = _foto_perfil_circular(usuario.get("foto_perfil"))
    if foto_circular:
        img_perfil = Image(foto_circular, width=3.6 * cm, height=3.6 * cm)
        img_perfil.hAlign = "CENTER"
        story.append(img_perfil)
        story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph("Perfil Físico Corporal IA", estilos["TituloCapa"]))
    story.append(Paragraph("Relatório Premium de Avaliação Física", estilos["SubtituloCapa"]))
    story.append(Paragraph(
        f'{usuario.get("nome", "")} • {datetime.now().strftime("%d/%m/%Y")}',
        estilos["SubtituloCapa"],
    ))
    if indices.get("nota_geral") is not None:
        story.append(Paragraph(
            f'Nota Geral: {indices["nota_geral"]:.1f} / 10',
            ParagraphStyle(name="Nota", parent=estilos["TituloCapa"], fontSize=20),
        ))
    story.append(PageBreak())

    # Dados pessoais
    story.append(Paragraph("Dados Pessoais", estilos["SecaoTitulo"]))
    dp = (
        f'Nome: {usuario.get("nome","-")}<br/>'
        f'Idade: {usuario.get("idade","-")} anos<br/>'
        f'Sexo: {usuario.get("sexo","-")}<br/>'
        f'Altura: {usuario.get("altura_cm","-")} cm<br/>'
        f'Tempo de treino: {usuario.get("tempo_treino_meses","-")} meses<br/>'
        f'Categoria: {usuario.get("natural_hormonizado","-")}<br/>'
        f'Objetivo: {usuario.get("objetivo","-")}'
    )
    story.append(Paragraph(dp, estilos["TextoNormal"]))

    # Medidas
    story.append(Paragraph("Medidas Corporais", estilos["SecaoTitulo"]))
    story.append(_tabela_medidas(medidas))

    # Índices
    story.append(Paragraph("Índices Automáticos", estilos["SecaoTitulo"]))
    story.append(_tabela_indices(indices))

    # Radar
    if grafico_radar_png:
        story.append(Paragraph("Radar Corporal", estilos["SecaoTitulo"]))
        story.append(Image(BytesIO(grafico_radar_png), width=13 * cm, height=13 * cm))

    story.append(PageBreak())

    # Leitura IA
    story.append(Paragraph("Leitura do Perfil Corporal", estilos["SecaoTitulo"]))
    linhas = [
        f'Estrutura óssea: {leitura_ia.get("estrutura_ossea","-")}',
        f'Nível muscular: {leitura_ia.get("nivel_muscular","-")}',
    ]
    for grupo, info in leitura_ia.get("grupos", {}).items():
        linhas.append(f'{grupo}: {info["rotulo"]} {info["cor"]}')
    if leitura_ia.get("estimativa_gordura") is not None:
        linhas.append(f'Estimativa de gordura: {leitura_ia["estimativa_gordura"]:.1f}%')
    story.append(Paragraph("<br/>".join(linhas), estilos["TextoNormal"]))

    story.append(Paragraph("Pontos Fortes", estilos["SecaoTitulo"]))
    fortes = leitura_ia.get("pontos_fortes") or ["Nenhum destaque nesta avaliação."]
    story.append(Paragraph("<br/>".join(f"• {p}" for p in fortes), estilos["TextoNormal"]))

    story.append(Paragraph("Pontos a Desenvolver", estilos["SecaoTitulo"]))
    fracos = leitura_ia.get("pontos_fracos") or ["Nenhum ponto crítico identificado."]
    story.append(Paragraph("<br/>".join(f"• {p}" for p in fracos), estilos["TextoNormal"]))

    # Metas
    if plano_metas:
        story.append(Paragraph("Metas e Projeção de Evolução", estilos["SecaoTitulo"]))
        dados = [["Item", "Atual", "Meta", "Prazo estimado"]]
        for m in plano_metas:
            prazo = f'{m["prazo_meses"]} meses' if m.get("prazo_meses") else "-"
            dados.append([
                m.get("nome_amigavel", m["campo"]),
                f'{m["valor_atual"]:.1f}', f'{m["valor_meta"]:.1f}', prazo,
            ])
        t = Table(dados, colWidths=[5 * cm, 3 * cm, 3 * cm, 3 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4FA")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
