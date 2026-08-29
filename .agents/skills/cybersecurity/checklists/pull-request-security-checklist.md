# Pull Request Security Checklist

Use this checklist when reviewing PRs that touch security-sensitive code.

## Input & Validation
- [ ] All external inputs validated with schemas (Pydantic/Zod)
- [ ] No raw user input in SQL queries (parameterized only)
- [ ] No raw user input in shell commands (subprocess with shell=False)
- [ ] No raw user input in HTML rendering (sanitized or escaped)
- [ ] File uploads validated: MIME type, extension, size, structure
- [ ] Redirect URLs validated against allowlist (no open redirects)

## Authentication & Authorization
- [ ] Authentication required for all sensitive endpoints
- [ ] Authorization checked per resource, not just per route (IDOR prevention)
- [ ] Sensitive actions require re-authentication or step-up verification
- [ ] Sessions/tokens invalidated properly on logout and credential reset

## Secrets & Data
- [ ] No secrets, API keys, or credentials in code, config files, or logs
- [ ] No internal error details, stack traces, or environment metadata in API responses
- [ ] Sensitive data not logged (tokens, passwords, PII, prompts with secrets)
- [ ] Secrets injected at runtime, not baked into Docker images

## AI & Agent Features
- [ ] Model output treated as untrusted (not directly executed)
- [ ] Tool arguments validated server-side before execution
- [ ] Authorization checks outside the model for sensitive tool calls
- [ ] Retrieved content marked as data, not instructions
- [ ] Tool execution sandboxed with timeouts and resource limits
- [ ] Tool calls logged with identity, arguments, and result

## Infrastructure
- [ ] Docker containers run as non-root
- [ ] No Docker socket or sensitive host paths mounted
- [ ] Dependencies pinned and scanned for vulnerabilities
- [ ] No development shortcuts in production config (debug ports, broad mounts)

## Observability
- [ ] Security-relevant events logged (auth failures, permission denials, admin actions)
- [ ] Request correlation IDs present
- [ ] No secrets in log output
