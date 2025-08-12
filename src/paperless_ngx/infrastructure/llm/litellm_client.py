"""LiteLLM Integration for unified LLM interface.

This module provides a unified interface for multiple LLM providers (Ollama, OpenAI)
with automatic fallback, retry logic, cost tracking, and rate limiting.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import litellm
from litellm import completion, acompletion, Router, get_model_cost_map
from litellm.exceptions import (
    APIError,
    Timeout,
    RateLimitError,
    ServiceUnavailableError,
    APIConnectionError
)

from src.paperless_ngx.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.drop_params = True  # Drop unsupported params instead of failing

# Optional: Add observability if langfuse is available
try:
    import langfuse
    litellm.success_callback = ["langfuse"]
    logger.debug("Langfuse observability enabled")
except ImportError:
    logger.debug("Langfuse not installed, observability disabled")


class ModelProvider(Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    CUSTOM = "custom"
    OPENAI_COMPATIBLE = "openai_compatible"


class CostTracker:
    """Track LLM usage costs."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize cost tracker.
        
        Args:
            storage_path: Path to store cost data persistently
        """
        self.storage_path = storage_path or (get_settings().app_data_dir / "llm_costs.json")
        self.costs: Dict[str, Dict[str, Union[float, int]]] = self._load_costs()
        self.session_costs: Dict[str, Decimal] = {}
        
    def _load_costs(self) -> Dict[str, Dict[str, Union[float, int]]]:
        """Load cost data from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load cost data: {e}")
        return {"total": {"cost": 0.0, "tokens": 0, "requests": 0}}
    
    def _save_costs(self) -> None:
        """Save cost data to storage."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w") as f:
                json.dump(self.costs, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cost data: {e}")
    
    def track_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: Optional[float] = None
    ) -> None:
        """Track LLM usage and costs.
        
        Args:
            model: Model identifier
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            cost: Optional pre-calculated cost
        """
        if cost is None:
            # Try to calculate cost using LiteLLM's cost map
            try:
                cost_per_token = get_model_cost_map().get(model, {})
                prompt_cost = cost_per_token.get("input_cost_per_token", 0) * prompt_tokens
                completion_cost = cost_per_token.get("output_cost_per_token", 0) * completion_tokens
                cost = prompt_cost + completion_cost
            except Exception:
                cost = 0.0
        
        # Update totals
        self.costs["total"]["cost"] += cost
        self.costs["total"]["tokens"] += prompt_tokens + completion_tokens
        self.costs["total"]["requests"] += 1
        
        # Update model-specific stats
        if model not in self.costs:
            self.costs[model] = {"cost": 0.0, "tokens": 0, "requests": 0}
        
        self.costs[model]["cost"] += cost
        self.costs[model]["tokens"] += prompt_tokens + completion_tokens
        self.costs[model]["requests"] += 1
        
        # Update session costs
        self.session_costs[model] = self.session_costs.get(model, Decimal(0)) + Decimal(str(cost))
        
        # Check alert threshold
        settings = get_settings()
        if settings.enable_cost_tracking and self.costs["total"]["cost"] > settings.cost_alert_threshold:
            logger.warning(
                f"LLM cost alert: Total costs ({self.costs['total']['cost']:.2f} EUR) "
                f"exceed threshold ({settings.cost_alert_threshold:.2f} EUR)"
            )
        
        self._save_costs()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get cost tracking summary.
        
        Returns:
            Dictionary with cost statistics
        """
        return {
            "total": self.costs.get("total", {}),
            "by_model": {k: v for k, v in self.costs.items() if k != "total"},
            "session": {k: float(v) for k, v in self.session_costs.items()}
        }


