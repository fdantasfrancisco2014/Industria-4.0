import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import math
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.graphics.shapes import Drawing, Rect, String

import gspread
from google.oauth2.service_account import Credentials

# ── Paleta ASES ───────────────────────────────────────────────────────────────
AZUL_ESCURO = colors.HexColor("#0A2540")
DOURADO     = colors.HexColor("#C9A84C")
CINZA_CLARO = colors.HexColor("#F8F7F4")
CINZA_MEDIO = colors.HexColor("#E5E3DC")
CINZA_TEXTO = colors.HexColor("#64748B")
BRANCO      = colors.white
PAGE_W, PAGE_H = A4

# ── Google Sheets ─────────────────────────────────────────────────────────────
def _abrir_sheet():
    info   = dict(st.secrets["gcp_service_account"])
    client = gspread.service_account_from_dict(info)
    return client.open("SmartCaixilho_Resultados").sheet1

def salvar_no_sheets(dados: dict):
    try:
        # Converter secrets para dict Python puro
        raw  = st.secrets["gcp_service_account"]
        info = {
            "type":                        str(raw["type"]),
            "project_id":                  str(raw["project_id"]),
            "private_key_id":              str(raw["private_key_id"]),
            "private_key":                 str(raw["private_key"]).replace("\\n", "\n"),
            "client_email":                str(raw["client_email"]),
            "client_id":                   str(raw["client_id"]),
            "auth_uri":                    str(raw["auth_uri"]),
            "token_uri":                   str(raw["token_uri"]),
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url":        f"https://www.googleapis.com/robot/v1/metadata/x509/{str(raw['client_email']).replace('@', '%40')}",
        }
        client = gspread.service_account_from_dict(info)
        sheet  = client.open("SmartCaixilho_Resultados").sheet1
        todas_linhas = sheet.get_all_values()
        if len(todas_linhas) == 0:
            sheet.append_row(list(dados.keys()))
        sheet.append_row([str(v) for v in dados.values()])
        return True
    except Exception as e:
        st.warning(f"⚠️ Erro ao salvar: {e}")
        return False

# ── Estilos PDF ───────────────────────────────────────────────────────────────
def _estilos():
    return {
        "label":   ParagraphStyle("label",   fontName="Helvetica",      fontSize=8,  textColor=CINZA_TEXTO, leading=10, spaceAfter=2),
        "valor":   ParagraphStyle("valor",   fontName="Helvetica-Bold", fontSize=22, textColor=AZUL_ESCURO, leading=26),
        "nivel":   ParagraphStyle("nivel",   fontName="Helvetica-Bold", fontSize=10, textColor=DOURADO,     leading=13),
        "secao":   ParagraphStyle("secao",   fontName="Helvetica-Bold", fontSize=7,  textColor=CINZA_TEXTO, leading=9,  spaceAfter=6),
        "rec_dim": ParagraphStyle("rec_dim", fontName="Helvetica-Bold", fontSize=8,  textColor=DOURADO,     leading=10, spaceAfter=2),
        "rec_txt": ParagraphStyle("rec_txt", fontName="Helvetica",      fontSize=8,  textColor=CINZA_TEXTO, leading=11),
        "rodape":  ParagraphStyle("rodape",  fontName="Helvetica",      fontSize=7,  textColor=CINZA_TEXTO, leading=9),
        "ia_label":ParagraphStyle("ia_label",fontName="Helvetica",      fontSize=8,  textColor=CINZA_TEXTO, leading=10, spaceAfter=2),
        "ia_score":ParagraphStyle("ia_score",fontName="Helvetica-Bold", fontSize=18, textColor=AZUL_ESCURO, leading=22),
        "ia_sug":  ParagraphStyle("ia_sug",  fontName="Helvetica",      fontSize=7,  textColor=CINZA_TEXTO, leading=10),
    }

