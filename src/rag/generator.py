"""
Answer Generator Module
-----------------------
Generates grounded, factual answers using Google Gemini API or OpenAI API.
Includes a deterministic offline fallback engine and enforces strict refusal behavior (FR-10)
when retrieved context is missing or irrelevant.
"""

import os
import time
from typing import List, Dict, Any, Tuple
from src.utils.logger import logger
from src.utils.metrics import metrics_tracker
from config import (
    GROUNDED_RAG_PROMPT,
    DEFAULT_LLM_PROVIDER,
    GEMINI_MODEL_NAME,
    TEMPERATURE,
    MAX_TOKENS
)

class RAGGenerator:
    """Grounded Answer Generator with LLM and offline fallback modes."""

    def __init__(self, provider: str = DEFAULT_LLM_PROVIDER, api_key: str = None):
        self.provider = provider
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

    def generate_response(self, question: str, retrieved_chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Generates a grounded answer with supporting file citations.

        Args:
            question: User question string.
            retrieved_chunks: List of relevant vector chunks retrieved from vector store.

        Returns:
            Tuple of (answer_string, list_of_citation_sources).
        """
        start_time = time.time()

        # Handle No-Answer case (FR-10) when no relevant content was retrieved or scores are low
        max_score = max([c.get("similarity_score", 0.0) for c in retrieved_chunks], default=0.0)
        if not retrieved_chunks or max_score < 0.10:
            elapsed = time.time() - start_time
            metrics_tracker.record_generation(elapsed)
            return (
                "I cannot answer this question based on the indexed documents. No relevant factual context was found in the knowledge base.",
                []
            )

        # Format context blocks from retrieved vector chunks with exact document location metadata
        context_blocks = []
        sources = []
        for i, chunk in enumerate(retrieved_chunks, start=1):
            meta = chunk.get("metadata", {})
            file_name = meta.get("file_name", "Unknown File")
            file_type = meta.get("file_type", "")
            
            # Format clean, human-readable location string
            if file_type == "pptx" or meta.get("slide_number"):
                slide_num = meta.get("slide_number", 1)
                slide_title = meta.get("slide_title", "")
                if slide_title and slide_title != f"Slide {slide_num}":
                    loc_str = f"Slide {slide_num} ({slide_title})"
                else:
                    loc_str = f"Slide {slide_num}"
            else:
                sheet = meta.get("sheet_name", "Sheet")
                r_range = meta.get("row_range", "")
                if r_range and r_range != "N/A" and not r_range.startswith("Overview"):
                    loc_str = f"{sheet} → {r_range}"
                else:
                    loc_str = sheet

            context_str = f"--- Context Block #{i} ---\nSource: {file_name} | Location: {loc_str}\n{chunk['text']}\n"
            context_blocks.append(context_str)

            sources.append({
                "file_name": file_name,
                "location": loc_str,
                "similarity_score": chunk.get("similarity_score", 0.0),
                "preview": chunk['text'][:180] + "..."
            })

        formatted_context = "\n".join(context_blocks)
        prompt = GROUNDED_RAG_PROMPT.format(context=formatted_context, question=question)

        # Attempt generation with Google Gemini or OpenAI LLM API
        answer = ""
        if self.provider == "gemini" or (self.api_key and "AIza" in self.api_key):
            answer = self._generate_gemini(prompt)
        elif self.provider == "openai" and self.api_key:
            answer = self._generate_openai(prompt)
        
        # Trigger offline fallback generator if no API key is provided or API call failed
        if not answer or "API key" in answer or "ERROR" in answer:
            logger.info("Using offline grounded template generator for local demonstration.")
            answer = self._generate_fallback(question, retrieved_chunks, sources)

        elapsed = time.time() - start_time
        metrics_tracker.record_generation(elapsed)
        logger.info(f"Generated grounded answer in {elapsed:.4f}s using provider '{self.provider}'")

        return answer, sources

    def _generate_gemini(self, prompt: str) -> str:
        """Invokes Google Gemini API for answer generation."""
        try:
            import google.generativeai as genai
            api_key = self.api_key or os.getenv("GEMINI_API_KEY")
            if not api_key:
                return ""
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(GEMINI_MODEL_NAME)
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=TEMPERATURE,
                    max_output_tokens=MAX_TOKENS
                )
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error during generation: {e}")
            return ""

    def _generate_openai(self, prompt: str) -> str:
        """Invokes OpenAI API for answer generation."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return ""

    def _generate_fallback(self, question: str, chunks: List[Dict[str, Any]], sources: List[Dict[str, Any]]) -> str:
        """Deterministic grounded fallback when no LLM API key is provided."""
        query_words = set(w.lower() for w in question.split() if len(w) > 3)
        context_all_text = " ".join([c["text"].lower() for c in chunks])
        matching_words = [w for w in query_words if w in context_all_text]

        # Enforce refusal if question keywords are completely absent from retrieved text
        if not matching_words and len(query_words) > 1:
            return "I cannot answer this question based on the indexed documents. The retrieved context does not mention the topic."

        summary_lines = [
            f"Based on the indexed documents, here is the relevant information for: **{question}**\n"
        ]
        for i, chunk in enumerate(chunks, start=1):
            src_info = sources[i - 1] if i <= len(sources) else {}
            file_name = src_info.get("file_name", "Unknown File")
            loc = src_info.get("location", "Location")
            summary_lines.append(f"**[{i}] {file_name} → {loc}**")
            text_snippet = "\n".join([line for line in chunk['text'].split("\n") if ":" in line or "[" in line][:5])
            if text_snippet:
                summary_lines.append(f"```\n{text_snippet}\n```")

        summary_lines.append("\n**Sources:**")
        for src in sources:
            summary_lines.append(f"- `{src['file_name']}` → {src['location']} (Relevance Score: {src['similarity_score']*100:.1f}%)")

        return "\n".join(summary_lines)
