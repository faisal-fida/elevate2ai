# Debugging and Troubleshooting Guide

This document provides guidance on how to debug and troubleshoot issues in the WhatsApp chatbot application.

## Error IDs

When an error occurs, you'll receive an error ID like:
```
An error occurred while processing your message. Please try again or contact support with error ID: abcd_INIT_1234
```

This error ID can be used to look up detailed information about the error.

## Debugging Tools

### 1. Debug API Endpoints

The application includes debug API endpoints (admin-only access):

- `GET /api/debug/error/{error_id}` - Get detailed information about a specific error
- `GET /api/debug/errors` - List and analyze recent errors 
- `GET /api/debug/status` - Get system status and error rates

### 2. Diagnostic Script

Use the diagnostic script to analyze logs and debug errors:

```bash
# Analyze a specific error
python scripts/diagnose.py --error-id <error_id>

# Analyze recent logs for patterns
python scripts/diagnose.py --analyze-logs --days 3

# Check context history for a specific client
python scripts/diagnose.py --check-context <client_id>

# Get verbose output with more details
python scripts/diagnose.py --error-id <error_id> --verbose
```

### 3. Log Files

Log files are stored in the `logs` directory:

- `logs/YYYY-MM-DD.log` - Daily logs with all levels
- `logs/YYYY-MM-DD-errors.log` - Daily error logs
- `logs/debug/` - Detailed error snapshots and context dumps

## Common Issues and Solutions

### 1. "No handler found for state X"

**Problem:** The system doesn't know how to handle a specific state.

**Solution:** Check if the state is properly defined in the `WorkflowState` enum and mapped to a handler in the `_message_processor` method of `WorkflowManager`.

### 2. WhatsApp API Error 131030

**Problem:** WhatsApp API returns error 131030, indicating the recipient is not in the allowed list.

**Solution:** In test environments, you need to add phone numbers to your allowed recipient list in the Meta developer portal. Go to your WhatsApp Business API app settings and add the phone number.

### 3. Media Selection Issues

**Problem:** Users get stuck in media selection states or media uploads aren't working.

**Solution:** Check the context flow from `MEDIA_SOURCE_SELECTION` to `WAITING_FOR_MEDIA_UPLOAD` to ensure proper state transitions. Use the diagnostic script to check context history:

```bash
python scripts/diagnose.py --check-context <client_id> --verbose
```

### 4. Missing Template Error

**Problem:** Error message about template not found or template validation failures.

**Solution:** Ensure the template exists in the `TEMPLATE_CONFIG` dictionary and has all required keys properly defined. Check for typos in template IDs.

## Debugging Workflow

When investigating an issue:

1. Get the error ID from the logs or user report
2. Look up detailed error information:
   ```bash
   python scripts/diagnose.py --error-id <error_id> --verbose
   ```
3. Check if it's a common error pattern:
   ```bash
   python scripts/diagnose.py --analyze-logs
   ```
4. Check the client's context history:
   ```bash
   python scripts/diagnose.py --check-context <client_id>
   ```
5. Review the logs for the specific time period in `logs/YYYY-MM-DD.log`
6. Fix the issue in the relevant handler or workflow component

## Adding More Debug Information

To add more debug information to an error:

1. Use the debug utilities in your code:
   ```python
   from app.services.common.debug import dump_context, save_error_snapshot
   
   # Dump context for debugging
   dump_context(client_id, context, "custom_label")
   
   # Save detailed error information
   error_id = save_error_snapshot(
       error=exception,
       client_id=client_id,
       state="CUSTOM_STATE",
       context={"key": "value"}
   )
   ```

2. Add more detailed logging:
   ```python
   from app.services.common.logging import log_exception
   
   # Log exception with full traceback
   log_exception(logger, "Custom error message", exception)
   ``` 