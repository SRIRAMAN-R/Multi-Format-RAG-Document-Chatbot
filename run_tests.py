"""
Comprehensive Test Suite for Multi-Format RAG Pipeline
-------------------------------------------------------
Executes automated unit and integration tests covering:
 1. Excel Parser extraction & row range metadata
 2. CSV Parser delimiter handling & row range metadata
 3. PPTX Parser slide title & text extraction
 4. Multi-format pipeline ingestion into ChromaDB
 5. Cross-document retrieval & grounded Q&A
 6. Strict grounding refusal behavior on out-of-scope queries (FR-10)
"""

import sys
import os
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Ensure stdout uses UTF-8 encoding on Windows CLI
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Import core parsers, vector store, and RAG pipeline components
from src.parsers.excel_parser import ExcelParser
from src.parsers.csv_parser import CSVParser
from src.parsers.pptx_parser import PPTXParser
from src.chunking.smart_chunker import SmartChunker
from src.embeddings.embedder import EmbeddingManager
from src.vectorstore.vector_store import VectorStoreManager
from src.rag.pipeline import RAGPipeline
from config import SAMPLE_DATA_DIR

class TestRAGPipeline(unittest.TestCase):
    """Test suite for validating RAG pipeline capabilities."""

    @classmethod
    def setUpClass(cls):
        """Prepares sample file paths and resets vector store collection."""
        cls.excel_file = str(SAMPLE_DATA_DIR / "acme_sales_q1.xlsx")
        cls.csv_file = str(SAMPLE_DATA_DIR / "acme_customers.csv")
        cls.pptx_file = str(SAMPLE_DATA_DIR / "acme_q1_business_review.pptx")
        
        # Instantiate test pipeline and reset database state
        cls.pipeline = RAGPipeline()
        cls.pipeline.clear_database()

    def test_01_excel_parsing(self):
        """Validates Excel workbook sheet and row metadata parsing."""
        parser = ExcelParser()
        chunks = parser.parse(self.excel_file)
        self.assertGreater(len(chunks), 0)
        first_chunk = chunks[0]
        self.assertEqual(first_chunk.metadata["file_type"], "excel")
        self.assertIn("sheet_name", first_chunk.metadata)
        self.assertIn("acme_sales_q1.xlsx", first_chunk.text)
        print("[OK] Excel Parser Test Passed")

    def test_02_csv_parsing(self):
        """Validates CSV delimiter detection and row context formatting."""
        parser = CSVParser()
        chunks = parser.parse(self.csv_file)
        self.assertGreater(len(chunks), 0)
        first_chunk = chunks[0]
        self.assertEqual(first_chunk.metadata["file_type"], "csv")
        self.assertIn("row_range", first_chunk.metadata)
        print("[OK] CSV Parser Test Passed")

    def test_03_pptx_parsing(self):
        """Validates PowerPoint presentation slide extraction."""
        parser = PPTXParser()
        chunks = parser.parse(self.pptx_file)
        self.assertGreater(len(chunks), 0)
        first_chunk = chunks[0]
        self.assertEqual(first_chunk.metadata["file_type"], "pptx")
        self.assertIn("slide_number", first_chunk.metadata)
        self.assertIn("slide_title", first_chunk.metadata)
        print("[OK] PPTX Parser Test Passed")

    def test_04_pipeline_ingestion(self):
        """Validates multi-format document ingestion into ChromaDB."""
        res1 = self.pipeline.ingest_file(self.excel_file)
        res2 = self.pipeline.ingest_file(self.csv_file)
        res3 = self.pipeline.ingest_file(self.pptx_file)

        self.assertEqual(res1["status"], "success")
        self.assertEqual(res2["status"], "success")
        self.assertEqual(res3["status"], "success")

        indexed_files = self.pipeline.get_indexed_files()
        self.assertEqual(len(indexed_files), 3)
        print("[OK] Full Multi-Format Document Ingestion Test Passed")

    def test_05_multi_document_retrieval_and_qa(self):
        """Validates cross-document retrieval and grounded answer generation."""
        question = "What was the Q1 performance of the South region and who is the account manager?"
        answer, sources, retrieved = self.pipeline.query(question, top_k=4)

        self.assertGreater(len(retrieved), 0)
        self.assertGreater(len(sources), 0)
        self.assertIn("South", answer)
        print(f"[OK] Query QA Answer:\n{answer}\n")
        print("[OK] Multi-Document Retrieval & QA Test Passed")

    def test_06_refusal_on_unrelated_query(self):
        """Validates strict grounding refusal behavior (FR-10) on out-of-scope queries."""
        question = "What is the orbital speed of the planet Jupiter in km/s?"
        answer, sources, retrieved = self.pipeline.query(question, top_k=4)

        self.assertIn("cannot answer", answer.lower())
        print("[OK] Strict Grounding & Refusal Behavior Test Passed (FR-10)")

def run_tests():
    """Main entry point for running the test runner."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRAGPipeline)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
