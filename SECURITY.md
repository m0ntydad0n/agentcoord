# Security Guide

## Critical Security Configuration

### Redis Authentication (CRITICAL)

**Always use Redis authentication in production:**

```bash
# Set Redis URL with password
export REDIS_URL="redis://:your-password@localhost:6379"

# Or with TLS for production
export REDIS_URL="rediss://:your-password@your-redis-host:6380"
```

**Redis Configuration:**

```bash
# In redis.conf
requirepass your-strong-password-here

# Enable TLS (production)
tls-port 6380
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.crt
```

**Default (localhost only):**
- `redis://localhost:6379` - NO PASSWORD (dev only)
- Only use this for local development
- Never expose Redis port to network without auth

### API Key Protection

**LLM API Keys:**

```bash
# Set via environment variable
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# NEVER commit API keys to git
# NEVER log API keys in code
# Rotate keys regularly
```

**Best Practices:**

1. **Environment Variables Only**
   - Never hardcode API keys
   - Use `.env` files (add to .gitignore)
   - Load with `os.getenv("ANTHROPIC_API_KEY")`

2. **Key Rotation**
   - Rotate API keys every 90 days minimum
   - Rotate immediately if exposed
   - Use separate keys for dev/staging/prod

3. **Logging**
   - Never log full API keys
   - Never log API request/response bodies containing keys
   - Only log token counts, not actual tokens

## Security Checklist

### Production Deployment

- [ ] Redis password configured (`requirepass` in redis.conf)
- [ ] Redis TLS enabled (use `rediss://` URL)
- [ ] `REDIS_URL` environment variable set with auth
- [ ] API keys in environment variables only
- [ ] No API keys in logs or error messages
- [ ] Redis port (6379) not exposed to internet
- [ ] Worker processes run with minimal privileges
- [ ] Regular API key rotation schedule
- [ ] `.env` files in `.gitignore`
- [ ] All Redis connections use auth

### Development

- [ ] Local Redis only (127.0.0.1)
- [ ] No production keys in dev environment
- [ ] Separate dev/prod Redis instances
- [ ] Test keys with limited quotas

## Threat Model

### Attack Vectors

**CRIT-001: Unauth Redis Access**
- **Risk**: Anyone on network can access Redis
- **Impact**: Read/modify all tasks, steal data, inject malicious tasks
- **Mitigation**: Enable `requirepass`, use TLS, firewall rules

**CRIT-002: API Key Exposure**
- **Risk**: Keys in logs, environment dumps, or code
- **Impact**: Unauthorized API usage, cost overruns
- **Mitigation**: No logging, env vars only, rotation

**HIGH-001: Worker Code Injection**
- **Risk**: Malicious tasks execute arbitrary code
- **Impact**: System compromise via worker execution
- **Mitigation**: Task validation, sandboxing, code review

### Mitigations

1. **Network Isolation**
   - Redis behind firewall
   - Only localhost or VPN access
   - No public Redis exposure

2. **Authentication**
   - Redis password required
   - TLS for all connections
   - Separate credentials per environment

3. **Monitoring**
   - Failed auth attempts logged
   - Unusual task patterns detected
   - API usage monitoring

## Incident Response

### API Key Compromised

1. **Immediate**: Rotate key in provider dashboard
2. **Update**: Set new key in all environments
3. **Review**: Check API usage logs for abuse
4. **Audit**: Search codebase/logs for exposure

### Redis Breach

1. **Immediate**: Flush Redis database (`FLUSHALL`)
2. **Secure**: Enable auth, restart with new password
3. **Review**: Audit task/audit logs for malicious activity
4. **Update**: Rotate all passwords, update `REDIS_URL`

## References

- [Redis Security](https://redis.io/docs/management/security/)
- [Anthropic API Keys](https://docs.anthropic.com/claude/reference/api-keys)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
