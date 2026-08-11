import streamlit as st
from modules import auth, projects, requirements, testing, metrics
from config.database import supabase
from config.ai_config import render_ai_provider_selector

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="QA & Requisitos Hub",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# 2. CONTROLE DE AUTENTICAÇÃO
# ==============================================================================
if not auth.is_authenticated():
    auth.render_auth_page()
    st.stop()

user_info = auth.get_logged_user()

# ==============================================================================
# 3. BUSCA DE EQUIPES VINCULADAS AO USUÁRIO (Relação N para N)
# ==============================================================================
user_teams_res = (
    supabase.table("team_members")
    .select("team_id, role, teams(id, name, invite_code)")
    .eq("user_id", user_info["id"])
    .execute()
)

user_teams = []
if user_teams_res.data:
    for item in user_teams_res.data:
        if item.get("teams"):
            team_info = item["teams"]
            team_info["user_role"] = item["role"]
            user_teams.append(team_info)

# Se o usuário não está vinculado a nenhuma equipe, exibe o onboarding de criação/entrada
if not user_teams:
    auth.render_team_onboarding()
    st.stop()

# Gerenciamento da Equipe Ativa na Sessão
if "current_team_id" not in st.session_state or not st.session_state["current_team_id"]:
    st.session_state["current_team_id"] = user_teams[0]["id"]

# Garante que o current_team_id pertence de fato às equipes do usuário
valid_team_ids = [t["id"] for t in user_teams]
if st.session_state["current_team_id"] not in valid_team_ids:
    st.session_state["current_team_id"] = user_teams[0]["id"]

# Define os dados da equipe ativa atual
active_team = next((t for t in user_teams if t["id"] == st.session_state["current_team_id"]), user_teams[0])
user_info["team_id"] = active_team["id"]
user_info["role"] = active_team.get("user_role", "editor")

# ==============================================================================
# 4. SIDEBAR (PERFIL, SELETOR DE EQUIPE, PROJETO E NAVEGAÇÃO)
# ==============================================================================
with st.sidebar:
    st.title("🎯 QA Hub")
    
    st.write(f"👤 **Usuário:** {user_info.get('name', 'Usuário')}")
    st.caption(f"📧 {user_info.get('email', '')}")
    st.caption(f"🛡️ **Papel:** `{user_info.get('role', 'editor')}`")
    
    st.divider()

    # --- SELETOR DE EQUIPE / ORGANIZAÇÃO ---
    st.subheader("🏢 Organização Ativa")
    team_options = {t["name"]: t["id"] for t in user_teams}
    selected_team_name = st.selectbox(
        "Alternar Equipe:", 
        options=list(team_options.keys()), 
        index=list(team_options.values()).index(active_team["id"])
    )
    
    # Se o usuário trocou de equipe no selectbox, atualiza a sessão e recarrega
    if team_options[selected_team_name] != st.session_state["current_team_id"]:
        st.session_state["current_team_id"] = team_options[selected_team_name]
        st.rerun()

    st.info(f"🔑 **Código da Equipe:** `{active_team.get('invite_code', 'N/A')}`")

    # Opção para entrar em outra equipe via código diretamente na barra lateral
    with st.expander("➕ Entrar em Outra Equipe"):
        with st.form("sidebar_join_team"):
            new_code = st.text_input("Código de Convite", placeholder="Ex: A1B2C3")
            if st.form_submit_button("Vincular Equipe"):
                if new_code.strip():
                    t_lookup = supabase.table("teams").select("id, name").eq("invite_code", new_code.strip().upper()).execute()
                    if t_lookup.data:
                        found_t = t_lookup.data[0]
                        # Insere na tabela de membros (caso não exista, faz o upsert)
                        supabase.table("team_members").upsert({
                            "team_id": found_t["id"],
                            "user_id": user_info["id"],
                            "role": "editor"
                        }, on_conflict="team_id,user_id").execute()
                        
                        st.session_state["current_team_id"] = found_t["id"]
                        st.success(f"Vinculado à equipe '{found_t['name']}' com sucesso!")
                        st.rerun()
                    else:
                        st.error("Código de convite inválido.")
                else:
                    st.error("Digite o código.")

    if st.button("🚪 Sair / Logout", use_container_width=True):
        auth.logout()

    st.divider()

    # Seletor de Provedor de IA
    render_ai_provider_selector()
    st.divider()

    # Navegação entre Módulos
    st.subheader("🧭 Navegação")
    page_options = [
        "📁 Gestão de Projetos",
        "📝 Requisitos",
        "🧪 Módulo de Testes",
        "📊 Métricas & Exportação",
    ]
    
    # Adiciona aba de gestão de membros se for admin da equipe ativa
    if user_info.get("role") == "admin":
        page_options.append("👥 Gestão de Equipe")

    page = st.radio("Ir para:", page_options)