# ── Radar matplotlib ──────────────────────────────────────────────────────────
def _gerar_radar(dims, largura_cm=8):
    categorias   = list(dims.keys())
    valores      = [dims[d]["media"] for d in categorias]
    N            = len(categorias)
    angulos      = [n / float(N) * 2 * math.pi for n in range(N)] + [0]
    valores_plot = valores + valores[:1]

    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.plot(angulos, valores_plot, "o-", linewidth=2, color="#C9A84C")
    ax.fill(angulos, valores_plot, alpha=0.18, color="#C9A84C")
    ax.set_xticks(angulos[:-1])
    ax.set_xticklabels(categorias, size=7, color="#334155")
    ax.set_ylim(0, 4)
    ax.set_yticks([1, 2, 3, 4])
    ax.set_yticklabels(["1", "2", "3", "4"], size=6, color="#94A3B8")
    ax.tick_params(pad=6)
    ax.spines["polar"].set_visible(False)
    ax.grid(color="#CBD5E1", linewidth=0.6, alpha=0.7)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=180, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    plt.close(fig)
    lp = largura_cm * cm
    return Image(buf, width=lp, height=lp)

# ── Barra de dimensão ─────────────────────────────────────────────────────────
def _barra_dim(label, media, col_w):
    lw, bw, sw = col_w * 0.42, col_w * 0.44, col_w * 0.14
    bar_total  = bw - 4
    bar_fill   = bar_total * (media / 4.0)
    d = Drawing(bw, 8)
    d.add(Rect(0, 1, bar_total, 6, fillColor=CINZA_MEDIO, strokeColor=None, rx=3, ry=3))
    if bar_fill > 0:
        d.add(Rect(0, 1, bar_fill, 6, fillColor=DOURADO, strokeColor=None, rx=3, ry=3))
    e = _estilos()
    t = Table([[Paragraph(label, e["rec_txt"]), d, Paragraph(f"{media:.1f}", e["rec_dim"])]], colWidths=[lw, bw, sw])
    t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))
    return t

# ── Cabeçalho PDF ─────────────────────────────────────────────────────────────
def _cabecalho(empresa, responsavel, cargo, data_hoje, estilos):
    W  = PAGE_W - 2 * cm
    dh = Drawing(W, 70)
    dh.add(Rect(0, 0, W, 70, fillColor=AZUL_ESCURO, strokeColor=None, rx=8, ry=8))
    dh.add(String(16, 44, "Diagnostico Smart Caixilho",       fontName="Helvetica-Bold", fontSize=16, fillColor=BRANCO))
    dh.add(String(16, 28, "Modernizacao da Cadeia de Esquadrias de Aluminio", fontName="Helvetica",      fontSize=9,  fillColor=colors.HexColor("#94A3B8")))
    dh.add(String(W-10, 50, "ASES",    fontName="Helvetica-Bold", fontSize=16, fillColor=DOURADO,     textAnchor="end"))
    dh.add(String(W-10, 35, data_hoje, fontName="Helvetica",      fontSize=8,  fillColor=CINZA_TEXTO, textAnchor="end"))
    de = Drawing(W, 32)
    de.add(Rect(0, 0, W, 32, fillColor=DOURADO, strokeColor=None))
    de.add(String(16, 18, empresa[:60],                        fontName="Helvetica-Bold", fontSize=12, fillColor=AZUL_ESCURO))
    de.add(String(16, 6,  f"Responsavel: {responsavel} - {cargo}", fontName="Helvetica", fontSize=8,  fillColor=colors.HexColor("#1E3A5F")))
    return [dh, Spacer(1, 0), de, Spacer(1, 10)]

