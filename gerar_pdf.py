"""
gerar_pdf.py — Módulo de geração de relatório PDF para o Smart Caixilho
Dependências: reportlab, matplotlib, numpy
Uso no Streamlit:
    from gerar_pdf import gerar_relatorio_pdf
    pdf_bytes = gerar_relatorio_pdf(empresa, responsavel, cargo, email, telefone,
                                    respostas, nivel, total, pct, data_hoje)
    st.download_button("📥 Baixar Relatório PDF", pdf_bytes,
                       file_name=f"SmartCaixilho_{empresa}.pdf", mime="application/pdf")
"""

import math
import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF

# ── Paleta ASES ──────────────────────────────────────────────────────────────
AZUL_ESCURO  = colors.HexColor("#0A2540")
DOURADO      = colors.HexColor("#C9A84C")
CINZA_CLARO  = colors.HexColor("#F8F7F4")
CINZA_MEDIO  = colors.HexColor("#E5E3DC")
CINZA_TEXTO  = colors.HexColor("#64748B")
BRANCO       = colors.white

PAGE_W, PAGE_H = A4  # 595 x 842 pt


# ── Estilos de parágrafo ─────────────────────────────────────────────────────
def _estilos():
    return {
        "titulo": ParagraphStyle(
            "titulo", fontName="Helvetica-Bold", fontSize=16,
            textColor=BRANCO, leading=20, spaceAfter=0
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", fontName="Helvetica", fontSize=9,
            textColor=colors.HexColor("#94A3B8"), leading=12
        ),
        "label": ParagraphStyle(
            "label", fontName="Helvetica", fontSize=8,
            textColor=CINZA_TEXTO, leading=10, spaceAfter=2
        ),
        "valor": ParagraphStyle(
            "valor", fontName="Helvetica-Bold", fontSize=22,
            textColor=AZUL_ESCURO, leading=26
        ),
        "nivel": ParagraphStyle(
            "nivel", fontName="Helvetica-Bold", fontSize=10,
            textColor=DOURADO, leading=13
        ),
        "secao": ParagraphStyle(
            "secao", fontName="Helvetica-Bold", fontSize=7,
            textColor=CINZA_TEXTO, leading=9, spaceAfter=6,
            borderPadding=(0, 0, 4, 0)
        ),
        "rec_dim": ParagraphStyle(
            "rec_dim", fontName="Helvetica-Bold", fontSize=8,
            textColor=DOURADO, leading=10, spaceAfter=2
        ),
        "rec_txt": ParagraphStyle(
            "rec_txt", fontName="Helvetica", fontSize=8,
            textColor=CINZA_TEXTO, leading=11
        ),
        "rodape": ParagraphStyle(
            "rodape", fontName="Helvetica", fontSize=7,
            textColor=CINZA_TEXTO, leading=9
        ),
        "ia_label": ParagraphStyle(
            "ia_label", fontName="Helvetica", fontSize=8,
            textColor=CINZA_TEXTO, leading=10, spaceAfter=2
        ),
        "ia_score": ParagraphStyle(
            "ia_score", fontName="Helvetica-Bold", fontSize=18,
            textColor=AZUL_ESCURO, leading=22
        ),
        "ia_sug": ParagraphStyle(
            "ia_sug", fontName="Helvetica", fontSize=7,
            textColor=CINZA_TEXTO, leading=10
        ),
    }


# ── Gráfico Radar ────────────────────────────────────────────────────────────
def _gerar_radar(dims: dict, largura_cm=8) -> Image:
    categorias = list(dims.keys())
    valores = [dims[d]["media"] for d in categorias]
    N = len(categorias)

    angulos = [n / float(N) * 2 * math.pi for n in range(N)]
    angulos += angulos[:1]
    valores_plot = valores + valores[:1]

    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.plot(angulos, valores_plot, "o-", linewidth=2, color="#C9A84C")
    ax.fill(angulos, valores_plot, alpha=0.18, color="#C9A84C")

    ax.set_xticks(angulos[:-1])
    ax.set_xticklabels(categorias, size=7, color="#334155",
                       fontfamily="DejaVu Sans")
    ax.set_ylim(0, 4)
    ax.set_yticks([1, 2, 3, 4])
    ax.set_yticklabels(["1", "2", "3", "4"], size=6, color="#94A3B8")
    ax.tick_params(pad=6)
    ax.spines["polar"].set_visible(False)
    ax.grid(color="#CBD5E1", linewidth=0.6, alpha=0.7)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=180, bbox_inches="tight",
                facecolor="white")
    buf.seek(0)
    plt.close(fig)

    largura_pt = largura_cm * cm
    img = Image(buf, width=largura_pt, height=largura_pt)
    return img


