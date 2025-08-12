# Research: ID Mapping Strategy for Paperless NGX API Integration

**Date**: 2025-08-12
**Researcher**: researcher agent
**Status**: Complete
**Decision**: Enhanced caching with get-or-create pattern

## Executive Summary
The "Incorrect type. Expected pk value, received str" error occurs because Paperless NGX API requires numeric database IDs for foreign key relationships (correspondent, document_type, tags), not string names. The solution involves implementing a robust ID mapping strategy with caching to minimize API calls while ensuring data consistency.

## Requirements Analysis
- **Core Challenge**: Map string names to numeric IDs for Paperless NGX entities
- **Success Criteria**: Zero API errors, minimal API calls, automatic entity creation
- **Constraints**: Must work with existing Clean Architecture, maintain backward compatibility
- **Performance Targets**: <100ms for ID resolution, cache hit rate >90%

## Research Findings

### Industry Best Practices

#### Django REST Framework Requirements
- **Primary Key Serialization**: Django REST Framework's `PrimaryKeyRelatedField` expects numeric IDs
- **Error Source**: Passing string values to foreign key fields triggers validation errors
- **Standard Pattern**: Use `get_or_create` methods to resolve names to IDs

#### Paperless NGX API Specifics
Based on API documentation and codebase analysis:
1. All entity references (correspondent, document_type, tags) require numeric IDs
2. The API provides creation endpoints for missing entities
3. Case-insensitive matching is recommended to prevent duplicates
4. Pagination must be handled for large entity lists

### Library Analysis (Context7)

| Library | Version | Pros | Cons | Verdict |
|---------|---------|------|------|---------|
| Django REST Framework | 3.14+ | Native PrimaryKeyRelatedField support, comprehensive documentation | N/A - already integrated | Use existing |
| rapidfuzz | 3.0+ | High-performance fuzzy matching, already in use | N/A | Continue using |
| cachetools | 5.0+ | TTL cache, LRU cache options | Additional dependency | Consider for future |

### Pattern Research

#### 1. Simple Dictionary Cache (Current Implementation)
```python
self._tag_cache: Optional[List[Dict[str, Any]]] = None
```
- **Pros**: Simple, fast lookups, no external dependencies
- **Cons**: No TTL, memory grows unbounded, manual invalidation

#### 2. Get-or-Create Pattern (Current Implementation)
```python
def get_or_create_correspondent(self, name: str) -> int:
    # Search cache
    for item in self._correspondent_cache:
        if item['name'].lower() == name.lower():
            return item['id']
    # Create if not found
    new_item = self.api_client.create_correspondent(name)
    self._correspondent_cache.append(new_item)
    return new_item['id']
```
- **Pros**: Automatic entity creation, prevents missing entity errors
- **Cons**: Can create duplicates if cache is stale

#### 3. Two-Level Cache with TTL
```python
# Memory cache (fast, TTL)
self._memory_cache = TTLCache(maxsize=1000, ttl=300)
# Persistent cache (database/file)
self._persistent_cache = PersistentCache()
```
- **Pros**: Fast access, automatic expiration, survives restarts
- **Cons**: Additional complexity, requires cache synchronization

## Solution Proposals

### Recommended: Enhanced Get-or-Create with Smart Caching

**Implementation Strategy**:
```python
class EntityResolver:
    """Resolves entity names to IDs with intelligent caching."""
    
    def __init__(self, api_client):
        self.api_client = api_client
        self._caches = {
            'correspondent': {},
            'document_type': {},
            'tag': {}
        }
        self._cache_loaded = {
            'correspondent': False,
            'document_type': False,
            'tag': False
        }
    
    def resolve_correspondent(self, name: str) -> int:
        """Resolve correspondent name to ID."""
        return self._resolve_entity('correspondent', name)
    
    def _resolve_entity(self, entity_type: str, name: str) -> int:
        """Generic entity resolution with caching."""
        # Normalize name for matching
        normalized = name.lower().strip()
        
        # Check memory cache
        if normalized in self._caches[entity_type]:
            return self._caches[entity_type][normalized]
        
        # Load cache if not loaded
        if not self._cache_loaded[entity_type]:
            self._load_cache(entity_type)
            if normalized in self._caches[entity_type]:
                return self._caches[entity_type][normalized]
        
        # Create new entity
        entity_id = self._create_entity(entity_type, name)
        self._caches[entity_type][normalized] = entity_id
        return entity_id
```

**Key Features**:
1. Lazy loading of entity caches
2. Case-insensitive matching
3. Automatic entity creation
4. Memory-efficient caching
5. Thread-safe operations (with locks)

### Alternative 1: Batch Pre-loading
Pre-load all entities at initialization and refresh periodically.
- **Why not chosen**: High initial latency, memory overhead for unused entities

### Alternative 2: Direct API Calls
No caching, always query API for ID resolution.
- **Why not chosen**: High API load, significant performance impact

## Risk Analysis

