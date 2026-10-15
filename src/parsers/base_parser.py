"""
Base Parser Interface & Document Data Models
--------------------------------------------
Defines the standard NormalizedChunk dataclass and abstract BaseParser interface.
All format-specific parsers (Excel, CSV, PPTX) inherit from BaseParser to guarantee
a uniform data contract across heterogeneous documents.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

@dataclass
class NormalizedChunk:
    """
    Standardized document chunk representation.
    
    Attributes:
        text: Formatted string text representation of chunk content.
        metadata: Dictionary containing document source, sheet/slide, row ranges, etc.
    """
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converts chunk instance to dictionary representation."""
        return {
            "text": self.text,
            "metadata": self.metadata
        }

class BaseParser(ABC):
    """Abstract Base Class interface enforced across all format parsers."""
    
    @abstractmethod
    def parse(self, file_path: str, original_filename: Optional[str] = None) -> List[NormalizedChunk]:
        """
        Parses a target file and returns a list of NormalizedChunk instances.
        
        Args:
            file_path: Local path to the source file.
            original_filename: User-facing file display name.
            
        Returns:
            List of NormalizedChunk objects ready for vector embedding.
        """
        pass
