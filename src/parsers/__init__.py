"""
Parsers Package Init
Factory for instantiating document format parsers based on file extension.
"""

import os
from typing import List, Optional
from src.parsers.base_parser import BaseParser, NormalizedChunk
from src.parsers.excel_parser import ExcelParser
from src.parsers.csv_parser import CSVParser
from src.parsers.pptx_parser import PPTXParser
from config import (
    SUPPORTED_EXCEL_EXTENSIONS,
    SUPPORTED_CSV_EXTENSIONS,
    SUPPORTED_PPT_EXTENSIONS,
    ALL_SUPPORTED_EXTENSIONS
)

def get_parser(file_path: str) -> BaseParser:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in SUPPORTED_EXCEL_EXTENSIONS:
        return ExcelParser()
    elif ext in SUPPORTED_CSV_EXTENSIONS:
        return CSVParser()
    elif ext in SUPPORTED_PPT_EXTENSIONS:
        return PPTXParser()
    else:
        raise ValueError(
            f"Unsupported file format '{ext}'. Supported formats are: {ALL_SUPPORTED_EXTENSIONS}"
        )

def parse_document(file_path: str, original_filename: Optional[str] = None) -> List[NormalizedChunk]:
    parser = get_parser(file_path)
    return parser.parse(file_path, original_filename=original_filename)
