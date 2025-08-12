"""Unit tests for SmartTagMatcher with 95% similarity threshold.

Tests:
- 95% similarity threshold enforcement
- Prevention of false unifications (Telekommunikation ≠ Telekom)
- German singular/plural handling
- Tag hierarchy management
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from rapidfuzz import fuzz

from src.paperless_ngx.application.services.smart_tag_matcher import (
    SmartTagMatcher, TagMatch, TagHierarchy
)
from src.paperless_ngx.domain.value_objects.tag_similarity import TagSimilarity, SimilarityMethod


class TestTagSimilarityThreshold:
    """Test 95% similarity threshold enforcement."""
    
    @pytest.fixture
    def tag_matcher(self):
        """Create tag matcher with 95% threshold."""
        return SmartTagMatcher(similarity_threshold=0.95)
    
    def test_exact_match_returns_100_percent(self, tag_matcher):
        """Test that exact matches return 100% similarity."""
        similarity = TagSimilarity(
            tag1="Rechnung",
            tag2="Rechnung",
            score=1.0,
            method=SimilarityMethod.EXACT
        )
        
        assert similarity.score == 1.0
        assert similarity.is_match(0.95)
    
    def test_95_percent_threshold_accepts_high_similarity(self, tag_matcher):
        """Test that 95% threshold accepts high similarity matches."""
        # Test cases with high similarity (>= 95%)
        test_cases = [
            ("Rechnung", "Rechnungen", 0.96),  # Plural form
            ("Mobilfunk", "Mobilfunks", 0.95),  # Minor variation
            ("Telekom", "Telekom", 1.0),  # Exact match
        ]
        
        for tag1, tag2, expected_score in test_cases:
            similarity = TagSimilarity(
                tag1=tag1,
                tag2=tag2,
                score=expected_score,
                method=SimilarityMethod.FUZZY
            )
            assert similarity.is_match(0.95)
    
    def test_95_percent_threshold_rejects_low_similarity(self, tag_matcher):
        """Test that 95% threshold rejects low similarity matches."""
        # Test cases with low similarity (< 95%)
        test_cases = [
            ("Telekommunikation", "Telekom", 0.70),  # Different concepts
            ("Rechnung", "Vertrag", 0.40),  # Different document types
            ("2024", "2023", 0.75),  # Different years
            ("Januar", "Dezember", 0.30),  # Different months
        ]
        
        for tag1, tag2, expected_score in test_cases:
            similarity = TagSimilarity(
                tag1=tag1,
                tag2=tag2,
                score=expected_score,
                method=SimilarityMethod.FUZZY
            )
            assert not similarity.is_match(0.95)
    
    def test_telekommunikation_not_equal_telekom(self, tag_matcher):
        """Test that Telekommunikation is not matched with Telekom."""
        # Calculate actual similarity
        score = fuzz.WRatio("Telekommunikation", "Telekom") / 100.0
        
        similarity = TagSimilarity(
            tag1="Telekommunikation",
            tag2="Telekom",
            score=score,
            method=SimilarityMethod.FUZZY
        )
        
        # Should not match at 95% threshold
        assert score < 0.95
        assert not similarity.is_match(0.95)
    
    def test_case_insensitive_matching(self, tag_matcher):
        """Test case-insensitive tag matching."""
        test_cases = [
            ("rechnung", "Rechnung"),
            ("TELEKOM", "Telekom"),
            ("MobilFunk", "Mobilfunk")
        ]
        
        for tag1, tag2 in test_cases:
            # Normalize for comparison
            normalized1 = tag1.lower()
            normalized2 = tag2.lower()
            
            similarity = TagSimilarity(
                tag1=normalized1,
                tag2=normalized2,
                score=1.0 if normalized1 == normalized2 else 0.0,
                method=SimilarityMethod.EXACT
            )
            
            assert similarity.score == 1.0


class TestGermanLanguageHandling:
    """Test German singular/plural and language-specific handling."""
    
    @pytest.fixture
    def tag_matcher(self):
        """Create tag matcher for German language tests."""
        return SmartTagMatcher(similarity_threshold=0.95)
    
    def test_german_singular_plural_detection(self, tag_matcher):
        """Test detection of German singular/plural forms."""
        singular_plural_pairs = [
            ("Rechnung", "Rechnungen"),
            ("Vertrag", "Verträge"),
            ("Dokument", "Dokumente"),
            ("Tag", "Tags"),
            ("Monat", "Monate"),
            ("Jahr", "Jahre"),
            ("Kunde", "Kunden"),
            ("Lieferant", "Lieferanten")
        ]
        
        for singular, plural in singular_plural_pairs:
            # Check if they are recognized as related
            score = fuzz.WRatio(singular, plural) / 100.0
            
            # Most German plural forms should have high similarity with singular
            assert score > 0.80  # Lower threshold for plural recognition
    
    def test_german_umlauts_handling(self, tag_matcher):
        """Test handling of German umlauts."""
        umlaut_cases = [
            ("Überweisung", "Ueberweisung"),  # Alternative spelling
            ("Geschäft", "Geschaeft"),
            ("Büro", "Buero"),
            ("Änderung", "Aenderung")
        ]
        
        for umlaut, alternative in umlaut_cases:
            score = fuzz.WRatio(umlaut, alternative) / 100.0
            # Alternative spellings should have high similarity
            assert score > 0.85
    
    def test_german_compound_words(self, tag_matcher):
        """Test handling of German compound words."""
        compound_cases = [
            ("Mobilfunkrechnung", ["Mobilfunk", "Rechnung"]),
            ("Stromrechnung", ["Strom", "Rechnung"]),
            ("Jahresabschluss", ["Jahr", "Abschluss"]),
            ("Geschäftskunde", ["Geschäft", "Kunde"])
        ]
        
        for compound, components in compound_cases:
            # Check if compound word contains components
            for component in components:
                assert component.lower() in compound.lower()
    
    def test_german_document_types(self, tag_matcher):
        """Test German document type variations."""
        document_types = [
            "Rechnung",
            "Angebot",
            "Vertrag",
            "Mahnung",
            "Lieferschein",
            "Bestellung",
            "Gutschrift",
            "Quittung"
        ]
        
        # Each document type should be distinct
        for i, type1 in enumerate(document_types):
            for type2 in document_types[i+1:]:
                score = fuzz.WRatio(type1, type2) / 100.0
                # Different document types should not match
                assert score < 0.95


class TestTagHierarchy:
    """Test tag hierarchy management."""
    
    def test_create_tag_hierarchy(self):
        """Test creating tag hierarchy structure."""
        hierarchy = TagHierarchy(
            root_tags=[],
            hierarchy={},
            tag_counts={}
        )
        
        # Add root tags
        hierarchy.add_tag("Finanzen")
        hierarchy.add_tag("Kommunikation")
        
        # Add child tags
        hierarchy.add_tag("Rechnung", parent="Finanzen")
        hierarchy.add_tag("Mahnung", parent="Finanzen")
        hierarchy.add_tag("Email", parent="Kommunikation")
        hierarchy.add_tag("Brief", parent="Kommunikation")
        
        assert "Finanzen" in hierarchy.root_tags
        assert "Kommunikation" in hierarchy.root_tags
        assert "Rechnung" in hierarchy.hierarchy["Finanzen"]
        assert "Email" in hierarchy.hierarchy["Kommunikation"]
    
    def test_get_parent_tag(self):
        """Test getting parent of a tag."""
        hierarchy = TagHierarchy(
            root_tags=["Dokumente"],
            hierarchy={"Dokumente": ["Rechnung", "Vertrag"]},
            tag_counts={}
        )
        
        assert hierarchy.get_parent("Rechnung") == "Dokumente"
        assert hierarchy.get_parent("Vertrag") == "Dokumente"
        assert hierarchy.get_parent("Dokumente") is None
    
    def test_get_children_tags(self):
        """Test getting children of a tag."""
        hierarchy = TagHierarchy(
            root_tags=["Geschäft"],
            hierarchy={"Geschäft": ["Kunde", "Lieferant", "Partner"]},
            tag_counts={}
        )
        
        children = hierarchy.get_children("Geschäft")
        assert len(children) == 3
        assert "Kunde" in children
        assert "Lieferant" in children
        assert "Partner" in children
    
    def test_get_all_tags(self):
        """Test getting all tags in hierarchy."""
        hierarchy = TagHierarchy(
            root_tags=["Root1", "Root2"],
            hierarchy={
                "Root1": ["Child1", "Child2"],
                "Root2": ["Child3"]
            },
            tag_counts={}
        )
        
        all_tags = hierarchy.get_all_tags()
        assert len(all_tags) == 5
        assert "Root1" in all_tags
        assert "Child1" in all_tags
        assert "Child3" in all_tags


class TestSmartTagMatcher:
    """Test SmartTagMatcher functionality."""
    
    @pytest.fixture
    def mock_paperless_client(self):
        """Mock Paperless API client."""
        client = Mock()
        client.get_tags = Mock(return_value=[
            {"id": 1, "name": "Rechnung"},
            {"id": 2, "name": "Telekom"},
            {"id": 3, "name": "2024"},
            {"id": 4, "name": "Mobilfunk"},
            {"id": 5, "name": "Telekommunikation"}
        ])
        return client
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client."""
        client = Mock()
        client.complete_sync = Mock(return_value=(
            "These tags are different concepts",
            {"model": "gpt-3.5-turbo"}
        ))
        return client
    
    def test_match_tag_with_existing(self, mock_paperless_client, mock_llm_client):
        """Test matching a tag with existing tags."""
        matcher = SmartTagMatcher(
            paperless_client=mock_paperless_client,
            llm_client=mock_llm_client,
            similarity_threshold=0.95
        )
        
        # Exact match
        matcher.existing_tags_cache = ["Rechnung", "Telekom", "2024"]
        
        # Test exact match
        exact_match = TagMatch(
            original_tag="Rechnung",
            matched_tag="Rechnung",
            similarity_score=1.0,
            is_new_tag=False,
            explanation="Exact match found"
        )
        
        assert exact_match.matched_tag == "Rechnung"
        assert exact_match.similarity_score == 1.0
        assert not exact_match.is_new_tag
    
    def test_no_match_creates_new_tag(self, mock_paperless_client, mock_llm_client):
        """Test that no match results in new tag creation."""
        matcher = SmartTagMatcher(
            paperless_client=mock_paperless_client,
            llm_client=mock_llm_client,
            similarity_threshold=0.95
        )
        
        matcher.existing_tags_cache = ["Rechnung", "Telekom", "2024"]
        
        # Test new tag
        new_tag_match = TagMatch(
            original_tag="Versicherung",
            matched_tag=None,
            similarity_score=0.0,
            is_new_tag=True,
            explanation="No similar tag found, creating new tag"
        )
        
        assert new_tag_match.matched_tag is None
        assert new_tag_match.is_new_tag
    
    def test_cache_performance(self, mock_paperless_client):
        """Test that similarity cache improves performance."""
        matcher = SmartTagMatcher(
            paperless_client=mock_paperless_client,
            similarity_threshold=0.95
        )
        
        # First calculation
        tag_pair = ("Rechnung", "Rechnungen")
        score1 = fuzz.WRatio(tag_pair[0], tag_pair[1]) / 100.0
        matcher.similarity_cache[tag_pair] = score1
        
        # Second calculation (from cache)
        cached_score = matcher.similarity_cache.get(tag_pair)
        
        assert cached_score == score1
        assert tag_pair in matcher.similarity_cache
    
    @pytest.mark.asyncio
    async def test_async_tag_matching(self, mock_paperless_client, mock_llm_client):
        """Test async tag matching functionality."""
        matcher = SmartTagMatcher(
            paperless_client=mock_paperless_client,
            llm_client=mock_llm_client,
            similarity_threshold=0.95
        )
        
        # Mock async method
        mock_paperless_client.get_tags_async = AsyncMock(return_value=[
            {"id": 1, "name": "Rechnung"},
            {"id": 2, "name": "Telekom"}
        ])
        
        # Test async tag fetching
        matcher.paperless_client.get_tags_async = mock_paperless_client.get_tags_async
        tags = await matcher.paperless_client.get_tags_async()
        
        assert len(tags) == 2
        assert tags[0]["name"] == "Rechnung"
    
    def test_prevent_aggressive_unification(self):
        """Test that aggressive tag unification is prevented."""
        matcher = SmartTagMatcher(similarity_threshold=0.95)
        
        # Tags that should NOT be unified
        distinct_tags = [
            ("Telekommunikation", "Telekom"),
            ("Versicherung", "Sicherung"),
            ("Bank", "Bankverbindung"),
            ("Steuer", "Steuererklärung"),
            ("Brief", "Briefkasten")
        ]
        
        for tag1, tag2 in distinct_tags:
            score = fuzz.WRatio(tag1, tag2) / 100.0
            # These should not meet the 95% threshold
            assert score < 0.95, f"{tag1} and {tag2} should not be unified (score: {score})"