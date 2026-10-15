"""
Centralized Configuration Settings for Multi-Format RAG Chatbot
--------------------------------------------------------------
Defines directory paths, supported file formats, chunking thresholds,
vector store parameters, and LLM model configurations.
"""

import os
from pathlib import Path

# ==============================================================================
# 1. BASE DIRECTORIES & FILE SYSTEM PATHS
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
VECTOR_DB_DIR = BASE_DIR / "vector_db_storage"

# Create required project directories if they do not exist
DATA_DIR.mkdir(exist_ok=True)
SAMPLE_DATA_DIR.mkdir(exist_ok=True)
VECTOR_DB_DIR.mkdir(exist_ok=True)

# ==============================================================================
# 2. SUPPORTED FILE FORMAT EXTENSIONS
# ==============================================================================
SUPPORTED_EXCEL_EXTENSIONS = [".xlsx", ".xls"]
SUPPORTED_CSV_EXTENSIONS = [".csv"]
SUPPORTED_PPT_EXTENSIONS = [".pptx", ".ppt"]
ALL_SUPPORTED_EXTENSIONS = (
    SUPPORTED_EXCEL_EXTENSIONS + SUPPORTED_CSV_EXTENSIONS + SUPPORTED_PPT_EXTENSIONS
)

# ==============================================================================
# 3. CHUNKING & SEGMENTATION PARAMETERS
# ==============================================================================
TABULAR_CHUNK_SIZE_ROWS = 3        # Rows per chunk — smaller = higher per-row retrieval precision
TEXT_CHUNK_SIZE_CHARS = 1000       # Maximum character limit per text chunk
TEXT_CHUNK_OVERLAP_CHARS = 150     # Overlapping character count for text boundary preservation

# ==============================================================================
# 4. VECTOR DATABASE & EMBEDDING CONFIGURATION
# ==============================================================================
COLLECTION_NAME = "acme_business_knowledge"
DEFAULT_EMBEDDING_PROVIDER = "sentence_transformers"  # Options: "sentence_transformers", "gemini", "openai"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K_RETRIEVAL = 8               # Number of top relevant chunks to retrieve per query
SIMILARITY_THRESHOLD = 0.05        # Minimum similarity score cutoff threshold

# ==============================================================================
# 5. LLM GENERATION & PROMPT ENGINEERING
# ==============================================================================
DEFAULT_LLM_PROVIDER = "gemini"    # Options: "gemini", "openai", "fallback"
GEMINI_MODEL_NAME = "gemini-2.5-flash"
OPENAI_MODEL_NAME = "gpt-4o-mini"
MAX_TOKENS = 1024
TEMPERATURE = 0.2                  # Low temperature for deterministic, fact-grounded outputs

# Grounded System Prompt Template with Strict Refusal & Citation Instructions
GROUNDED_RAG_PROMPT = """You are an authoritative business analyst assistant for Acme Retail.
Your task is to answer the user's question accurately based ONLY on the provided context retrieved from organizational documents.

Strict Rules for Answering:
1. Base your answer STRICTLY on the retrieved context below. Do NOT use outside knowledge or make assumptions.
2. If the context contains relevant data (even partial), synthesize and compute the answer from available numbers (e.g., multiply Price × Units Sold to get revenue, sum values across rows, compare percentages). Always show your reasoning.
3. If the context truly does not contain ANY relevant information to answer the question, clearly state: "I cannot answer this question based on the indexed documents."
4. Cite your sources clearly at the end of your answer in the format:
   Sources:
   - File: <filename> | Sheet/Slide: <sheet_name or slide_number> | Location: <row_range or section>
5. Include quantitative details (percentages, dollar amounts, targets) exactly as given in the context.
6. When answering questions about rankings or comparisons, organize the answer as a clear ranked list.

Retrieved Context:
-----------------
{context}
-----------------

User Question: {question}

Answer:"""
