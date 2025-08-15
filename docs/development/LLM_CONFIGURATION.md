# LLM Configuration Guide

## Table of Contents
1. [Overview](#overview)
2. [Provider Configuration](#provider-configuration)
3. [Model Selection](#model-selection)
4. [Common Configuration Errors](#common-configuration-errors)
5. [JSON Response Format](#json-response-format)
6. [Troubleshooting](#troubleshooting)
7. [Performance Optimization](#performance-optimization)
8. [Cost Management](#cost-management)

## Overview

The Paperless NGX Integration system uses LiteLLM to provide multi-provider LLM support with automatic failover and cost tracking. This guide covers all aspects of LLM configuration.

## Provider Configuration

### OpenAI

```bash
# .env configuration
OPENAI_ENABLED=true
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini              # Recommended for production
OPENAI_TEMPERATURE=0.1                # 0.0-1.0 (lower = more deterministic)
OPENAI_MAX_TOKENS=2000                # Response length limit
OPENAI_TIMEOUT=30                     # Request timeout in seconds
OPENAI_ORGANIZATION=                  # Optional: org ID
```

**Available Models** (as of January 2025):
- `gpt-4o-mini` - **RECOMMENDED**: Best price/performance, 128k context
- `gpt-4o` - Latest flagship model, 128k context
- `gpt-4-turbo` - High quality, 128k context
- `gpt-4-turbo-preview` - Preview features, 128k context
- `gpt-3.5-turbo` - Budget option, 16k context
- `gpt-3.5-turbo-16k` - Extended context budget option

**⚠️ WARNING: Non-Existent Models**
```bash
# THESE MODELS DO NOT EXIST - DO NOT USE:
OPENAI_MODEL=gpt-5-nano        # ❌ FICTIONAL
OPENAI_MODEL=gpt-5-mini        # ❌ FICTIONAL
OPENAI_MODEL=gpt-5             # ❌ NOT RELEASED
OPENAI_MODEL=gpt-4o5-mini      # ❌ TYPO (should be gpt-4o-mini)
```

### Ollama (Local LLM)

```bash
# .env configuration
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TEMPERATURE=0.1
OLLAMA_MAX_TOKENS=2000
OLLAMA_TIMEOUT=60                     # Longer timeout for local models
```

**Setup Instructions**:
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull recommended models
ollama pull llama3.1:8b               # 8B parameters, balanced
ollama pull mistral:7b                # Alternative, faster
ollama pull llama3.1:70b              # High quality, requires 40GB+ RAM

# Verify installation
ollama list
```

### Anthropic (Claude)

```bash
# .env configuration
ANTHROPIC_ENABLED=true
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_TEMPERATURE=0.1
ANTHROPIC_MAX_TOKENS=2000
ANTHROPIC_TIMEOUT=30
```

### Provider Order and Failover

```bash
# Define failover chain (comma-separated)
LLM_PROVIDER_ORDER=openai,ollama,anthropic

# Special third fallback using OpenAI mini model
LLM_PROVIDER_ORDER=openai,ollama,openai_mini
```

The system will automatically try providers in order if one fails:
1. Primary: OpenAI with configured model
2. Fallback 1: Ollama (local, no API costs)
3. Fallback 2: Anthropic or OpenAI mini model

## Model Selection

### Decision Matrix

| Use Case | Recommended Model | Reasoning |
|----------|------------------|-----------|
| **Production** | `gpt-4o-mini` | Best value, JSON support, 128k context |
| **High Quality** | `gpt-4-turbo` | Superior accuracy, complex documents |
| **Budget** | `gpt-3.5-turbo` | Low cost, adequate for simple documents |
| **Privacy** | `ollama/llama3.1:8b` | Local processing, no data leaves system |
| **Large Documents** | `gpt-4o` | 128k context window |
| **German Documents** | `gpt-4o-mini` | Excellent German language support |

### Switching Models

**Method 1: Environment Variable** (Recommended)
```bash
# Edit .env file
OPENAI_MODEL=gpt-4o-mini

# Restart application
python run.py
```

**Method 2: Runtime Override**
```python
# In your code (not recommended for production)
from src.paperless_ngx.infrastructure.config.settings import get_settings
settings = get_settings()
settings.openai_model = "gpt-4o-mini"
```

## Common Configuration Errors

### Error: "Model not found"

**Symptoms**:
```
litellm.exceptions.BadRequestError: OpenAI BadRequestError - Error code: 400 - {'error': {'message': 'The model `gpt-4o5-mini` does not exist'}}
```

**Causes & Solutions**:

1. **Typo in model name**
   ```bash
   # Wrong
   OPENAI_MODEL=gpt-4o5-mini     # Extra "5"
   
   # Correct
   OPENAI_MODEL=gpt-4o-mini
   ```

2. **Using fictional model**
   ```bash
   # Wrong
   OPENAI_MODEL=gpt-5-mini        # GPT-5 doesn't exist
   
   # Correct
   OPENAI_MODEL=gpt-4o-mini
   ```

3. **Missing hyphens**
   ```bash
   # Wrong
   OPENAI_MODEL=gpt4omini
   
   # Correct
   OPENAI_MODEL=gpt-4o-mini
   ```

### Error: "Invalid API key"

**Check**:
```bash
# Verify API key format
echo $OPENAI_API_KEY
# Should start with "sk-" for OpenAI

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Error: "Context length exceeded"

**Solution 1**: Use model with larger context
```bash
# Change from
OPENAI_MODEL=gpt-3.5-turbo      # 16k context

# To
OPENAI_MODEL=gpt-4o-mini         # 128k context
```

**Solution 2**: Adjust text truncation
```python
# In metadata_extraction.py
def _truncate_text_for_llm(self, text: str, max_chars: int = 40000):
    # Increase for larger models
    # max_chars = 100000  # For 128k context models
```

## JSON Response Format

### Automatic Detection

The system automatically detects JSON-capable models:

```python
# Models with JSON support (litellm_client.py:220-223)
json_supported_models = [
    "gpt-4-turbo-preview", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini",
    "gpt-3.5-turbo-1106", "gpt-3.5-turbo-0125", "gpt-3.5-turbo"
]
```

### Manual Override

```python
# Force JSON format (use with caution)
response = client.generate_metadata(
    text=document_text,
    response_format={"type": "json_object"}  # Force JSON
)
```

### Fallback Extraction

If JSON format fails, the system automatically falls back to text extraction:

```python
# In metadata_extraction.py
try:
    # Primary: JSON extraction
    metadata = json.loads(response)
except json.JSONDecodeError:
    # Fallback: Regex extraction
    metadata = self._extract_from_text(response)
```

## Troubleshooting

### Debug Logging

Enable debug logging to see LLM interactions:

```bash
# In .env
LOG_LEVEL=DEBUG
LOG_FORMAT=detailed

# Run with debug output
python run.py --debug --workflow 2
```

### Test LLM Connection

```python
# test_llm.py
from src.paperless_ngx.infrastructure.llm.litellm_client import get_llm_client

client = get_llm_client()
response = client.test_connection()
print(f"Provider: {response['provider']}")
print(f"Model: {response['model']}")
print(f"Status: {response['status']}")
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "Primary JSON extraction failed" | Switch to JSON-capable model (gpt-4o-mini) |
| "Rate limit exceeded" | Reduce batch size or add delays |
| "Timeout error" | Increase timeout: `OPENAI_TIMEOUT=60` |
| "SSL verification failed" | Check proxy settings or firewall |
| "Cost limit exceeded" | Monitor with cost tracker, switch to budget model |

## Performance Optimization

### Batch Processing

```bash
# Optimize batch sizes
BATCH_SIZE=10                    # Process 10 documents at once
RATE_LIMIT_DELAY=0.5            # Delay between batches
```

### Caching

```bash
# Enable response caching
ENABLE_LLM_CACHE=true
CACHE_TTL=3600                  # Cache for 1 hour
```

### Context Optimization

```python
# Reduce context size for faster processing
MAX_CONTEXT_CHARS=20000         # Reduce from 40000
INCLUDE_EXAMPLES=false          # Skip examples in prompts
```

## Cost Management

### Monitor Costs

```python
# Check current costs
from src.paperless_ngx.infrastructure.llm.litellm_client import get_llm_client

client = get_llm_client()
costs = client.cost_tracker.get_total_cost()
print(f"Total cost: ${costs:.4f}")
print(f"By provider: {client.cost_tracker.get_cost_by_provider()}")
```

### Cost Optimization Strategies

1. **Use appropriate models**:
   - Simple documents: `gpt-3.5-turbo` ($0.50/M tokens)
   - Standard documents: `gpt-4o-mini` ($0.15/M tokens)
   - Complex only: `gpt-4-turbo` ($10/M tokens)

2. **Implement caching**:
   - Cache similar document types
   - Reuse extracted patterns

3. **Local processing**:
   - Use Ollama for non-critical documents
   - Hybrid approach: Local first, API for failures

4. **Optimize prompts**:
   - Shorter, focused prompts
   - Remove unnecessary examples
   - Use system prompts efficiently

### Cost Limits

```bash
# Set daily/monthly limits
DAILY_COST_LIMIT=10.00          # Stop at $10/day
MONTHLY_COST_LIMIT=100.00       # Stop at $100/month

# Alert thresholds
COST_ALERT_THRESHOLD=5.00       # Alert at $5
```

## Migration Guide

### From GPT-5 (Fictional) to Real Models

If you have configuration using non-existent GPT-5 models:

```bash
# Step 1: Identify current configuration
grep "gpt-5" .env

# Step 2: Replace with real models
sed -i 's/gpt-5-nano/gpt-4o-mini/g' .env
sed -i 's/gpt-5-mini/gpt-4o-mini/g' .env
sed -i 's/gpt-4o5-mini/gpt-4o-mini/g' .env

# Step 3: Verify
grep "OPENAI_MODEL" .env
# Should show: OPENAI_MODEL=gpt-4o-mini

# Step 4: Test
python test_connections.py
```

### From Older Models

```bash
# Update deprecated models
sed -i 's/text-davinci-003/gpt-3.5-turbo/g' .env
sed -i 's/gpt-4-0613/gpt-4-turbo/g' .env
sed -i 's/gpt-3.5-turbo-0301/gpt-3.5-turbo/g' .env
```

## Best Practices

1. **Always use real model names** - Check OpenAI documentation
2. **Test configuration changes** - Run test_connections.py
3. **Monitor costs** - Set up alerts and limits
4. **Use appropriate models** - Don't use GPT-4 for simple tasks
5. **Enable fallbacks** - Configure multiple providers
6. **Cache when possible** - Reduce API calls
7. **Validate JSON support** - Not all models support JSON format
8. **Keep models updated** - Check for new releases quarterly

## References

- [OpenAI Models Documentation](https://platform.openai.com/docs/models)
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Ollama Model Library](https://ollama.ai/library)
- [MODEL_SWITCHING_GUIDE.md](MODEL_SWITCHING_GUIDE.md) - Quick switching guide
- [API_MODELS.md](API_MODELS.md) - Detailed model capabilities