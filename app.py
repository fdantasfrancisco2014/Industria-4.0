import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from gerar_pdf import gerar_relatorio_pdf

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Diagnóstico Smart Caixilho", layout="centered")

if 'db_leads' not in st.session_state:
    st.session_state['db_leads'] = []

# --- CABEÇALHO ---
st.title("Diagnóstico Smart Caixilho")
st.subheader("Modernização da Cadeia de Esquadrias de Alumínio")
st.markdown("---")

# --- 1. CADASTRO ---
with st.expander("📝 Passo 1: Cadastro da Empresa", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        empresa     = st.text_input("Nome da Empresa")
        responsavel = st.text_input("Responsável / Cargo")
    with col2:
        telefone = st.text_input("Telefone (WhatsApp)")
        email    = st.text_input("E-mail de Contato")

# --- 2. QUESTIONÁRIO ---
st.markdown("### 📝 Passo 2: Avaliação de Maturidade")

st.markdown("""
> Este diagnóstico avalia a maturidade digital da sua fábrica em automação,
> integração de dados, gestão e cultura de inovação. Responda com sinceridade
> — não há certo ou errado. Em menos de 5 minutos, você recebe um relatório
> personalizado com seu perfil atual e recomendações práticas para evoluir.
""")

st.info("Deslize para dar uma nota: 0 - Inexistente | 1 - Inicial | 2 - Parcial | 3 - Estruturado | 4 - Integrado")

perguntas = [
    {
        "id": "Q1", "dim": "Integração & Dados",
        "txt": "Os orçamentos são feitos manualmente ou em software integrado?",
        "desc": "O orçamento é o ponto de partida de quase tudo na fábrica. Quando feito de forma manual ou isolada, erros e retrabalhos se multiplicam ao longo da produção.",
        "sug": "Padronizar o processo de orçamento e integrar com projeto/produção."
    },
    {
        "id": "Q2", "dim": "Gestão & Indicadores",
        "txt": "A empresa coleta e analisa dados de produção e vendas?",
        "desc": "Empresas que tomam decisões baseadas em dados crescem mais rápido e erram menos. Esta pergunta mede se sua gestão é orientada por números reais ou por intuição.",
        "sug": "Criar rotina mínima de coleta de dados e transformar em 3 indicadores semanais."
    },
    {
        "id": "Q3", "dim": "Automação",
        "txt": "Existem máquinas CNC ou equipamentos automatizados?",
        "desc": "A automação reduz perdas de material, aumenta precisão e libera mão de obra para tarefas de maior valor. É um dos pilares centrais da Indústria 4.0.",
        "sug": "Mapear gargalos e avaliar automação incremental no processo mais crítico."
    },
    {
        "id": "Q4", "dim": "Integração & Dados",
        "txt": "Os equipamentos estão conectados a softwares de projeto ou ERP?",
        "desc": "Quando a máquina e o software não se conversam, dados valiosos de produção ficam perdidos. A conectividade entre equipamentos e sistemas transforma dados em decisões.",
        "sug": "Conectar dados de produção ao software/ERP (mesmo que via importação)."
    },
    {
        "id": "Q5", "dim": "Integração & Dados",
        "txt": "Há integração entre orçamento, projeto, produção e logística?",
        "desc": "Do orçamento à entrega, cada setor desconectado é um gargalo em potencial. A integração de processos é o que permite escalar sem perder controle.",
        "sug": "Definir fluxo ponta a ponta e criar responsáveis e checkpoints."
    },
    {
        "id": "Q6", "dim": "Pessoas & Cultura",
        "txt": "Os colaboradores recebem treinamentos em tecnologias digitais?",
        "desc": "Tecnologia sem capacitação não gera resultado. Esta pergunta avalia se as pessoas da empresa estão sendo preparadas para operar em um ambiente cada vez mais digital.",
        "sug": "Plano de capacitação: 1 treinamento prático por mês."
    },
    {
        "id": "Q7", "dim": "Pessoas & Cultura",
        "txt": "A liderança incentiva a inovação e o uso de dados?",
        "desc": "A transformação digital começa pela liderança. Quando a gestão incentiva o uso de dados e inovação, toda a equipe tende a seguir o mesmo caminho.",
        "sug": "Implantar ritual de gestão: reunião semanal com indicadores (PDCA)."
    },
    {
        "id": "Q08", "dim": "Prontidão para IA",
        "txt": "A empresa coleta e armazena dados de produção, vendas ou processos de forma organizada?",
        "desc": "Dados organizados são o combustível da inteligência artificial. Sem eles, nenhuma ferramenta de IA funciona bem — independente de quanto se invista.",
        "sug": "Sem dados organizados não existe IA aplicável: comece digitalizando um setor por vez."
    },
    {
        "id": "Q09", "dim": "Prontidão para IA",
        "txt": "A liderança conhece e avalia o uso de ferramentas de IA aplicadas ao setor, como previsão de demanda, otimização de corte ou assistentes de orçamento?",
        "desc": "A IA já está transformando fábricas no setor. Esta pergunta mede se sua liderança está acompanhando esse movimento ou sendo surpreendida por ele.",
        "sug": "Reserve 1h por mês para explorar ferramentas de IA do setor: YouTube, feiras e fornecedores são bons pontos de partida."
    },
    {
        "id": "Q10", "dim": "Prontidão para IA",
        "txt": "A empresa utiliza ou já testou alguma ferramenta com IA para apoiar decisões operacionais ou comerciais?",
        "desc": "Usar IA não exige grandes investimentos para começar. Esta pergunta avalia se a empresa já deu os primeiros passos práticos nessa direção.",
        "sug": "Comece por uma ferramenta simples: assistente de orçamento com IA ou chatbot de atendimento ao cliente."
    },
]

respostas = {}
for p in perguntas:
    st.markdown(f"**{p['id']}** — {p['txt']}")
    st.caption(p['desc'])
    respostas[p['id']] = st.select_slider(
        label=p['id'],
        options=[0, 1, 2, 3, 4],
        key=p['id'],
        label_visibility="collapsed"
    )
    st.markdown("")

# --- 3. PROCESSAMENTO ---
if st.button("📊 FINALIZAR DIAGNÓSTICO E GERAR RELATÓRIO"):
    if not empresa or not email:
        st.error("⚠️ Por favor, preencha os dados de cadastro (Empresa e E-mail) antes de continuar.")
    else:
        total    = sum(respostas.values())
        pct      = (total / 40) * 100
        data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")

        if total <= 10:   nivel = "Nível 1 – Operação Invisível"
        elif total <= 20: nivel = "Nível 2 – Parcialmente Visível"
        elif total <= 30: nivel = "Nível 3 – Operação Controlada"
        else:             nivel = "Nível 4 – Operação Inteligente"

        st.session_state['db_leads'].append({
            "Data": data_hoje, "Empresa": empresa, "Responsavel": responsavel,
            "Telefone": telefone, "Email": email, "Pontuacao": total, "Nivel": nivel
        })

        st.success(f"### Diagnóstico Concluído para {empresa}!")
        c1, c2, c3 = st.columns(3)
        c1.metric("Pontos", f"{total}/40")
        c2.metric("Maturidade", f"{pct:.0f}%")
        c3.info(f"**{nivel}**")

        # Gráfico Radar
        df_radar    = pd.DataFrame([{"Dim": p['dim'], "Nota": respostas[p['id']]} for p in perguntas])
        resumo_radar = df_radar.groupby("Dim")["Nota"].mean().reset_index()

        fig = go.Figure(data=go.Scatterpolar(
            r=resumo_radar['Nota'],
            theta=resumo_radar['Dim'],
            fill='toself',
            line_color='#C9A84C',
            fillcolor='rgba(201,168,76,0.18)'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 4])),
            showlegend=False
        )
        st.plotly_chart(fig)

        # Recomendações
        st.subheader("💡 Recomendações Prioritárias")
        piores = sorted(perguntas, key=lambda x: respostas[x['id']])[:3]
        for p in piores:
            st.warning(f"**{p['dim']}**: {p['sug']}")

        # Botão PDF
        st.markdown("---")
        with st.spinner("Gerando seu relatório em PDF..."):
            pdf_bytes = gerar_relatorio_pdf(
                empresa=empresa,
                responsavel=responsavel,
                cargo=responsavel,
                email=email,
                telefone=telefone,
                respostas=respostas,
                nivel=nivel,
                total=total,
                pct=int(pct),
                data_hoje=data_hoje,
            )

        st.download_button(
            label="📥 Baixar Relatório Completo (PDF)",
            data=pdf_bytes,
            file_name=f"SmartCaixilho_{empresa.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )

# --- 4. PAINEL SECRETO ---
st.sidebar.markdown("---")
senha = st.sidebar.text_input("🔑 Área do Orientador (Senha)", type="password")

if senha == "cba2026":
    st.sidebar.success("Acesso Autorizado")
    st.markdown("---")
    st.header("🕵️ Painel Interno de Leads")
    if st.session_state['db_leads']:
        df_leads = pd.DataFrame(st.session_state['db_leads'])
        st.dataframe(df_leads)
        csv = df_leads.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Base Completa (CSV)", csv,
                           "leads_smart_caixilho.csv", "text/csv")
    else:
        st.info("Nenhum diagnóstico realizado nesta sessão ainda.")
