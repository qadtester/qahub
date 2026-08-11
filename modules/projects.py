import streamlit as st
from config.database import supabase

def get_user_projects(team_id: str):
    res = supabase.table("projects").select("*").eq("team_id", team_id).execute()
    return res.data or []

def render_project_selector():
    user_info = st.session_state.get("user")
    if not user_info or "team_id" not in user_info:
        return None

    projects = get_user_projects(user_info["team_id"])
    if not projects:
        st.info("Nenhum projeto encontrado.")
        return None

    project_options = {p["name"]: p for p in projects}
    selected_name = st.selectbox("Selecione o Projeto:", options=list(project_options.keys()))
    
    active_project = project_options[selected_name]
    st.session_state["current_project_id"] = active_project["id"]
    return active_project

def render_projects_page():
    st.title("📁 Gestão de Projetos")
    user_info = st.session_state.get("user")
    if not user_info or "team_id" not in user_info:
        st.error("Usuário sem time vinculado.")
        return

    team_id = user_info["team_id"]
    tab_list, tab_create = st.tabs(["📌 Meus Projetos", "➕ Criar Novo Projeto"])

    with tab_list:
        projects = get_user_projects(team_id)
        if not projects:
            st.info("Nenhum projeto cadastrado ainda.")
        else:
            for proj in projects:
                with st.expander(f"📁 {proj['name']}"):
                    st.write(f"**Descrição:** {proj.get('description', 'Sem descrição')}")
                    st.caption(f"ID: `{proj['id']}`")
                    
                    # --- LISTA DE DOCUMENTOS JÁ CADASTRADOS NO PROJETO ---
                    docs = supabase.table("project_documents").select("*").eq("project_id", proj['id']).execute().data or []
                    if docs:
                        st.markdown("---")
                        st.markdown("📂 **Documentos/Contextos vinculados a este projeto:**")
                        for d in docs:
                            st.caption(f"📄 **{d['file_name']}** (Enviado em: {d['created_at'][:10]})")

                    # --- ADICIONAR DOCUMENTOS/CONTEXTO ADICIONAL ---
                    with st.expander("➕ Adicionar Novo Documento ou Texto"):
                        with st.form(key=f"form_add_context_{proj['id']}"):
                            st.write("Envie novos arquivos ou cole textos adicionais. Eles serão salvos no banco para enriquecer a base de conhecimento da IA.")
                            new_file = st.file_uploader("Novo documento (PDF, TXT, CSV):", type=["pdf", "txt", "csv"], key=f"file_{proj['id']}")
                            new_text = st.text_area("Ou adicione observações/regras extras em texto:", placeholder="Cole novas especificações aqui...", key=f"text_{proj['id']}")
                            
                            if st.form_submit_button("📥 Salvar Documento no Projeto"):
                                file_name = "Texto Manual"
                                file_content = ""

                                if new_file is not None:
                                    file_name = new_file.name
                                    try:
                                        file_content = new_file.read().decode("utf-8", errors="ignore")
                                    except Exception:
                                        file_content = ""

                                if new_text.strip():
                                    if file_content:
                                        file_content += f"\n\n{new_text}"
                                    else:
                                        file_content = new_text
                                        file_name = f"Nota de Texto - {proj['name']}"

                                if file_content.strip():
                                    supabase.table("project_documents").insert({
                                        "project_id": proj['id'],
                                        "file_name": file_name,
                                        "file_content": file_content
                                    }).execute()
                                    st.success("Documento salvo com sucesso na base do projeto!")
                                    st.rerun()
                                else:
                                    st.warning("Insira um texto ou envie um arquivo válido.")

                    st.markdown("---")
                    col_edit, col_del = st.columns(2)
                    
                    with col_edit:
                        with st.popover("✏️ Editar Projeto"):
                            new_name = st.text_input("Novo Nome", value=proj['name'], key=f"edit_p_name_{proj['id']}")
                            new_desc = st.text_area("Nova Descrição", value=proj.get('description', ''), key=f"edit_p_desc_{proj['id']}")
                            if st.button("Salvar Alterações", key=f"btn_save_p_{proj['id']}"):
                                supabase.table("projects").update({"name": new_name, "description": new_desc}).eq("id", proj['id']).execute()
                                st.success("Projeto atualizado!")
                                st.rerun()

                    with col_del:
                        with st.popover("🗑️ Excluir Projeto"):
                            st.warning("⚠️ **Atenção:** Esta ação excluirá permanentemente este projeto e TODOS os requisitos, testes, documentos e riscos associados!")
                            confirm_text = st.text_input("Digite 'EXCLUIR' para confirmar:", key=f"conf_del_p_{proj['id']}")
                            if st.button("Confirmar Exclusão", type="primary", key=f"btn_del_p_{proj['id']}"):
                                if confirm_text == "EXCLUIR":
                                    supabase.table("projects").delete().eq("id", proj['id']).execute()
                                    if st.session_state.get("current_project_id") == proj['id']:
                                        st.session_state["current_project_id"] = None
                                    st.success("Projeto e dados excluídos com sucesso!")
                                    st.rerun()
                                else:
                                    st.error("Palavra de confirmação incorreta.")

    with tab_create:
        with st.form("create_project_form", clear_on_submit=True):
            p_name = st.text_input("Nome do Projeto:")
            p_desc = st.text_area("Descrição do Projeto:")
            
            st.markdown("---")
            st.markdown("### 🤖 Documentação Inicial (Opcional)")
            uploaded_file = st.file_uploader("Carregar documento de escopo/requisitos (PDF, TXT, CSV):", type=["pdf", "txt", "csv"])
            p_raw_text = st.text_area("Ou cole o texto bruto de requisitos/contexto:", placeholder="Cole aqui os detalhes técnicos...")

            if st.form_submit_button("🚀 Criar Projeto"):
                if p_name:
                    # 1. Cria o projeto
                    res = supabase.table("projects").insert({
                        "team_id": team_id, 
                        "name": p_name, 
                        "description": p_desc
                    }).execute()
                    
                    # Se criou com sucesso e há dados de documento/texto, salva na tabela de documentos
                    if res.data and (uploaded_file is not None or p_raw_text.strip()):
                        new_proj_id = res.data[0]['id']
                        file_name = "Documento Inicial"
                        file_content = ""

                        if uploaded_file is not None:
                            file_name = uploaded_file.name
                            try:
                                file_content = uploaded_file.read().decode("utf-8", errors="ignore")
                            except Exception:
                                file_content = ""

                        if p_raw_text.strip():
                            if file_content:
                                file_content += f"\n\n{p_raw_text}"
                            else:
                                file_content = p_raw_text
                                file_name = "Contexto Inicial"

                        if file_content.strip():
                            supabase.table("project_documents").insert({
                                "project_id": new_proj_id,
                                "file_name": file_name,
                                "file_content": file_content
                            }).execute()

                    st.success("Projeto criado e documentação vinculada com sucesso!")
                    st.rerun()
                else:
                    st.error("O nome do projeto é obrigatório.")