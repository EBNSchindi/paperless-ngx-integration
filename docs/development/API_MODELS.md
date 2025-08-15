# API Models Reference

## OpenAI Models (January 2025)

### Production Models

#### gpt-4o-mini ⭐ RECOMMENDED
```json
{
  "model": "gpt-4o-mini",
  "context_window": 128000,
  "max_output": 16384,
  "json_format": true,
  "cost_per_million": {
    "input": 0.15,
    "output": 0.60
  },
  "features": [
    "JSON response format",
    "Function calling",
    "Vision capabilities",
    "128k context window",
    "Fast response time"
  ],
  "best_for": [
    "Document processing",
    "Metadata extraction",
    "Production use",
    "Cost-sensitive applications"
  ]
}
```

#### gpt-4o
```json
{
  "model": "gpt-4o",
  "context_window": 128000,
  "max_output": 4096,
  "json_format": true,
  "cost_per_million": {
    "input": 5.00,
    "output": 15.00
  },
  "features": [
    "Latest GPT-4 model",
    "JSON response format",
    "Function calling",
    "Vision capabilities",
    "Highest quality"
  ],
  "best_for": [
    "Complex documents",
    "Multi-language processing",
    "Maximum accuracy needed"
  ]
}
```

#### gpt-4-turbo
```json
{
  "model": "gpt-4-turbo",
  "context_window": 128000,
  "max_output": 4096,
  "json_format": true,
  "cost_per_million": {
    "input": 10.00,
    "output": 30.00
  },
  "features": [
    "JSON response format",
    "Function calling",
    "Vision capabilities",
    "128k context window"
  ],
  "best_for": [
    "High-quality processing",
    "Complex reasoning",
    "Professional documents"
  ]
}
```

#### gpt-3.5-turbo
```json
{
  "model": "gpt-3.5-turbo",
  "context_window": 16385,
  "max_output": 4096,
  "json_format": true,
  "cost_per_million": {
    "input": 0.50,
    "output": 1.50
  },
  "features": [
    "JSON response format",
    "Function calling",
    "Fast response",
    "Budget-friendly"
  ],
  "best_for": [
    "Simple documents",
    "Budget operations",
    "High-volume processing",
    "Quick extractions"
  ]
}
```

### Non-Existent Models ❌

**These models DO NOT exist and will cause errors:**

```json
{
  "fictional_models": [
    {
      "name": "gpt-5-nano",
      "status": "DOES NOT EXIST",
      "error": "Model not found",
      "alternative": "gpt-4o-mini"
    },
    {
      "name": "gpt-5-mini",
      "status": "DOES NOT EXIST",
      "error": "Model not found",
      "alternative": "gpt-4o-mini"
    },
    {
      "name": "gpt-5",
      "status": "NOT RELEASED",
      "error": "Model not found",
      "alternative": "gpt-4o"
    },
    {
      "name": "gpt-4o5-mini",
      "status": "TYPO",
      "error": "Model not found",
      "correct": "gpt-4o-mini"
    }
  ]
}
```

## JSON Format Support

### Models with Native JSON Support

```python
# These models support response_format={"type": "json_object"}
JSON_CAPABLE_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-4-turbo-preview",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0125"
]
```

### Implementation in Code

```python
# litellm_client.py implementation
def _get_model_config(self, model_name: str) -> dict:
    """Get configuration for a specific model."""
    
    # Check if model supports JSON format
    json_supported = any(
        m in model_name for m in JSON_CAPABLE_MODELS
    )
    
    config = {
        "model": model_name,
        "temperature": self.settings.openai_temperature,
        "max_tokens": self.settings.openai_max_tokens,
    }
    
    if json_supported:
        config["response_format"] = {"type": "json_object"}
        logger.info(f"JSON format enabled for {model_name}")
    else:
        logger.warning(f"Model {model_name} does not support JSON format")
    
    return config
```

## Ollama Models (Local)

### Available Models

```yaml
llama3.1:8b:
  parameters: 8_billion
  context_window: 8192
  json_format: false  # Use prompt engineering
  requirements:
    ram: 16GB
    vram: 8GB (optional)
  best_for:
    - Privacy-sensitive documents
    - Local processing
    - No API costs

mistral:7b:
  parameters: 7_billion
  context_window: 8192
  json_format: false
  requirements:
    ram: 8GB
    vram: 6GB (optional)
  best_for:
    - Fast local processing
    - Simple extractions

llama3.1:70b:
  parameters: 70_billion
  context_window: 8192
  json_format: false
  requirements:
    ram: 40GB+
    vram: 48GB (recommended)
  best_for:
    - High-quality local processing
    - Complex documents
```

