# Multi-Format RAG Document Chatbot

A production-oriented **Retrieval-Augmented Generation (RAG)** pipeline and interactive web chatbot built for multi-format organizational knowledge retrieval across **Excel workbooks (.xlsx/.xls)**, **CSV files (.csv)**, and **PowerPoint presentations (.pptx)**.

---

## 🌟 Key Features & Capabilities

- **Format-Specific Extraction**:
  - **Excel**: Preserves sheet titles, column headers, row ranges, and tabular records.
  - **CSV**: Auto-detects delimiters, formats headers, and groups tabular rows.
  - **PowerPoint**: Extracts slide titles, body text, slide tables, speaker notes, and slide numbers.
- **Metadata-Aware Smart Chunking**: Converts tabular rows into structured context blocks with column headers preserved per chunk to prevent fragmented table splitting.
- **Dense Vector Search**: Powered by `ChromaDB` vector storage and HuggingFace `SentenceTransformers` (`all-MiniLM-L6-v2`) embeddings with automatic fallback support.
- **Grounded Answer Generation & Citations**: Strictly grounds LLM answers (Google Gemini / OpenAI) in retrieved context with explicit file, sheet/slide, and row citations.
- **Strict Grounding Refusal (FR-10)**: Clear refusal mechanism ("I cannot answer this question based on the indexed documents") when evidence is insufficient or question is out of scope.
- **Interactive Web Interface**: Streamlit UI featuring Chatbot with expander citations, Document Ingestion Hub, Vector Retrieval Sandbox, and System Latency Analytics.
- **Pre-packaged Sample Dataset**: Fictional company **Acme Retail** quarterly datasets (`acme_sales_q1.xlsx`, `acme_customers.csv`, `acme_q1_business_review.pptx`).

---

## 🏗 System Architecture

```
                               ┌────────────────────────┐
                               │  Uploaded Documents    │
                               │ (Excel, CSV, PPTX)     │
                               └───────────┬────────────┘
                                           │
                                           ▼
                               ┌────────────────────────┐
                               │ Format Parsers &       │
                               │ Smart Table Chunker    │
                               └───────────┬────────────┘
                                           │
                                           ▼
                               ┌────────────────────────┐
                               │ Embedding Manager &    │
                               │ ChromaDB Vector Store  │
                               └───────────┬────────────┘
                                           │
                     ┌─────────────────────┴─────────────────────┐
                     │                                           │
                     ▼                                           ▼
        ┌────────────────────────┐                  ┌────────────────────────┐
        │ Semantic Similarity    │                  │  Grounded Generator    │
        │ Retriever              ├─────────────────►│  (Gemini / Offline)    │
        └────────────────────────┘                  └───────────┬────────────┘
                                                                │
                                                                ▼
                                                    ┌────────────────────────┐
                                                    │ Grounded Answer with   │
                                                    │ Source Citations       │
                                                    └────────────────────────┘
```

---

## 📋 Functional Requirements Traceability (FR-01 to FR-10)

| Requirement ID | Description | Implementation Details |
|---|---|---|
| **FR-01** | File Upload | Supports `.xlsx`, `.xls`, `.csv`, `.pptx`, `.ppt` uploads in Streamlit sidebar & ingestion hub. |
| **FR-02** | Parsing | Specialized modules `excel_parser.py`, `csv_parser.py`, `pptx_parser.py`. |
| **FR-03** | Chunking | `smart_chunker.py` preserves table headers and slide titles across chunk boundaries. |
| **FR-04** | Embedding | `embedder.py` generates 384-dim dense vector embeddings. |
| **FR-05** | Vector Store | `vector_store.py` persists vectors and metadata using ChromaDB. |
| **FR-06** | Retrieval | `retriever.py` executes cosine similarity search with distance thresholding. |
| **FR-07** | Generation | `generator.py` leverages Google Gemini / OpenAI with strict system prompts. |
| **FR-08** | Grounding | Every response outputs explicit file names, sheet/slide, and row numbers. |
| **FR-09** | Multi-Doc QA | Answers queries combining Excel sales data, CSV accounts, and PPTX reviews. |
| **FR-10** | No-Answer | Automatically returns refusal notice when context is insufficient. |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- Virtual environment (recommended)

### 2. Installation
```bash
git clone <repo-url>
cd "Multi-Format RAG Document Chatbot"
pip install -r requirements.txt
```

### 3. Generate Sample Data & Run Tests
```bash
# Generate Acme Retail sample datasets
python generate_sample_data.py

# Run comprehensive test suite
python run_tests.py
```

### 4. Launch Web Chatbot UI
```bash
streamlit run app.py
```

---

## 📁 Repository Structure

```
Multi-Format RAG Document Chatbot/
├── app.py                      # Streamlit Web Application
├── config.py                   # Centralized pipeline configurations
├── generate_sample_data.py     # Acme Retail sample dataset generator
├── run_tests.py                # Unit & Integration test suite
├── requirements.txt            # Python dependencies
├── sample_data/                # Sample Excel, CSV, PPTX files
└── src/
    ├── parsers/                # Format-specific parsers
    │   ├── base_parser.py
    │   ├── excel_parser.py
    │   ├── csv_parser.py
    │   └── pptx_parser.py
    ├── chunking/               # Table & document chunker
    │   └── smart_chunker.py
    ├── embeddings/             # Embedding manager
    │   └── embedder.py
    ├── vectorstore/            # ChromaDB manager
    │   └── vector_store.py
    ├── rag/                    # Retrieval & generation
    │   ├── retriever.py
    │   ├── generator.py
    │   └── pipeline.py
    └── utils/                  # Logging and metrics tracking
        ├── logger.py
        └── metrics.py
```

---
