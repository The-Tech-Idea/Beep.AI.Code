# Phase 3 Quick Reference Guide

**Date**: February 7, 2026  
**Phase**: Phase 3 (Complete)  
**Status**: Production-Ready

---

## File Locations

### Plugin System Core
```
app/models/researcher/plugins.py           - Plugin models (5)
app/services/plugin_base.py               - Base classes
app/services/plugin_manager.py            - Manager service
app/services/plugin_registry.py           - Registry service
tests/test_plugin_system.py               - Plugin tests (50+)
```

### Domain Plugins
```
app/plugins/medical.py                    - Medical plugin (600+ lines)
app/plugins/legal.py                      - Legal plugin (550+ lines)
app/plugins/engineering.py                - Engineering plugin (550+ lines)
```

### Extraction Integration
```
app/models/researcher/extraction_plugins.py    - Extraction models (3)
app/services/extraction_validation.py         - Validation service
app/routes/extraction.py                      - Extraction routes (updated)
tests/test_extraction_validation.py           - Validation tests (30+)
```

### Admin & Debug
```
app/routes/admin/plugin_management.py     - Admin routes (12 endpoints)
app/routes/admin/debug.py                 - Debug routes (9 endpoints)
tests/test_debug_routes.py                - Debug tests (30+)
```

---

## Plugin Development

### Creating a New Plugin

```python
from app.services.plugin_base import PluginBase, HookResult

class MyPlugin(PluginBase):
    """Custom plugin implementation."""
    
    def get_metadata(self):
        return PluginMetadata(
            name='my_plugin',
            version='1.0.0',
            author='Your Name',
            description='Plugin description',
            dependencies=[],
            schemas={},
            hooks_enabled=['validate_field', 'on_extraction']
        )
    
    async def validate_field(self, field_name: str, value: str, context: dict) -> HookResult:
        """Validate field value."""
        try:
            # Your validation logic
            is_valid = validate_value(value)
            
            return HookResult(
                success=True,
                is_valid=is_valid,
                error_message=None if is_valid else 'Validation failed',
                suggestions=['suggestion1'] if not is_valid else [],
                data={'validated': is_valid}
            )
        except Exception as e:
            return HookResult(
                success=False,
                error_message=str(e)
            )
    
    async def on_extraction(self, data: dict, context: dict) -> HookResult:
        """Process extraction."""
        # Your extraction logic
        return HookResult(
            success=True,
            data=processed_data
        )
```

### Registering a Plugin

```python
from app.services.plugin_manager import get_plugin_manager

# Get manager
manager = get_plugin_manager()

# Create plugin instance
my_plugin = MyPlugin()

# Register
manager.register_plugin('my_plugin', my_plugin)
```

---

## API Endpoints Reference

### Admin Plugin Management
```bash
# List all plugins
GET /api/admin/plugins

# Get plugin details
GET /api/admin/plugins/{name}

# Enable/disable
POST /api/admin/plugins/{name}/enable
POST /api/admin/plugins/{name}/disable

# Configuration
GET /api/admin/plugins/{name}/config
POST /api/admin/plugins/{name}/config

# Execution logs
GET /api/admin/plugins/{name}/logs?limit=100&offset=0

# Test plugin
POST /api/admin/plugins/{name}/test
{
  "hook_point": "validate_field",
  "test_data": {...}
}

# Statistics
GET /api/admin/plugins/stats/summary
GET /api/admin/plugins/{name}/stats

# Registry sync
POST /api/admin/plugins/registry/sync
```

### Extraction Validation
```bash
# Validate extraction result
POST /projects/{project_id}/extractions/{result_id}/validate
{
  "validate_all_fields": true,
  "field_names": ["field1", "field2"]
}

# List fields
GET /projects/{project_id}/schemas/{schema_id}/fields

# Create/update field
POST /projects/{project_id}/schemas/{schema_id}/fields
{
  "field_name": "diagnosis",
  "field_type": "string",
  "is_required": true,
  "plugin_validators": [
    {
      "plugin_name": "medical",
      "validator_method": "validate_field",
      "fail_on_error": false
    }
  ],
  "plugin_resolvers": [
    {
      "plugin_name": "medical",
      "resolver_method": "resolve_field"
    }
  ]
}

# Get field values
GET /projects/{project_id}/extractions/{result_id}/field-values

# List validators
GET /projects/{project_id}/schemas/{schema_id}/validators
```

### Debug & Analytics
```bash
# Execution tracing
GET /api/admin/debug/plugins/trace/latest?limit=50&plugin_name=medical
GET /api/admin/debug/plugins/trace/{execution_id}
GET /api/admin/debug/plugins/{name}/trace?days=7

# Performance analytics
GET /api/admin/debug/plugins/analytics/performance?days=7
GET /api/admin/debug/plugins/{name}/analytics?days=7
GET /api/admin/debug/plugins/analytics/comparison?metric=time&period=7d

# Validation analytics
GET /api/admin/debug/validation/history?days=7&limit=100
GET /api/admin/debug/validation/summary?days=7

# Health
GET /api/admin/debug/health
```

