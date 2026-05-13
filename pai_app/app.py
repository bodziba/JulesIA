import streamlit as st
import os

from config import SCOPES, SCOPE_GLOBAL, SCOPE_SYSTEM
from storage import get_all_tickets, add_ticket, delete_ticket, clear_all_tickets
from rag import index_pdf, get_indexed_documents, remove_document, remove_all_documents, get_relevant_context
from agent import analyze_ticket, extract_criticality

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

# --- Layout: Main Title ---
st.title("🧠 PAI — Publicenter Artificial Intelligence")

# --- Navigation Tabs ---
tab_dash, tab_open, tab_kb = st.tabs(["📊 Dashboard", "📝 Abrir Chamado", "📚 Base de Conhecimento"])


# ==========================================
# TAB 1: DASHBOARD
# ==========================================
with tab_dash:
    st.header("Visão Geral dos Chamados")

    tickets = get_all_tickets()
    docs = get_indexed_documents()

    total_tickets = len(tickets)
    critical_tickets = sum(1 for t in tickets if t.get("criticality") == "Alta")
    total_docs = len(docs)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Chamados", total_tickets)
    col2.metric("Chamados Críticos", critical_tickets)
    col3.metric("Documentos Indexados", total_docs)

    st.markdown("---")

    d_col1, d_col2 = st.columns([0.8, 0.2])
    with d_col1:
        st.subheader("Últimos Chamados")
    with d_col2:
        if st.button("🗑️ Limpar tudo", key="btn_clear_all", help="Requer confirmação", type="primary", use_container_width=True):
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

    if not tickets:
        st.info("Nenhum chamado encontrado.")
    else:
        for t in tickets:
            crit_class = "ticket-critical" if t.get("criticality") == "Alta" else ""
            badge_class = "badge-critical" if t.get("criticality") == "Alta" else ""

            with st.container():
                st.markdown(f"""
                <div class="ticket-card {crit_class}">
                    <div class="ticket-header">
                        <span style="font-weight: bold; color: var(--primary-blue); font-size: 1.1em;">{t.get('type')} - {t.get('system')}</span>
                        <span class="badge {badge_class}">Criticidade: {t.get('criticality', 'Desconhecida')}</span>
                    </div>
                    <div><strong>Cliente:</strong> {t.get('client')}</div>
                    <div><strong>Data:</strong> {t.get('date')}</div>
                    <div style="margin-top: 10px; color: #555;"><strong>Resumo:</strong> {t.get('description', '')[:100]}...</div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander("Ver Análise da IA"):
                    st.markdown(t.get('analysis', 'Sem análise disponível.'))

                if st.button("🗑️ Excluir", key=f"del_{t.get('id')}"):
                    st.session_state[f"confirm_del_{t.get('id')}"] = True

                if st.session_state.get(f"confirm_del_{t.get('id')}", False):
                    st.warning("Confirmar exclusão?")
                    c1, c2 = st.columns(2)
                    if c1.button("Sim", key=f"yes_{t.get('id')}"):
                        delete_ticket(t.get('id'))
                        st.session_state[f"confirm_del_{t.get('id')}"] = False
                        st.success("Excluído!")
                        trigger_refresh()
                        st.rerun()
                    if c2.button("Não", key=f"no_{t.get('id')}"):
                        st.session_state[f"confirm_del_{t.get('id')}"] = False
                        st.rerun()
            st.write("") # spacing


# ==========================================
# TAB 2: ABERTURA DE CHAMADO
# ==========================================
with tab_open:
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
                with st.spinner("Processando chamado..."):
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

                    # Refresh to update dashboard
                    trigger_refresh()


# ==========================================
# TAB 3: BASE DE CONHECIMENTO (RAG)
# ==========================================
with tab_kb:
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
