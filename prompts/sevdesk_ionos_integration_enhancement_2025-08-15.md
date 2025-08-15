# **TECHNICAL IMPLEMENTATION PROMPT - NOT EXECUTED - DRAFT ONLY**

## **Problem Statement**

The Paperless NGX Integration System requires enhancements to improve IONOS mail compatibility, enhance tag management, implement stricter file filtering, simplify storage organization, and optimize filenames for Sevdesk import compatibility.

## **Current Architecture Analysis**

The system follows Clean Architecture with these key components:
- **Email Layer**: `EmailFetcherService` + `IMAPEmailClient` + `EmailSettings`  
- **Processing Layer**: `AttachmentProcessor` with metadata extraction and file organization
- **Tag Management**: Smart tag matching with 95% threshold, prevents false unifications
- **Storage**: Month-based organization with staging folders and JSON metadata files
- **LLM Integration**: Configurable provider order (OpenAI → Ollama → Anthropic)

## **Requirements Breakdown**

### **1. IONOS Mail Issue Fix**
**Current State**: IONOS attachments not downloading properly
**Required**: Debug and fix IMAP connection/attachment extraction for IONOS provider

### **2. Enhanced Tag Management**
**Current State**: 7 tags max, domain-based and type-based tags
**Required**: 
- Maximum 4 tags per document
- Automatic "Rechnung" and "Kassenbon" tags for invoices/receipts
- Include gross prices (Gesamtpreise Brutto) as tags from LLM analysis

### **3. Strict File Filtering**
**Current State**: Broad file type acceptance (`.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.txt`)
**Required**: Only PDF attachments and images of invoices/receipts/documents

### **4. Simplified Storage**
**Current State**: Month-based organization with staging folders and JSON metadata
**Required**: 
- Direct downloads folder (no staging)
- No month-based subfolders
- No JSON metadata files
- Single flat directory structure

### **5. Sevdesk-Compatible Filenames**
**Current State**: Custom email-based naming pattern
**Required**: Optimize for Sevdesk import (128 character limit)

## **Recommended Agent Chain Implementation**

### **Phase 1: Research & Diagnosis Agent**
**Agent Type**: `researcher`
**Duration**: 2-3 hours
**Tasks**:
1. **IONOS Investigation**:
   - Analyze IONOS IMAP connection logs
   - Compare Gmail vs IONOS email client behavior
   - Debug attachment extraction in `_extract_attachments()` method
   - Test IONOS-specific SSL/TLS requirements

2. **Sevdesk Research**:
   - Research Sevdesk filename requirements and best practices
   - Validate 128 character limit assumption
   - Analyze optimal filename patterns for import compatibility

**Deliverables**:
- IONOS connection diagnostic report
- Sevdesk filename requirements specification  
- Current vs required architecture gap analysis

### **Phase 2: Architecture Validation Agent**
**Agent Type**: `architect-cleaner`
**Duration**: 1-2 hours
**Tasks**:
1. **Clean Architecture Compliance**: Verify changes don't violate dependency rules
2. **Service Layer Impact**: Assess changes to `EmailFetcherService` and `AttachmentProcessor`  
3. **Configuration Changes**: Plan environment variable and settings updates
4. **Backward Compatibility**: Ensure existing functionality remains intact

**Deliverables**:
- Architecture impact assessment
- Service modification recommendations
- Configuration migration plan

### **Phase 3: Implementation Agent**
**Agent Type**: `python-generator`
**Duration**: 4-6 hours
**Primary Focus**: Implement core functionality changes

**3.1 IONOS Email Fix**:
- **File**: `/src/paperless_ngx/infrastructure/email/email_client.py`
- **Changes**: 
  - Debug `IMAPEmailClient.connect()` for IONOS provider
  - Fix SSL/TLS context for `imap.ionos.de`
  - Enhance `_extract_attachments()` error handling
  - Add IONOS-specific connection parameters

**3.2 File Filtering Enhancement**:
- **File**: `/src/paperless_ngx/infrastructure/email/email_config.py`
- **Changes**: 
  - Modify `allowed_extensions` to `[".pdf", ".png", ".jpg", ".jpeg", ".tiff"]`
  - Add content-based filtering logic for invoice/receipt detection
  - Implement image content validation

**3.3 Tag Management Enhancement**:
- **File**: `/src/paperless_ngx/application/use_cases/attachment_processor.py`
- **Changes**:
  - Modify `_generate_tags()` to limit to 4 tags maximum
  - Add automatic "Rechnung" detection for invoices
  - Add automatic "Kassenbon" detection for receipts
  - Integrate LLM-based gross price extraction as tags
  - Update tag priority system

**3.4 Storage Simplification**:
- **File**: `/src/paperless_ngx/application/use_cases/attachment_processor.py`
- **Changes**:
  - Modify `_get_target_directory()` to return flat structure
  - Remove month-based organization (`organize_by_date=False`)
  - Disable JSON metadata file generation in `_save_attachment_metadata()`
  - Update `EmailFetcherService` constructor parameters