---

## Database Models

### Plugin Core Models
```python
class Plugin:
    id, name, version, author, description
    status (enum), plugin_type (enum)
    config_schema (JSON)
    stats (created_at, last_executed_at, execution_count, error_count)

class PluginConfiguration:
    id, plugin_id, project_id, tenant_id
    is_enabled, config_json (JSON)

class PluginExecutionLog:
    id, plugin_id, hook_point
    request_id, status
    execution_time_ms, error_message, traceback
    request_data, response_data (JSON)
    executed_at (datetime)

class PluginHookRegistration:
    id, plugin_id, hook_point
    handler_method, execution_order
    stats (execution_count, error_count, average_time_ms)

class PluginRegistry:
    id, registry_name, plugin_count
    registry_url, created_at
```

### Extraction Models
```python
class ExtractionField:
    id, schema_id, field_name, field_type
    is_required, description
    extraction_instructions
    plugin_validators_json (JSON)
    plugin_resolvers_json (JSON)
    extraction_count, validation_failure_count, validation_correction_count

class ExtractedFieldValue:
    id, result_id, field_id
    raw_value, extracted_value
    confidence_score
    validation_status (enum)
    validation_errors_json, corrections_applied_json (JSON)
    suggested_values_json, plugin_executions_json (JSON)

class ExtractionValidationResult:
    id, field_value_id, plugin_id
    is_valid, validation_message
    correction_applied
    suggestions_json (JSON)
    execution_time_ms, executed_at
```

---

## Domain Plugin APIs

### Medical Plugin
```python
# Available methods
medical_plugin.check_drug_interactions(drug1, drug2)
medical_plugin.validate_icd10(code)
medical_plugin.lookup_cpt(code)
medical_plugin.expand_abbreviation(abbr)
medical_plugin.check_hipaa_compliance(text)
medical_plugin.validate_field(field_name, value, context)

# Example
result = await medical_plugin.validate_field('diagnosis', 'E1', {})
# Returns: HookResult with suggestions=['E10', 'E11']
```

### Legal Plugin
```python
# Available methods
legal_plugin.extract_clauses(text)
legal_plugin.check_compliance(text, framework)  # framework: GDPR|CCPA
legal_plugin.assess_risk(text)
legal_plugin.analyze_legal_terms(text)
legal_plugin.validate_field(field_name, value, context)

# Example
result = await legal_plugin.validate_field('clause_type', 'limitation', {})
# Returns: HookResult with validation outcome
```

### Engineering Plugin
```python
# Available methods
engineering_plugin.check_standards_compliance(text)
engineering_plugin.lookup_material(name)
engineering_plugin.lookup_part(name)
engineering_plugin.check_safety_concerns(text)
engineering_plugin.validate_units(value, unit)
engineering_plugin.validate_field(field_name, value, context)

# Example
result = await engineering_plugin.validate_field('units', 'mm', {})
# Returns: HookResult with validation outcome
```

---

## Hook Points Reference

### Available Hooks
```
on_plugin_load           Plugin loaded and initialized
on_plugin_unload         Plugin being unloaded
on_document_upload       Document uploaded to project
on_extraction           LLM extraction completed
on_code_creation        Code generated
on_export               Exporting project
on_search               Searching within project
on_import              Importing data
validate_field         Validating extracted field value
```

### Hook Signature
```python
async def hook_name(self, data: dict, context: HookContext) -> HookResult:
    """Execute hook."""
    pass
```

### Hook Context
```python
class HookContext:
    hook_point: str              # Which hook triggered
    project_id: int              # Project ID
    tenant_id: int               # Tenant ID
    user_id: int                 # User ID
    request_id: str              # Unique request ID
    timestamp: datetime           # When hook executed
    data: dict                    # Input data
    metadata: dict                # Additional metadata
```

### Hook Result
```python
class HookResult:
    success: bool                 # Was execution successful?
    plugin_name: str              # Plugin name
    hook_point: str               # Which hook
    execution_time_ms: float      # Execution duration
    status: str                   # Status message
    error: str                    # Error message if failed
    traceback: str                # Traceback if failed
    data: dict                    # Output data
    suggestions: list[str]        # Suggestions for corrections
```

---

## Configuration Examples

### Medical Field with ICD-10 Validation
```json
{
  "field_name": "diagnosis",
  "field_type": "string",
  "is_required": true,
  "extraction_instructions": "Extract ICD-10 diagnosis code",
  "plugin_validators": [
    {
      "plugin_name": "medical",
      "validator_method": "validate_field",
      "fail_on_error": false,
      "suggest_corrections": true
    }
  ]
}
```