# ── Barra de dimensão ────────────────────────────────────────────────────────
def _barra_dim(label: str, media: float, col_w: float) -> Table:
    """Retorna uma mini-tabela: [label | barra | score]"""
    label_w = col_w * 0.42
    barra_w = col_w * 0.44
    score_w = col_w * 0.14

    pct = media / 4.0
    bar_total = barra_w - 4
    bar_fill  = bar_total * pct

    d = Drawing(barra_w, 8)
    d.add(Rect(0, 1, bar_total, 6, fillColor=CINZA_MEDIO,
               strokeColor=None, rx=3, ry=3))
    if bar_fill > 0:
        d.add(Rect(0, 1, bar_fill, 6, fillColor=DOURADO,
                   strokeColor=None, rx=3, ry=3))

    estilos = _estilos()
    data = [[
        Paragraph(label, estilos["rec_txt"]),
        d,
        Paragraph(f"{media:.1f}", estilos["rec_dim"]),
    ]]
    t = Table(data, colWidths=[label_w, barra_w, score_w])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))
    return t


# ── Cabeçalho ────────────────────────────────────────────────────────────────
def _cabecalho(empresa, responsavel, cargo, data_hoje, estilos) -> list:
    W = PAGE_W - 2 * cm  # largura útil

    # Faixa azul escura
    d_header = Drawing(W, 70)
    d_header.add(Rect(0, 0, W, 70, fillColor=AZUL_ESCURO,
                      strokeColor=None, rx=8, ry=8))
    d_header.add(String(16, 44, "Diagnóstico Smart Caixilho",
                        fontName="Helvetica-Bold", fontSize=16,
                        fillColor=colors.white))
    d_header.add(String(16, 28, "Modernização da Cadeia de Esquadrias de Alumínio",
                        fontName="Helvetica", fontSize=9,
                        fillColor=colors.HexColor("#94A3B8")))
    d_header.add(String(W - 10, 50, "ASES",
                        fontName="Helvetica-Bold", fontSize=16,
                        fillColor=colors.HexColor("#C9A84C"),
                        textAnchor="end"))
    d_header.add(String(W - 10, 35, data_hoje,
                        fontName="Helvetica", fontSize=8,
                        fillColor=colors.HexColor("#64748B"),
                        textAnchor="end"))

    # Faixa dourada com nome da empresa
    d_empresa = Drawing(W, 32)
    d_empresa.add(Rect(0, 0, W, 32, fillColor=DOURADO,
                       strokeColor=None, rx=0, ry=0))
    d_empresa.add(String(16, 18, empresa,
                         fontName="Helvetica-Bold", fontSize=12,
                         fillColor=AZUL_ESCURO))
    d_empresa.add(String(16, 6, f"Responsável: {responsavel} — {cargo}",
                         fontName="Helvetica", fontSize=8,
                         fillColor=colors.HexColor("#1E3A5F")))

    return [d_header, Spacer(1, 0), d_empresa, Spacer(1, 10)]


# ── Métricas principais ───────────────────────────────────────────────────────
def _metricas(total, pct, nivel, estilos) -> Table:
    W = PAGE_W - 2 * cm
    cell_w = W / 3

    def cell(label, val, sub=None):
        items = [
            Paragraph(label.upper(), estilos["label"]),
            Paragraph(str(val), estilos["valor"]),
        ]
        if sub:
            items.append(Paragraph(sub, estilos["nivel"]))
        return items

    nivel_curto = nivel.replace(" – ", "\n")
    data = [[
        cell("Pontuação",       f"{total}/40"),
        cell("Maturidade digital", f"{pct}%"),
        cell("Nível",           "",  nivel_curto),
    ]]
    t = Table(data, colWidths=[cell_w] * 3)
    t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND",    (0, 0), (-1, -1), CINZA_CLARO),
        ("LINEAFTER",     (0, 0), (1, 0),   0.5, CINZA_MEDIO),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("LINEBELOW",     (0, 0), (-1, 0),  0.5, CINZA_MEDIO),
    ]))
    return t