class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, max_requests_per_second: float = 5.0):
        """Initialize rate limiter.
        
        Args:
            max_requests_per_second: Maximum allowed requests per second
        """
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0.0
        self.request_times: List[float] = []
        
    async def acquire(self) -> None:
        """Acquire permission to make a request (async)."""
        current_time = time.time()
        
        # Clean old request times (older than 1 second)
        self.request_times = [
            t for t in self.request_times 
            if current_time - t < 1.0
        ]
        
        # Check if we need to wait
        if len(self.request_times) >= self.max_requests_per_second:
            sleep_time = 1.0 - (current_time - self.request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                current_time = time.time()
        
        # Record this request
        self.request_times.append(current_time)
        self.last_request_time = current_time
    
    def acquire_sync(self) -> None:
        """Acquire permission to make a request (sync)."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        
        self.last_request_time = time.time()


class LiteLLMClient:
    """Unified LLM client using LiteLLM with fallback and retry logic."""
    
    def __init__(self):
        """Initialize LiteLLM client with configuration."""
        self.settings = get_settings()
        self.cost_tracker = CostTracker()
        self.rate_limiter = RateLimiter(max_requests_per_second=5.0)
        self.router = self._setup_router()
        self.request_id_counter = 0
        
    def _setup_router(self) -> Router:
        """Setup LiteLLM router with multiple models based on provider order.
        
        Returns:
            Configured Router instance
        """
        model_list = []
        provider_models = {}  # Map provider name to model configuration
        
        # Build configurations for each enabled provider
        if self.settings.openai_enabled and self.settings.openai_api_key:
            provider_models["openai"] = {
                "litellm_params": {
                    "model": self.settings.openai_model,
                    "api_key": self.settings.get_secret_value("openai_api_key"),
                    "timeout": self.settings.openai_timeout,
                    "max_tokens": self.settings.openai_max_tokens,
                    "temperature": self.settings.openai_temperature,
                    "stream": False,
                },
                "model_info": {
                    "provider": ModelProvider.OPENAI.value,
                }
            }
            if self.settings.openai_organization:
                provider_models["openai"]["litellm_params"]["organization"] = self.settings.openai_organization
        
        if self.settings.ollama_enabled:
            provider_models["ollama"] = {
                "litellm_params": {
                    "model": f"ollama/{self.settings.ollama_model}",
                    "api_base": self.settings.ollama_base_url,
                    "timeout": self.settings.ollama_timeout,
                    "stream": False,
                },
                "model_info": {
                    "provider": ModelProvider.OLLAMA.value,
                }
            }
        
        if self.settings.anthropic_enabled and self.settings.anthropic_api_key:
            provider_models["anthropic"] = {
                "litellm_params": {
                    "model": f"claude-3-5-sonnet-20241022",  # Use actual Anthropic model name
                    "api_key": self.settings.get_secret_value("anthropic_api_key"),
                    "timeout": 30,
                    "stream": False,
                },
                "model_info": {
                    "provider": ModelProvider.ANTHROPIC.value,
                }
            }
        
        if self.settings.gemini_enabled and self.settings.gemini_api_key:
            provider_models["gemini"] = {
                "litellm_params": {
                    "model": f"gemini/{self.settings.gemini_model}",
                    "api_key": self.settings.get_secret_value("gemini_api_key"),
                    "timeout": 30,
                    "stream": False,
                },
                "model_info": {
                    "provider": ModelProvider.GEMINI.value,
                }
            }
        
        if self.settings.custom_llm_enabled and self.settings.custom_llm_api_key:
            provider_models["custom"] = {
                "litellm_params": {
                    "model": self.settings.custom_llm_model,
                    "api_key": self.settings.get_secret_value("custom_llm_api_key"),
                    "api_base": self.settings.custom_llm_base_url,
                    "timeout": 30,
                    "stream": False,
                },
                "model_info": {
                    "provider": ModelProvider.CUSTOM.value,
                }
            }
        
        # Build model list based on provider order
        for i, provider in enumerate(self.settings.llm_provider_order):
            if provider in provider_models:
                model_name = f"llm-{i+1}-{provider}"
                model_config = {
                    "model_name": model_name,
                    **provider_models[provider]
                }
                model_config["model_info"]["priority"] = i + 1
                model_list.append(model_config)
        
        if not model_list:
            raise ValueError(
                "No LLM models configured. Check that providers in LLM_PROVIDER_ORDER "
                "are enabled and have API keys."
            )
        
        # Build fallback chain based on order
        fallbacks = []
        if len(model_list) > 1:
            fallback_chain = {}
            for i in range(len(model_list) - 1):
                current_model = model_list[i]["model_name"]
                next_models = [model_list[j]["model_name"] for j in range(i + 1, len(model_list))]
                fallback_chain[current_model] = next_models
            fallbacks = [fallback_chain]
        
        # Create router with retry and fallback configuration
        router = Router(
            model_list=model_list,
            fallbacks=fallbacks,
            retry_after=1,  # Retry after 1 second
            allowed_fails=3,  # Allow 3 fails before switching to next provider
            cache_responses=True,
            routing_strategy="usage-based-routing-v2",  # Smart routing based on usage
        )
        
        logger.info(f"LLM Router configured with providers: {[m['model_name'] for m in model_list]}")
        
        return router
    
    def _get_request_id(self) -> str:
        """Generate unique request ID.
        
        Returns:
            Request ID string
        """
        self.request_id_counter += 1
        return f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.request_id_counter:04d}"
    
    async def _handle_retry(
        self,
        func,
        *args,
        max_retries: int = 3,
        **kwargs
    ) -> Any:
        """Handle retries with exponential backoff.
        
        Args:
            func: Function to retry
            max_retries: Maximum number of retries
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
        """
        delay = 1.0
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except (APIError, Timeout, ServiceUnavailableError, APIConnectionError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt)
                    logger.warning(
                        f"LLM request failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All LLM retry attempts failed: {e}")
            except RateLimitError as e:
                # Handle rate limiting with longer wait
                wait_time = 60  # Wait 1 minute for rate limit
                logger.warning(f"Rate limit hit: {e}. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                last_error = e
        
        raise last_error or Exception("All retry attempts failed")
    
    async def complete_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_retries: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate completion asynchronously with fallback and retry.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_retries: Override default max retries
            metadata: Optional metadata for tracking
            
        Returns:
            Tuple of (response text, response metadata)
        """
        request_id = self._get_request_id()
        max_retries = max_retries or self.settings.ollama_max_retries
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        # Log request
        logger.info(f"[{request_id}] Starting LLM request")
        start_time = time.time()
        
        try:
            # Use router for automatic fallback - use first model in list
            first_model = self.router.model_list[0]["model_name"] if self.router.model_list else "primary-llm"
            response = await self._handle_retry(
                self.router.acompletion,
                model=first_model,
                messages=messages,
                metadata={
                    "request_id": request_id,
                    **(metadata or {})
                },
                max_retries=max_retries
            )
            
            # Extract response
            content = response.choices[0].message.content
            model_used = response.model
            
            # Determine provider from model name
            provider = "unknown"
            if "ollama" in model_used.lower():
                provider = "ollama"
            elif "gpt" in model_used.lower() or "openai" in model_used.lower():
                provider = "openai"
            elif "claude" in model_used.lower() or "anthropic" in model_used.lower():
                provider = "anthropic"
            elif "gemini" in model_used.lower():
                provider = "gemini"
            elif "custom" in model_used.lower():
                provider = self.settings.custom_llm_name
            
            # Track costs
            if self.settings.enable_cost_tracking:
                usage = response.usage
                self.cost_tracker.track_usage(
                    model=model_used,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens
                )
            
            # Log success
            elapsed = time.time() - start_time
            logger.info(
                f"[{request_id}] LLM request completed in {elapsed:.2f}s "
                f"using {provider} ({model_used})"
            )
            
            return content, {
                "request_id": request_id,
                "model": model_used,
                "provider": provider,
                "elapsed_time": elapsed,
                "tokens": {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[{request_id}] LLM request failed after {elapsed:.2f}s: {e}")
            raise
    
    def complete_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_retries: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate completion synchronously with fallback and retry.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_retries: Override default max retries
            metadata: Optional metadata for tracking
            
        Returns:
            Tuple of (response text, response metadata)
        """
        request_id = self._get_request_id()
        max_retries = max_retries or self.settings.ollama_max_retries
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Apply rate limiting
        self.rate_limiter.acquire_sync()
        
        # Log request
        logger.info(f"[{request_id}] Starting LLM request")
        start_time = time.time()
        
        delay = 1.0
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Use router for automatic fallback - use first model in list
                first_model = self.router.model_list[0]["model_name"] if self.router.model_list else "primary-llm"
                response = self.router.completion(
                    model=first_model,
                    messages=messages,
                    metadata={
                        "request_id": request_id,
                        **(metadata or {})
                    }
                )
                
                # Extract response
                content = response.choices[0].message.content
                model_used = response.model
                
                # Determine provider from model name
                provider = "unknown"
                if "ollama" in model_used.lower():
                    provider = "ollama"
                elif "gpt" in model_used.lower() or "openai" in model_used.lower():
                    provider = "openai"
                elif "claude" in model_used.lower() or "anthropic" in model_used.lower():
                    provider = "anthropic"
                elif "gemini" in model_used.lower():
                    provider = "gemini"
                elif "custom" in model_used.lower():
                    provider = self.settings.custom_llm_name
                
                # Track costs
                if self.settings.enable_cost_tracking:
                    usage = response.usage
                    self.cost_tracker.track_usage(
                        model=model_used,
                        prompt_tokens=usage.prompt_tokens,
                        completion_tokens=usage.completion_tokens
                    )
                
                # Log success
                elapsed = time.time() - start_time
                logger.info(
                    f"[{request_id}] LLM request completed in {elapsed:.2f}s "
                    f"using {provider} ({model_used})"
                )
                
                return content, {
                    "request_id": request_id,
                    "model": model_used,
                    "provider": provider,
                    "elapsed_time": elapsed,
                    "tokens": {
                        "prompt": response.usage.prompt_tokens,
                        "completion": response.usage.completion_tokens,
                        "total": response.usage.total_tokens
                    }
                }
                
            except (APIError, Timeout, ServiceUnavailableError, APIConnectionError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt)
                    logger.warning(
                        f"[{request_id}] LLM request failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"[{request_id}] All LLM retry attempts failed: {e}")
            except RateLimitError as e:
                # Handle rate limiting with longer wait
                wait_time = 60  # Wait 1 minute for rate limit
                logger.warning(f"[{request_id}] Rate limit hit: {e}. Waiting {wait_time}s...")
                time.sleep(wait_time)
                last_error = e
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"[{request_id}] LLM request failed after {elapsed:.2f}s: {e}")
                raise
        
        raise last_error or Exception("All retry attempts failed")
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost tracking summary.
        
        Returns:
            Cost statistics dictionary
        """
        return self.cost_tracker.get_summary()
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of configured LLM providers.
        
        Returns:
            Dictionary with provider health status
        """
        health = {}
        
        # Check OpenAI
        if self.settings.openai_enabled and self.settings.openai_api_key:
            try:
                response = litellm.completion(
                    model=self.settings.openai_model,
                    messages=[{"role": "user", "content": "test"}],
                    api_key=self.settings.get_secret_value("openai_api_key"),
                    max_tokens=1,
                    timeout=5
                )
                health["openai"] = True
            except Exception as e:
                logger.warning(f"OpenAI health check failed: {e}")
                health["openai"] = False
        
        # Check Ollama
        if self.settings.ollama_enabled:
            try:
                response = litellm.completion(
                    model=f"ollama/{self.settings.ollama_model}",
                    messages=[{"role": "user", "content": "test"}],
                    api_base=self.settings.ollama_base_url,
                    max_tokens=1,
                    timeout=5
                )
                health["ollama"] = True
            except Exception as e:
                logger.warning(f"Ollama health check failed: {e}")
                health["ollama"] = False
        
        # Check Anthropic
        if self.settings.anthropic_enabled and self.settings.anthropic_api_key:
            try:
                response = litellm.completion(
                    model="claude-3-5-sonnet-20241022",
                    messages=[{"role": "user", "content": "test"}],
                    api_key=self.settings.get_secret_value("anthropic_api_key"),
                    max_tokens=1,
                    timeout=5
                )
                health["anthropic"] = True
            except Exception as e:
                logger.warning(f"Anthropic health check failed: {e}")
                health["anthropic"] = False
        
        # Check Gemini
        if self.settings.gemini_enabled and self.settings.gemini_api_key:
            try:
                response = litellm.completion(
                    model=f"gemini/{self.settings.gemini_model}",
                    messages=[{"role": "user", "content": "test"}],
                    api_key=self.settings.get_secret_value("gemini_api_key"),
                    max_tokens=1,
                    timeout=5
                )
                health["gemini"] = True
            except Exception as e:
                logger.warning(f"Gemini health check failed: {e}")
                health["gemini"] = False
        
        # Check Custom LLM
        if self.settings.custom_llm_enabled and self.settings.custom_llm_api_key:
            try:
                response = litellm.completion(
                    model=self.settings.custom_llm_model,
                    messages=[{"role": "user", "content": "test"}],
                    api_key=self.settings.get_secret_value("custom_llm_api_key"),
                    api_base=self.settings.custom_llm_base_url,
                    max_tokens=1,
                    timeout=5
                )
                health[self.settings.custom_llm_name] = True
            except Exception as e:
                logger.warning(f"Custom LLM ({self.settings.custom_llm_name}) health check failed: {e}")
                health[self.settings.custom_llm_name] = False
        
        return health


# Singleton instance
_client_instance: Optional[LiteLLMClient] = None


def get_llm_client() -> LiteLLMClient:
    """Get or create LiteLLM client singleton.
    
    Returns:
        Configured LiteLLMClient instance
    """
    global _client_instance
    
    if _client_instance is None:
        _client_instance = LiteLLMClient()
    
    return _client_instance