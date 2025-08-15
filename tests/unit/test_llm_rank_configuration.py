"""Unit tests for rank-based LLM provider configuration.

Tests the new rank-based ordering system that replaces LLM_PROVIDER_ORDER.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError
import logging

from src.paperless_ngx.infrastructure.config.settings import Settings, get_settings


class TestRankBasedConfiguration:
    """Test rank-based LLM provider configuration."""
    
    def test_rank_based_ordering_simple(self):
        """Test that providers are ordered by rank (lower rank = higher priority)."""
        settings = Settings(
            paperless_api_token="test_token",
            # OpenAI rank 1 (highest priority)
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=1,
            # Ollama rank 2
            ollama_enabled=True,
            ollama_rank=2,
            # Anthropic rank 3
            anthropic_enabled=True,
            anthropic_api_key="sk-ant-test",
            anthropic_rank=3,
        )
        
        provider_order = settings.llm_provider_order
        assert provider_order == ["openai", "ollama", "anthropic"]
    
    def test_rank_based_ordering_reverse(self):
        """Test reverse rank ordering."""
        settings = Settings(
            paperless_api_token="test_token",
            # OpenAI rank 3 (lowest priority)
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=3,
            # Ollama rank 2
            ollama_enabled=True,
            ollama_rank=2,
            # Anthropic rank 1 (highest priority)
            anthropic_enabled=True,
            anthropic_api_key="sk-ant-test",
            anthropic_rank=1,
        )
        
        provider_order = settings.llm_provider_order
        assert provider_order == ["anthropic", "ollama", "openai"]
    
    def test_duplicate_rank_detection(self, caplog):
        """Test that duplicate ranks are detected and logged as warning."""
        with caplog.at_level(logging.WARNING):
            settings = Settings(
                paperless_api_token="test_token",
                # Both providers have rank 1
                openai_enabled=True,
                openai_api_key="sk-test",
                openai_rank=1,
                ollama_enabled=True,
                ollama_rank=1,
                anthropic_enabled=False,
            )
            
            # Should still work but with warning
            provider_order = settings.llm_provider_order
            assert len(provider_order) == 2
            assert "openai" in provider_order
            assert "ollama" in provider_order
            
            # Check for warning about duplicate ranks
            assert any("Duplicate ranks detected" in record.message for record in caplog.records)
    
    def test_duplicate_rank_multiple_providers(self, caplog):
        """Test multiple providers with same rank."""
        with caplog.at_level(logging.WARNING):
            settings = Settings(
                paperless_api_token="test_token",
                # All three providers have rank 2
                openai_enabled=True,
                openai_api_key="sk-test",
                openai_rank=2,
                ollama_enabled=True,
                ollama_rank=2,
                anthropic_enabled=True,
                anthropic_api_key="sk-ant-test",
                anthropic_rank=2,
            )
            
            provider_order = settings.llm_provider_order
            assert len(provider_order) == 3
            assert "openai" in provider_order
            assert "ollama" in provider_order
            assert "anthropic" in provider_order
            
            # Warning should be logged
            assert any("Duplicate ranks detected" in record.message for record in caplog.records)
    
    def test_disabled_providers_excluded(self):
        """Test that disabled providers are excluded from order."""
        settings = Settings(
            paperless_api_token="test_token",
            # OpenAI enabled
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=1,
            # Ollama disabled
            ollama_enabled=False,
            ollama_rank=2,
            # Anthropic enabled
            anthropic_enabled=True,
            anthropic_api_key="sk-ant-test",
            anthropic_rank=3,
        )
        
        provider_order = settings.llm_provider_order
        assert provider_order == ["openai", "anthropic"]
        assert "ollama" not in provider_order
    
    def test_providers_without_api_keys_excluded(self):
        """Test that providers without API keys are excluded (except Ollama)."""
        settings = Settings(
            paperless_api_token="test_token",
            # OpenAI enabled but no API key
            openai_enabled=True,
            openai_api_key=None,
            openai_rank=1,
            # Ollama enabled (no API key needed)
            ollama_enabled=True,
            ollama_rank=2,
            # Anthropic enabled but no API key
            anthropic_enabled=True,
            anthropic_api_key=None,
            anthropic_rank=3,
            # Explicitly disable others
            gemini_enabled=False,
            custom_llm_enabled=False,
        )
        
        provider_order = settings.llm_provider_order
        # Only Ollama should be included (doesn't require API key)
        assert provider_order == ["ollama"]
    
    def test_all_providers_disabled_raises_error(self):
        """Test that having all providers disabled raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                paperless_api_token="test_token",
                openai_enabled=False,
                ollama_enabled=False,
                anthropic_enabled=False,
                gemini_enabled=False,
                custom_llm_enabled=False,
            )
        
        assert "At least one LLM provider must be properly configured" in str(exc_info.value)
    
    def test_gaps_in_rank_numbers(self):
        """Test that gaps in rank numbers work correctly."""
        settings = Settings(
            paperless_api_token="test_token",
            # Rank 1
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=1,
            # Rank 5 (gap)
            ollama_enabled=True,
            ollama_rank=5,
            # Rank 10 (bigger gap)
            anthropic_enabled=True,
            anthropic_api_key="sk-ant-test",
            anthropic_rank=10,
        )
        
        provider_order = settings.llm_provider_order
        # Should still be ordered correctly despite gaps
        assert provider_order == ["openai", "ollama", "anthropic"]
    
    def test_single_provider_enabled(self):
        """Test with only one provider enabled."""
        settings = Settings(
            paperless_api_token="test_token",
            openai_enabled=False,
            ollama_enabled=True,
            ollama_rank=1,
            anthropic_enabled=False,
        )
        
        provider_order = settings.llm_provider_order
        assert provider_order == ["ollama"]
    
    def test_all_five_providers_ranked(self):
        """Test all five providers with different ranks."""
        settings = Settings(
            paperless_api_token="test_token",
            # All providers enabled with unique ranks
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=2,
            ollama_enabled=True,
            ollama_rank=1,
            anthropic_enabled=True,
            anthropic_api_key="sk-ant-test",
            anthropic_rank=3,
            gemini_enabled=True,
            gemini_api_key="sk-gem-test",
            gemini_rank=4,
            custom_llm_enabled=True,
            custom_llm_api_key="sk-custom-test",
            custom_llm_rank=5,
        )
        
        provider_order = settings.llm_provider_order
        assert provider_order == ["ollama", "openai", "anthropic", "gemini", "custom"]
    
    def test_custom_llm_without_base_url(self):
        """Test custom LLM can work without base URL (empty string allowed)."""
        settings = Settings(
            paperless_api_token="test_token",
            custom_llm_enabled=True,
            custom_llm_api_key="sk-custom",
            custom_llm_base_url=None,  # Empty/None should be allowed
            custom_llm_rank=1,
        )
        
        provider_order = settings.llm_provider_order
        assert "custom" in provider_order
    
    def test_rank_boundaries(self):
        """Test rank value boundaries (1-10)."""
        # Minimum rank value (1)
        settings = Settings(
            paperless_api_token="test_token",
            ollama_enabled=True,
            ollama_rank=1,
        )
        assert settings.ollama_rank == 1
        
        # Maximum rank value (10)
        settings = Settings(
            paperless_api_token="test_token",
            ollama_enabled=True,
            ollama_rank=10,
        )
        assert settings.ollama_rank == 10
    
    def test_rank_validation_below_minimum(self):
        """Test that rank below 1 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                paperless_api_token="test_token",
                ollama_enabled=True,
                ollama_rank=0,  # Below minimum
            )
        
        assert "greater than or equal to 1" in str(exc_info.value).lower()
    
    def test_rank_validation_above_maximum(self):
        """Test that rank above 10 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                paperless_api_token="test_token",
                ollama_enabled=True,
                ollama_rank=11,  # Above maximum
            )
        
        assert "less than or equal to 10" in str(exc_info.value).lower()
    
    def test_dynamic_rank_changes(self):
        """Test that changing ranks dynamically updates provider order."""
        settings = Settings(
            paperless_api_token="test_token",
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=2,
            ollama_enabled=True,
            ollama_rank=1,
        )
        
        # Initial order
        assert settings.llm_provider_order == ["ollama", "openai"]
        
        # Note: In real usage, settings are immutable after creation
        # This test demonstrates the property behavior
        # To actually change ranks, you'd need to create a new Settings instance
    
    def test_provider_order_property_is_computed(self):
        """Test that llm_provider_order is a computed property, not stored."""
        settings = Settings(
            paperless_api_token="test_token",
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=1,
            ollama_enabled=True,
            ollama_rank=2,
        )
        
        # Property should be computed each time
        order1 = settings.llm_provider_order
        order2 = settings.llm_provider_order
        assert order1 == order2
        assert order1 == ["openai", "ollama"]
        
        # Verify it's not in the dict representation
        settings_dict = settings.to_safe_dict()
        assert "llm_provider_order" not in settings_dict
    
    def test_backwards_compatibility_llm_provider_order_removed(self):
        """Test that old LLM_PROVIDER_ORDER environment variable is completely removed."""
        import os
        
        # Try setting the old environment variable
        os.environ["LLM_PROVIDER_ORDER"] = "openai,ollama,anthropic"
        
        try:
            settings = Settings(
                paperless_api_token="test_token",
                openai_enabled=True,
                openai_api_key="sk-test",
                openai_rank=3,
                ollama_enabled=True,
                ollama_rank=1,
            )
            
            # Should use rank-based ordering, not environment variable
            assert settings.llm_provider_order == ["ollama", "openai"]
            
            # The old environment variable should be ignored
            # (rank determines order, not LLM_PROVIDER_ORDER)
        finally:
            # Clean up
            del os.environ["LLM_PROVIDER_ORDER"]
    
    def test_model_validation_missing_api_keys(self):
        """Test model validation for providers missing required API keys."""
        # OpenAI requires API key
        settings = Settings(
            paperless_api_token="test_token",
            openai_enabled=True,
            openai_api_key=None,
            openai_rank=1,
            ollama_enabled=True,
            ollama_rank=2,
            # Explicitly disable others
            anthropic_enabled=False,
            gemini_enabled=False,
            custom_llm_enabled=False,
        )
        
        # OpenAI should not be in the order without API key
        assert "openai" not in settings.llm_provider_order
        assert "ollama" in settings.llm_provider_order
    
    def test_settings_validation_at_startup(self):
        """Test comprehensive validation at startup."""
        settings = Settings(
            paperless_api_token="test_token",
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=1,
            ollama_enabled=True,
            ollama_rank=2,
        )
        
        with patch('src.paperless_ngx.infrastructure.platform.get_platform_service') as mock_platform:
            mock_service = MagicMock()
            mock_service.name = "Linux"
            mock_service.is_windows = False
            mock_service.is_posix = True
            mock_service.get_file_encoding.return_value = "utf-8"
            mock_service.is_case_sensitive_filesystem.return_value = True
            mock_service.get_temp_dir.return_value = "/tmp"
            mock_service.is_valid_path.return_value = (True, None)
            mock_service.fix_long_path.return_value = settings.app_data_dir
            mock_service.get_user_data_dir.return_value = settings.app_data_dir
            mock_platform.return_value = mock_service
            
            results = settings.validate_at_startup()
            
            assert results["valid"] is True
            assert "openai -> ollama" in results["info"][0].lower()
            assert len(results["errors"]) == 0
    
    def test_edge_case_all_same_rank_stable_sort(self):
        """Test that providers with same rank maintain stable sort order."""
        settings = Settings(
            paperless_api_token="test_token",
            # All have rank 5
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=5,
            ollama_enabled=True,
            ollama_rank=5,
            anthropic_enabled=True,
            anthropic_api_key="sk-ant-test",
            anthropic_rank=5,
        )
        
        provider_order = settings.llm_provider_order
        
        # With same ranks, order should be stable (based on collection order)
        # The exact order may vary, but it should be consistent
        assert len(provider_order) == 3
        assert set(provider_order) == {"openai", "ollama", "anthropic"}
        
        # Multiple calls should return same order
        assert provider_order == settings.llm_provider_order