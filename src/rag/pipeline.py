"""
RAG Pipeline Orchestrator Module
--------------------------------
Main coordinator class connecting file parsers, smart chunking, vector embeddings,
ChromaDB indexing, similarity retrieval, grounded LLM generation, and deletion operations.
"""

import os
import time
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from src.parsers import parse_document
from src.chunking.smart_chunker import SmartChunker
from src.embeddings.embedder import EmbeddingManager
from src.vectorstore.vector_store import VectorStoreManager
from src.rag.retriever import SemanticRetriever
from src.rag.generator import RAGGenerator
from src.utils.logger import logger
from src.utils.metrics import metrics_tracker
from config import TOP_K_RETRIEVAL, SIMILARITY_THRESHOLD, VECTOR_DB_DIR

class RAGPipeline:
    """End-to-End RAG Pipeline Coordinator with Hash Caching & Multi-Tenant Security."""

    def __init__(self, api_key: Optional[str] = None):
        """Initializes pipeline sub-components (Embeddings, Vector Store, Retriever, Generator)."""
        self.embedding_manager = EmbeddingManager()
        self.vector_store = VectorStoreManager()
        self.smart_chunker = SmartChunker()
        self.retriever = SemanticRetriever(self.vector_store, self.embedding_manager)
        self.generator = RAGGenerator(api_key=api_key)
        self.hash_file_path = os.path.join(str(VECTOR_DB_DIR), "file_hashes.json")
        self.file_hashes = self._load_file_hashes()

    def _load_file_hashes(self) -> Dict[str, str]:
        """Loads persistent file SHA-256 hash cache from disk."""
        if os.path.exists(self.hash_file_path):
            try:
                with open(self.hash_file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_file_hashes(self):
        """Saves file SHA-256 hash cache to disk."""
        try:
            with open(self.hash_file_path, "w", encoding="utf-8") as f:
                json.dump(self.file_hashes, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save file hash cache: {e}")

    def _compute_file_hash(self, file_path: str) -> str:
        """Computes SHA-256 hash of a file for change detection."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def set_api_key(self, api_key: str):
        """Dynamically updates the LLM API key."""
        self.generator.api_key = api_key
        if api_key and api_key.startswith("AIza"):
            self.generator.provider = "gemini"

    def ingest_file(self, file_path: str, original_filename: Optional[str] = None, session_id: Optional[str] = None, force_reindex: bool = False) -> Dict[str, Any]:
        """
        Parses, chunks, embeds, and indexes a single document into ChromaDB.
        Skips re-embedding if file content hash is unchanged.

        Args:
            file_path: Local disk path to document.
            original_filename: User-facing file display name.
            session_id: Optional user/session isolation identifier.
            force_reindex: If True, bypasses hash check and forces re-indexing.

        Returns:
            Dictionary containing status, chunk_count, and execution duration.
        """
        start_time = time.time()
        display_name = original_filename or os.path.basename(file_path)

        # Performance Optimization: Skip re-embedding if file is unchanged
        current_hash = self._compute_file_hash(file_path)
        indexed_files = self.vector_store.get_indexed_files()
        
        if not force_reindex and display_name in indexed_files and self.file_hashes.get(display_name) == current_hash:
            logger.info(f"File '{display_name}' is unchanged (SHA-256 hash match). Skipping re-embedding for performance.")
            return {
                "status": "skipped",
                "filename": display_name,
                "message": "File unchanged (skipped re-embedding)",
                "chunk_count": 0,
                "duration_seconds": 0.001
            }

        logger.info(f"Starting pipeline ingestion for file: {display_name}")

        try:
            # Step 1: Parse document using format-specific parser
            raw_chunks = parse_document(file_path, original_filename=display_name)
            if not raw_chunks:
                return {"status": "warning", "message": f"No content extracted from {display_name}", "chunk_count": 0}

            # Inject session_id metadata if provided for multi-user security isolation
            if session_id:
                for rc in raw_chunks:
                    rc.metadata["session_id"] = session_id

            # Step 2: Apply smart metadata-aware chunking
            chunks = self.smart_chunker.process_chunks(raw_chunks)

            # Step 3: Delete existing index for this file to prevent duplicate vectors
            self.vector_store.delete_file_chunks(display_name)

            # Step 4: Generate vector embeddings and store in ChromaDB
            added_count = self.vector_store.add_chunks(chunks, self.embedding_manager)

            # Update persistent hash cache
            self.file_hashes[display_name] = current_hash
            self._save_file_hashes()

            elapsed = time.time() - start_time
            metrics_tracker.record_ingestion(elapsed, added_count, 1)

            logger.info(f"Successfully ingested '{display_name}' ({added_count} chunks) in {elapsed:.4f}s")
            return {
                "status": "success",
                "filename": display_name,
                "chunk_count": added_count,
                "duration_seconds": round(elapsed, 4)
            }

        except Exception as e:
            logger.error(f"Failed to ingest file '{display_name}': {str(e)}")
            return {
                "status": "error",
                "filename": display_name,
                "error": str(e)
            }

    def ingest_multiple_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Batch ingests multiple files into pipeline."""
        results = []
        for fp in file_paths:
            res = self.ingest_file(fp)
            results.append(res)
        return results

    def query(self, question: str, top_k: int = TOP_K_RETRIEVAL, filter_file: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Executes end-to-end question answering across indexed documents.

        Args:
            question: User input question.
            top_k: Number of vector chunks to retrieve.
            filter_file: Optional single file filter.

        Returns:
            Tuple of (answer_string, list_of_sources, list_of_raw_chunks).
        """
        # Step 1: Retrieve top matching chunks
        retrieved_chunks = self.retriever.retrieve(
            query=question,
            top_k=top_k,
            threshold=SIMILARITY_THRESHOLD,
            filter_file=filter_file
        )

        # Step 2: Generate grounded answer with citations
        answer, sources = self.generator.generate_response(question, retrieved_chunks)

        return answer, sources, retrieved_chunks

    def clear_database(self):
        """Clears the entire vector store database and hash cache."""
        self.vector_store.clear_all()
        self.file_hashes.clear()
        self._save_file_hashes()
        logger.info("Database and file hash cache cleared.")

    def delete_file(self, filename: str) -> int:
        """Deletes vector embeddings and hash cache for a specific file."""
        count = self.vector_store.delete_file_chunks(filename)
        if filename in self.file_hashes:
            del self.file_hashes[filename]
            self._save_file_hashes()
        logger.info(f"Deleted {count} chunks for file '{filename}'.")
        return count

    def get_indexed_files(self) -> List[str]:
        """Returns list of active indexed document filenames."""
        return self.vector_store.get_indexed_files()

    def get_total_chunks(self) -> int:
        """Returns total chunk count in vector store."""
        return self.vector_store.get_total_chunks()
