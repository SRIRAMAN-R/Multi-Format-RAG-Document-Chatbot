"""
Vector Store Management Module
-------------------------------
Manages persistent vector embeddings and metadata indexing using ChromaDB.
Provides document chunk insertion, similarity search, metadata filtering,
individual document deletion, and index clearing.
"""

import os
import uuid
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from src.parsers.base_parser import NormalizedChunk
from src.embeddings.embedder import EmbeddingManager
from src.utils.logger import logger
from config import VECTOR_DB_DIR, COLLECTION_NAME, TOP_K_RETRIEVAL

class VectorStoreManager:
    """Manager class for persistent ChromaDB vector store operations."""

    def __init__(self, collection_name: str = COLLECTION_NAME, db_path: Optional[str] = str(VECTOR_DB_DIR)):
        self.collection_name = collection_name
        self.db_path = db_path
        
        # Initialize persistent ChromaDB client on local disk
        if db_path:
            os.makedirs(db_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=db_path)
        else:
            self.client = chromadb.Client()

        # Retrieve or create collection with Cosine similarity distance metric
        self._ensure_collection()
        logger.info(f"VectorStore initialized with collection '{collection_name}'. Current chunk count: {self.get_total_chunks()}")

    def _ensure_collection(self):
        """Ensures active handle to the ChromaDB collection."""
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def _safe_collection_op(self, op_func):
        """Wrapper to safely execute collection operations and recover if collection was recreated externally."""
        try:
            return op_func()
        except Exception as e:
            if "NotFoundError" in type(e).__name__ or "does not exist" in str(e):
                logger.warning("ChromaDB collection handle invalid, re-fetching collection...")
                self._ensure_collection()
                return op_func()
            raise e

    def add_chunks(self, chunks: List[NormalizedChunk], embedding_manager: EmbeddingManager) -> int:
        """
        Embeds document chunks and stores them in ChromaDB with metadata.

        Args:
            chunks: List of NormalizedChunk objects.
            embedding_manager: EmbeddingManager instance.

        Returns:
            Number of chunks successfully added.
        """
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        metadatas = [c.metadata for c in chunks]
        
        # Generate unique IDs for each chunk record
        ids = [f"{c.metadata.get('file_name', 'doc')}_{i}_{uuid.uuid4().hex[:6]}" for i, c in enumerate(chunks)]

        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = embedding_manager.embed_texts(texts)

        # Sanitize metadata to standard types for ChromaDB compatibility
        sanitized_metadatas = []
        for m in metadatas:
            sanitized = {}
            for k, v in m.items():
                if isinstance(v, (str, int, float, bool)):
                    sanitized[k] = v
                else:
                    sanitized[k] = str(v)
            sanitized_metadatas.append(sanitized)

        # Insert documents, vectors, and metadata into ChromaDB
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=sanitized_metadatas,
            ids=ids
        )

        logger.info(f"Successfully added {len(chunks)} chunks to vector database.")
        return len(chunks)

    def query(self, query_text: str, embedding_manager: EmbeddingManager, top_k: int = TOP_K_RETRIEVAL, where_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Performs vector similarity search for a query.

        Args:
            query_text: User question.
            embedding_manager: EmbeddingManager instance.
            top_k: Number of nearest neighbor chunks to return.
            where_filter: Optional metadata filter dict.

        Returns:
            List of matching results with similarity scores and metadata.
        """
        if self.collection.count() == 0:
            logger.warning("Vector store is empty. Query returned 0 results.")
            return []

        query_embedding = embedding_manager.embed_query(query_text)

        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, self.collection.count()),
            "include": ["documents", "metadatas", "distances"]
        }
        if where_filter:
            kwargs["where"] = where_filter

        results = self.collection.query(**kwargs)

        formatted_results = []
        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0]

            for doc, meta, dist in zip(docs, metas, distances):
                # Calculate cosine similarity score from distance
                similarity_score = max(0.0, 1.0 - float(dist))
                formatted_results.append({
                    "text": doc,
                    "metadata": meta,
                    "distance": float(dist),
                    "similarity_score": round(similarity_score, 4)
                })

        return formatted_results

    def delete_file_chunks(self, filename: str) -> int:
        """
        Deletes all chunks associated with a specific file from ChromaDB.

        Args:
            filename: Document file name to delete.

        Returns:
            Number of deleted chunk records.
        """
        try:
            results = self.collection.get(where={"file_name": filename})
            if results and results.get("ids"):
                ids_to_delete = results["ids"]
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} chunks for file '{filename}'")
                return len(ids_to_delete)
            return 0
        except Exception as e:
            logger.error(f"Error deleting file chunks for '{filename}': {e}")
            return 0

    def clear_all(self):
        """Purges and resets the entire vector collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("Cleared all collections from Vector Store.")

    def get_indexed_files(self) -> List[str]:
        """Returns a list of unique document filenames indexed in ChromaDB."""
        def _get():
            if self.collection.count() == 0:
                return []
            all_records = self.collection.get(include=["metadatas"])
            metas = all_records.get("metadatas", [])
            files = set(m.get("file_name") for m in metas if m and "file_name" in m)
            return sorted(list(files))
        return self._safe_collection_op(_get)

    def get_total_chunks(self) -> int:
        """Returns total vector count in collection."""
        def _count():
            return self.collection.count()
        return self._safe_collection_op(_count)
