"""
PowerPoint Format Parser Module
-------------------------------
Parses PPTX presentations (.pptx, .ppt).
Extracts slide titles, body text frames, slide tables, speaker notes, and slide numbers
into metadata-annotated slide chunk objects.
"""

import os
from typing import List, Optional
from pptx import Presentation
from src.parsers.base_parser import BaseParser, NormalizedChunk
from src.utils.logger import logger

class PPTXParser(BaseParser):
    """Parser implementation for Microsoft PowerPoint presentations (.pptx)."""

    def parse(self, file_path: str, original_filename: Optional[str] = None) -> List[NormalizedChunk]:
        """
        Parses slides from a PowerPoint presentation into normalized chunks.

        Args:
            file_path: Local file path.
            original_filename: User-facing display filename.

        Returns:
            List of NormalizedChunk objects per slide.
        """
        filename = original_filename or os.path.basename(file_path)
        chunks: List[NormalizedChunk] = []

        target_path = file_path
        temp_pptx_created = False

        # Support for legacy binary PowerPoint (.ppt) files
        if file_path.lower().endswith(".ppt") and not file_path.lower().endswith(".pptx"):
            logger.info(f"Detected legacy binary PPT presentation '{filename}'. Attempting conversion...")
            converted_pptx = self._convert_ppt_to_pptx(file_path)
            if converted_pptx and os.path.exists(converted_pptx):
                target_path = converted_pptx
                temp_pptx_created = True
            else:
                # Fallback to binary stream text extraction if COM PowerPoint is unavailable
                return self._parse_legacy_ppt_fallback(file_path, filename)

        try:
            prs = Presentation(target_path)
            logger.info(f"Parsing PPT presentation '{filename}' with {len(prs.slides)} slides")

            # Iterate slide by slide
            for slide_num, slide in enumerate(prs.slides, start=1):
                slide_title = f"Slide {slide_num}"
                text_elements: List[str] = []
                table_elements: List[str] = []

                # Pre-extract title shape ID to avoid direct shape comparison
                # which causes '<' not supported between 'slice' and 'int'
                title_shape_id = None
                try:
                    if hasattr(slide.shapes, "title") and slide.shapes.title and slide.shapes.title.has_text_frame:
                        title_text = slide.shapes.title.text_frame.text.strip()
                        if title_text:
                            slide_title = title_text
                        title_shape_id = slide.shapes.title.shape_id
                except Exception:
                    pass  # Some slides may not have a title placeholder

                # If slide title was not found via placeholder, check first text box paragraph
                if slide_title == f"Slide {slide_num}":
                    for shape in slide.shapes:
                        if shape.has_text_frame and shape.text_frame.text.strip():
                            first_p = shape.text_frame.paragraphs[0].text.strip()
                            if first_p and len(first_p) < 100:
                                slide_title = first_p
                                break

                # Extract shapes (Text Boxes, Tables) — skip title shape
                for shape in slide.shapes:
                    # Skip the title shape (already extracted above)
                    if title_shape_id and shape.shape_id == title_shape_id:
                        continue

                    # Detect Body Text Frame shapes
                    if shape.has_text_frame:
                        text = shape.text_frame.text.strip()
                        if text:
                            text_elements.append(text)

                    # Detect Table shapes on slide
                    elif shape.has_table:
                        table = shape.table
                        # Convert rows to list since python-pptx _Rows does NOT support slicing
                        all_rows = list(table.rows)
                        headers = [cell.text.strip() for cell in all_rows[0].cells]
                        table_rows = []
                        for row in all_rows[1:]:  # Skip header row
                            row_vals = [cell.text.strip() for cell in row.cells]
                            row_str = " | ".join(f"{h}: {v}" for h, v in zip(headers, row_vals) if v)
                            table_rows.append(row_str)
                        if table_rows:
                            table_elements.append("Slide Table:\n" + "\n".join(table_rows))

                # Extract Speaker Notes if accessible
                notes_text = ""
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                    notes_text = slide.notes_slide.notes_text_frame.text.strip()

                # Assemble slide content blocks
                content_blocks = []
                if text_elements:
                    content_blocks.append("Slide Content:\n" + "\n".join(text_elements))
                if table_elements:
                    content_blocks.append("\n".join(table_elements))
                if notes_text:
                    content_blocks.append(f"Speaker Notes: {notes_text}")

                full_slide_text = "\n\n".join(content_blocks) if content_blocks else "Empty slide"

                chunk_text = (
                    f"Source Presentation: {filename}\n"
                    f"Slide Number: {slide_num}\n"
                    f"Slide Title: {slide_title}\n"
                    f"Content:\n{full_slide_text}"
                )

                chunks.append(NormalizedChunk(
                    text=chunk_text,
                    metadata={
                        "file_name": filename,
                        "file_type": "pptx",
                        "slide_number": slide_num,
                        "slide_title": slide_title,
                        "sheet_name": f"Slide {slide_num}",
                        "row_range": "N/A",
                        "section_type": "slide_content"
                    }
                ))

            logger.info(f"Successfully extracted {len(chunks)} slide chunks from PPTX '{filename}'")
            if temp_pptx_created and os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except Exception:
                    pass
            return chunks

        except Exception as e:
            logger.error(f"Error parsing PPTX presentation '{filename}': {str(e)}")
            if temp_pptx_created and os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except Exception:
                    pass
            raise RuntimeError(f"Failed to parse PPTX presentation '{filename}': {str(e)}")

    def _convert_ppt_to_pptx(self, ppt_path: str) -> Optional[str]:
        """Converts legacy .ppt file to .pptx format using Windows PowerPoint COM automation."""
        try:
            import win32com.client
            import tempfile
            
            abs_ppt_path = os.path.abspath(ppt_path)
            temp_dir = tempfile.gettempdir()
            pptx_filename = f"converted_{os.path.splitext(os.path.basename(ppt_path))[0]}.pptx"
            abs_pptx_path = os.path.join(temp_dir, pptx_filename)

            powerpoint = win32com.client.Dispatch("PowerPoint.Application")
            # Open presentation silently without window flash
            presentation = powerpoint.Presentations.Open(abs_ppt_path, WithWindow=False)
            # 24 corresponds to ppSaveAsOpenXMLPresentation (.pptx format)
            presentation.SaveAs(abs_pptx_path, 24)
            presentation.Close()
            return abs_pptx_path
        except Exception as e:
            logger.warning(f"PowerPoint COM conversion failed for '{ppt_path}': {e}")
            return None

    def _parse_legacy_ppt_fallback(self, file_path: str, filename: str) -> List[NormalizedChunk]:
        """Fallback text extractor for legacy .ppt files when PowerPoint COM is unavailable."""
        import re
        logger.info(f"Using binary text extraction fallback for legacy PPT file '{filename}'")
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            
            # Extract printable ASCII / UTF-16 text fragments from binary OLE stream
            text_blocks = re.findall(rb'[\x20-\x7E]{4,}', content)
            clean_strings = []
            for b in text_blocks:
                s = b.decode("ascii", errors="ignore").strip()
                if len(s) > 10 and not s.startswith("Font") and not s.startswith("Slide"):
                    clean_strings.append(s)

            extracted_text = "\n".join(clean_strings[:30]) if clean_strings else "Legacy PowerPoint .ppt binary content"
            
            return [NormalizedChunk(
                text=f"Source Presentation: {filename} (Legacy PPT)\nContent:\n{extracted_text}",
                metadata={
                    "file_name": filename,
                    "file_type": "ppt",
                    "slide_number": 1,
                    "slide_title": "Legacy Presentation",
                    "sheet_name": "Slide 1",
                    "row_range": "N/A",
                    "section_type": "slide_content"
                }
            )]
        except Exception as e:
            logger.error(f"Fallback PPT parser failed for '{filename}': {e}")
            raise RuntimeError(f"Failed to parse legacy PPT file '{filename}': {e}")
