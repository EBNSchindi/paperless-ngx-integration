"""Tag similarity value object for intelligent tag matching.

This module provides tag similarity calculation with a 95% threshold
to prevent false unifications like "Telekommunikation" ≠ "Telekom".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    # Fallback to difflib if RapidFuzz not available
    import difflib


class SimilarityMethod(Enum):
    """Methods used for similarity calculation."""
    EXACT = "exact"
    LEVENSHTEIN = "levenshtein"
    SEMANTIC = "semantic"
    GERMAN_OPTIMIZED = "german_optimized"
    COMBINED = "combined"
    CACHED = "cached"


@dataclass(frozen=True)
class TagSimilarity:
    """Immutable tag similarity calculation result.
    
    Attributes:
        tag1: First tag being compared
        tag2: Second tag being compared
        similarity_score: Calculated similarity score (0.0 to 1.0)
        calculation_method: Method used for calculation
        is_singular_plural: Whether tags are singular/plural variants
    """
    
    tag1: str
    tag2: str
    similarity_score: float
    calculation_method: SimilarityMethod
    is_singular_plural: bool = False
    
    def __post_init__(self):
        """Validate similarity score after initialization."""
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError(f"Similarity score must be between 0.0 and 1.0, got {self.similarity_score}")
    
    @classmethod
    def calculate(cls, tag1: str, tag2: str, use_semantic: bool = False) -> TagSimilarity:
        """Calculate similarity between two tags.
        
        Args:
            tag1: First tag
            tag2: Second tag
            use_semantic: Whether to include semantic similarity (requires LLM)
            
        Returns:
            TagSimilarity instance with calculated score
        """
        # Normalize tags for comparison
        tag1_normalized = tag1.lower().strip()
        tag2_normalized = tag2.lower().strip()
        
        # Check for exact match
        if tag1_normalized == tag2_normalized:
            return cls(
                tag1=tag1,
                tag2=tag2,
                similarity_score=1.0,
                calculation_method=SimilarityMethod.EXACT,
                is_singular_plural=False
            )
        
        # Check for singular/plural variants
        is_singular_plural = cls._check_singular_plural(tag1_normalized, tag2_normalized)
        if is_singular_plural:
            # High similarity for singular/plural pairs
            return cls(
                tag1=tag1,
                tag2=tag2,
                similarity_score=0.98,
                calculation_method=SimilarityMethod.GERMAN_OPTIMIZED,
                is_singular_plural=True
            )
        
        # Calculate string similarity
        if RAPIDFUZZ_AVAILABLE:
            # Use RapidFuzz for best performance
            similarity = fuzz.WRatio(tag1_normalized, tag2_normalized) / 100.0
            method = SimilarityMethod.LEVENSHTEIN
        else:
            # Fallback to difflib
            similarity = difflib.SequenceMatcher(None, tag1_normalized, tag2_normalized).ratio()
            method = SimilarityMethod.LEVENSHTEIN
        
        # Apply German-specific adjustments
        similarity = cls._apply_german_adjustments(tag1_normalized, tag2_normalized, similarity)
        
        return cls(
            tag1=tag1,
            tag2=tag2,
            similarity_score=similarity,
            calculation_method=method,
            is_singular_plural=is_singular_plural
        )
    
    @staticmethod
    def _check_singular_plural(tag1: str, tag2: str) -> bool:
        """Check if two tags are singular/plural variants.
        
        Args:
            tag1: First tag (normalized)
            tag2: Second tag (normalized)
            
        Returns:
            True if tags are singular/plural variants
        """
        # Common German plural patterns
        plural_patterns = [
            ("", "e"),      # Brief -> Briefe
            ("", "en"),     # Rechnung -> Rechnungen
            ("", "n"),      # Lieferung -> Lieferungen
            ("", "er"),     # Kind -> Kinder
            ("", "s"),      # Auto -> Autos
            ("a", "ä"),     # Bank -> Bänke (with umlaut)
            ("o", "ö"),     # Ton -> Töne
            ("u", "ü"),     # Buch -> Bücher
            ("ag", "äge"),  # Vertrag -> Verträge
        ]
        
        for singular_end, plural_end in plural_patterns:
            # Check if tag2 is plural of tag1
            if singular_end:
                if tag1.endswith(singular_end) and tag2 == tag1[:-len(singular_end)] + plural_end:
                    return True
            else:
                if tag2 == tag1 + plural_end:
                    return True
            
            # Check reverse (tag1 is plural of tag2)
            if singular_end:
                if tag2.endswith(singular_end) and tag1 == tag2[:-len(singular_end)] + plural_end:
                    return True
            else:
                if tag1 == tag2 + plural_end:
                    return True
        
        return False
    
    @staticmethod
    def _apply_german_adjustments(tag1: str, tag2: str, base_similarity: float) -> float:
        """Apply German-specific similarity adjustments.
        
        Args:
            tag1: First tag (normalized)
            tag2: Second tag (normalized)
            base_similarity: Base similarity score
            
        Returns:
            Adjusted similarity score
        """
        # Known false positives to prevent
        false_positives = [
            ("telekommunikation", "telekom"),
            ("versicherung", "versicherer"),
            ("bank", "banking"),
            ("steuer", "steuern"),  # Tax vs steering
            ("rechnung", "rechnungswesen"),
            ("internet", "intern"),
            ("vertrag", "vortrag"),  # Contract vs presentation
            ("brief", "briefing"),
        ]
        
        # Check for known false positives
        for fp1, fp2 in false_positives:
            if (tag1 == fp1 and tag2 == fp2) or (tag1 == fp2 and tag2 == fp1):
                # Reduce similarity for known false positives
                return min(base_similarity * 0.7, 0.85)  # Cap at 85% to prevent unification
        
        # Check for compound words (common in German)
        if tag1 in tag2 or tag2 in tag1:
            # One tag is contained in the other
            shorter = min(tag1, tag2, key=len)
            longer = max(tag1, tag2, key=len)
            
            # Check if it's a meaningful compound
            if len(shorter) >= 4 and len(longer) - len(shorter) >= 3:
                # Likely a compound word, boost similarity slightly
                return min(base_similarity * 1.1, 0.94)  # Still below 95% threshold
        
        return base_similarity
    
    def should_unify(self, threshold: float = 0.95) -> bool:
        """Determine if tags should be unified based on threshold.
        
        Args:
            threshold: Similarity threshold for unification (default 0.95)
            
        Returns:
            True if tags should be unified
        """
        return self.similarity_score >= threshold
    
    def get_unified_tag(self) -> str:
        """Get the recommended unified tag name.
        
        Returns:
            The tag that should be used as the unified version
        """
        # Prefer shorter, more common form
        if self.is_singular_plural:
            # Prefer singular form for German business context
            return min(self.tag1, self.tag2, key=len)
        
        # For other cases, prefer the shorter tag
        if len(self.tag1) <= len(self.tag2):
            return self.tag1
        return self.tag2
    
    def explain_similarity(self) -> str:
        """Provide human-readable explanation of similarity.
        
        Returns:
            Explanation string in German
        """
        if self.similarity_score >= 1.0:
            return "Identische Tags"
        elif self.is_singular_plural:
            return "Singular/Plural-Variante"
        elif self.similarity_score >= 0.95:
            return "Sehr ähnliche Tags (Tippfehler oder Variante)"
        elif self.similarity_score >= 0.85:
            return "Ähnliche Tags (möglicherweise verwandt)"
        elif self.similarity_score >= 0.70:
            return "Teilweise ähnlich (verschiedene Konzepte)"
        else:
            return "Unterschiedliche Tags"
    
    def __str__(self) -> str:
        """String representation of similarity."""
        percentage = self.similarity_score * 100
        return f"'{self.tag1}' ~ '{self.tag2}': {percentage:.1f}% ({self.explain_similarity()})"
    
    def __repr__(self) -> str:
        """Developer representation of similarity."""
        return (f"TagSimilarity('{self.tag1}', '{self.tag2}', "
                f"{self.similarity_score:.3f}, {self.calculation_method.value})")
    
    @classmethod
    def find_best_match(cls, tag: str, candidates: list[str], threshold: float = 0.95) -> Optional[str]:
        """Find the best matching tag from a list of candidates.
        
        Args:
            tag: Tag to match
            candidates: List of candidate tags
            threshold: Minimum similarity threshold
            
        Returns:
            Best matching tag or None if no match above threshold
        """
        if not candidates:
            return None
        
        if RAPIDFUZZ_AVAILABLE:
            # Use RapidFuzz for efficient searching
            result = process.extractOne(
                tag.lower().strip(),
                [c.lower().strip() for c in candidates],
                scorer=fuzz.WRatio,
                score_cutoff=threshold * 100
            )
            
            if result:
                # Find original candidate (with original casing)
                matched_lower = result[0]
                for candidate in candidates:
                    if candidate.lower().strip() == matched_lower:
                        return candidate
        else:
            # Fallback to manual comparison
            best_match = None
            best_score = 0.0
            
            for candidate in candidates:
                similarity = cls.calculate(tag, candidate)
                if similarity.similarity_score > best_score and similarity.similarity_score >= threshold:
                    best_score = similarity.similarity_score
                    best_match = candidate
            
            return best_match
        
        return None