# ── Métricas PDF ──────────────────────────────────────────────────────────────
def _metricas(total, pct, nivel, estilos):
    W  = PAGE_W - 2 * cm
    cw = W / 3
    def cell(lbl, val, sub=None):
        items = [Paragraph(lbl.upper(), estilos["label"]), Paragraph(str(val), estilos["valor"])]
        if sub: items.append(Paragraph(sub, estilos["nivel"]))
        return items
    nivel_fmt = nivel.replace(" – ", "\n").replace(" - ", "\n")
    data = [[cell("Pontuacao", f"{total}/40"), cell("Maturidade digital", f"{pct}%"), cell("Nivel", "", nivel_fmt)]]
    t = Table(data, colWidths=[cw]*3)
    t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(-1,-1),CINZA_CLARO),("LINEAFTER",(0,0),(1,0),0.5,CINZA_MEDIO),("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),12),("LEFTPADDING",(0,0),(-1,-1),14),("RIGHTPADDING",(0,0),(-1,-1),8),("LINEBELOW",(0,0),(-1,0),0.5,CINZA_MEDIO)]))
    return t

# ── Radar + Recomendações PDF ─────────────────────────────────────────────────
def _radar_e_recs(dims, perguntas, respostas, estilos):
    W       = PAGE_W - 2 * cm
    cr, cc  = W * 0.46, W * 0.54
    radar_img = _gerar_radar(dims, largura_cm=(cr - 10) / cm)
    barras  = [Paragraph("PERFIL POR DIMENSAO", estilos["secao"])]
    for dim, val in dims.items():
        barras.append(_barra_dim(dim, val["media"], cr - 12))
        barras.append(Spacer(1, 2))
    piores = sorted(perguntas, key=lambda p: respostas[p["id"]])[:3]
    recs   = [Paragraph("RECOMENDACOES PRIORITARIAS", estilos["secao"])]
    for p in piores:
        recs.append(Paragraph(p["dim"], estilos["rec_dim"]))
        recs.append(Paragraph(p["sug"], estilos["rec_txt"]))
        recs.append(Spacer(1, 6))
    col_e = [[Paragraph("RADAR DE MATURIDADE", estilos["secao"])], [radar_img], [Spacer(1,8)]] + [[b] for b in barras]
    col_d = [[r] for r in recs]
    mr = max(len(col_e), len(col_d))
    while len(col_e) < mr: col_e.append([Spacer(1,1)])
    while len(col_d) < mr: col_d.append([Spacer(1,1)])
    data = [[col_e[i][0], col_d[i][0]] for i in range(mr)]
    t = Table(data, colWidths=[cr, cc])
    t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),("LEFTPADDING",(0,0),(0,-1),14),("LEFTPADDING",(1,0),(1,-1),16),("RIGHTPADDING",(0,0),(-1,-1),8),("LINEAFTER",(0,0),(0,-1),0.5,CINZA_MEDIO),("BACKGROUND",(0,0),(-1,-1),BRANCO)]))
    return t

# ── Bloco IA PDF ──────────────────────────────────────────────────────────────
def _bloco_ia(perguntas_ia, respostas, estilos):
    W  = PAGE_W - 2 * cm
    cw = W / len(perguntas_ia)
    cells = []
    for p in perguntas_ia:
        nota = respostas[p["id"]]
        cells.append([Paragraph(p["label"], estilos["ia_label"]), Paragraph(f"{nota}/4", estilos["ia_score"]), Paragraph(p["sug"], estilos["ia_sug"])])
    t = Table([cells], colWidths=[cw]*len(perguntas_ia))
    t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(-1,-1),CINZA_CLARO),("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),12),("LEFTPADDING",(0,0),(-1,-1),14),("RIGHTPADDING",(0,0),(-1,-1),8),("LINEAFTER",(0,0),(1,0),0.5,CINZA_MEDIO),("LINEABOVE",(0,0),(-1,0),0.5,CINZA_MEDIO)]))
    return t

# ── Rodapé PDF ────────────────────────────────────────────────────────────────
def _rodape(estilos):
    W    = PAGE_W - 2 * cm
    data = [[Paragraph("smart-caixilho.streamlit.app", estilos["rodape"]), Paragraph("ASES Consultoria em Esquadrias", ParagraphStyle("rd", fontName="Helvetica-Bold", fontSize=7, textColor=DOURADO, alignment=2))]]
    t = Table(data, colWidths=[W*0.6, W*0.4])
    t.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),("LEFTPADDING",(0,0),(-1,-1),14),("RIGHTPADDING",(0,0),(-1,-1),8),("LINEABOVE",(0,0),(-1,0),0.5,CINZA_MEDIO),("BACKGROUND",(0,0),(-1,-1),BRANCO)]))
    return t

