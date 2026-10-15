"""
Logging Utility for RAG Pipeline
Provides structured logging for tracking ingestion, vector indexing, retrieval, and LLM calls.
"""

import logging
import sys

def get_logger(name: str = "RAG_Chatbot") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    return logger

logger = get_logger("RAG_Pipeline")