## Model Selection Matrix

| Use Case | Recommended | Fallback | Budget |
|----------|------------|----------|---------|
| **Invoice Processing** | gpt-4o-mini | gpt-3.5-turbo | ollama/mistral |
| **Legal Documents** | gpt-4-turbo | gpt-4o | gpt-4o-mini |
| **Simple Receipts** | gpt-3.5-turbo | gpt-4o-mini | ollama/llama3.1:8b |
| **Multi-language** | gpt-4o | gpt-4-turbo | gpt-4o-mini |
| **High Volume** | gpt-4o-mini | gpt-3.5-turbo | ollama/mistral |
| **Privacy Critical** | ollama/llama3.1:70b | ollama/llama3.1:8b | - |

## API Response Examples

### Successful Response (JSON Format)

```json
{
  "correspondent": "Amazon Services LLC",
  "document_type": "Invoice",
  "title": "Order #123-4567890",
  "tags": ["invoice", "amazon", "online-shopping", "2025"],
  "description": "Amazon order for office supplies",
  "date": "2025-01-15"
}
```

### Fallback Text Response (Non-JSON Models)

```text
Correspondent: Amazon Services LLC
Document Type: Invoice
Title: Order #123-4567890
Tags: invoice, amazon, online-shopping, 2025
Description: Amazon order for office supplies
Date: 2025-01-15
```

### Error Response

```json
{
  "error": {
    "message": "The model `gpt-5-mini` does not exist",
    "type": "invalid_request_error",
    "code": "model_not_found"
  }
}
```

## Model Capabilities Comparison

| Feature | gpt-4o-mini | gpt-4o | gpt-4-turbo | gpt-3.5-turbo | ollama |
|---------|------------|--------|-------------|---------------|---------|
| **JSON Format** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Function Calling** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Vision** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **128k Context** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **German Support** | Excellent | Excellent | Excellent | Good | Varies |
| **Speed** | Fast | Medium | Medium | Very Fast | Depends |
| **Cost** | Low | Medium | High | Very Low | Free |
| **Privacy** | API | API | API | API | Local |

## Configuration Examples

### Production Setup
```bash
# .env
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.1
OPENAI_MAX_TOKENS=2000
LLM_PROVIDER_ORDER=openai,ollama,openai_mini
```

### High Quality Setup
```bash
# .env
OPENAI_MODEL=gpt-4-turbo
OPENAI_TEMPERATURE=0.2
OPENAI_MAX_TOKENS=3000
LLM_PROVIDER_ORDER=openai
```

### Budget Setup
```bash
# .env
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.1
OPENAI_MAX_TOKENS=1500
LLM_PROVIDER_ORDER=ollama,openai
```

### Privacy-First Setup
```bash
# .env
OLLAMA_ENABLED=true
OLLAMA_MODEL=llama3.1:70b
OPENAI_ENABLED=false
LLM_PROVIDER_ORDER=ollama
```

## Model Migration Path

### From Fictional to Real Models

```bash
# Migration mapping
gpt-5-nano     → gpt-4o-mini
gpt-5-mini     → gpt-4o-mini
gpt-5          → gpt-4o
gpt-4o5-mini   → gpt-4o-mini (typo fix)
```

### From Deprecated to Current

```bash
# OpenAI deprecated models
text-davinci-003    → gpt-3.5-turbo
code-davinci-002    → gpt-4o-mini
gpt-4-0613          → gpt-4-turbo
gpt-3.5-turbo-0301  → gpt-3.5-turbo
```

## Testing Model Configuration

```python
# test_model_config.py
from src.paperless_ngx.infrastructure.llm.litellm_client import get_llm_client
from src.paperless_ngx.infrastructure.config.settings import get_settings

def test_model_configuration():
    """Test current model configuration."""
    settings = get_settings()
    client = get_llm_client()
    
    print(f"Current Model: {settings.openai_model}")
    print(f"JSON Support: {settings.openai_model in JSON_CAPABLE_MODELS}")
    print(f"Provider Order: {settings.llm_provider_order}")
    
    # Test connection
    try:
        response = client.test_connection()
        print(f"✅ Model active: {response['model']}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_model_configuration()
```

## References

- [OpenAI Models](https://platform.openai.com/docs/models)
- [OpenAI Pricing](https://openai.com/pricing)
- [Ollama Library](https://ollama.ai/library)
- [LiteLLM Models](https://docs.litellm.ai/docs/providers)
- [JSON Response Format](https://platform.openai.com/docs/guides/text-generation/json-mode)