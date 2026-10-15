"""
Multi-Format RAG Document Chatbot - Streamlit User Interface
-------------------------------------------------------------
This module implements a production-grade, interactive web frontend for the RAG pipeline.
Features:
 - Interactive Chatbot with strict factual grounding & source citations
 - Document Ingestion Hub supporting Excel (.xlsx/.xls), CSV (.csv), and PowerPoint (.pptx/.ppt)
 - Individual and bulk document deletion from vector storage
 - Vector Retrieval Sandbox for similarity score inspection
 - Real-time pipeline observability and latency metrics
"""

import sys
import os
import time
import pandas as pd
from pathlib import Path

# ==============================================================================
# TORCH COMPATIBILITY PATCH
# Streamlit's file watcher tries to inspect torch.classes.__path__._path which
# raises RuntimeError. Patching __path__ to an empty list suppresses this error.
# This must be done BEFORE importing streamlit.
# ==============================================================================
try:
    import torch
    torch.classes.__path__ = []
except Exception:
    pass

import streamlit as st

# Add project root directory to Python path for seamless imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import core RAG pipeline components and configuration settings
from src.rag.pipeline import RAGPipeline
from src.utils.metrics import metrics_tracker
from generate_sample_data import generate_all_samples
from config import SAMPLE_DATA_DIR, ALL_SUPPORTED_EXTENSIONS

