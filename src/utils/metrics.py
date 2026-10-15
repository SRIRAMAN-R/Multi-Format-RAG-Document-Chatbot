"""
Metrics and Observability Module
Tracks ingestion time, retrieval latency, query counts, and document stats.
"""

import time
from typing import Dict, Any, List

class RAGMetrics:
    def __init__(self):
        self.ingestion_times: List[float] = []
        self.retrieval_times: List[float] = []
        self.generation_times: List[float] = []
        self.total_queries: int = 0
        self.total_chunks_indexed: int = 0
        self.total_files_indexed: int = 0

    def record_ingestion(self, duration: float, chunk_count: int, file_count: int):
        self.ingestion_times.append(duration)
        self.total_chunks_indexed += chunk_count
        self.total_files_indexed += file_count

    def record_retrieval(self, duration: float):
        self.retrieval_times.append(duration)
        self.total_queries += 1

    def record_generation(self, duration: float):
        self.generation_times.append(duration)

    def get_summary(self) -> Dict[str, Any]:
        avg_retrieval = (sum(self.retrieval_times) / len(self.retrieval_times)) if self.retrieval_times else 0.0
        avg_generation = (sum(self.generation_times) / len(self.generation_times)) if self.generation_times else 0.0
        return {
            "total_files": self.total_files_indexed,
            "total_chunks": self.total_chunks_indexed,
            "total_queries": self.total_queries,
            "avg_retrieval_latency_sec": round(avg_retrieval, 4),
            "avg_generation_latency_sec": round(avg_generation, 4)
        }

metrics_tracker = RAGMetrics()
