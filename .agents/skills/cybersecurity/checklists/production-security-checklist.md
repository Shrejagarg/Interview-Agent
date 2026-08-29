# Production Security Checklist

Verify before deploying to production.

## Transport & Network
- [ ] TLS/HTTPS enforced on all external-facing endpoints
- [ ] Reverse proxy or API gateway in front of backend services
- [ ] Internal services not exposed publicly (databases, queues, admin tools)
- [ ] Outbound network restricted for services that don't need internet access
- [ ] Docker networks segmented (frontend/backend/database isolation)

## Containers
- [ ] Base images are minimal and version-pinned (never `:latest`)
- [ ] All containers run as non-root users
- [ ] Filesystems are read-only where possible
- [ ] All capabilities dropped (`cap_drop: ALL`), only required ones added back
- [ ] No-new-privileges enabled on all containers
- [ ] CPU and memory limits set on all containers
- [ ] Health checks configured for all services
- [ ] Multi-stage builds used (no build tools in runtime images)
- [ ] Docker socket NOT mounted in any application container
- [ ] No sensitive host paths mounted

## Secrets
- [ ] All secrets injected at runtime (env vars or secret manager)
- [ ] No secrets in source control, Docker images, or config files
- [ ] Secrets rotated after any personnel change or incident
- [ ] Secrets excluded from logs, traces, and error messages

## Authentication & Authorization
- [ ] Auth rules centralized and consistent across all routes
- [ ] Least privilege applied to all users, service accounts, and machine identities
- [ ] Short-lived tokens with secure refresh rotation
- [ ] Passwords stored with modern hashing (bcrypt/argon2)
- [ ] Session invalidation works on logout, reset, and role changes

## Dependencies & Supply Chain
- [ ] All dependency versions pinned with lockfiles
- [ ] Dependencies scanned for known vulnerabilities (pip-audit, npm audit, trivy)
- [ ] Unused dependencies removed
- [ ] Third-party packages and Docker images verified before adoption

## Observability & Incident Readiness
- [ ] Structured logging with request IDs across all services
- [ ] Security events logged: auth failures, permission denials, rate limits, admin actions
- [ ] Alerting configured for error spikes, access denials, container restarts
- [ ] Incident response plan: revocation, containment, audit trail access
- [ ] No PII, secrets, or tokens in log output

## AI & Agent Systems (if applicable)
- [ ] All model inputs treated as untrusted
- [ ] Tool allowlists enforced — minimum tools exposed
- [ ] Tool arguments validated server-side before execution
- [ ] Authorization checks outside the model for sensitive actions
- [ ] Human approval required for high-risk agent actions
- [ ] Every tool call logged with identity, arguments, policy decision, result
- [ ] Prompt injection tested with hostile examples
