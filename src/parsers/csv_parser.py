"""
CSV Format Parser Module
------------------------
Parses CSV (.csv) documents, handles automatic delimiter detection (comma, tab, semicolon),
extracts column headers, and formats rows into metadata-enriched text chunks.
"""

import os
import pandas as pd
from typing import List, Optional
from src.parsers.base_parser import BaseParser, NormalizedChunk
from src.utils.logger import logger
from config import TABULAR_CHUNK_SIZE_ROWS

class CSVParser(BaseParser):
    """Parser implementation for Comma-Separated Values (.csv) files."""

    def __init__(self, chunk_rows: int = TABULAR_CHUNK_SIZE_ROWS):
        self.chunk_rows = chunk_rows

    def parse(self, file_path: str, original_filename: Optional[str] = None) -> List[NormalizedChunk]:
        """
        Parses CSV records into structured chunks.

        Args:
            file_path: Absolute path to the CSV file.
            original_filename: User-facing display name.

        Returns:
            List of NormalizedChunk objects ready for embedding.
        """
        filename = original_filename or os.path.basename(file_path)
        chunks: List[NormalizedChunk] = []

        try:
            logger.info(f"Parsing CSV file '{filename}'")
            # Attempt parsing with standard comma delimiter first, with Python fallback engine for autodetect
            try:
                df = pd.read_csv(file_path)
            except Exception:
                df = pd.read_csv(file_path, sep=None, engine='python')

            if df.empty:
                logger.warning(f"CSV file '{filename}' is empty")
                return []

            # Clean and sanitize column names
            df.columns = [str(col).strip() for col in df.columns]
            columns_list = list(df.columns)
            num_rows = len(df)

            # High-level CSV Document Overview Chunk
            csv_summary = (
                f"Document: {filename} (CSV)\n"
                f"Columns ({len(columns_list)}): {', '.join(columns_list)}\n"
                f"Total Records: {num_rows} rows."
            )
            chunks.append(NormalizedChunk(
                text=csv_summary,
                metadata={
                    "file_name": filename,
                    "file_type": "csv",
                    "sheet_name": "CSV Data",
                    "row_range": f"Overview (1-{num_rows})",
                    "section_type": "csv_summary"
                }
            ))

            # Batch CSV rows into structured tabular context blocks
            for start_idx in range(0, num_rows, self.chunk_rows):
                end_idx = min(start_idx + self.chunk_rows, num_rows)
                batch_df = df.iloc[start_idx:end_idx]

                row_strings = []
                for idx, row in batch_df.iterrows():
                    row_items = []
                    for col in columns_list:
                        val = row[col]
                        if pd.notna(val) and str(val).strip() != "":
                            row_items.append(f"{col}: {val}")
                    row_str = f"[Row {idx + 2}] " + " | ".join(row_items)
                    row_strings.append(row_str)

                chunk_text = (
                    f"Source File: {filename}\n"
                    f"Format: CSV\n"
                    f"Row Range: {start_idx + 2} to {end_idx + 1}\n"
                    f"Content:\n" + "\n".join(row_strings)
                )

                chunks.append(NormalizedChunk(
                    text=chunk_text,
                    metadata={
                        "file_name": filename,
                        "file_type": "csv",
                        "sheet_name": "CSV Data",
                        "row_range": f"Rows {start_idx + 2}-{end_idx + 1}",
                        "section_type": "tabular_data"
                    }
                ))

            logger.info(f"Successfully extracted {len(chunks)} chunks from CSV '{filename}'")
            return chunks

        except Exception as e:
            logger.error(f"Error parsing CSV file '{filename}': {str(e)}")
            raise RuntimeError(f"Failed to parse CSV file '{filename}': {str(e)}")
