"""
Excel Format Parser Module
--------------------------
Parses multi-sheet Excel workbooks (.xlsx, .xls).
Preserves sheet titles, column headers, and formats rows into key-value context records
so tabular data is not broken across arbitrary chunk boundaries.
"""

import os
import pandas as pd
from typing import List, Optional
from src.parsers.base_parser import BaseParser, NormalizedChunk
from src.utils.logger import logger
from config import TABULAR_CHUNK_SIZE_ROWS

class ExcelParser(BaseParser):
    """Parser implementation for Microsoft Excel workbooks (.xlsx, .xls)."""

    def __init__(self, chunk_rows: int = TABULAR_CHUNK_SIZE_ROWS):
        self.chunk_rows = chunk_rows

    def parse(self, file_path: str, original_filename: Optional[str] = None) -> List[NormalizedChunk]:
        """
        Extracts content from all sheets in an Excel workbook.

        Args:
            file_path: Physical location of the Excel file on disk.
            original_filename: Display name of the file.

        Returns:
            List of NormalizedChunk objects enriched with sheet and row metadata.
        """
        filename = original_filename or os.path.basename(file_path)
        chunks: List[NormalizedChunk] = []

        try:
            # Open workbook and retrieve sheet list
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            logger.info(f"Parsing Excel file '{filename}' with sheets: {sheet_names}")

            # Process each sheet individually
            for sheet_name in sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                # Skip blank sheets
                if df.empty:
                    continue

                # Clean column headers
                df.columns = [str(col).strip() for col in df.columns]
                columns_list = list(df.columns)
                num_rows = len(df)

                # Generate a High-level Sheet Summary Chunk for holistic retrieval
                sheet_summary = (
                    f"Document: {filename} | Sheet: {sheet_name}\n"
                    f"Columns ({len(columns_list)}): {', '.join(columns_list)}\n"
                    f"Total Records: {num_rows} rows."
                )
                chunks.append(NormalizedChunk(
                    text=sheet_summary,
                    metadata={
                        "file_name": filename,
                        "file_type": "excel",
                        "sheet_name": sheet_name,
                        "row_range": f"Overview (1-{num_rows})",
                        "section_type": "sheet_summary"
                    }
                ))

                # Batch table rows into chunks with column headers attached to each row record
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
                        f"Sheet Name: {sheet_name}\n"
                        f"Row Range: {start_idx + 2} to {end_idx + 1}\n"
                        f"Content:\n" + "\n".join(row_strings)
                    )

                    chunks.append(NormalizedChunk(
                        text=chunk_text,
                        metadata={
                            "file_name": filename,
                            "file_type": "excel",
                            "sheet_name": sheet_name,
                            "row_range": f"Rows {start_idx + 2}-{end_idx + 1}",
                            "section_type": "tabular_data"
                        }
                    ))

            logger.info(f"Successfully extracted {len(chunks)} chunks from Excel '{filename}'")
            return chunks

        except Exception as e:
            logger.error(f"Error parsing Excel file '{filename}': {str(e)}")
            raise RuntimeError(f"Failed to parse Excel file '{filename}': {str(e)}")
