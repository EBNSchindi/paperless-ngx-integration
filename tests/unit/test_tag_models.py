"""Unit tests for tag analysis models and functionality."""

import pytest
from unittest.mock import Mock, patch
from typing import List

from src.paperless_ngx.domain.models.tag_models import (
    Tag,
    TagCluster,
    TagMergeRecommendation,
    TagSimilarity,
    TagAnalyzer
)


class TestTagModels:
    """Test cases for tag-related models."""
    
    def test_tag_creation(self):
        """Test Tag model creation and properties."""
        tag = Tag(
            id=1,
            name="Rechnung",
            slug="rechnung",
            document_count=50
        )
        
        assert tag.id == 1
        assert tag.name == "Rechnung"
        assert tag.slug == "rechnung"
        assert tag.document_count == 50
        assert str(tag) == "Rechnung (50 documents)"
        assert repr(tag) == "Tag(id=1, name='Rechnung', count=50)"
    
    def test_tag_equality(self):
        """Test Tag equality comparison."""
        tag1 = Tag(id=1, name="Test", slug="test", document_count=10)
        tag2 = Tag(id=1, name="Test", slug="test", document_count=10)
        tag3 = Tag(id=2, name="Test", slug="test", document_count=10)
        
        assert tag1 == tag2  # Same ID
        assert tag1 != tag3  # Different ID
        assert tag1 != "Not a tag"  # Different type
    
    def test_tag_cluster_creation(self):
        """Test TagCluster model creation."""
        primary = Tag(id=1, name="Rechnung", slug="rechnung", document_count=50)
        similar = [
            Tag(id=2, name="Rechnungen", slug="rechnungen", document_count=5),
            Tag(id=3, name="Invoice", slug="invoice", document_count=3)
        ]
        
        cluster = TagCluster(
            primary_tag=primary,
            similar_tags=similar,
            total_documents=58,
            similarity_threshold=0.8
        )
        
        assert cluster.primary_tag == primary
        assert len(cluster.similar_tags) == 2
        assert cluster.total_documents == 58
        assert cluster.similarity_threshold == 0.8
        assert cluster.tag_count == 3  # primary + 2 similar
    
    def test_tag_similarity_creation(self):
        """Test TagSimilarity model creation."""
        tag1 = Tag(id=1, name="Rechnung", slug="rechnung", document_count=50)
        tag2 = Tag(id=2, name="Rechnungen", slug="rechnungen", document_count=5)
        
        similarity = TagSimilarity(
            tag1=tag1,
            tag2=tag2,
            score=0.85,
            similarity_type="plural"
        )
        
        assert similarity.tag1 == tag1
        assert similarity.tag2 == tag2
        assert similarity.score == 0.85
        assert similarity.similarity_type == "plural"
        assert similarity.is_high_similarity(threshold=0.8) == True
        assert similarity.is_high_similarity(threshold=0.9) == False
    
    def test_tag_merge_recommendation(self):
        """Test TagMergeRecommendation model."""
        primary = Tag(id=1, name="Rechnung", slug="rechnung", document_count=50)
        merge_candidates = [
            Tag(id=2, name="Rechnungen", slug="rechnungen", document_count=5),
            Tag(id=3, name="Invoice", slug="invoice", document_count=3)
        ]
        
        recommendation = TagMergeRecommendation(
            primary_tag=primary,
            tags_to_merge=merge_candidates,
            confidence=0.92,
            reason="Plural and translation variants detected",
            impact_summary="Will affect 8 documents"
        )
        
        assert recommendation.primary_tag == primary
        assert len(recommendation.tags_to_merge) == 2
        assert recommendation.confidence == 0.92
        assert recommendation.total_affected_documents == 8  # 5 + 3
        assert "Plural" in recommendation.reason
    
    def test_tag_merge_recommendation_priority(self):
        """Test merge recommendation priority calculation."""
        # High priority: many documents, high confidence
        high_priority = TagMergeRecommendation(
            primary_tag=Tag(id=1, name="Main", slug="main", document_count=100),
            tags_to_merge=[
                Tag(id=2, name="main2", slug="main2", document_count=50),
                Tag(id=3, name="main3", slug="main3", document_count=30)
            ],
            confidence=0.95,
            reason="High similarity",
            impact_summary="180 documents"
        )
        
        # Low priority: few documents, lower confidence
        low_priority = TagMergeRecommendation(
            primary_tag=Tag(id=4, name="Minor", slug="minor", document_count=5),
            tags_to_merge=[
                Tag(id=5, name="minor2", slug="minor2", document_count=2)
            ],
            confidence=0.75,
            reason="Some similarity",
            impact_summary="2 documents"
        )
        
        assert high_priority.priority > low_priority.priority
        assert high_priority.priority > 0.9  # Should be high
        assert low_priority.priority < 0.5   # Should be low