### Legal Field with GDPR Compliance Check
```json
{
  "field_name": "clause",
  "field_type": "string",
  "extraction_instructions": "Extract contract clause",
  "plugin_validators": [
    {
      "plugin_name": "legal",
      "validator_method": "validate_field",
      "fail_on_error": false
    }
  ],
  "plugin_resolvers": [
    {
      "plugin_name": "legal",
      "resolver_method": "resolve_field"
    }
  ]
}
```

### Engineering Field with Standards Check
```json
{
  "field_name": "material",
  "field_type": "string",
  "extraction_instructions": "Extract material specification",
  "plugin_validators": [
    {
      "plugin_name": "engineering",
      "validator_method": "validate_field",
      "fail_on_error": false
    }
  ]
}
```

---

## Common Tasks

### Enable a Plugin
```bash
curl -X POST http://localhost:5000/api/admin/plugins/medical/enable \
  -H "Authorization: Bearer token"
```

### Validate Extraction with Plugins
```bash
curl -X POST http://localhost:5000/projects/1/extractions/123/validate \
  -H "Content-Type: application/json" \
  -d '{"validate_all_fields": true}'
```

### Get Plugin Performance
```bash
curl http://localhost:5000/api/admin/debug/plugins/medical/analytics?days=7 \
  -H "Authorization: Bearer token"
```

### Check System Health
```bash
curl http://localhost:5000/api/admin/debug/health \
  -H "Authorization: Bearer token"
```

### Get Field Validation Results
```bash
curl http://localhost:5000/projects/1/extractions/123/field-values \
  -H "Authorization: Bearer token"
```

---

## Error Handling

### Plugin Not Loaded
```
Status: 404
{
  "error": "Plugin medical not loaded"
}
```

### Validation Failed
```
Status: 200
{
  "is_valid": false,
  "validation_status": "invalid",
  "errors": ["ICD-10 code not valid"],
  "suggestions": ["E10", "E11"]
}
```

### Plugin Timeout
```
{
  "success": false,
  "error": "Validator timeout (>30s)"
}
```

### Database Error
```
Status: 500
{
  "error": "Database error occurred"
}
```

---

## Testing

### Running Plugin Tests
```bash
cd Beep.AI.Researcher
python -m pytest tests/test_plugin_system.py -v
```

### Running Extraction Validation Tests
```bash
python -m pytest tests/test_extraction_validation.py -v
```

### Running Debug Routes Tests
```bash
python -m pytest tests/test_debug_routes.py -v
```

### Running All Phase 3 Tests
```bash
python -m pytest tests/test_plugin_system.py \
                 tests/test_extraction_validation.py \
                 tests/test_debug_routes.py -v
```

---

## Performance Tips

1. **Use Pagination**: Always paginate execution logs and validation history
   ```
   /trace?limit=50&offset=0
   ```

2. **Filter by Plugin**: Use plugin_name filter to reduce query scope
   ```
   /trace/latest?plugin_name=medical
   ```

3. **Time Period Filtering**: Limit to recent data
   ```
   /analytics/performance?days=7
   ```

4. **Batch Validation**: For multiple extractions, use batch endpoint (Phase 3.7)

5. **Caching**: Admin should cache plugin list periodically

6. **Enable Only Used Plugins**: Disable unused plugins to reduce overhead

---

## Security

### Authorization
All admin and debug endpoints require `@admin_required` decorator

### Input Validation
- Plugin names validated against loaded plugins
- Field names validated against schema
- Configuration validated against JSON schema
- Execution logs never expose sensitive data

### Error Messages
- Production errors are generic (no stack traces to clients)
- Full tracebacks only logged server-side
- No SQL queries exposed in error messages

---

## Monitoring

### Key Metrics to Monitor
1. Average execution time per plugin
2. Error rate per plugin
3. Timeout occurrences
4. Validation success rate
5. Plugin availability

### Health Thresholds
- Healthy: <5 errors/hour, 0 timeouts
- Degraded: 5-20 errors/hour, 2-10 timeouts
- Unhealthy: >20 errors/hour, >10 timeouts

### Recommended Alerts
- Plugin execution error rate >10%
- Average execution time >500ms
- Timeout occurrences >2 per hour
- Plugin disabled unexpectedly

---

## Version Information

**Phase 3 Version**: 3.0 (Complete)
- Last Updated: February 7, 2026
- Status: Production-Ready
- Test Coverage: 169+ tests (100% passing)
- Documentation: Complete

---

**For more details**, see:
- `PHASE_3_COMPLETE_FINAL_REPORT.md` - Comprehensive overview
- `PHASE_3_6_EXTRACTION_INTEGRATION.md` - Schema integration details
- `PHASE_3_7_DEBUG_ROUTES.md` - Debug API details
- `PHASE_3_7_IMPLEMENTATION_PLAN.md` - Technical details