# ── Função principal PDF ──────────────────────────────────────────────────────
def gerar_relatorio_pdf(empresa, responsavel, cargo, email, telefone, respostas, nivel, total, pct, data_hoje):
    perguntas_principais = [
        {"id":"Q1",  "dim":"Integracao & Dados",   "sug":"Padronizar orcamento e integrar com projeto/producao."},
        {"id":"Q2",  "dim":"Gestao & Indicadores", "sug":"Criar 3 indicadores semanais de producao e vendas."},
        {"id":"Q3",  "dim":"Automacao",             "sug":"Mapear gargalos e avaliar automacao incremental."},
        {"id":"Q4",  "dim":"Integracao & Dados",   "sug":"Conectar producao ao ERP, mesmo via importacao manual."},
        {"id":"Q5",  "dim":"Integracao & Dados",   "sug":"Definir fluxo ponta a ponta com checkpoints claros."},
        {"id":"Q6",  "dim":"Pessoas & Cultura",    "sug":"Implementar 1 treinamento digital por mes."},
        {"id":"Q7",  "dim":"Pessoas & Cultura",    "sug":"Reuniao semanal com indicadores - metodo PDCA."},
    ]
    perguntas_ia = [
        {"id":"Q08","dim":"Prontidao para IA","label":"Organizacao de dados",   "sug":"Digitalize um setor por vez para criar base de dados."},
        {"id":"Q09","dim":"Prontidao para IA","label":"Conhecimento em IA",     "sug":"Reserve 1h/mes para explorar ferramentas de IA do setor."},
        {"id":"Q10","dim":"Prontidao para IA","label":"Uso de IA em operacoes", "sug":"Experimente um assistente de orcamento com IA."},
    ]
    dims = {}
    for p in perguntas_principais:
        d = p["dim"]
        if d not in dims: dims[d] = {"total":0,"count":0,"media":0.0}
        dims[d]["total"] += respostas.get(p["id"], 0)
        dims[d]["count"] += 1
    for d in dims:
        dims[d]["media"] = dims[d]["total"] / dims[d]["count"]
    # Adicionar Prontidao para IA como dimensao no radar
    ia_media = round((respostas.get("Q08",0) + respostas.get("Q09",0) + respostas.get("Q10",0)) / 3, 2)
    dims["Prontidao para IA"] = {"total": respostas.get("Q08",0)+respostas.get("Q09",0)+respostas.get("Q10",0), "count":3, "media": ia_media}

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=cm, rightMargin=cm, topMargin=cm, bottomMargin=cm)
    estilos = _estilos()
    story   = []
    for elem in _cabecalho(empresa, responsavel, cargo, data_hoje, estilos):
        story.append(elem)
    story.append(_metricas(total, pct, nivel, estilos))
    story.append(Spacer(1, 6))
    story.append(_radar_e_recs(dims, perguntas_principais, respostas, estilos))
    story.append(Spacer(1, 6))
    ia_header = Drawing(PAGE_W - 2*cm, 28)
    ia_header.add(Rect(0, 0, PAGE_W - 2*cm, 28, fillColor=AZUL_ESCURO, strokeColor=None))
    ia_header.add(String(16, 10, "IA  -  PRONTIDAO PARA INTELIGENCIA ARTIFICIAL", fontName="Helvetica-Bold", fontSize=9, fillColor=DOURADO))
    story.append(ia_header)
    story.append(_bloco_ia(perguntas_ia, respostas, estilos))
    story.append(Spacer(1, 6))
    story.append(_rodape(estilos))
    doc.build(story)
    buf.seek(0)
    return buf.read()


