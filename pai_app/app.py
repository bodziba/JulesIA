import streamlit as st
import os

import markdown
from config import SCOPES, SCOPE_GLOBAL, SCOPE_SYSTEM
from storage import get_all_tickets, add_ticket, delete_ticket, clear_all_tickets
from rag import index_pdf, get_indexed_documents, remove_document, remove_all_documents, get_relevant_context
from agent import analyze_ticket, extract_criticality
from streamlit_option_menu import option_menu

# --- Page Config ---
st.set_page_config(
    page_title="PAI — Publicenter Artificial Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load Custom CSS ---
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# --- Helpers ---
@st.cache_resource
def get_cached_components():
    return True

# Ensure cache setup
get_cached_components()

# --- Session State Management ---
if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0

def trigger_refresh():
    st.session_state.refresh_counter += 1

# --- Sidebar Navigation ---
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 20px;">
        <div style="background-color: var(--highlight-orange); border-radius: 8px; padding: 10px; margin-right: 15px;">
            <span style="font-size: 24px;">🧠</span>
        </div>
        <div>
            <div style="font-weight: bold; font-size: 20px; color: white;">PAI</div>
            <div style="font-size: 12px; color: #aaa;">Publicenter AI</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin-top: 0;'>", unsafe_allow_html=True)

    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Novo Chamado", "Base de Conhecimento", "Consulta RAG"],
        icons=["grid", "plus-circle", "book", "search"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "white", "font-size": "16px"},
            "nav-link": {"color": "white", "font-size": "15px", "text-align": "left", "margin":"0px", "--hover-color": "rgba(255,255,255,0.1)"},
            "nav-link-selected": {"background-color": "var(--highlight-orange)"},
        }
    )

    st.markdown("<br><br><br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background-color: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
        <div style="font-size: 12px; color: #aaa;">Powered by</div>
        <div style="font-weight: bold; color: var(--highlight-orange);">Publicenter AI</div>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# PAGE 1: DASHBOARD
# ==========================================
if selected == "Dashboard":

    # Header Area
    col_h1, col_h2 = st.columns([0.8, 0.2])
    with col_h1:
        st.markdown("<h1 style='margin-bottom: 0;'>Dashboard</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #6c757d; font-size: 1.1rem;'>Visão geral dos chamados e documentos</p>", unsafe_allow_html=True)
    with col_h2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Limpar tudo", key="btn_clear_all", help="Requer confirmação"):
            st.session_state.confirm_clear_all = True

    if st.session_state.get("confirm_clear_all", False):
        st.warning("Tem certeza que deseja apagar TODOS os chamados? Esta ação não pode ser desfeita.")
        col_c1, col_c2 = st.columns(2)
        if col_c1.button("Sim, apagar tudo", type="primary"):
            clear_all_tickets()
            st.session_state.confirm_clear_all = False
            st.success("Todos os chamados apagados.")
            trigger_refresh()
            st.rerun()
        if col_c2.button("Cancelar"):
            st.session_state.confirm_clear_all = False
            st.rerun()

    tickets = get_all_tickets()
    docs = get_indexed_documents()

    total_tickets = len(tickets)
    critical_tickets = sum(1 for t in tickets if t.get("criticality") == "Alta")
    total_docs = len(docs)
    total_analysis = total_tickets # Assuming 1 analysis per ticket

    # 4 Metric Cards Layout
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div>
                <div class="metric-title">Total de Chamados</div>
                <div class="metric-value">{total_tickets}</div>
            </div>
            <div class="metric-icon" style="color: var(--primary-blue);">🎫</div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown(f"""
        <div class="metric-card critical">
            <div>
                <div class="metric-title" style="color: #dc3545;">Chamados Críticos</div>
                <div class="metric-value" style="color: #dc3545;">{critical_tickets}</div>
            </div>
            <div class="metric-icon" style="color: #dc3545;">⚠️</div>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        st.markdown(f"""
        <div class="metric-card indexed">
            <div>
                <div class="metric-title">Documentos Indexados</div>
                <div class="metric-value">{total_docs}</div>
            </div>
            <div class="metric-icon">📖</div>
        </div>
        """, unsafe_allow_html=True)

    with m4:
        st.markdown(f"""
        <div class="metric-card ai">
            <div>
                <div class="metric-title">Análises IA</div>
                <div class="metric-value">{total_analysis}</div>
            </div>
            <div class="metric-icon">🤖</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Últimos Chamados")

    if not tickets:
        st.info("Nenhum chamado encontrado.")
    else:
        # Create a 3-column grid for tickets
        cols = st.columns(3)
        for i, t in enumerate(tickets):
            col = cols[i % 3]

            with col:
                crit_class = "ticket-critical" if t.get("criticality") == "Alta" else ""
                badge_class = "badge-critical" if t.get("criticality") == "Alta" else ""

                # Convert Markdown to HTML
                analysis_html = markdown.markdown(t.get('analysis', 'Sem análise disponível.'))

                # Escape Description text
                description = str(t.get('description', '')).replace('<', '&lt;').replace('>', '&gt;')

                st.markdown(f"""
                <div class="ticket-card {crit_class}" style="padding: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <div>
                            <span class="badge" style="margin-right: 5px;">{t.get('type')}</span>
                            <span class="badge {badge_class}">{t.get('criticality', 'Desconhecida')}</span>
                        </div>
                    </div>
                    <div style="font-weight: bold; font-size: 1.1em; color: var(--text-dark); margin-bottom: 10px;">
                        {t.get('system')}
                    </div>
                    <div style="color: #666; font-size: 0.9em; margin-bottom: 15px; height: 60px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;">
                        {description}
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.8em; color: #999; border-top: 1px solid #eee; padding-top: 10px;">
                        <span>{t.get('client')}</span>
                        <span>📅 {t.get('date').split(' ')[0]}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Expandable analysis
                with st.expander("Ver Descrição Completa e Análise"):
                    st.markdown(f"**Cliente:** {t.get('client')}")
                    st.markdown(f"**Data:** {t.get('date')}")
                    st.markdown(f"**Descrição:**\n\n{description}")
                    st.markdown("---")
                    st.markdown("### Análise da IA")
                    st.markdown(t.get('analysis', 'Sem análise disponível.'))

                # Delete button under the card
                if st.button("🗑️ Excluir", key=f"del_{t.get('id')}", use_container_width=True):
                    st.session_state[f"confirm_del_{t.get('id')}"] = True

                if st.session_state.get(f"confirm_del_{t.get('id')}", False):
                    st.warning("Confirmar exclusão?")
                    c1, c2 = st.columns(2)
                    if c1.button("Sim", key=f"yes_{t.get('id')}"):
                        delete_ticket(t.get('id'))
                        st.session_state[f"confirm_del_{t.get('id')}"] = False
                        trigger_refresh()
                        st.rerun()
                    if c2.button("Não", key=f"no_{t.get('id')}"):
                        st.session_state[f"confirm_del_{t.get('id')}"] = False
                        st.rerun()

            st.write("") # spacing


# ==========================================
# PAGE 2: ABERTURA DE CHAMADO
# ==========================================
elif selected == "Novo Chamado":
    st.header("Novo Chamado Corporativo")

    with st.form("new_ticket_form"):
        col1, col2 = st.columns(2)
        with col1:
            f_system = st.text_input("Sistema *", placeholder="Ex: ERP Publicenter")
        with col2:
            f_client = st.text_input("Cliente *", placeholder="Ex: Empresa S.A.")

        f_type = st.selectbox("Tipo *", ["Bug", "Demanda"])
        f_desc = st.text_area("Descrição do Problema / Solicitação *", height=150)

        st.markdown("### Documentos de Apoio (Opcional)")
        st.info("Documentos enviados aqui serão automaticamente indexados com metadados básicos herdados do chamado e utilizados nesta e em futuras análises.")
        f_files = st.file_uploader("Upload de PDFs relacionados", type=["pdf"], accept_multiple_files=True)

        submit_btn = st.form_submit_button("Enviar Chamado", type="primary")

        if submit_btn:
            if not f_system or not f_client or not f_desc:
                st.error("Por favor, preencha todos os campos obrigatórios (*).")
            else:
                with st.spinner("A IA está analisando o chamado..."):
                    # 1. Index PDFs if any
                    docs_indexed = 0
                    if f_files:
                        for file in f_files:
                            try:
                                # Inherit metadata from ticket context
                                meta = {
                                    "document_type": "TICKET_ATTACHMENT",
                                    "scope": SCOPE_SYSTEM, # Defaulting to system scope for attachments
                                    "client": f_client,
                                    "system": f_system,
                                    "module": "General",
                                    "version": "1.0",
                                    "tags": "attachment",
                                    "compliance": "Standard"
                                }
                                chunks = index_pdf(file, meta)
                                docs_indexed += 1
                            except Exception as e:
                                st.error(f"Erro ao processar arquivo {file.name}: {e}")

                    # 2. Retrieve Context
                    context = get_relevant_context(f_desc, f_system, f_client)

                    # 3. Analyze with AI
                    analysis_result = analyze_ticket(f_desc, context)
                    criticality = extract_criticality(analysis_result)

                    # 4. Save Ticket
                    add_ticket(
                        system=f_system,
                        client=f_client,
                        type_str=f_type,
                        description=f_desc,
                        analysis=analysis_result,
                        criticality=criticality
                    )

                    st.success("Chamado aberto e analisado com sucesso!")
                    if docs_indexed > 0:
                        st.info(f"{docs_indexed} documentos foram indexados e incluídos na base de conhecimento.")

                # Display the analysis result after the spinner completes
                st.markdown("---")
                st.markdown("### 🤖 Resultado da Análise da IA")
                st.info("Abaixo está a análise automática gerada para o seu chamado com base nos documentos de contexto fornecidos.")

                # Add a stylized container specifically for the AI response
                st.markdown(f"""
                <div style="background-color: #ffffff; border-left: 5px solid var(--highlight-orange); padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-top: 15px; margin-bottom: 25px;">
                    <div style="color: #333;">{markdown.markdown(analysis_result)}</div>
                </div>
                """, unsafe_allow_html=True)

                # We do not call trigger_refresh() or st.rerun() here immediately
                # so the user has time to read the analysis.
                # The dashboard tab will reflect the new ticket the next time it's clicked.


# ==========================================
# PAGE 3: BASE DE CONHECIMENTO (RAG)
# ==========================================
elif selected == "Base de Conhecimento":
    st.header("Documentos Indexados (RAG)")

    # Upload new standalone documents
    with st.expander("➕ Adicionar Novo Documento"):
        with st.form("upload_doc_form"):
            st.markdown("### Metadados Obrigatórios")
            c1, c2, c3 = st.columns(3)
            with c1:
                m_doc_type = st.text_input("Document Type", value="Manual")
                m_scope = st.selectbox("Scope", SCOPES)
                m_client = st.text_input("Client", help="Deixe em branco se Scope for GLOBAL")
            with c2:
                m_system = st.text_input("System")
                m_module = st.text_input("Module", value="All")
                m_version = st.text_input("Version", value="1.0")
            with c3:
                m_tags = st.text_input("Tags (separadas por vírgula)")
                m_compliance = st.text_input("Compliance", value="N/A")

            kb_files = st.file_uploader("Arquivos PDF", type=["pdf"], accept_multiple_files=True, key="kb_files")

            kb_submit = st.form_submit_button("Indexar Documentos", type="primary")
            if kb_submit:
                if not kb_files:
                    st.error("Selecione pelo menos um arquivo PDF.")
                else:
                    with st.spinner("Indexando documentos no ChromaDB..."):
                        success_count = 0
                        for f in kb_files:
                            try:
                                metadata = {
                                    "document_type": m_doc_type,
                                    "scope": m_scope,
                                    "client": m_client,
                                    "system": m_system,
                                    "module": m_module,
                                    "version": m_version,
                                    "tags": m_tags,
                                    "compliance": m_compliance
                                }
                                index_pdf(f, metadata)
                                success_count += 1
                            except Exception as e:
                                st.error(f"Erro ao indexar {f.name}: {e}")

                        if success_count > 0:
                            st.success(f"{success_count} documentos indexados com sucesso!")
                            trigger_refresh()
                            st.rerun()

    st.markdown("---")

    k_col1, k_col2 = st.columns([0.8, 0.2])
    with k_col1:
        st.subheader("Biblioteca de Documentos")
    with k_col2:
        if st.button("🗑️ Remover Todos", key="btn_clear_docs", type="primary", use_container_width=True):
            st.session_state.confirm_clear_docs = True

    if st.session_state.get("confirm_clear_docs", False):
        st.warning("Tem certeza que deseja apagar TODOS os documentos indexados?")
        col_c1, col_c2 = st.columns(2)
        if col_c1.button("Sim, apagar documentos", type="primary"):
            remove_all_documents()
            st.session_state.confirm_clear_docs = False
            st.success("Todos os documentos removidos do banco vetorial.")
            trigger_refresh()
            st.rerun()
        if col_c2.button("Cancelar", key="cancel_clear_docs"):
            st.session_state.confirm_clear_docs = False
            st.rerun()

    if not docs:
        st.info("Nenhum documento indexado na base de conhecimento.")
    else:
        for doc in docs:
            with st.container():
                st.markdown(f"""
                <div class="doc-card">
                    <div>
                        <div style="font-weight: bold; color: var(--primary-blue); font-size: 1.1em;">📄 {doc.get('filename')}</div>
                        <div style="color: #666; font-size: 0.9em; margin-top: 5px;">
                            <span><strong>Data:</strong> {doc.get('uploaded_at')}</span> |
                            <span><strong>Chunks:</strong> {doc.get('chunks')}</span> |
                            <span><strong>Scope:</strong> {doc.get('metadata', {}).get('scope', 'N/A')}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_btn, col_meta = st.columns([0.2, 0.8])
                with col_btn:
                    if st.button("🗑️ Remover", key=f"del_doc_{doc.get('doc_id')}"):
                        if remove_document(doc.get('doc_id')):
                            st.success("Removido!")
                            trigger_refresh()
                            st.rerun()
                        else:
                            st.error("Erro ao remover.")
                with col_meta:
                    with st.expander("Ver Metadados"):
                        st.json(doc.get('metadata', {}))


# ==========================================
# PAGE 4: CONSULTA RAG (INTERACTIVE)
# ==========================================
elif selected == "Consulta RAG":
    st.header("🔍 Consulta à Base de Conhecimento (RAG)")
    st.markdown("Faça buscas diretas na base de documentos indexados no ChromaDB.")

    with st.form("rag_query_form"):
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            q_system = st.text_input("Filtrar por Sistema (Opcional)")
        with col_s2:
            q_client = st.text_input("Filtrar por Cliente (Opcional)")

        q_query = st.text_input("Sua pergunta ou termo de busca *")

        q_submit = st.form_submit_button("Pesquisar", type="primary")

        if q_submit:
            if not q_query:
                st.error("Por favor, informe um termo para busca.")
            else:
                with st.spinner("Buscando no banco de dados vetorial..."):
                    context = get_relevant_context(q_query, q_system, q_client)

                    if not context:
                        st.warning("Nenhum documento relevante encontrado para os critérios e filtros informados.")
                    else:
                        st.success("Busca concluída!")
                        st.markdown("### Contexto Recuperado")
                        st.markdown(f"""
                        <div style="background-color: white; border: 1px solid #ddd; padding: 20px; border-radius: 8px; max-height: 500px; overflow-y: auto;">
                            {markdown.markdown(context)}
                        </div>
                        """, unsafe_allow_html=True)