**3.5 Filename Optimization**:
- **File**: `/src/paperless_ngx/domain/utilities/filename_utils.py`
- **Changes**:
  - Implement Sevdesk-optimized filename pattern
  - Enforce 128 character limit with intelligent truncation
  - Preserve essential metadata (date, sender, type)
  - Add filename validation function

### **Phase 4: Integration Testing Agent**
**Agent Type**: `test-engineer`
**Duration**: 2-3 hours
**Tasks**:
1. **Unit Tests**: Update existing tests for modified components
2. **Integration Tests**: Create IONOS email connection tests
3. **Workflow Tests**: Verify simplified 3-point workflow compatibility
4. **Edge Case Tests**: Test filename truncation, tag limiting, file filtering

**Test Files to Update**:
- `/tests/integration/test_email_accounts.py`
- `/tests/unit/test_attachment_processor.py`
- `/tests/integration/test_workflows.py`

## **Implementation Complexity Assessment**

### **Low Complexity (1-2 hours)**:
- File filtering enhancement
- Storage structure simplification  
- Tag count limiting

### **Medium Complexity (2-4 hours)**:
- Filename optimization for Sevdesk
- Tag enhancement with price extraction
- Configuration updates

### **High Complexity (4-6 hours)**:
- IONOS mail debugging and fix
- LLM integration for price tags
- Integration testing and validation

### **Total Estimated Duration**: 10-16 hours

## **Risk Assessment**

### **High Risk**:
- **IONOS Mail Fix**: May require provider-specific SSL configurations
- **LLM Price Extraction**: Accuracy depends on OCR quality and document variety

### **Medium Risk**:
- **Filename Truncation**: Risk of losing important metadata
- **Tag Limiting**: May reduce document discoverability

### **Low Risk**:
- **Storage Simplification**: Straightforward directory structure change
- **File Filtering**: Simple extension-based filtering

## **Alternative Approaches**

### **Option A: Incremental Implementation**
1. Start with storage simplification and file filtering (low risk)
2. Address IONOS issue in isolation
3. Enhance tags and filename optimization last

### **Option B: Provider-Specific Solution**
1. Create IONOS-specific email client subclass
2. Implement provider-aware configuration
3. Maintain separate code paths for different providers

### **Option C: Configuration-Driven Changes**
1. Make all changes configurable via environment variables
2. Maintain backward compatibility through feature flags
3. Allow gradual migration to new behavior

## **Configuration Changes Required**

```bash
# New environment variables
ENABLE_SIMPLIFIED_STORAGE=true
MAX_TAGS_PER_DOCUMENT=4
SEVDESK_FILENAME_OPTIMIZATION=true
AUTOMATIC_INVOICE_TAGS=true
IONOS_SSL_VERIFY_MODE=relaxed

# Modified settings
EMAIL_ALLOWED_EXTENSIONS=".pdf,.png,.jpg,.jpeg,.tiff"
ATTACHMENT_ORGANIZE_BY_DATE=false
ATTACHMENT_SAVE_METADATA=false
```

## **Success Criteria**

1. **IONOS Mail**: Successful attachment download from IONOS accounts
2. **Tag Management**: Maximum 4 tags with automatic invoice/receipt detection
3. **File Filtering**: Only relevant file types processed
4. **Storage**: Flat directory structure without subfolders
5. **Filenames**: Sevdesk-compatible naming under 128 characters
6. **Compatibility**: Existing workflows remain functional

## **Execution Command**

```bash
# Run comprehensive implementation
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 1
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 2  
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 3

# Test all email accounts including IONOS
python run.py --test-email-connections

# Validate enhanced processing
pytest tests/integration/test_email_accounts.py -v
```

## **Original Requirements (German)**

1. **Ionos Mail überprüfen** - Anhänge werden nicht heruntergeladen
2. **Rechnungen und Kassenbons** sollen auch als Tags gekennzeichnet werden. Maximal 4 Tags je Dokument. Gesamtpreise Brutto hier auch immer die Werte als Tags
3. **Berücksichtige nur PDF Anhänge und Bilder** von Rechnungen, Belegen etc. Keine anderen Dateien.
4. **Staging Ordner wird nicht benötigt**, heruntergeladene Dateien landen ja ohnehin im download ordner. Hier auch keine Einordnung in Monate notwendig. Alles in einen Ordner. Json Datein wird nicht benötigt.
5. **Dateibenennung anpassen** (maximale Zeichenlänge für den Import von Dateien in Sevedesk) - vermutlich 128 Zeichen. Hierfür aber Recherchieren

---

**READY FOR EXECUTION**: This prompt provides a comprehensive roadmap for implementing all required changes while maintaining system integrity and following Clean Architecture principles. The phased approach allows for iterative testing and reduces implementation risk.