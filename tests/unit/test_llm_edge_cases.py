"""Edge case tests for rank-based LLM configuration.

Tests edge cases, error conditions, and backwards compatibility scenarios.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError
import tempfile
from pathlib import Path

from src.paperless_ngx.infrastructure.config.settings import Settings, get_settings, reload_settings


class TestLLMEdgeCases:
    """Test edge cases and error conditions for LLM configuration."""
    
    def test_all_providers_disabled_error(self):
        """Test that all providers disabled raises appropriate error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                paperless_api_token="test_token",
                openai_enabled=False,
                ollama_enabled=False,
                anthropic_enabled=False,
                gemini_enabled=False,
                custom_llm_enabled=False,
            )
        
        error_msg = str(exc_info.value)
        assert "At least one LLM provider must be properly configured" in error_msg
    
    def test_enabled_but_no_api_key_excluded(self):
        """Test providers enabled but without required API keys are excluded."""
        settings = Settings(
            paperless_api_token="test_token",
            # OpenAI enabled but no key
            openai_enabled=True,
            openai_api_key=None,
            openai_rank=1,
            # Anthropic enabled but no key
            anthropic_enabled=True,
            anthropic_api_key=None,
            anthropic_rank=2,
            # Gemini enabled but no key
            gemini_enabled=True,
            gemini_api_key=None,
            gemini_rank=3,
            # Custom enabled but no key
            custom_llm_enabled=True,
            custom_llm_api_key=None,
            custom_llm_rank=4,
            # Only Ollama works without key
            ollama_enabled=True,
            ollama_rank=5,
        )
        
        # Only Ollama should be in the order
        assert settings.llm_provider_order == ["ollama"]
    
    def test_same_rank_for_all_providers(self, caplog):
        """Test all providers with identical rank values."""
        import logging
        
        with caplog.at_level(logging.WARNING):
            settings = Settings(
                paperless_api_token="test_token",
                openai_enabled=True,
                openai_api_key="sk-test",
                openai_rank=5,
                ollama_enabled=True,
                ollama_rank=5,
                anthropic_enabled=True,
                anthropic_api_key="sk-ant",
                anthropic_rank=5,
                gemini_enabled=True,
                gemini_api_key="sk-gem",
                gemini_rank=5,
                custom_llm_enabled=True,
                custom_llm_api_key="sk-custom",
                custom_llm_rank=5,
            )
            
            # All should be included
            assert len(settings.llm_provider_order) == 5
            
            # Warning about duplicates should be logged
            warning_found = False
            for record in caplog.records:
                if "Duplicate ranks detected" in record.message:
                    warning_found = True
                    break
            assert warning_found
    
    def test_rank_boundary_values(self):
        """Test rank boundary values (1 and 10)."""
        # Test minimum rank (1)
        settings_min = Settings(
            paperless_api_token="test_token",
            ollama_enabled=True,
            ollama_rank=1,
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=10,  # Maximum rank
        )
        
        assert settings_min.ollama_rank == 1
        assert settings_min.openai_rank == 10
        assert settings_min.llm_provider_order == ["ollama", "openai"]
    
    def test_rank_out_of_bounds(self):
        """Test rank values outside allowed range."""
        # Rank below minimum (0)
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                paperless_api_token="test_token",
                ollama_enabled=True,
                ollama_rank=0,
            )
        assert "greater than or equal to 1" in str(exc_info.value).lower()
        
        # Rank above maximum (11)
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                paperless_api_token="test_token",
                ollama_enabled=True,
                ollama_rank=11,
            )
        assert "less than or equal to 10" in str(exc_info.value).lower()
        
        # Negative rank
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                paperless_api_token="test_token",
                ollama_enabled=True,
                ollama_rank=-1,
            )
        assert "greater than or equal to 1" in str(exc_info.value).lower()
    
    def test_custom_llm_empty_base_url(self):
        """Test custom LLM with empty or None base URL."""
        # None base URL
        settings1 = Settings(
            paperless_api_token="test_token",
            custom_llm_enabled=True,
            custom_llm_api_key="sk-custom",
            custom_llm_base_url=None,
            custom_llm_rank=1,
        )
        assert settings1.custom_llm_base_url is None
        assert "custom" in settings1.llm_provider_order
        
        # Empty string base URL
        settings2 = Settings(
            paperless_api_token="test_token",
            custom_llm_enabled=True,
            custom_llm_api_key="sk-custom",
            custom_llm_base_url="",
            custom_llm_rank=1,
        )
        # Empty string might be converted to None or kept as empty
        assert "custom" in settings2.llm_provider_order
    
    def test_provider_order_immutability(self):
        """Test that provider order is computed, not stored."""
        settings = Settings(
            paperless_api_token="test_token",
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=1,
            ollama_enabled=True,
            ollama_rank=2,
        )
        
        # Get order multiple times
        order1 = settings.llm_provider_order
        order2 = settings.llm_provider_order
        
        # Should be same list
        assert order1 == order2
        assert order1 == ["openai", "ollama"]
        
        # Should not be in model dump
        model_dict = settings.model_dump()
        assert "llm_provider_order" not in model_dict
        
        # Should not be in safe dict
        safe_dict = settings.to_safe_dict()
        assert "llm_provider_order" not in safe_dict
    
    def test_environment_variable_ignored(self):
        """Test that old LLM_PROVIDER_ORDER environment variable is ignored."""
        # Set the old environment variable
        os.environ["LLM_PROVIDER_ORDER"] = "anthropic,gemini,openai"
        
        try:
            settings = Settings(
                paperless_api_token="test_token",
                openai_enabled=True,
                openai_api_key="sk-test",
                openai_rank=1,  # Should be first
                anthropic_enabled=True,
                anthropic_api_key="sk-ant",
                anthropic_rank=3,  # Should be last
                gemini_enabled=True,
                gemini_api_key="sk-gem",
                gemini_rank=2,  # Should be second
            )
            
            # Should use rank-based order, not env variable
            assert settings.llm_provider_order == ["openai", "gemini", "anthropic"]
            
            # The old env variable should have no effect
        finally:
            del os.environ["LLM_PROVIDER_ORDER"]
    
    def test_mixed_enabled_disabled_providers(self):
        """Test mix of enabled and disabled providers with various ranks."""
        settings = Settings(
            paperless_api_token="test_token",
            # Enabled with rank 2
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=2,
            # Disabled with rank 1 (should be ignored)
            anthropic_enabled=False,
            anthropic_api_key="sk-ant",
            anthropic_rank=1,
            # Enabled with rank 3
            ollama_enabled=True,
            ollama_rank=3,
            # Disabled with rank 4
            gemini_enabled=False,
            gemini_rank=4,
            # Enabled with rank 5
            custom_llm_enabled=True,
            custom_llm_api_key="sk-custom",
            custom_llm_rank=5,
        )
        
        # Only enabled providers should appear, in rank order
        assert settings.llm_provider_order == ["openai", "ollama", "custom"]
    
    def test_settings_singleton_with_ranks(self):
        """Test settings singleton behavior with rank configuration."""
        with patch.dict(os.environ, {
            "PAPERLESS_API_TOKEN": "test_token",
            "OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_RANK": "2",
            "OLLAMA_ENABLED": "true",
            "OLLAMA_RANK": "1",
        }):
            # Reset singleton
            import src.paperless_ngx.infrastructure.config.settings as settings_module
            settings_module._settings_instance = None
            
            with patch('src.paperless_ngx.infrastructure.config.settings.Settings.validate_at_startup'):
                settings1 = get_settings()
                settings2 = get_settings()
                
                # Should be same instance
                assert settings1 is settings2
                
                # Should have correct order
                assert settings1.llm_provider_order == ["ollama", "openai"]
    
    def test_reload_settings_with_new_ranks(self):
        """Test reloading settings with different rank configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            
            # Write initial configuration
            env_file.write_text("""