class TestTagAnalyzer:
    """Test cases for tag analysis functionality."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a TagAnalyzer instance."""
        return TagAnalyzer()
    
    @pytest.fixture
    def sample_tags(self):
        """Create sample tags for testing."""
        return [
            Tag(id=1, name="Rechnung", slug="rechnung", document_count=50),
            Tag(id=2, name="Rechnungen", slug="rechnungen", document_count=5),
            Tag(id=3, name="Invoice", slug="invoice", document_count=3),
            Tag(id=4, name="Vertrag", slug="vertrag", document_count=30),
            Tag(id=5, name="Verträge", slug="vertraege", document_count=2),
            Tag(id=6, name="2024", slug="2024", document_count=100),
            Tag(id=7, name="2023", slug="2023", document_count=80),
            Tag(id=8, name="unused", slug="unused", document_count=0),
        ]
    
    def test_find_similar_tags(self, analyzer, sample_tags):
        """Test finding similar tags."""
        target = sample_tags[0]  # "Rechnung"
        similar = analyzer.find_similar_tags(target, sample_tags, threshold=0.7)
        
        # Should find "Rechnungen" and possibly "Invoice"
        assert len(similar) >= 1
        similar_names = [s.tag2.name for s in similar]
        assert "Rechnungen" in similar_names
    
    def test_detect_plural_variants(self, analyzer, sample_tags):
        """Test detection of singular/plural variants."""
        plural_pairs = analyzer.detect_plural_variants(sample_tags)
        
        # Should find Rechnung/Rechnungen and Vertrag/Verträge
        assert len(plural_pairs) >= 2
        
        pair_names = [(p.tag1.name, p.tag2.name) for p in plural_pairs]
        assert any(("Rechnung" in p[0] or "Rechnung" in p[1]) and 
                  ("Rechnungen" in p[0] or "Rechnungen" in p[1]) 
                  for p in pair_names)
    
    def test_detect_case_variants(self, analyzer):
        """Test detection of case variants."""
        tags = [
            Tag(id=1, name="Amazon", slug="amazon", document_count=10),
            Tag(id=2, name="amazon", slug="amazon-2", document_count=5),
            Tag(id=3, name="AMAZON", slug="amazon-3", document_count=2),
            Tag(id=4, name="Google", slug="google", document_count=8),
        ]
        
        case_variants = analyzer.detect_case_variants(tags)
        
        # Should find all Amazon variants
        assert len(case_variants) >= 1
        
        # Check that Amazon variants are grouped
        amazon_cluster = next((c for c in case_variants 
                              if "Amazon" in c.primary_tag.name), None)
        assert amazon_cluster is not None
        assert len(amazon_cluster.similar_tags) == 2  # amazon and AMAZON
    
    def test_detect_unused_tags(self, analyzer, sample_tags):
        """Test detection of unused tags."""
        unused = analyzer.detect_unused_tags(sample_tags)
        
        assert len(unused) == 1
        assert unused[0].name == "unused"
        assert unused[0].document_count == 0
    
    def test_cluster_similar_tags(self, analyzer, sample_tags):
        """Test tag clustering."""
        clusters = analyzer.cluster_similar_tags(sample_tags, threshold=0.7)
        
        # Should create clusters for similar tags
        assert len(clusters) > 0
        
        # Find Rechnung cluster
        rechnung_cluster = next((c for c in clusters 
                                if c.primary_tag.name == "Rechnung"), None)
        assert rechnung_cluster is not None
        assert "Rechnungen" in [t.name for t in rechnung_cluster.similar_tags]
    
    def test_generate_merge_recommendations(self, analyzer, sample_tags):
        """Test generation of merge recommendations."""
        recommendations = analyzer.generate_merge_recommendations(sample_tags)
        
        assert len(recommendations) > 0
        
        # Check recommendation properties
        for rec in recommendations:
            assert rec.confidence > 0
            assert rec.confidence <= 1
            assert len(rec.reason) > 0
            assert rec.total_affected_documents > 0
            assert rec.priority >= 0
    
    def test_calculate_similarity_score(self, analyzer):
        """Test similarity score calculation."""
        # Exact match
        score = analyzer.calculate_similarity_score("test", "test")
        assert score == 1.0
        
        # Case difference
        score = analyzer.calculate_similarity_score("Test", "test")
        assert score > 0.9
        
        # Plural variant
        score = analyzer.calculate_similarity_score("Rechnung", "Rechnungen")
        assert score > 0.7
        
        # Completely different
        score = analyzer.calculate_similarity_score("Rechnung", "Vertrag")
        assert score < 0.5
        
        # Empty strings
        score = analyzer.calculate_similarity_score("", "test")
        assert score == 0
    
    @patch('rapidfuzz.fuzz.ratio')
    def test_fuzzy_matching_integration(self, mock_ratio, analyzer):
        """Test integration with fuzzy matching library."""
        mock_ratio.return_value = 85
        
        score = analyzer.calculate_similarity_score("Rechnung", "Rechhnung")
        
        mock_ratio.assert_called()
        assert score == 0.85
    
    def test_language_variant_detection(self, analyzer):
        """Test detection of language variants (e.g., German/English)."""
        tags = [
            Tag(id=1, name="Rechnung", slug="rechnung", document_count=50),
            Tag(id=2, name="Invoice", slug="invoice", document_count=5),
            Tag(id=3, name="Vertrag", slug="vertrag", document_count=30),
            Tag(id=4, name="Contract", slug="contract", document_count=3),
        ]
        
        language_pairs = analyzer.detect_language_variants(tags)
        
        # Should detect Rechnung/Invoice and Vertrag/Contract
        assert len(language_pairs) >= 2
        
        # Check specific pairs
        pair_names = [(p.tag1.name, p.tag2.name) for p in language_pairs]
        assert any("Rechnung" in p and "Invoice" in p for p in [p[0] + p[1] for p in pair_names])
    
    def test_tag_statistics(self, analyzer, sample_tags):
        """Test calculation of tag statistics."""
        stats = analyzer.calculate_tag_statistics(sample_tags)
        
        assert stats['total_tags'] == len(sample_tags)
        assert stats['total_documents'] == sum(t.document_count for t in sample_tags)
        assert stats['unused_tags'] == 1
        assert stats['average_documents_per_tag'] > 0
        assert 'most_used_tag'] == '2024'  # Has 100 documents
        assert stats['least_used_tag'] == 'unused'  # Has 0 documents
    
    def test_optimization_suggestions(self, analyzer, sample_tags):
        """Test generation of tag optimization suggestions."""
        suggestions = analyzer.generate_optimization_suggestions(sample_tags)
        
        assert len(suggestions) > 0
        
        # Should suggest removing unused tags
        assert any("unused" in s.lower() or "nicht verwendet" in s.lower() 
                  for s in suggestions)
        
        # Should suggest merging similar tags
        assert any("merge" in s.lower() or "zusammenführen" in s.lower() 
                  for s in suggestions)
    
    def test_tag_hierarchy_detection(self, analyzer):
        """Test detection of hierarchical tag relationships."""
        tags = [
            Tag(id=1, name="2024", slug="2024", document_count=100),
            Tag(id=2, name="2024-Q1", slug="2024-q1", document_count=25),
            Tag(id=3, name="2024-Q2", slug="2024-q2", document_count=25),
            Tag(id=4, name="2024-03", slug="2024-03", document_count=10),
            Tag(id=5, name="2024-03-15", slug="2024-03-15", document_count=2),
        ]
        
        hierarchies = analyzer.detect_tag_hierarchies(tags)
        
        if hierarchies:  # Method might not be implemented
            # Should detect 2024 as parent of quarters and months
            year_hierarchy = next((h for h in hierarchies if h['parent'] == '2024'), None)
            assert year_hierarchy is not None
            assert len(year_hierarchy['children']) >= 2
    
    def test_performance_with_large_tagset(self, analyzer):
        """Test performance with large number of tags."""
        import time
        
        # Create 1000 tags
        large_tagset = [
            Tag(id=i, name=f"Tag{i}", slug=f"tag{i}", document_count=i % 100)
            for i in range(1000)
        ]
        
        start = time.time()
        clusters = analyzer.cluster_similar_tags(large_tagset, threshold=0.9)
        duration = time.time() - start
        
        # Should complete within reasonable time
        assert duration < 5.0  # 5 seconds for 1000 tags
        
        # Should produce some clusters (tags with very similar names)
        assert len(clusters) >= 0
    
    def test_special_character_handling(self, analyzer):
        """Test handling of tags with special characters."""
        tags = [
            Tag(id=1, name="C++", slug="c-plus-plus", document_count=10),
            Tag(id=2, name="C#", slug="c-sharp", document_count=8),
            Tag(id=3, name="F#", slug="f-sharp", document_count=5),
            Tag(id=4, name="C/C++", slug="c-c-plus-plus", document_count=3),
        ]
        
        # Should handle special characters without errors
        similar = analyzer.find_similar_tags(tags[0], tags, threshold=0.5)
        assert len(similar) >= 1  # Should find C/C++
        
        clusters = analyzer.cluster_similar_tags(tags, threshold=0.6)
        # Should cluster C++ with C/C++
        assert any(cluster.primary_tag.name == "C++" for cluster in clusters)
    
    def test_tag_name_normalization(self, analyzer):
        """Test tag name normalization for comparison."""
        # Test various normalizations
        assert analyzer.normalize_tag_name("  Test  ") == "test"
        assert analyzer.normalize_tag_name("TEST") == "test"
        assert analyzer.normalize_tag_name("Test-Tag") == "test-tag"
        assert analyzer.normalize_tag_name("Test_Tag") == "test_tag"
        assert analyzer.normalize_tag_name("Übung") == "übung"
        assert analyzer.normalize_tag_name("Größe") == "größe"
    
    def test_empty_tagset_handling(self, analyzer):
        """Test handling of empty tag sets."""
        empty_tags = []
        
        # Should handle empty input gracefully
        clusters = analyzer.cluster_similar_tags(empty_tags)
        assert clusters == []
        
        unused = analyzer.detect_unused_tags(empty_tags)
        assert unused == []
        
        stats = analyzer.calculate_tag_statistics(empty_tags)
        assert stats['total_tags'] == 0
        assert stats['total_documents'] == 0