# ── Seção radar + recomendações ───────────────────────────────────────────────
def _radar_e_recs(dims, perguntas, respostas, estilos) -> Table:
    W = PAGE_W - 2 * cm
    col_radar = W * 0.46
    col_recs  = W * 0.54

    radar_img = _gerar_radar(dims, largura_cm=(col_radar - 10) / cm)

    # Barras de dimensão
    barras = [Paragraph("PERFIL POR DIMENSÃO", estilos["secao"])]
    for dim, val in dims.items():
        barras.append(_barra_dim(dim, val["media"], col_radar - 12))
        barras.append(Spacer(1, 2))

    # Top 3 recomendações (piores notas)
    piores = sorted(perguntas, key=lambda p: respostas[p["id"]])[:3]
    recs = [Paragraph("RECOMENDAÇÕES PRIORITÁRIAS", estilos["secao"])]
    for p in piores:
        recs.append(Paragraph(p["dim"], estilos["rec_dim"]))
        recs.append(Paragraph(p["sug"], estilos["rec_txt"]))
        recs.append(Spacer(1, 6))

    col_esq = [[Paragraph("RADAR DE MATURIDADE", estilos["secao"])],
               [radar_img],
               [Spacer(1, 8)]] + [[b] for b in barras]

    col_dir = [[r] for r in recs]

    # Montar as duas colunas como tabela
    max_rows = max(len(col_esq), len(col_dir))
    while len(col_esq) < max_rows: col_esq.append([Spacer(1, 1)])
    while len(col_dir) < max_rows: col_dir.append([Spacer(1, 1)])

    data = [[col_esq[i][0], col_dir[i][0]] for i in range(max_rows)]

    t = Table(data, colWidths=[col_radar, col_recs])
    t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (0, -1),  14),
        ("LEFTPADDING",   (1, 0), (1, -1),  16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("LINEAFTER",     (0, 0), (0, -1),  0.5, CINZA_MEDIO),
        ("BACKGROUND",    (0, 0), (-1, -1), BRANCO),
    ]))
    return t


# ── Bloco de Prontidão para IA ────────────────────────────────────────────────
def _bloco_ia(perguntas_ia, respostas, estilos) -> Table:
    W = PAGE_W - 2 * cm
    cell_w = W / len(perguntas_ia)

    cells = []
    for p in perguntas_ia:
        nota = respostas[p["id"]]
        bg = colors.HexColor("#FDF8EE") if nota <= 1 else CINZA_CLARO
        brd = DOURADO if nota <= 1 else CINZA_MEDIO
        cell_content = [
            Paragraph(p["label"], estilos["ia_label"]),
            Paragraph(f"{nota}/4", estilos["ia_score"]),
            Paragraph(p["sug"], estilos["ia_sug"]),
        ]
        cells.append(cell_content)

    data = [cells]
    t = Table(data, colWidths=[cell_w] * len(perguntas_ia))
    t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND",    (0, 0), (-1, -1), CINZA_CLARO),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("LINEAFTER",     (0, 0), (1, 0),   0.5, CINZA_MEDIO),
        ("LINEABOVE",     (0, 0), (-1, 0),  0.5, CINZA_MEDIO),
    ]))
    return t


# ── Rodapé ────────────────────────────────────────────────────────────────────
def _rodape(estilos) -> Table:
    W = PAGE_W - 2 * cm
    data = [[
        Paragraph("smart-caixilho.streamlit.app", estilos["rodape"]),
        Paragraph("ASES Consultoria em Esquadrias",
                  ParagraphStyle("rdir", fontName="Helvetica-Bold",
                                 fontSize=7, textColor=DOURADO,
                                 alignment=2)),
    ]]
    t = Table(data, colWidths=[W * 0.6, W * 0.4])
    t.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("LINEABOVE",     (0, 0), (-1, 0),  0.5, CINZA_MEDIO),
        ("BACKGROUND",    (0, 0), (-1, -1), BRANCO),
    ]))
    return t