# ==============================================================================
# 1. PAGE CONFIGURATION & CUSTOM CSS STYLING
# ==============================================================================
st.set_page_config(
    page_title="Multi-Format RAG Document Chatbot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply sleek dark glassmorphic styling for a modern presentation UI
st.markdown("""
<style>
    /* Main body background styling */
    .main {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .stApp {
        background: linear-gradient(135deg, #0b0f19 0%, #111827 100%);
    }
    .css-1d3780e, .stSidebar {
        background-color: #1e293b !important;
    }
    /* Stat cards for metrics dashboard */
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 13px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    /* Format tag badges for document inventory */
    .badge-excel { background-color: #15803d; color: #fff; padding: 3px 8px; border-radius: 6px; font-size: 12px; }
    .badge-csv { background-color: #0369a1; color: #fff; padding: 3px 8px; border-radius: 6px; font-size: 12px; }
    .badge-pptx { background-color: #c2410c; color: #fff; padding: 3px 8px; border-radius: 6px; font-size: 12px; }
    
    /* Sticky chat input box pinned at bottom under chat history */
    .stChatInput {
        position: sticky;
        bottom: 0px;
        z-index: 99;
        padding-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. RAG PIPELINE & SESSION STATE INITIALIZATION
# ==============================================================================
@st.cache_resource
def get_pipeline() -> RAGPipeline:
    """Instantiates and caches the core RAG Pipeline instance across user re-renders."""
    pipeline = RAGPipeline()
    return pipeline

# Retrieve cached pipeline instance
pipeline = get_pipeline()

# Initialize conversational message history in Streamlit session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! Welcome to the Multi-Format RAG Document Chatbot. Please upload your Excel (.xlsx), CSV (.csv), or PowerPoint (.pptx) files in the sidebar or **Document Ingestion Hub** tab to start asking grounded questions!",
            "sources": []
        }
    ]

# ==============================================================================
# 3. SIDEBAR NAVIGATION & CONTROL CENTER
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/isometric/96/database.png", width=64)
    st.title("Control Center")
    st.markdown("---")

    # SECTION 3.1: API Key Configuration
    st.subheader("🔑 LLM Configuration")
    user_api_key = st.text_input(
        "Google Gemini API Key",
        type="password",
        help="Optional: Enter your Gemini API key. If left blank, the offline grounded extractor will be used."
    )
    if user_api_key:
        pipeline.set_api_key(user_api_key)
        st.success("API Key updated!")

    st.markdown("---")

    # SECTION 3.2: Quick Document Upload via Sidebar
    st.subheader("📁 Upload Documents")
    sidebar_uploads = st.file_uploader(
        "Upload Excel, CSV, or PPTX",
        type=["xlsx", "xls", "csv", "pptx", "ppt"],
        accept_multiple_files=True,
        key="sidebar_uploader"
    )
    if sidebar_uploads:
        if st.button("Process Uploads", use_container_width=True, type="primary"):
            with st.spinner("Parsing & Indexing files into vector store..."):
                for ufile in sidebar_uploads:
                    # Save temporary file on local disk for parsing
                    temp_path = os.path.join(SAMPLE_DATA_DIR, ufile.name)
                    with open(temp_path, "wb") as f:
                        f.write(ufile.getbuffer())
                    # Ingest file into RAG pipeline
                    pipeline.ingest_file(temp_path, original_filename=ufile.name)
            st.success("Indexing Complete!")
            st.rerun()

    st.markdown("---")

    # SECTION 3.3: Optional Demo Sample Data Generator
    st.subheader("⚡ Demo Sample Data")
    if st.button("Load Demo Sample Files", use_container_width=True):
        generate_all_samples()
        with st.spinner("Indexing sample files..."):
            for sample_file in SAMPLE_DATA_DIR.glob("*.*"):
                pipeline.ingest_file(str(sample_file))
        st.success("Demo sample files loaded!")
        st.rerun()

    st.markdown("---")

    # SECTION 3.4: Active Knowledge Base Inventory with Delete Controls
    st.subheader("📚 Indexed Documents")
    indexed_files = pipeline.get_indexed_files()
    total_chunks = pipeline.get_total_chunks()

    if indexed_files:
        for fname in indexed_files:
            col_file, col_del = st.columns([0.8, 0.2])
            with col_file:
                if fname.endswith((".xlsx", ".xls")):
                    st.markdown(f"<span class='badge-excel'>EXCEL</span> <code>{fname}</code>", unsafe_allow_html=True)
                elif fname.endswith(".csv"):
                    st.markdown(f"<span class='badge-csv'>CSV</span> <code>{fname}</code>", unsafe_allow_html=True)
                elif fname.endswith((".pptx", ".ppt")):
                    st.markdown(f"<span class='badge-pptx'>PPTX</span> <code>{fname}</code>", unsafe_allow_html=True)
                else:
                    st.markdown(f"📄 <code>{fname}</code>", unsafe_allow_html=True)
            with col_del:
                # Delete individual file from ChromaDB vector store
                if st.button("❌", key=f"sb_del_{fname}", help=f"Remove {fname} from vector store"):
                    pipeline.delete_file(fname)
                    st.toast(f"Removed '{fname}' from index!")
                    st.rerun()
        st.caption(f"Total Vectors Indexed: **{total_chunks}**")
    else:
        st.info("No documents indexed. Upload files to begin!")

    st.markdown("---")
    # SECTION 3.5: Clear Entire Vector Database Index
    if st.button("🗑️ Clear Vector Index", use_container_width=True):
        pipeline.clear_database()
        st.warning("Database cleared!")
        st.rerun()


# ==============================================================================
# 4. MAIN APPLICATION HEADER
# ==============================================================================
st.title("Multi-Format RAG Document Chatbot")
st.caption("Prototype | Excel, CSV & PowerPoint Context-Aware Question Answering")

# ==============================================================================
# SMART RE-INDEX WARNING
# Chunk config changed (15→3 rows). If documents already indexed with old chunk
# size, warn user to re-index for improved retrieval precision.
# ==============================================================================
from config import TABULAR_CHUNK_SIZE_ROWS
_EXPECTED_CHUNK_KEY = f"chunk_size_v{TABULAR_CHUNK_SIZE_ROWS}"
if st.session_state.get("chunk_config_key") != _EXPECTED_CHUNK_KEY and pipeline.get_total_chunks() > 0:
    st.warning(
        f"⚠️ **Chunk size was updated to {TABULAR_CHUNK_SIZE_ROWS} rows/chunk** for better retrieval precision. "
        f"Your indexed documents were built with an older chunk size. "
        f"Please click **'Clear Vector Index'** in the sidebar and re-upload your files to apply the improvement.",
        icon="⚠️"
    )
st.session_state["chunk_config_key"] = _EXPECTED_CHUNK_KEY

# ==============================================================================
# 5. TABBED WORKSPACE LAYOUT
# ==============================================================================
tab_chat, tab_ingest, tab_retrieval, tab_metrics = st.tabs([
    "💬 Interactive Chatbot",
    "📁 Document Ingestion Hub",
    "🔍 Retrieval Sandbox",
    "📊 System Analytics & Metrics"
])

# ------------------------------------------------------------------------------
# TAB 1: INTERACTIVE CHATBOT & GROUNDED RESPONSE GENERATION
# ------------------------------------------------------------------------------
with tab_chat:
    st.markdown("#### Ask Questions Across Your Uploaded Files")

    # Render historical conversation messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📚 View Supporting Source References", expanded=False):
                    for src in msg["sources"]:
                        st.markdown(f"- **{src['file_name']}** → `{src['location']}` (Relevance: {src['similarity_score']*100:.1f}%)")
                        if src.get("preview"):
                            st.caption(f"Snippet: {src['preview']}")

    # Handle incoming user query from input box
    if prompt := st.chat_input("Ask a question based on your uploaded documents..."):
        # Append user question to session history
        st.session_state.messages.append({"role": "user", "content": prompt, "sources": []})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Execute RAG query (Retrieve -> Grounded Generation)
        with st.chat_message("assistant"):
            with st.spinner("Retrieving vector embeddings & generating grounded answer..."):
                answer, sources, retrieved = pipeline.query(prompt)

                st.markdown(answer)

                # Display clickable/expandable source citations
                if sources:
                    with st.expander("📚 View Supporting Source References", expanded=True):
                        for src in sources:
                            st.markdown(f"- **{src['file_name']}** → `{src['location']}` (Relevance: {src['similarity_score']*100:.1f}%)")
                            st.caption(f"Snippet: {src['preview']}")

        # Store assistant response in session history
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources
        })
        st.rerun()

# ------------------------------------------------------------------------------
# TAB 2: DOCUMENT INGESTION HUB & ACTIVE INVENTORY
# ------------------------------------------------------------------------------
with tab_ingest:
    st.markdown("#### Upload and Parse Custom Files")
    uploaded_files = st.file_uploader(
        "Choose Excel (.xlsx/.xls), CSV (.csv), or PowerPoint (.pptx) files",
        type=["xlsx", "xls", "csv", "pptx", "ppt"],
        accept_multiple_files=True,
        key="main_tab_uploader"
    )

    if uploaded_files:
        if st.button("Process & Index Uploaded Files", type="primary", key="main_process_btn"):
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, ufile in enumerate(uploaded_files):
                status_text.text(f"Processing '{ufile.name}'...")
                temp_path = os.path.join(SAMPLE_DATA_DIR, ufile.name)
                with open(temp_path, "wb") as f:
                    f.write(ufile.getbuffer())

                res = pipeline.ingest_file(temp_path, original_filename=ufile.name)
                if res["status"] == "success":
                    st.success(f"Indexed **{ufile.name}**: {res['chunk_count']} chunks in {res['duration_seconds']}s")
                else:
                    st.error(f"Error indexing **{ufile.name}**: {res.get('error')}")

                progress_bar.progress((idx + 1) / len(uploaded_files))

            status_text.text("Ingestion completed!")
            st.rerun()

    st.divider()
    st.markdown("#### Active Knowledge Base Contents")
    files = pipeline.get_indexed_files()
    if files:
        for fname in files:
            col_info, col_action = st.columns([0.8, 0.2])
            with col_info:
                st.markdown(f"📄 **{fname}** (`{os.path.splitext(fname)[1].upper()}`)")
            with col_action:
                # Delete individual document from ChromaDB vector store
                if st.button("Delete File 🗑️", key=f"tab_del_{fname}"):
                    pipeline.delete_file(fname)
                    st.success(f"Deleted '{fname}' vectors!")
                    st.rerun()
    else:
        st.info("No documents currently indexed.")

# ------------------------------------------------------------------------------
# TAB 3: RETRIEVAL SANDBOX FOR VECTOR SCORE INSPECTION
# ------------------------------------------------------------------------------
with tab_retrieval:
    st.markdown("#### Vector Retrieval & Chunk Similarity Inspector")
    sandbox_query = st.text_input("Enter retrieval query to inspect raw vector matches:", "")
    top_k_select = st.slider("Top K Chunks", min_value=1, max_value=10, value=4)

    if st.button("Run Vector Retrieval Test"):
        if not sandbox_query:
            st.warning("Please enter a query.")
        else:
            retrieved = pipeline.retriever.retrieve(sandbox_query, top_k=top_k_select, threshold=0.0)
            st.markdown(f"Found **{len(retrieved)}** matching chunks in Vector Database:")

            for i, item in enumerate(retrieved, start=1):
                meta = item["metadata"]
                st.markdown(f"##### Chunk #{i} — Score: `{item['similarity_score']*100:.2f}%` | File: `{meta.get('file_name')}`")
                st.caption(f"Metadata: Sheet/Slide: {meta.get('sheet_name')} | Row Range: {meta.get('row_range')}")
                st.code(item["text"], language="text")

# ------------------------------------------------------------------------------
# TAB 4: SYSTEM METRICS & PIPELINE OBSERVABILITY
# ------------------------------------------------------------------------------
with tab_metrics:
    st.markdown("#### Observability & Latency Benchmarks")
    m_summary = metrics_tracker.get_summary()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"<div class='metric-card'><div class='metric-value'>{pipeline.get_total_chunks()}</div><div class='metric-label'>Indexed Vectors</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(pipeline.get_indexed_files())}</div><div class='metric-label'>Active Files</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-card'><div class='metric-value'>{m_summary['avg_retrieval_latency_sec']}s</div><div class='metric-label'>Avg Retrieval Latency</div></div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='metric-card'><div class='metric-value'>{m_summary['avg_generation_latency_sec']}s</div><div class='metric-label'>Avg LLM Latency</div></div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("#### End-to-End Pipeline Architecture")
    st.markdown("""
    <div style="background: rgba(30, 41, 59, 0.8); padding: 22px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1);">
        <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; text-align: center;">
            <div style="flex: 1; min-width: 150px; background: #0f172a; padding: 16px; border-radius: 10px; border-top: 4px solid #38bdf8;">
                <strong style="color: #38bdf8; font-size: 15px;">1. File Upload</strong><br>
                <span style="font-size: 12px; color: #94a3b8;">Excel, CSV, PPTX</span>
            </div>
            <div style="color: #64748b; font-size: 22px; font-weight: bold;">➔</div>
            <div style="flex: 1; min-width: 150px; background: #0f172a; padding: 16px; border-radius: 10px; border-top: 4px solid #a855f7;">
                <strong style="color: #a855f7; font-size: 15px;">2. Format Parsers</strong><br>
                <span style="font-size: 12px; color: #94a3b8;">Metadata Enrichment</span>
            </div>
            <div style="color: #64748b; font-size: 22px; font-weight: bold;">➔</div>
            <div style="flex: 1; min-width: 150px; background: #0f172a; padding: 16px; border-radius: 10px; border-top: 4px solid #ec4899;">
                <strong style="color: #ec4899; font-size: 15px;">3. Smart Chunker</strong><br>
                <span style="font-size: 12px; color: #94a3b8;">Header Preservation</span>
            </div>
            <div style="color: #64748b; font-size: 22px; font-weight: bold;">➔</div>
            <div style="flex: 1; min-width: 150px; background: #0f172a; padding: 16px; border-radius: 10px; border-top: 4px solid #22c55e;">
                <strong style="color: #22c55e; font-size: 15px;">4. Vector Store</strong><br>
                <span style="font-size: 12px; color: #94a3b8;">ChromaDB + MiniLM</span>
            </div>
            <div style="color: #64748b; font-size: 22px; font-weight: bold;">➔</div>
            <div style="flex: 1; min-width: 150px; background: #0f172a; padding: 16px; border-radius: 10px; border-top: 4px solid #f59e0b;">
                <strong style="color: #f59e0b; font-size: 15px;">5. Grounded LLM</strong><br>
                <span style="font-size: 12px; color: #94a3b8;">Answer & Citations</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
