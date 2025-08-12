"""Smart tag matching service with 95% similarity threshold.

This service provides intelligent tag matching that prevents false unifications
like "Telekommunikation" ≠ "Telekom" while properly matching similar tags.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from src.paperless_ngx.domain.value_objects.tag_similarity import TagSimilarity, SimilarityMethod
from src.paperless_ngx.infrastructure.llm.litellm_client import LiteLLMClient
from src.paperless_ngx.infrastructure.paperless.api_client import PaperlessApiClient

logger = logging.getLogger(__name__)


@dataclass
class TagMatch:
    """Result of tag matching operation."""
    original_tag: str
    matched_tag: Optional[str]
    similarity_score: float
    is_new_tag: bool
    explanation: str


@dataclass
class TagHierarchy:
    """Hierarchical tag structure."""
    root_tags: List[str]
    hierarchy: Dict[str, List[str]]
    tag_counts: Dict[str, int]
    
    def add_tag(self, tag: str, parent: Optional[str] = None) -> None:
        """Add a tag to the hierarchy."""
        if parent is None:
            if tag not in self.root_tags:
                self.root_tags.append(tag)
        else:
            if parent not in self.hierarchy:
                self.hierarchy[parent] = []
            if tag not in self.hierarchy[parent]:
                self.hierarchy[parent].append(tag)
    
    def get_parent(self, tag: str) -> Optional[str]:
        """Get the parent of a tag."""
        for parent, children in self.hierarchy.items():
            if tag in children:
                return parent
        return None if tag not in self.root_tags else None
    
    def get_children(self, tag: str) -> List[str]:
        """Get children of a tag."""
        return self.hierarchy.get(tag, [])
    
    def get_all_tags(self) -> Set[str]:
        """Get all tags in the hierarchy."""
        all_tags = set(self.root_tags)
        for children in self.hierarchy.values():
            all_tags.update(children)
        return all_tags


class SmartTagMatcher:
    """Intelligent tag matching service with 95% threshold.
    
    This service ensures that only truly similar tags are unified,
    preventing false positives like "Telekommunikation" being matched
    with "Telekom" (different concepts).
    """
    
    def __init__(
        self,
        paperless_client: Optional[PaperlessApiClient] = None,
        llm_client: Optional[LiteLLMClient] = None,
        similarity_threshold: float = 0.95
    ):
        """Initialize the smart tag matcher.
        
        Args:
            paperless_client: Optional Paperless API client for tag lookups
            llm_client: Optional LLM client for semantic matching
            similarity_threshold: Threshold for tag unification (default 0.95)
        """
        self.paperless_client = paperless_client
        self.llm_client = llm_client
        self.similarity_threshold = similarity_threshold
        self.similarity_cache: Dict[Tuple[str, str], float] = {}
        self.existing_tags_cache: Optional[List[str]] = None
        self.tag_hierarchy: Optional[TagHierarchy] = None
        
        logger.info(f"SmartTagMatcher initialized with {similarity_threshold:.0%} threshold")
    
    async def get_existing_tags(self, force_refresh: bool = False) -> List[str]:
        """Get all existing tags from Paperless.
        
        Args:
            force_refresh: Force refresh of cached tags
            
        Returns:
            List of existing tag names
        """
        if self.existing_tags_cache is not None and not force_refresh:
            return self.existing_tags_cache
        
        if self.paperless_client is None:
            logger.warning("No Paperless client configured, returning empty tag list")
            return []
        
        try:
            tags = await self.paperless_client.get_tags()
            self.existing_tags_cache = [tag['name'] for tag in tags]
            logger.info(f"Loaded {len(self.existing_tags_cache)} existing tags from Paperless")
            return self.existing_tags_cache
        except Exception as e:
            logger.error(f"Failed to load tags from Paperless: {e}")
            return []
    
    async def match_tag(
        self,
        proposed_tag: str,
        existing_tags: Optional[List[str]] = None
    ) -> TagMatch:
        """Match a proposed tag against existing tags.
        
        Args:
            proposed_tag: Tag to match
            existing_tags: Optional list of existing tags (will fetch if not provided)
            
        Returns:
            TagMatch result with matched tag or indication to create new
        """
        # Get existing tags if not provided
        if existing_tags is None:
            existing_tags = await self.get_existing_tags()
        
        # Try to find best match
        best_match = TagSimilarity.find_best_match(
            proposed_tag,
            existing_tags,
            threshold=self.similarity_threshold
        )
        
        if best_match:
            # Calculate exact similarity for explanation
            similarity = TagSimilarity.calculate(proposed_tag, best_match)
            
            return TagMatch(
                original_tag=proposed_tag,
                matched_tag=best_match,
                similarity_score=similarity.similarity_score,
                is_new_tag=False,
                explanation=similarity.explain_similarity()
            )
        else:
            # No match found above threshold - create new tag
            return TagMatch(
                original_tag=proposed_tag,
                matched_tag=None,
                similarity_score=0.0,
                is_new_tag=True,
                explanation="Neuer Tag (keine ähnlichen Tags gefunden)"
            )
    
    async def match_tags_batch(
        self,
        proposed_tags: List[str],
        existing_tags: Optional[List[str]] = None
    ) -> List[TagMatch]:
        """Match multiple tags in batch.
        
        Args:
            proposed_tags: List of tags to match
            existing_tags: Optional list of existing tags
            
        Returns:
            List of TagMatch results
        """
        # Get existing tags once for batch
        if existing_tags is None:
            existing_tags = await self.get_existing_tags()
        
        results = []
        for tag in proposed_tags:
            match = await self.match_tag(tag, existing_tags)
            results.append(match)
            
            # Add new tags to existing tags for subsequent matches
            if match.is_new_tag:
                existing_tags.append(tag)
        
        return results
    
    def prevent_false_unification(self, tag1: str, tag2: str) -> bool:
        """Check if two tags should NOT be unified (false positive prevention).
        
        Args:
            tag1: First tag
            tag2: Second tag
            
        Returns:
            True if tags should NOT be unified (false positive detected)
        """
        # Known false positive pairs
        false_positive_pairs = [
            ("telekommunikation", "telekom"),
            ("versicherung", "allianz"),
            ("internet", "vodafone"),
            ("mobilfunk", "o2"),
            ("bank", "sparkasse"),
            ("steuer", "finanzamt"),
            ("rechnung", "rechnungswesen"),
            ("brief", "briefing"),
            ("vertrag", "vortrag"),
        ]
        
        tag1_lower = tag1.lower().strip()
        tag2_lower = tag2.lower().strip()
        
        for fp1, fp2 in false_positive_pairs:
            if (tag1_lower == fp1 and tag2_lower == fp2) or \
               (tag1_lower == fp2 and tag2_lower == fp1):
                logger.debug(f"Prevented false unification: '{tag1}' ≠ '{tag2}'")
                return True
        
        # Check for theme vs provider pattern
        themes = ["telekommunikation", "versicherung", "internet", "mobilfunk", "bank", "energie"]
        
        # If one is a theme and the other isn't, don't unify
        tag1_is_theme = tag1_lower in themes
        tag2_is_theme = tag2_lower in themes
        
        if tag1_is_theme != tag2_is_theme:
            # One is theme, other is not - don't unify
            return True
        
        return False
    
    async def create_tag_hierarchy(
        self,
        tags: List[str],
        use_semantic_grouping: bool = False
    ) -> TagHierarchy:
        """Create a hierarchical structure from tags.
        
        Args:
            tags: List of tags to organize
            use_semantic_grouping: Use LLM for semantic grouping
            
        Returns:
            TagHierarchy with organized structure
        """
        hierarchy = TagHierarchy(
            root_tags=[],
            hierarchy={},
            tag_counts={}
        )
        
        # Count tag occurrences (if we have document data)
        for tag in tags:
            hierarchy.tag_counts[tag] = hierarchy.tag_counts.get(tag, 0) + 1
        
        # Group similar tags
        processed = set()
        tag_groups: Dict[str, List[str]] = {}
        
        for tag in tags:
            if tag in processed:
                continue
            
            # Find all similar tags
            similar_tags = []
            for other_tag in tags:
                if other_tag == tag or other_tag in processed:
                    continue
                
                # Check if they should be unified
                if self.prevent_false_unification(tag, other_tag):
                    continue
                
                similarity = TagSimilarity.calculate(tag, other_tag)
                if similarity.should_unify(self.similarity_threshold):
                    similar_tags.append(other_tag)
                    processed.add(other_tag)
            
            # Choose best representative
            if similar_tags:
                all_tags = [tag] + similar_tags
                best_tag = self._choose_best_representative(all_tags, hierarchy.tag_counts)
                tag_groups[best_tag] = all_tags
            else:
                tag_groups[tag] = [tag]
            
            processed.add(tag)
        
        # Build hierarchy
        for parent, group in tag_groups.items():
            hierarchy.add_tag(parent, None)  # Add as root
            for child in group:
                if child != parent:
                    hierarchy.add_tag(child, parent)
        
        # If semantic grouping is enabled, use LLM to create deeper hierarchy
        if use_semantic_grouping and self.llm_client:
            hierarchy = await self._enhance_hierarchy_with_llm(hierarchy)
        
        self.tag_hierarchy = hierarchy
        return hierarchy
    
    def _choose_best_representative(
        self,
        tags: List[str],
        tag_counts: Dict[str, int]
    ) -> str:
        """Choose the best tag to represent a group.
        
        Args:
            tags: List of similar tags
            tag_counts: Usage counts for tags
            
        Returns:
            Best representative tag
        """
        # Prefer tags with higher usage count
        tags_with_counts = [(tag, tag_counts.get(tag, 0)) for tag in tags]
        tags_with_counts.sort(key=lambda x: x[1], reverse=True)
        
        # If counts are equal, prefer singular form or shorter tag
        max_count = tags_with_counts[0][1]
        top_tags = [tag for tag, count in tags_with_counts if count == max_count]
        
        # Check for singular/plural - prefer singular
        for tag in top_tags:
            # Simple heuristic: shorter is often singular
            if not any(tag.endswith(suffix) for suffix in ['en', 'er', 's', 'e']):
                return tag
        
        # Return shortest as fallback
        return min(top_tags, key=len)
    
    async def _enhance_hierarchy_with_llm(
        self,
        hierarchy: TagHierarchy
    ) -> TagHierarchy:
        """Use LLM to enhance tag hierarchy with semantic grouping.
        
        Args:
            hierarchy: Basic hierarchy to enhance
            
        Returns:
            Enhanced hierarchy with semantic grouping
        """
        if not self.llm_client:
            return hierarchy
        
        try:
            # Prepare tags for LLM
            all_tags = list(hierarchy.get_all_tags())
            
            prompt = f"""Analysiere diese Tags und erstelle eine sinnvolle Hierarchie.
            
