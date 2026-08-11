import pandas as pd
import plotly.express as px
import streamlit as st
from config.ai_config import call_ai_service

def render_metrics_dashboard(
    test_cases: list[dict],
    bug_reports: list[dict],
    risk_matrix: list[dict],
    user_stories: list[dict],
):
    st.title("📊 Dashboard de Métricas & Exportação")

    df_tc = pd.DataFrame(test_cases)
    df_bugs = pd.DataFrame(bug_reports)
    df_risks = pd.DataFrame(risk_matrix)
    df_stories = pd.DataFrame(user_stories)

    # ------------------------------------------
    # 1. ANÁLISE DE SAÚDE E RISCOS DA RELEASE
    # ------------------------------------------
    st.subheader("🤖 Análise Inteligente de Qualidade (Release Health)")
    
    if "ai_analysis_result" not in st.session_state:
        st.session_state["ai_analysis_result"] = None

    # Métricas agregadas para cruzamento
    total_tc = len(df_tc)
    passed_tc = len(df_tc[df_tc["status"] == "Passou"]) if not df_tc.empty and "status" in df_tc.columns else 0
    failed_tc = len(df_tc[df_tc["status"] == "Falhou"]) if not df_tc.empty and "status" in df_tc.columns else 0
    
    bugs_open = len(df_bugs[df_bugs["status"].isin(["Aberto", "Em correção"])]) if not df_bugs.empty and "status" in df_bugs.columns else len(df_bugs)
    high_risks = len(df_risks[df_risks["risk_score"] >= 15]) if not df_risks.empty and "risk_score" in df_risks.columns else 0

    col_btn, col_info = st.columns([2, 3])
    with col_btn:
        if st.button("✨ Analisar Saúde da Release com IA", type="primary", use_container_width=True):
            with st.spinner("IA consolidando Casos de Teste, Bugs e Matriz de Risco..."):
                prompt = f"""
                Atue como um QA Lead especialista sênior. Analise estes dados consolidados do projeto e elabore um parecer executivo:

                - Casos de Teste: {total_tc} total (Passaram: {passed_tc}, Falharam: {failed_tc})
                - Bugs Abertos/Em Correção: {bugs_open}
                - Riscos Críticos na Matriz (Score >= 15): {high_risks}
                - Histórias de Usuário Mapeadas: {len(df_stories)}

                Forneça de forma estruturada:
                1. Parecer Geral de Risco para Deploy (Baixo, Médio ou Alto) com justificativa técnica.
                2. Correlação entre os riscos identificados e a cobertura de testes atual.
                3. Top 3 Recomendações Críticas para a equipe de QA/Dev antes do Go-Live.
                """
                try:
                    res = call_ai_service(prompt)
                    st.session_state["ai_analysis_result"] = res
                except Exception as e:
                    st.session_state["ai_analysis_result"] = None
                    st.warning(f"Servidor de IA indisponível ou sem chave configurada. Exibindo estatísticas estruturadas locais. (Erro: {e})")

    # Exibe resultado da IA ou fallback estatístico inteligente se a IA estiver ausente
    if st.session_state["ai_analysis_result"]:
        st.info(st.session_state["ai_analysis_result"])
    else:
        # Fallback Estatístico Profissional (Funciona 100% sem IA)
        st.markdown("### 📊 Relatório Estatístico Automatizado (Modo Offline/Estatístico)")
        risk_level = "🔴 ALTO" if high_risks > 2 or failed_tc > 0 else ("🟡 MÉDIO" if bugs_open > 0 else "🟢 BAIXO")
        st.write(f"**Nível Estimado de Risco da Release:** {risk_level}")
        st.markdown(f"""
        - **Resumo de Cobertura:** {passed_tc} de {total_tc} testes aprovados com sucesso.
        - **Atenção a Bugs:** Existem `{bugs_open}` bugs pendentes de resolução na esteira.
        - **Mitigação de Riscos:** Há `{high_risks}` riscos mapeados com alta pontuação na Matriz de Risco. Recomenda-se validação manual pré-release.
        """)

    st.divider()

    # ------------------------------------------
    # 2. KPIS E GRÁFICOS EXECUTIVOS
    # ------------------------------------------
    st.subheader("🚀 Indicadores Chave de Desempenho (KPIs)")
    c1, c2, c3, c4 = st.columns(4)
    
    c1.metric("Total Casos de Teste", total_tc)
    
    rate = (passed_tc / total_tc * 100) if total_tc > 0 else 0.0
    c2.metric("Taxa de Sucesso", f"{rate:.1f}%")
    
    c3.metric("Bugs Registrados", len(df_bugs))
    c4.metric("Riscos Mapeados", len(df_risks))

    st.markdown("---")
    
    # Gráficos Visuais Avançados (Plotly)
    g1, g2 = st.columns(2)
    with g1:
        if not df_tc.empty and "status" in df_tc.columns:
            fig_tc = px.pie(df_tc, names="status", title="Distribuição de Casos de Teste por Status", hole=0.4)
            st.plotly_chart(fig_tc, use_container_width=True)
        else:
            st.info("Sem dados de testes suficientes para o gráfico.")

    with g2:
        if not df_bugs.empty and "severity" in df_bugs.columns:
            fig_bugs = px.bar(df_bugs, x="severity", title="Bugs por Nível de Severidade", color="severity")
            st.plotly_chart(fig_bugs, use_container_width=True)
        else:
            st.info("Sem dados de bugs suficientes para o gráfico.")

    # Terceira linha de gráficos: Matriz de Risco cruzada
    if not df_risks.empty and "risk_score" in df_risks.columns:
        st.markdown("### ⚠️ Distribuição de Riscos do Projeto")
        fig_risks = px.scatter(
            df_risks, 
            x="probability", 
            y="impact", 
            size="risk_score", 
            color="risk_type",
            hover_name="risk_description",
            title="Matriz de Risco (Probabilidade vs Impacto)"
        )
        st.plotly_chart(fig_risks, use_container_width=True)

    st.divider()

    # ------------------------------------------
    # 3. EXPORTAÇÃO E DOWNLOADS
    # ------------------------------------------
    st.subheader("📥 Exportação de Relatórios Executivos")
    
    analysis_text = st.session_state['ai_analysis_result'] if st.session_state['ai_analysis_result'] else "Análise gerada estatisticamente pela plataforma sem IA."
    
    report_text = f"""# Relatório Executivo de QA & Qualidade

## 📈 KPIs Gerais
- **Total de Casos de Teste:** {total_tc}
- **Taxa de Sucesso:** {rate:.1f}%
- **Bugs Registrados:** {len(df_bugs)}
- **Riscos Mapeados:** {len(df_risks)}
- **Histórias de Usuário:** {len(df_stories)}

## 🤖 Avaliação de Saúde da Release
{analysis_text}
"""

    st.download_button(
        label="📄 Baixar Relatório Executivo Completo (Markdown)",
        data=report_text,
        file_name="relatorio_executivo_qa.md",
        mime="text/markdown",
        use_container_width=True
    )