### Technical Risks
- **Cache Staleness**: Entities created outside system won't be in cache
  - *Mitigation*: Implement cache refresh on 404 errors
- **Memory Growth**: Large numbers of entities could consume significant memory
  - *Mitigation*: Implement LRU eviction or size limits
- **Race Conditions**: Concurrent requests might create duplicates
  - *Mitigation*: Use database-level unique constraints

### Performance Risks
- **Initial Load Time**: First request for each entity type slower
  - *Mitigation*: Background pre-loading for common entities
- **API Rate Limiting**: Bulk operations might hit rate limits
  - *Mitigation*: Implement request batching and rate limiting

### Maintenance Risks
- **Cache Invalidation**: Complex to determine when to refresh
  - *Mitigation*: Time-based expiration with manual refresh option

## Implementation Roadmap

### Phase 1: Fix Immediate Error (1 hour)
1. Update `update_document_metadata` to use IDs instead of strings
2. Ensure all API calls pass numeric IDs
3. Add validation for ID types

### Phase 2: Optimize Caching (2 hours)
1. Implement `EntityResolver` class
2. Add lazy loading for entity caches
3. Implement cache refresh mechanism
4. Add metrics for cache hit rates

### Phase 3: Advanced Features (Optional, 2 hours)
1. Add fuzzy matching for similar names
2. Implement persistent cache layer
3. Add bulk entity creation
4. Implement cache pre-warming

## Code Changes Required

### 1. Fix in `paperless_api_service.py`
```python
def update_document_metadata(self, document_id: int, ...):
    update_data = {}
    
    # Ensure we're using IDs, not strings
    if correspondent:
        correspondent_id = self.get_or_create_correspondent(correspondent)
        update_data['correspondent'] = correspondent_id  # Must be int
    
    if document_type:
        document_type_id = self.get_or_create_document_type(document_type)
        update_data['document_type'] = document_type_id  # Must be int
    
    if tags:
        tag_ids = [self.get_or_create_tag(tag) for tag in tags]
        update_data['tags'] = tag_ids  # Must be list of ints
```

### 2. Add ID Validation
```python
def _validate_id_type(self, value: Any, field_name: str) -> int:
    """Ensure value is an integer ID."""
    if isinstance(value, str):
        raise ValidationError(
            f"{field_name} must be an integer ID, not a string. "
            f"Use get_or_create_{field_name}() to resolve names to IDs."
        )
    return int(value)
```

### 3. Enhance Cache Management
```python
def refresh_cache(self, entity_type: Optional[str] = None):
    """Refresh entity caches."""
    if entity_type:
        self._cache_loaded[entity_type] = False
        self._caches[entity_type].clear()
    else:
        for et in self._caches:
            self._cache_loaded[et] = False
            self._caches[et].clear()
```

## Recommended Agent Chain
1. **architect-cleaner** → Validate architecture alignment
2. **python-generator** → Implement EntityResolver class
3. **test-engineer** → Create comprehensive test suite
4. **code-reviewer** → Ensure thread safety and error handling
5. **doc-writer** → Update API documentation

## Key Decisions Log
- **Chose ID resolution over string passing** because Django REST Framework requires it
- **Decided to use in-memory caching** for performance with <100ms resolution time
- **Avoided external cache services** to maintain single-environment simplicity
- **Implemented get-or-create pattern** to handle missing entities gracefully
- **Used case-insensitive matching** to prevent duplicate entity creation

## Testing Strategy

### Unit Tests
```python
def test_resolve_correspondent_creates_if_missing():
    """Test that missing correspondents are created."""
    resolver = EntityResolver(mock_api_client)
    correspondent_id = resolver.resolve_correspondent("New Company")
    assert isinstance(correspondent_id, int)
    assert mock_api_client.create_correspondent.called_once()

def test_resolve_correspondent_uses_cache():
    """Test that subsequent calls use cache."""
    resolver = EntityResolver(mock_api_client)
    id1 = resolver.resolve_correspondent("Company")
    id2 = resolver.resolve_correspondent("company")  # Different case
    assert id1 == id2
    assert mock_api_client.create_correspondent.called_once()
```

### Integration Tests
```python
def test_update_document_with_string_names():
    """Test that string names are properly resolved to IDs."""
    service = PaperlessApiService()
    result = service.update_document_metadata(
        document_id=123,
        correspondent="ACME Corp",
        document_type="Rechnung",
        tags=["wichtig", "2024"]
    )
    assert result['correspondent'] == 45  # Numeric ID
    assert result['document_type'] == 12  # Numeric ID
    assert all(isinstance(tag_id, int) for tag_id in result['tags'])
```

## References
- [Django REST Framework Relations Documentation](https://www.django-rest-framework.org/api-guide/relations/)
- [Paperless NGX API Documentation](https://docs.paperless-ngx.com/api/)
- [Django REST Framework PrimaryKeyRelatedField](https://www.django-rest-framework.org/api-guide/relations/#primarykeyrelatedfield)
- Context7 docs: /encode/django-rest-framework - Field serialization and foreign key handling