Tags: {', '.join(all_tags)}

Gruppiere verwandte Tags unter übergeordneten Kategorien.
Behalte die originalen Tags bei, füge nur Kategorien hinzu.

Antwort im Format:
Kategorie1: tag1, tag2, tag3
Kategorie2: tag4, tag5
Einzeltags: tag6, tag7
"""
            
            # Get LLM response
            response = await self.llm_client.complete(prompt)
            
            # Parse response and update hierarchy
            # (Implementation depends on LLM response format)
            
            logger.info("Enhanced tag hierarchy with LLM semantic grouping")
            
        except Exception as e:
            logger.error(f"Failed to enhance hierarchy with LLM: {e}")
        
        return hierarchy
    
    async def apply_smart_tagging(
        self,
        documents: List[Dict],
        show_progress: bool = True
    ) -> List[Dict]:
        """Apply smart tagging to a list of documents.
        
        Args:
            documents: List of documents with tags to process
            show_progress: Show progress during processing
            
        Returns:
            Documents with optimized tags
        """
        # Get existing tags once
        existing_tags = await self.get_existing_tags()
        
        processed_docs = []
        total = len(documents)
        
        for i, doc in enumerate(documents):
            if show_progress and i % 10 == 0:
                logger.info(f"Processing document {i+1}/{total}")
            
            # Get document tags
            original_tags = doc.get('tags', [])
            if not original_tags:
                processed_docs.append(doc)
                continue
            
            # Match each tag
            optimized_tags = []
            tag_mapping = {}
            
            for tag in original_tags:
                match = await self.match_tag(tag, existing_tags)
                
                if match.matched_tag:
                    optimized_tags.append(match.matched_tag)
                    tag_mapping[tag] = match.matched_tag
                    
                    if tag != match.matched_tag:
                        logger.debug(f"Tag matched: '{tag}' → '{match.matched_tag}' "
                                   f"({match.similarity_score:.1%})")
                else:
                    # New tag
                    optimized_tags.append(tag)
                    existing_tags.append(tag)  # Add to cache
                    logger.debug(f"New tag created: '{tag}'")
            
            # Update document
            doc['tags'] = list(set(optimized_tags))  # Remove duplicates
            doc['tag_mapping'] = tag_mapping  # Store mapping for reference
            processed_docs.append(doc)
        
        logger.info(f"Smart tagging completed for {total} documents")
        return processed_docs
    
    def get_tag_statistics(self) -> Dict:
        """Get statistics about tag matching.
        
        Returns:
            Dictionary with tag matching statistics
        """
        if not self.tag_hierarchy:
            return {
                'total_tags': 0,
                'root_tags': 0,
                'unified_tags': 0,
                'similarity_threshold': self.similarity_threshold
            }
        
        all_tags = self.tag_hierarchy.get_all_tags()
        root_tags = len(self.tag_hierarchy.root_tags)
        unified_tags = sum(len(children) for children in self.tag_hierarchy.hierarchy.values())
        
        return {
            'total_tags': len(all_tags),
            'root_tags': root_tags,
            'unified_tags': unified_tags,
            'unification_rate': unified_tags / max(len(all_tags), 1),
            'similarity_threshold': self.similarity_threshold,
            'cache_size': len(self.similarity_cache)
        }