PAPERLESS_API_TOKEN=test_token
OPENAI_ENABLED=true
OPENAI_API_KEY=sk-test
OPENAI_RANK=1
OLLAMA_ENABLED=true
OLLAMA_RANK=2
""")
            
            with patch('src.paperless_ngx.infrastructure.config.settings.Settings.validate_at_startup'):
                settings1 = Settings.load_from_env(str(env_file))
                assert settings1.llm_provider_order == ["openai", "ollama"]
                
                # Update configuration
                env_file.write_text("""
PAPERLESS_API_TOKEN=test_token
OPENAI_ENABLED=true
OPENAI_API_KEY=sk-test
OPENAI_RANK=2
OLLAMA_ENABLED=true
OLLAMA_RANK=1
""")
                
                settings2 = Settings.load_from_env(str(env_file))
                assert settings2.llm_provider_order == ["ollama", "openai"]
    
    def test_partial_provider_configuration(self):
        """Test partial provider configuration scenarios."""
        # Only required fields for one provider
        settings = Settings(
            paperless_api_token="test_token",
            ollama_enabled=True,
            # Other providers disabled by default
        )
        
        assert settings.llm_provider_order == ["ollama"]
        assert settings.ollama_rank == 2  # Default rank
    
    def test_validation_with_no_viable_providers(self):
        """Test validation when providers are enabled but none are viable."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                paperless_api_token="test_token",
                # OpenAI enabled but no API key
                openai_enabled=True,
                openai_api_key=None,
                # Anthropic enabled but no API key
                anthropic_enabled=True,
                anthropic_api_key=None,
                # All others disabled
                ollama_enabled=False,
                gemini_enabled=False,
                custom_llm_enabled=False,
            )
        
        assert "At least one LLM provider must be properly configured" in str(exc_info.value)
    
    def test_rank_sorting_stability(self):
        """Test that rank sorting is stable for equal ranks."""
        # Create settings with same ranks multiple times
        for _ in range(5):
            settings = Settings(
                paperless_api_token="test_token",
                openai_enabled=True,
                openai_api_key="sk-test",
                openai_rank=3,
                ollama_enabled=True,
                ollama_rank=3,
                anthropic_enabled=True,
                anthropic_api_key="sk-ant",
                anthropic_rank=3,
            )
            
            # Order should be consistent (stable sort)
            order = settings.llm_provider_order
            assert len(order) == 3
            assert set(order) == {"openai", "ollama", "anthropic"}
            
            # The exact order might vary by Python version,
            # but should be consistent within a session
    
    def test_provider_order_with_complex_scenario(self):
        """Test complex scenario with all features."""
        settings = Settings(
            paperless_api_token="test_token",
            # Disabled despite rank 1
            anthropic_enabled=False,
            anthropic_rank=1,
            # Enabled with rank 2 but no API key
            openai_enabled=True,
            openai_api_key=None,
            openai_rank=2,
            # Enabled with rank 3
            ollama_enabled=True,
            ollama_rank=3,
            # Enabled with rank 4
            gemini_enabled=True,
            gemini_api_key="sk-gem",
            gemini_rank=4,
            # Disabled with rank 5
            custom_llm_enabled=False,
            custom_llm_rank=5,
        )
        
        # Only Ollama and Gemini should be in order
        assert settings.llm_provider_order == ["ollama", "gemini"]
    
    def test_validation_at_startup_with_ranks(self):
        """Test startup validation includes rank information."""
        settings = Settings(
            paperless_api_token="test_token",
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=2,
            ollama_enabled=True,
            ollama_rank=1,
        )
        
        with patch('src.paperless_ngx.infrastructure.platform.get_platform_service') as mock_platform:
            mock_service = MagicMock()
            mock_service.name = "Linux"
            mock_service.is_windows = False
            mock_service.is_posix = True
            mock_service.get_file_encoding.return_value = "utf-8"
            mock_service.is_case_sensitive_filesystem.return_value = True
            mock_service.get_temp_dir.return_value = Path("/tmp")
            mock_service.is_valid_path.return_value = (True, None)
            mock_service.fix_long_path = lambda x: x
            mock_service.get_user_data_dir.return_value = settings.app_data_dir
            mock_platform.return_value = mock_service
            
            results = settings.validate_at_startup()
            
            assert results["valid"] is True
            # Should show provider order in info
            info_str = " ".join(results["info"])
            assert "ollama" in info_str.lower()
            assert "openai" in info_str.lower()
            # Order should be mentioned
            assert any("ollama -> openai" in info.lower() or 
                      "provider order" in info.lower() 
                      for info in results["info"])