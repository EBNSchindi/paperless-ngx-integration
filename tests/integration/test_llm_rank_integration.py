"""Integration tests for rank-based LLM provider configuration with LiteLLM client.

Tests the integration between rank-based settings and actual LLM client behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import asyncio
from litellm.exceptions import APIError, RateLimitError, ServiceUnavailableError

from src.paperless_ngx.infrastructure.config.settings import Settings
from src.paperless_ngx.infrastructure.llm.litellm_client import LiteLLMClient, ModelProvider


class TestLLMRankIntegration:
    """Test LLM client integration with rank-based configuration."""
    
    @pytest.fixture
    def settings_rank_ordered(self):
        """Settings with specific rank ordering."""
        return Settings(
            paperless_api_token="test_token",
            # Anthropic rank 1 (highest priority)
            anthropic_enabled=True,
            anthropic_api_key="sk-ant-test",
            anthropic_rank=1,
            # OpenAI rank 2
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=2,
            # Ollama rank 3 (lowest priority)
            ollama_enabled=True,
            ollama_rank=3,
        )
    
    @pytest.fixture
    def settings_ollama_first(self):
        """Settings with Ollama as highest priority."""
        return Settings(
            paperless_api_token="test_token",
            ollama_enabled=True,
            ollama_rank=1,
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=2,
            anthropic_enabled=True,
            anthropic_api_key="sk-ant-test",
            anthropic_rank=3,
        )
    
    def test_router_respects_rank_ordering(self, settings_rank_ordered):
        """Test that router configuration respects rank-based ordering."""
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings_rank_ordered):
            client = LiteLLMClient()
            
            # Check router model list order
            model_list = client.router.model_list
            assert len(model_list) == 3
            
            # Models should be ordered by rank
            assert "anthropic" in model_list[0]["model_name"]  # rank 1
            assert "openai" in model_list[1]["model_name"]     # rank 2
            assert "ollama" in model_list[2]["model_name"]     # rank 3
            
            # Verify priorities match ranks
            assert model_list[0]["model_info"]["priority"] == 1
            assert model_list[1]["model_info"]["priority"] == 2
            assert model_list[2]["model_info"]["priority"] == 3
    
    def test_fallback_chain_follows_rank_order(self, settings_rank_ordered):
        """Test that fallback chain is built according to rank order."""
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings_rank_ordered):
            client = LiteLLMClient()
            
            # Check fallbacks structure
            fallbacks = client.router.fallbacks
            assert len(fallbacks) == 2  # n-1 fallback entries for n models
            
            # First model should fallback to second and third
            first_model = list(fallbacks[0].keys())[0]
            assert "anthropic" in first_model
            
            fallback_models = fallbacks[0][first_model]
            assert len(fallback_models) == 2
            assert any("openai" in m for m in fallback_models)
            assert any("ollama" in m for m in fallback_models)
    
    @patch('litellm.Router.completion')
    def test_rank_1_provider_called_first(self, mock_completion, settings_rank_ordered):
        """Test that rank 1 provider is always attempted first."""
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings_rank_ordered):
            client = LiteLLMClient()
            
            # Mock successful response
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Anthropic response"))]
            mock_response.model = "claude-3-5-sonnet-20241022"
            mock_response.usage = Mock(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30
            )
            mock_completion.return_value = mock_response
            
            response, metadata = client.complete_sync("Test prompt")
            
            # Verify rank 1 model (Anthropic) was called
            mock_completion.assert_called_once()
            call_args = mock_completion.call_args
            assert "anthropic" in call_args[1]['model']
            assert metadata['provider'] == 'anthropic'
    
    @patch('litellm.Router.completion')
    def test_fallback_respects_rank_order(self, mock_completion, settings_rank_ordered):
        """Test that fallback follows rank order when primary fails."""
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings_rank_ordered):
            client = LiteLLMClient()
            
            # First call (Anthropic) fails, second call (OpenAI) succeeds
            anthropic_error = APIError("Anthropic API error")
            
            openai_response = Mock()
            openai_response.choices = [Mock(message=Mock(content="OpenAI response"))]
            openai_response.model = "gpt-3.5-turbo"
            openai_response.usage = Mock(
                prompt_tokens=15,
                completion_tokens=25,
                total_tokens=40
            )
            
            mock_completion.side_effect = [anthropic_error, openai_response]
            
            response, metadata = client.complete_sync("Test prompt", max_retries=2)
            
            # Should have tried twice
            assert mock_completion.call_count == 2
            
            # First call should be Anthropic (rank 1)
            first_call = mock_completion.call_args_list[0]
            assert "anthropic" in first_call[1]['model']
            
            # Second call should be OpenAI (rank 2)
            second_call = mock_completion.call_args_list[1]
            # Note: Router may use internal model names
            
            assert response == "OpenAI response"
    
    def test_model_switching_by_rank_change(self):
        """Test that changing ranks changes the model priority."""
        # First configuration: OpenAI rank 1
        settings1 = Settings(
            paperless_api_token="test_token",
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=1,
            ollama_enabled=True,
            ollama_rank=2,
        )
        
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings1):
            client1 = LiteLLMClient()
            model_list1 = client1.router.model_list
            assert "openai" in model_list1[0]["model_name"]
        
        # Second configuration: Ollama rank 1
        settings2 = Settings(
            paperless_api_token="test_token",
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=2,
            ollama_enabled=True,
            ollama_rank=1,
        )
        
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings2):
            client2 = LiteLLMClient()
            model_list2 = client2.router.model_list
            assert "ollama" in model_list2[0]["model_name"]
    
    def test_disabled_providers_not_in_router(self):
        """Test that disabled providers are not included in router."""
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
        
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings):
            client = LiteLLMClient()
            
            model_list = client.router.model_list
            assert len(model_list) == 2
            
            # Check that only enabled providers are present
            model_names = [m["model_name"] for m in model_list]
            assert any("openai" in name for name in model_names)
            assert any("anthropic" in name for name in model_names)
            assert not any("ollama" in name for name in model_names)
    
    @pytest.mark.asyncio
    async def test_async_completion_respects_rank(self, settings_ollama_first):
        """Test async completion respects rank ordering."""
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings_ollama_first):
            client = LiteLLMClient()
            
            with patch('litellm.Router.acompletion') as mock_acompletion:
                mock_response = Mock()
                mock_response.choices = [Mock(message=Mock(content="Ollama async response"))]
                mock_response.model = "ollama/llama3.1:8b"
                mock_response.usage = Mock(
                    prompt_tokens=10,
                    completion_tokens=20,
                    total_tokens=30
                )
                mock_acompletion.return_value = mock_response
                
                response, metadata = await client.complete_async("Test prompt")
                
                # Should use Ollama (rank 1)
                mock_acompletion.assert_called_once()
                call_args = mock_acompletion.call_args
                assert "ollama" in call_args[1]['model']
                assert metadata['provider'] == 'ollama'
    
    def test_all_providers_fail_raises_exception(self, settings_rank_ordered):
        """Test that exception is raised when all providers fail."""
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings_rank_ordered):
            client = LiteLLMClient()
            
            with patch('litellm.Router.completion') as mock_completion:
                # All providers fail
                mock_completion.side_effect = APIError("All providers failed")
                
                with pytest.raises(Exception) as exc_info:
                    client.complete_sync("Test prompt", max_retries=1)
                
                assert "All providers failed" in str(exc_info.value)
    
    def test_rank_gaps_do_not_affect_ordering(self):
        """Test that gaps in rank numbers don't affect ordering."""
        settings = Settings(
            paperless_api_token="test_token",
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=2,
            ollama_enabled=True,
            ollama_rank=7,  # Gap in ranks
            anthropic_enabled=True,
            anthropic_api_key="sk-ant-test",
            anthropic_rank=9,  # Another gap
        )
        
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings):
            client = LiteLLMClient()
            
            model_list = client.router.model_list
            # Should still be ordered correctly: 2, 7, 9
            assert "openai" in model_list[0]["model_name"]
            assert "ollama" in model_list[1]["model_name"]
            assert "anthropic" in model_list[2]["model_name"]
    
    def test_single_provider_no_fallback(self):
        """Test single provider configuration has no fallback."""
        settings = Settings(
            paperless_api_token="test_token",
            openai_enabled=False,
            ollama_enabled=True,
            ollama_rank=1,
            anthropic_enabled=False,
        )
        
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings):
            client = LiteLLMClient()
            
            # Should only have one model
            assert len(client.router.model_list) == 1
            assert "ollama" in client.router.model_list[0]["model_name"]
            
            # No fallbacks when only one provider
            assert len(client.router.fallbacks) == 0
    
    def test_custom_provider_with_rank(self):
        """Test custom LLM provider respects rank ordering."""
        settings = Settings(
            paperless_api_token="test_token",
            custom_llm_enabled=True,
            custom_llm_api_key="sk-custom",
            custom_llm_base_url="http://custom.llm",
            custom_llm_rank=1,  # Highest priority
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=2,
        )
        
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings):
            client = LiteLLMClient()
            
            model_list = client.router.model_list
            # Custom should be first (rank 1)
            assert "custom" in model_list[0]["model_name"]
            assert model_list[0]["model_info"]["provider"] == "custom"
    
    @patch('litellm.Router.completion')
    def test_rate_limiting_triggers_next_provider(self, mock_completion, settings_rank_ordered):
        """Test that rate limiting on high-rank provider triggers next in line."""
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings_rank_ordered):
            client = LiteLLMClient()
            
            # Anthropic (rank 1) hits rate limit, OpenAI (rank 2) succeeds
            rate_limit_error = RateLimitError("Rate limit exceeded")
            
            openai_response = Mock()
            openai_response.choices = [Mock(message=Mock(content="OpenAI after rate limit"))]
            openai_response.model = "gpt-3.5-turbo"
            openai_response.usage = Mock(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30
            )
            
            # First call rate limited, second succeeds
            mock_completion.side_effect = [rate_limit_error, openai_response]
            
            # Note: Rate limiting has special handling with longer wait
            # This test may timeout if actual sleep is used
            with patch('asyncio.sleep'):
                with patch('time.sleep'):
                    response, metadata = client.complete_sync("Test prompt", max_retries=2)
            
            assert response == "OpenAI after rate limit"
    
    def test_health_check_all_ranked_providers(self, settings_rank_ordered):
        """Test health check includes all ranked providers."""
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings_rank_ordered):
            with patch('litellm.completion') as mock_completion:
                # Mock successful health checks
                mock_response = Mock()
                mock_response.choices = [Mock(message=Mock(content="healthy"))]
                mock_completion.return_value = mock_response
                
                client = LiteLLMClient()
                health = client.health_check()
                
                # All three providers should be checked
                assert 'anthropic' in health
                assert 'openai' in health
                assert 'ollama' in health
                
                # Number of health checks should match number of providers
                assert mock_completion.call_count == 3
    
    def test_cost_tracking_with_ranked_providers(self, settings_rank_ordered):
        """Test cost tracking works correctly with rank-based ordering."""
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings_rank_ordered):
            client = LiteLLMClient()
            
            with patch('litellm.Router.completion') as mock_completion:
                # Mock responses from different providers
                responses = [
                    Mock(
                        choices=[Mock(message=Mock(content="Response 1"))],
                        model="claude-3-5-sonnet-20241022",
                        usage=Mock(prompt_tokens=100, completion_tokens=200, total_tokens=300)
                    ),
                    Mock(
                        choices=[Mock(message=Mock(content="Response 2"))],
                        model="gpt-3.5-turbo",
                        usage=Mock(prompt_tokens=150, completion_tokens=250, total_tokens=400)
                    ),
                ]
                
                mock_completion.side_effect = responses
                
                # Make multiple requests
                client.complete_sync("Test 1")
                client.complete_sync("Test 2")
                
                # Check cost tracking
                summary = client.get_cost_summary()
                assert summary['total']['requests'] == 2
                assert summary['total']['tokens'] == 700  # 300 + 400
    
    def test_gemini_provider_with_rank(self):
        """Test Gemini provider respects rank ordering."""
        settings = Settings(
            paperless_api_token="test_token",
            gemini_enabled=True,
            gemini_api_key="sk-gem-test",
            gemini_rank=1,  # Highest priority
            openai_enabled=True,
            openai_api_key="sk-test",
            openai_rank=2,
        )
        
        with patch('src.paperless_ngx.infrastructure.llm.litellm_client.get_settings', 
                   return_value=settings):
            client = LiteLLMClient()
            
            model_list = client.router.model_list
            # Gemini should be first (rank 1)
            assert "gemini" in model_list[0]["model_name"]
            assert model_list[0]["model_info"]["provider"] == "gemini"