# ==============================================================================
# 5. CARREGAMENTO DO PROJETO ATIVO
# ==============================================================================
active_project = None
if page != "👥 Gestão de Equipe":
    active_project = projects.render_project_selector()
    
    if not active_project and page in ["📝 Requisitos", "🧪 Módulo de Testes", "📊 Métricas & Exportação"]:
        st.warning("⚠️ **Nenhum projeto selecionado!**")
        st.info("Por favor, selecione ou crie um projeto no menu lateral (ou no módulo **Gestão de Projetos**) para prosseguir.")
        st.stop()

# ==============================================================================
# 6. EXECUÇÃO DO MÓDULO SELECIONADO
# ==============================================================================
if page == "📁 Gestão de Projetos":
    projects.render_projects_page()

elif page == "📝 Requisitos":
    requirements.render_requirements_module()

elif page == "🧪 Módulo de Testes":
    testing.render_testing_module(active_project["id"])

elif page == "📊 Métricas & Exportação":
    project_id = active_project["id"]
    try:
        test_cases = supabase.table("test_cases").select("*").eq("project_id", project_id).execute().data or []
        bug_reports = supabase.table("bug_reports").select("*").eq("project_id", project_id).execute().data or []
        risk_matrix = supabase.table("risk_matrix").select("*").eq("project_id", project_id).execute().data or []
        user_stories = supabase.table("user_stories").select("*").eq("project_id", project_id).execute().data or []
    except Exception as e:
        st.error(f"Erro ao carregar métricas do Supabase: {e}")
        test_cases, bug_reports, risk_matrix, user_stories = [], [], [], []

    metrics.render_metrics_dashboard(test_cases, bug_reports, risk_matrix, user_stories)

elif page == "👥 Gestão de Equipe":
    st.title("👥 Gestão de Membros da Organização")
    st.write(f"Gerencie os usuários vinculados à organização ativa **{active_team.get('name')}**.")
    
    # Busca membros na tabela team_members cruzando com a tabela users
    members_res = (
        supabase.table("team_members")
        .select("role, users(id, name, email, created_at)")
        .eq("team_id", active_team["id"])
        .execute()
    )
    
    members = []
    if members_res.data:
        for m in members_res.data:
            if m.get("users"):
                u_data = m["users"]
                u_data["role"] = m["role"]
                members.append(u_data)
    
    for member in members:
        cols = st.columns([3, 2, 2, 2])
        with cols[0]:
            st.write(f"**{member['name']}**")
            st.caption(member['email'])
        with cols[1]:
            st.write(f"Papel: `{member['role']}`")
        with cols[2]:
            st.write(f"Criado em: {member['created_at'][:10] if member.get('created_at') else ''}")
        with cols[3]:
            # Impede o admin de se remover a si mesmo por engano nesta tela
            if member["id"] != user_info["id"]:
                if st.button("🗑️ Remover", key=f"rm_mem_{member['id']}"):
                    # Remove da tabela de relacionamento team_members (não deleta o usuário do sistema)
                    supabase.table("team_members").delete().eq("team_id", active_team["id"]).eq("user_id", member["id"]).execute()
                    st.success(f"Usuário {member['name']} removido da equipe.")
                    st.rerun()
            else:
                st.caption("Você (Admin)")