# =============================================================================
# STREAMLIT APP
# =============================================================================
st.set_page_config(page_title="Diagnóstico Smart Caixilho", layout="centered")

if 'db_leads' not in st.session_state:
    st.session_state['db_leads'] = []

st.title("Diagnóstico Smart Caixilho")
st.subheader("Modernização da Cadeia de Esquadrias de Alumínio")
st.markdown("---")

with st.expander("📝 Passo 1: Cadastro da Empresa", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        empresa     = st.text_input("Nome da Empresa")
        responsavel = st.text_input("Responsável / Cargo")
    with col2:
        telefone = st.text_input("Telefone (WhatsApp)")
        email    = st.text_input("E-mail de Contato")

st.markdown("### 📝 Passo 2: Avaliação de Maturidade")
st.markdown("""
> Este diagnóstico avalia a maturidade digital da sua fábrica em automação,
> integração de dados, gestão e cultura de inovação. Responda com sinceridade
> — não há certo ou errado. Em menos de 5 minutos, você recebe um relatório
> personalizado com seu perfil atual e recomendações práticas para evoluir.
""")
st.info("Deslize para dar uma nota: 0 - Inexistente | 1 - Inicial | 2 - Parcial | 3 - Estruturado | 4 - Integrado")

perguntas = [
    {"id":"Q1",  "dim":"Integração & Dados",
     "txt":"Os orçamentos são feitos manualmente ou em software integrado?",
     "desc":"O orçamento é o ponto de partida de quase tudo na fábrica. Quando feito de forma manual ou isolada, erros e retrabalhos se multiplicam ao longo da produção.",
     "sug":"Padronizar o processo de orçamento e integrar com projeto/produção."},
    {"id":"Q2",  "dim":"Gestão & Indicadores",
     "txt":"A empresa coleta e analisa dados de produção e vendas?",
     "desc":"Empresas que tomam decisões baseadas em dados crescem mais rápido e erram menos. Esta pergunta mede se sua gestão é orientada por números reais ou por intuição.",
     "sug":"Criar rotina mínima de coleta de dados e transformar em 3 indicadores semanais."},
    {"id":"Q3",  "dim":"Automação",
     "txt":"Existem máquinas CNC ou equipamentos automatizados?",
     "desc":"A automação reduz perdas de material, aumenta precisão e libera mão de obra para tarefas de maior valor. É um dos pilares centrais da Indústria 4.0.",
     "sug":"Mapear gargalos e avaliar automação incremental no processo mais crítico."},
    {"id":"Q4",  "dim":"Integração & Dados",
     "txt":"Os equipamentos estão conectados a softwares de projeto ou ERP?",
     "desc":"Quando a máquina e o software não se conversam, dados valiosos de produção ficam perdidos. A conectividade entre equipamentos e sistemas transforma dados em decisões.",
     "sug":"Conectar dados de produção ao software/ERP (mesmo que via importação)."},
    {"id":"Q5",  "dim":"Integração & Dados",
     "txt":"Há integração entre orçamento, projeto, produção e logística?",
     "desc":"Do orçamento à entrega, cada setor desconectado é um gargalo em potencial. A integração de processos é o que permite escalar sem perder controle.",
     "sug":"Definir fluxo ponta a ponta e criar responsáveis e checkpoints."},
    {"id":"Q6",  "dim":"Pessoas & Cultura",
     "txt":"Os colaboradores recebem treinamentos em tecnologias digitais?",
     "desc":"Tecnologia sem capacitação não gera resultado. Esta pergunta avalia se as pessoas da empresa estão sendo preparadas para operar em um ambiente cada vez mais digital.",
     "sug":"Plano de capacitação: 1 treinamento prático por mês."},
    {"id":"Q7",  "dim":"Pessoas & Cultura",
     "txt":"A liderança incentiva a inovação e o uso de dados?",
     "desc":"A transformação digital começa pela liderança. Quando a gestão incentiva o uso de dados e inovação, toda a equipe tende a seguir o mesmo caminho.",
     "sug":"Implantar ritual de gestão: reunião semanal com indicadores (PDCA)."},
    {"id":"Q08", "dim":"Prontidão para IA",
     "txt":"A empresa coleta e armazena dados de produção, vendas ou processos de forma organizada?",
     "desc":"Dados organizados são o combustível da inteligência artificial. Sem eles, nenhuma ferramenta de IA funciona bem — independente de quanto se invista.",
     "sug":"Sem dados organizados não existe IA aplicável: comece digitalizando um setor por vez."},
    {"id":"Q09", "dim":"Prontidão para IA",
     "txt":"A liderança conhece e avalia o uso de ferramentas de IA aplicadas ao setor, como previsão de demanda, otimização de corte ou assistentes de orçamento?",
     "desc":"A IA já está transformando fábricas no setor. Esta pergunta mede se sua liderança está acompanhando esse movimento ou sendo surpreendida por ele.",
     "sug":"Reserve 1h por mês para explorar ferramentas de IA do setor: YouTube, feiras e fornecedores são bons pontos de partida."},
    {"id":"Q10", "dim":"Prontidão para IA",
     "txt":"A empresa utiliza ou já testou alguma ferramenta com IA para apoiar decisões operacionais ou comerciais?",
     "desc":"Usar IA não exige grandes investimentos para começar. Esta pergunta avalia se a empresa já deu os primeiros passos práticos nessa direção.",
     "sug":"Comece por uma ferramenta simples: assistente de orçamento com IA ou chatbot de atendimento ao cliente."},
]

respostas = {}
for p in perguntas:
    st.markdown(f"**{p['id']}** — {p['txt']}")
    st.caption(p['desc'])
    respostas[p['id']] = st.select_slider(
        label=p['id'], options=[0,1,2,3,4],
        key=p['id'], label_visibility="collapsed"
    )
    st.markdown("")

if st.button("📊 FINALIZAR DIAGNÓSTICO E GERAR RELATÓRIO"):
    if not empresa or not email:
        st.error("⚠️ Por favor, preencha os dados de cadastro (Empresa e E-mail) antes de continuar.")
    else:
        total     = sum(respostas.values())
        pct       = (total / 40) * 100
        data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")

        if total <= 10:   nivel = "Nível 1 – Operação Invisível"
        elif total <= 20: nivel = "Nível 2 – Parcialmente Visível"
        elif total <= 30: nivel = "Nível 3 – Operação Controlada"
        else:             nivel = "Nível 4 – Operação Inteligente"

        # ── Salvar no Google Sheets ───────────────────────────────────────────
        dados_sheets = {
            "Data":        data_hoje,
            "Empresa":     empresa,
            "Responsavel": responsavel,
            "Telefone":    telefone,
            "Email":       email,
            "Pontuacao":   total,
            "Percentual":  f"{pct:.0f}%",
            "Nivel":       nivel,
            "Q1":  respostas["Q1"],
            "Q2":  respostas["Q2"],
            "Q3":  respostas["Q3"],
            "Q4":  respostas["Q4"],
            "Q5":  respostas["Q5"],
            "Q6":  respostas["Q6"],
            "Q7":  respostas["Q7"],
            "Q08": respostas["Q08"],
            "Q09": respostas["Q09"],
            "Q10": respostas["Q10"],
        }
        salvar_no_sheets(dados_sheets)

        # ── Exibir resultados ─────────────────────────────────────────────────
        st.success(f"### Diagnóstico Concluído para {empresa}!")
        c1, c2, c3 = st.columns(3)
        c1.metric("Pontos", f"{total}/40")
        c2.metric("Maturidade", f"{pct:.0f}%")
        c3.info(f"**{nivel}**")

        # Radar com mesmas 5 dimensoes do PDF
        dims_radar = {
            "Integracao & Dados":   round((respostas["Q1"] + respostas["Q4"] + respostas["Q5"]) / 3, 2),
            "Gestao & Indicadores": respostas["Q2"],
            "Automacao":            respostas["Q3"],
            "Pessoas & Cultura":    round((respostas["Q6"] + respostas["Q7"]) / 2, 2),
            "Prontidao para IA":    round((respostas["Q08"] + respostas["Q09"] + respostas["Q10"]) / 3, 2),
        }
        fig = go.Figure(data=go.Scatterpolar(
            r=list(dims_radar.values()),
            theta=list(dims_radar.keys()),
            fill="toself", line_color="#C9A84C", fillcolor="rgba(201,168,76,0.18)"
        ))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,4])), showlegend=False)
        st.plotly_chart(fig)

        st.subheader("💡 Recomendações Prioritárias")
        for p in sorted(perguntas, key=lambda x: respostas[x['id']])[:3]:
            st.warning(f"**{p['dim']}**: {p['sug']}")

        st.markdown("---")
        with st.spinner("Gerando seu relatório em PDF..."):
            pdf_bytes = gerar_relatorio_pdf(
                empresa=empresa, responsavel=responsavel, cargo=responsavel,
                email=email, telefone=telefone, respostas=respostas,
                nivel=nivel, total=total, pct=int(pct), data_hoje=data_hoje,
            )
        st.download_button(
            label="📥 Baixar Relatório Completo (PDF)",
            data=pdf_bytes,
            file_name=f"SmartCaixilho_{empresa.replace(' ','_')}.pdf",
            mime="application/pdf"
        )