# ── Função principal exportada ────────────────────────────────────────────────
def gerar_relatorio_pdf(
    empresa: str,
    responsavel: str,
    cargo: str,
    email: str,
    telefone: str,
    respostas: dict,
    nivel: str,
    total: int,
    pct: int,
    data_hoje: str,
) -> bytes:
    """
    Gera o relatório PDF e retorna os bytes prontos para st.download_button.

    Parâmetros
    ----------
    respostas : dict
        Dicionário com as respostas de TODAS as perguntas (Q1–Q10).
        Ex.: {"Q1": 2, "Q2": 1, "Q3": 0, ...}
    """

    # ── Definição das perguntas (igual ao app) ──────────────────────────────
    perguntas_principais = [
        {"id": "Q1",  "dim": "Integração & Dados",   "label": "Orçamento integrado",
         "sug": "Padronizar orçamento e integrar com projeto/produção."},
        {"id": "Q2",  "dim": "Gestão & Indicadores", "label": "Coleta e análise de dados",
         "sug": "Criar 3 indicadores semanais de produção e vendas."},
        {"id": "Q3",  "dim": "Automação",             "label": "Máquinas CNC / automatizadas",
         "sug": "Mapear gargalos e avaliar automação incremental."},
        {"id": "Q4",  "dim": "Integração & Dados",   "label": "Equipamentos conectados ao ERP",
         "sug": "Conectar produção ao ERP, mesmo via importação manual."},
        {"id": "Q5",  "dim": "Integração & Dados",   "label": "Integração ponta a ponta",
         "sug": "Definir fluxo ponta a ponta com checkpoints claros."},
        {"id": "Q6",  "dim": "Pessoas & Cultura",    "label": "Treinamentos digitais",
         "sug": "Implementar 1 treinamento digital por mês."},
        {"id": "Q7",  "dim": "Pessoas & Cultura",    "label": "Liderança orientada a dados",
         "sug": "Reunião semanal com indicadores — método PDCA."},
    ]

    perguntas_ia = [
        {"id": "Q08", "dim": "Prontidão para IA", "label": "Organização de dados",
         "sug": "Digitalize um setor por vez para criar base de dados."},
        {"id": "Q09", "dim": "Prontidão para IA", "label": "Conhecimento em IA",
         "sug": "Reserve 1h/mês para explorar ferramentas de IA do setor."},
        {"id": "Q10", "dim": "Prontidão para IA", "label": "Uso de IA em operações",
         "sug": "Experimente um assistente de orçamento com IA."},
    ]

    # ── Agregar médias por dimensão ─────────────────────────────────────────
    dims: dict = {}
    for p in perguntas_principais:
        d = p["dim"]
        if d not in dims:
            dims[d] = {"total": 0, "count": 0, "media": 0.0}
        dims[d]["total"] += respostas.get(p["id"], 0)
        dims[d]["count"] += 1
    for d in dims:
        dims[d]["media"] = dims[d]["total"] / dims[d]["count"]

    # ── Montar documento ────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=cm, rightMargin=cm,
        topMargin=cm, bottomMargin=cm,
    )

    estilos = _estilos()
    story = []

    # Cabeçalho
    for elem in _cabecalho(empresa, responsavel, cargo, data_hoje, estilos):
        story.append(elem)

    # Métricas
    story.append(_metricas(total, pct, nivel, estilos))
    story.append(Spacer(1, 6))

    # Radar + Recomendações
    story.append(_radar_e_recs(dims, perguntas_principais, respostas, estilos))
    story.append(Spacer(1, 6))

    # Bloco IA
    ia_header = Drawing(PAGE_W - 2 * cm, 28)
    ia_header.add(Rect(0, 0, PAGE_W - 2 * cm, 28,
                       fillColor=AZUL_ESCURO, strokeColor=None))
    ia_header.add(String(16, 10, "IA  —  PRONTIDÃO PARA INTELIGÊNCIA ARTIFICIAL",
                         fontName="Helvetica-Bold", fontSize=9,
                         fillColor=DOURADO))
    story.append(ia_header)
    story.append(_bloco_ia(perguntas_ia, respostas, estilos))
    story.append(Spacer(1, 6))

    # Rodapé
    story.append(_rodape(estilos))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ── Teste local ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    respostas_teste = {
        "Q1": 2, "Q2": 2, "Q3": 0, "Q4": 0,
        "Q5": 1, "Q6": 0, "Q7": 0,
        "Q08": 0, "Q09": 1, "Q10": 0,
    }
    pdf = gerar_relatorio_pdf(
        empresa="Empresa Teste Ltda.",
        responsavel="Maria Silva", cargo="CEO",
        email="teste@empresa.com.br", telefone="11 99999-0000",
        respostas=respostas_teste,
        nivel="Nível 1 – Operação Invisível",
        total=6, pct=15,
        data_hoje=datetime.now().strftime("%d/%m/%Y"),
    )
    with open("/home/claude/relatorio_teste.pdf", "wb") as f:
        f.write(pdf)
    print(f"PDF gerado: {len(pdf)} bytes")
