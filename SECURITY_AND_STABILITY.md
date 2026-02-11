# Security and Stability Guide

## 🔒 Security Measures Implemented

### Environment Variables
- All sensitive configuration moved to `.env` files
- No hardcoded secrets in code
- Comprehensive `.env.example` template provided
- Environment variables validated on startup

### Security Headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (for HTTPS)
- `Content-Security-Policy` for script sources
- `Referrer-Policy: strict-origin-when-cross-origin`

### Session Security
- Secure session configuration
- HTTPOnly cookies (prevents XSS)
- SameSite cookie protection
- Configurable session lifetime
- Secure session key generation

### Input Validation
- File size limits (50MB max)
- Allowed file extensions validation
- Filename length limits
- Input sanitization

### Error Handling
- Comprehensive error logging
- No sensitive data in error responses
- Standardized error responses
- Global error handlers
- Spotify API error handling

## 🛡️ Security Configuration

### CORS Settings
```python
CORS_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:3001',
    'http://127.0.0.1:3001'
]
```

### Rate Limiting
- 60 requests per minute
- Burst limit: 10 requests
- Configurable per environment

### File Upload Security
- Maximum file size: 50MB
- Allowed extensions: txt, csv
- Secure filename handling
- Upload directory isolation

## 🔧 Error Handling

### API Error Responses
All API errors return standardized JSON:
```json
{
  "error": "Error message",
  "type": "error_type",
  "timestamp": "2025-10-18T23:17:31.580998",
  "status": "error"
}
```

### Error Types
- `bad_request` (400)
- `unauthorized` (401)
- `forbidden` (403)
- `not_found` (404)
- `file_too_large` (413)
- `rate_limit` (429)
- `internal_error` (500)
- `unexpected_error` (500)

### Spotify API Error Handling
- Authentication errors (401)
- Permission errors (403)
- Rate limit errors (429)
- Service unavailable (503)

## 📝 Environment Setup

### Required Environment Variables
```bash
# Spotify OAuth (Required)
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8004/callback

# Flask Security (Optional - auto-generated if not provided)
FLASK_SECRET_KEY=your_secret_key_here

# API Configuration (Optional)
REACT_APP_API_URL=http://localhost:8004
```

### Optional Environment Variables
```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Security Settings
SESSION_COOKIE_SECURE=False  # Set to True in production
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# File Upload
MAX_FILE_SIZE_MB=50
ALLOWED_FILE_EXTENSIONS=txt,csv
```

## 🚀 Production Deployment

### Security Checklist
- [ ] Set `SESSION_COOKIE_SECURE=True` for HTTPS
- [ ] Use strong `FLASK_SECRET_KEY`
- [ ] Configure proper CORS origins
- [ ] Enable Redis for session storage
- [ ] Set up proper logging
- [ ] Use HTTPS in production
- [ ] Configure rate limiting
- [ ] Set up monitoring

### Environment Variables for Production
```bash
# Production Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Strict

# Production URLs
SPOTIFY_REDIRECT_URI=https://yourdomain.com/callback
REACT_APP_API_URL=https://yourdomain.com

# Redis for Production
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_DB=0
```

## 🔍 Monitoring and Logging

### Security Events Logged
- Authentication failures
- Rate limit violations
- File upload errors
- API errors
- Unexpected exceptions

### Log Levels
- `DEBUG`: Development information
- `INFO`: Normal operations
- `WARNING`: Security events
- `ERROR`: Errors and exceptions

## 📚 Best Practices

### Development
1. Never commit `.env` files
2. Use `.env.example` as template
3. Test with different environments
4. Validate all inputs
5. Handle all errors gracefully

### Production
1. Use HTTPS everywhere
2. Set secure session cookies
3. Enable Redis for sessions
4. Monitor error logs
5. Regular security updates
6. Rate limiting enabled
7. Input validation strict

## 🛠️ Troubleshooting

### Common Issues
1. **CORS errors**: Check CORS_ORIGINS configuration
2. **Session issues**: Verify FLASK_SECRET_KEY
3. **File upload fails**: Check file size and extensions
4. **Spotify auth fails**: Verify client credentials
5. **Rate limiting**: Adjust RATE_LIMIT settings

### Debug Mode
Set `FLASK_DEBUG=True` for detailed error information (development only).

## 📞 Support

For security issues or questions:
1. Check logs for error details
2. Verify environment variables
3. Test with minimal configuration
4. Review security headers
5. Contact development team
