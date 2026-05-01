# SendGrid OTP Provider Integration

## Overview
SendGrid has been integrated as an email provider for the OTP service. Configuration is stored in the PostgreSQL database `provider_config` table rather than environment variables, enabling runtime updates without redeployment.

## Setup Instructions

### 1. Apply the Migration
When deploying to an environment, run:
```bash
cd otp_service
alembic upgrade head
```

This will insert the SendGrid provider configuration record into `provider_config`.

### 2. Configure SendGrid Credentials
After migration, update the SendGrid provider config in the database:
```sql
UPDATE provider_config 
SET settings_json = jsonb_set(
  settings_json,
  '{api_key}',
  '"YOUR_SENDGRID_API_KEY"'
)
WHERE provider_id = 'sendgrid';

UPDATE provider_config
SET settings_json = jsonb_set(
  settings_json,
  '{from_email}',
  '"noreply@yourdomain.com"'
)
WHERE provider_id = 'sendgrid';
```

### 3. Verify Configuration
```sql
SELECT provider_id, settings_json, enabled FROM provider_config 
WHERE provider_id = 'sendgrid';
```

Expected output:
```
provider_id | settings_json | enabled
sendgrid    | {"adapter": "app.providers.adapters.SendGridEmailProvider", "api_key": "SG.xxx", "from_email": "noreply@yourdomain.com"} | true
```

## Provider Configuration

**Provider ID**: `sendgrid`  
**Tier**: `fallback`  
**Settings Schema**:
```json
{
  "adapter": "app.providers.adapters.SendGridEmailProvider",
  "api_key": "SG.your-api-key",
  "from_email": "noreply@example.com"
}
```

## How It Works

1. **OTP Service** queries the `provider_config` table for enabled providers
2. **Provider Registry** loads the SendGridEmailProvider adapter dynamically based on the adapter path in settings_json
3. **SendGridEmailProvider** sends emails via SendGrid API using the api_key and from_email from settings_json
4. **Error Handling**: Maps SendGrid API responses to OTP service error types (auth_error, retryable, non_retryable)

## Testing

All SendGrid provider tests pass:
```bash
pytest tests/test_sendgrid_provider.py -v
```

Tests cover:
- ✅ Successful email sending
- ✅ Auth errors
- ✅ Retryable errors (5xx)
- ✅ Non-retryable errors (4xx)
- ✅ Health checks

## Security

- API key is stored in database, NOT in `.env` or code
- Use your actual SendGrid API key in production (update via database SQL)
- The key exposed during setup has been noted - revoke it in SendGrid dashboard immediately
- Ensure database access is restricted to authorized personnel only

## Dependencies

Added to `requirements.txt`:
- `sendgrid==6.11.0`

## Files Modified/Created

- ✅ `otp_service/requirements.txt` - Added sendgrid dependency
- ✅ `otp_service/app/providers/adapters.py` - Added SendGridEmailProvider class
- ✅ `otp_service/alembic/versions/002_add_sendgrid_provider.py` - Migration file
- ✅ `otp_service/tests/test_sendgrid_provider.py` - Comprehensive test suite (7 tests)
