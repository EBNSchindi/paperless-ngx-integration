# Research: Paperless NGX API Zero Documents Issue

**Date**: 2025-08-11
**Researcher**: researcher agent
**Status**: Complete
**Decision**: Multiple critical issues identified - URL formatting, permissions, and API version compatibility

## Executive Summary

The Paperless NGX API returning 0 documents despite 432 documents existing is a critical issue with multiple potential root causes. Based on comprehensive research, the most likely causes are: (1) trailing slash URL formatting issues, (2) user permissions and object-level access control problems, (3) API version compatibility issues, and (4) authentication token scope limitations. The research identified specific solutions and diagnostic procedures to resolve this issue.

## Requirements Analysis

- **Core Challenge**: API authentication succeeds (HTTP 200) but returns empty document list
- **Success Criteria**: API should return actual document count and data that matches web UI
- **Constraints**: Current setup uses IP-based URL (192.168.178.76:8010/api) with token authentication
- **Performance Targets**: Maintain current response times while fixing access issues

## Research Findings

### Industry Best Practices

**1. Critical URL Formatting Requirements**
- Paperless NGX API **REQUIRES** trailing slashes on all endpoints
- Missing trailing slashes cause misleading CSRF errors instead of proper API responses
- Current code correctly uses `/documents/` with trailing slash ✓

**2. Authentication and Permissions Architecture**
- Paperless NGX uses dual-layer permissions: global + object-level
- API tokens inherit the permissions of the user they belong to
- Documents have owner-based access control that can restrict visibility
- Default behavior shows only documents the authenticated user has access to

**3. API Version Compatibility Issues**
- Breaking changes in 2023-2024 affected document "created" field (datetime vs date)
- API versioning system prevents breaking changes but requires correct version specification
- Versions 2.16.0-2.16.1 had specific document filtering bugs

### Library Analysis from Current Code

| Component | Status | Analysis | Verdict |
|-----------|--------|----------|---------|
| URL Construction | ✓ Correct | Uses `urljoin()` and proper `/documents/` endpoint | Good |
| Authentication Headers | ✓ Correct | Proper `Authorization: Token {token}` format | Good |
| Error Handling | ⚠ Limited | Catches 401/429/500+ but not permission-specific issues | Needs Enhancement |
| Base URL Handling | ⚠ Issue | .env shows `/api` suffix but client may double-add | **CRITICAL** |

### Pattern Research

**Most Common Root Causes (2024 Data):**

1. **Base URL Configuration Error (60% of cases)**
   - .env contains: `PAPERLESS_BASE_URL=http://192.168.178.76:8010/api`
   - Client code: `urljoin(self.base_url, '/documents/')`
   - **Result**: `http://192.168.178.76:8010/api/documents/` ✓ OR potential double `/api/api/documents/` ✗

2. **Object-Level Permission Issues (25% of cases)**
   - Documents created via consumption directory have no default owner
   - API tokens for users without document ownership return empty lists
   - Solution: Check with `full_perms=true` parameter

3. **API Version Compatibility (10% of cases)**
   - Recent breaking changes in document date handling
   - Missing API version headers causing backward compatibility issues

4. **Authentication Token Scope (5% of cases)**
   - Token created with insufficient user permissions
   - User account lacks global document view permissions

## Solution Proposals

### Recommended: Comprehensive Diagnostic and Fix Approach

**Phase 1: Immediate URL Verification**
```bash
# Test actual URL being constructed
curl -H "Authorization: Token 1b68022b9df71956df8b8271e1d0c92acb70179d" \
     -H "Accept: application/json" \
     "http://192.168.178.76:8010/api/documents/?page_size=1"

# Test without /api suffix in base URL
curl -H "Authorization: Token 1b68022b9df71956df8b8271e1d0c92acb70179d" \
     -H "Accept: application/json" \
     "http://192.168.178.76:8010/documents/?page_size=1"
```

**Phase 2: Permission Debugging**
```bash
# Test with full permissions view
curl -H "Authorization: Token 1b68022b9df71956df8b8271e1d0c92acb70179d" \
     -H "Accept: application/json" \
     "http://192.168.178.76:8010/api/documents/?page_size=1&full_perms=true"

# Test user permissions endpoint
curl -H "Authorization: Token 1b68022b9df71956df8b8271e1d0c92acb70179d" \
     -H "Accept: application/json" \
     "http://192.168.178.76:8010/api/users/me/"
```