# ── Painel secreto ────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
senha = st.sidebar.text_input("🔑 Área do Orientador (Senha)", type="password")
if senha == "cba2026":
    st.sidebar.success("Acesso Autorizado")
    st.markdown("---")
    st.header("🕵️ Painel Interno")

    # Diagnóstico temporário
    try:
        raw = st.secrets["gcp_service_account"]
        pk  = str(raw["private_key"])
        st.code(f"Tipo private_key: {type(pk).__name__}\nInicio: {pk[:40]}\nFim: {pk[-40:]}\nTem \\n: {'\\\\n' in pk}\nTem \\n real: {chr(10) in pk}")
    except Exception as diag_e:
        st.error(f"Diagnóstico: {diag_e}")
    try:
        raw  = st.secrets["gcp_service_account"]
        info = {
            "type":                        str(raw["type"]),
            "project_id":                  str(raw["project_id"]),
            "private_key_id":              str(raw["private_key_id"]),
            "private_key":                 str(raw["private_key"]).replace("\\n", "\n"),
            "client_email":                str(raw["client_email"]),
            "client_id":                   str(raw["client_id"]),
            "auth_uri":                    str(raw["auth_uri"]),
            "token_uri":                   str(raw["token_uri"]),
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url":        f"https://www.googleapis.com/robot/v1/metadata/x509/{str(raw['client_email']).replace('@', '%40')}",
        }
        client = gspread.service_account_from_dict(info)
        sheet  = client.open("SmartCaixilho_Resultados").sheet1
        dados  = sheet.get_all_records()
        if dados:
            df = pd.DataFrame(dados)
            st.dataframe(df)
            st.download_button("📥 Baixar Base Completa (CSV)",
                               df.to_csv(index=False).encode('utf-8'),
                               "SmartCaixilho_Resultados.csv", "text/csv")
            st.metric("Total de diagnósticos", len(df))
        else:
            st.info("Nenhum diagnóstico registrado ainda.")
    except Exception as e:
        st.error(f"Erro ao carregar planilha: {e}")