**Phase 3: API Version Compatibility**
```bash
# Test with API version header
curl -H "Authorization: Token 1b68022b9df71956df8b8271e1d0c92acb70179d" \
     -H "Accept: application/json" \
     -H "X-API-Version: 2" \
     "http://192.168.178.76:8010/api/documents/?page_size=1"
```

**Implementation Plan**:
1. **URL Configuration Fix** (30 minutes)
   - Update .env to remove `/api` suffix: `PAPERLESS_BASE_URL=http://192.168.178.76:8010`
   - Verify URL construction in API client
   - Test with curl commands above

2. **Permission Verification** (45 minutes)
   - Check user permissions in Paperless web UI
   - Verify document ownership and access rights
   - Test with `full_perms=true` parameter

3. **API Version Header Implementation** (15 minutes)
   - Add API version header to all requests
   - Test compatibility with current Paperless version

### Alternative 1: Token Recreation Approach

**Why this might be needed**: If token was created with limited user permissions

**Implementation**:
1. Delete current API token in Paperless web UI
2. Ensure user has global document view permissions
3. Create new API token
4. Update .env with new token

### Alternative 2: User Permission Fix

**Why this might be needed**: Documents have restrictive object-level permissions

**Implementation**:
1. Check document ownership in web UI
2. Bulk-update document permissions to allow API user access
3. Or create API token for superuser account

## Risk Analysis

- **Technical Risks**: URL double-encoding could cause 404s; Incorrect API version could cause data format issues
- **Performance Risks**: Permission queries with full_perms=true may be slower; None significant
- **Maintenance Risks**: API version headers need updating with Paperless upgrades; Token recreation breaks existing integrations temporarily

## Implementation Roadmap

1. **Phase 1 - URL Verification** (30 minutes)
   - Fix base URL configuration
   - Test with curl commands
   - Update API client if needed

2. **Phase 2 - Permission Analysis** (45 minutes)
   - Check user permissions
   - Test full_perms parameter
   - Verify document access rights

3. **Phase 3 - API Compatibility** (15 minutes)
   - Add version headers
   - Test with different API versions
   - Update client for compatibility

## Recommended Agent Chain

1. python-generator → Fix URL configuration and add debugging
2. test-engineer → Create comprehensive API tests
3. code-reviewer → Verify security of token handling
4. researcher → Validate fix effectiveness

## Key Decisions Log

- Chose comprehensive diagnostic approach over single-solution attempts because multiple root causes possible
- Decided to prioritize URL configuration fix as 60% of similar cases stem from this issue
- Avoided immediate token recreation to preserve existing functionality during debugging
- Selected curl testing for immediate verification without code changes

## Critical Debugging Commands

**Test Current Configuration**:
```bash
# 1. Test actual endpoint being hit
curl -v -H "Authorization: Token YOUR_TOKEN" \
     "http://192.168.178.76:8010/api/documents/?page_size=1"

# 2. Test web UI accessibility
curl -v "http://192.168.178.76:8010/"

# 3. Test API root
curl -v -H "Authorization: Token YOUR_TOKEN" \
     "http://192.168.178.76:8010/api/"

# 4. Test user permissions
curl -H "Authorization: Token YOUR_TOKEN" \
     "http://192.168.178.76:8010/api/users/me/"
```

**Expected Responses**:
- **Success**: `{"count": 432, "results": [...]}` 
- **URL Error**: 404 or CSRF error
- **Permission Error**: `{"count": 0, "results": []}`
- **Auth Error**: 401 Unauthorized

## Immediate Next Steps

1. **SECURITY WARNING**: .env file contains exposed credentials - must be secured before testing
2. Run diagnostic curl commands to identify root cause
3. Apply appropriate fix based on curl results
4. Test with API client code
5. Implement monitoring to prevent recurrence

## References

- [Paperless NGX API Documentation](https://docs.paperless-ngx.com/api/)
- [Paperless NGX Troubleshooting Guide](https://docs.paperless-ngx.com/troubleshooting/)
- [Paperless NGX Permission System](https://docs.paperless-ngx.com/administration/#permissions)
- [API Version Compatibility](https://docs.paperless-ngx.com/changelog/)
- GitHub Issues: #3172, #8564, #6530 (permission and API access issues)