# Web Security — Frontend + Backend

## Frontend Security (Next.js)

- Never place secrets, private API keys, database credentials, or signing keys in client-side code, public environment variables, or bundled assets — everything shipped to the browser is visible to attackers
- Use server-side logic, route handlers, or backend APIs for all privileged operations — security implemented only in the frontend can always be bypassed
- Sanitize and validate all data received from APIs before rendering, especially rich text, markdown, HTML fragments, or third-party content
- Avoid `dangerouslySetInnerHTML` unless absolutely necessary — if used, sanitize with a hardened allowlist-based sanitizer
- Apply a strict Content Security Policy (CSP) and avoid inline scripts — CSP is the second line of defense against XSS
- Use secure cookie settings: `HttpOnly`, `Secure`, `SameSite=Strict` (or `Lax`) for session cookies
- Protect all state-changing requests against CSRF in cookie-based auth flows
- Do not rely on hidden buttons, route guards, disabled UI elements, or client-side checks for authorization — these are UX, not security
- Avoid exposing internal error details, stack traces, or debugging metadata to users
- Strictly validate redirect URLs and callback destinations to prevent open redirect abuse
- Limit third-party scripts and analytics to the absolute minimum — every third-party script has significant access inside the browser
- Handle file uploads: validate basic constraints in frontend for UX, but all real validation must happen on the backend

## Backend Security (FastAPI)

- Validate all request data with explicit Pydantic schemas — body, query params, path params, headers, config values
- Enforce authentication and authorization separately — authenticated ≠ authorized
- Perform object-level authorization on every resource access (prevent IDOR)
- Use parameterized queries and ORM protections — never build SQL via string concatenation
- Avoid unsafe shell execution, subprocess with user-controlled arguments, and dynamic interpreter execution
- Restrict file handling aggressively: validate MIME type, extension, size, structure, and storage destination
- Enforce request size limits, rate limits, and timeouts at the application boundary
- Never expose internal stack traces, ORM errors, or environment metadata in API responses
- Use consistent security headers on auth endpoints and browser-consumed APIs
- Separate domain, application, infrastructure, and API layers to improve security reviewability
- Log security-relevant events: auth attempts, password resets, permission failures, admin actions, token issuance, suspicious uploads, rate limit triggers
- Implement strict CORS — only allow known origins that actually need access
- Use short-lived tokens and rotate refresh credentials securely
- Store passwords with strong modern hashing algorithms (bcrypt, argon2) — never general-purpose hashes
- Treat background jobs, workers, cron tasks, and internal endpoints as production attack surfaces

## Authentication & Authorization

- Centralize auth rules — inconsistent enforcement across routes causes privilege escalation
- Apply least privilege by default to users, service accounts, tools, and background jobs
- Require re-authentication or step-up verification for highly sensitive actions (changing email, resetting MFA, exporting data, rotating API keys)
- Separate user roles, system roles, and machine identities clearly — mixing creates invisible escalation paths
- Invalidate sessions and tokens after logout, credential reset, role changes, or account compromise
- Use audit trails for privileged actions — ensure logs cannot be modified by the actors performing the actions

## Secrets Management

- Never commit secrets, API keys, database URLs, private certs, SSH keys, or tokens to source control
- Never bake secrets into Docker images, frontend bundles, static files, or example templates
- Inject secrets at runtime through environment variables or a dedicated secret manager — minimize which services receive which secrets
- Rotate secrets regularly and especially after personnel changes, environment copies, or incident suspicion
- Prevent secrets from appearing in logs, traces, metrics labels, exception messages, and debugging output

## Input Validation & Output Safety

- Validate input as close to the boundary as possible, then work with trusted internal types afterward
- Use allowlists instead of blocklists whenever practical
- Normalize input before validation when case, Unicode, whitespace, or encoding may affect security decisions
- Encode or escape output according to context (HTML, JavaScript, JSON, URLs, logs)
- Treat filenames, URLs, markdown, templates, and serialized objects as potentially dangerous — not harmless strings

## Secure API Design

- Version APIs explicitly (`/api/v1/`) for safe evolution
- Return consistent error structures that do not leak internals
- Paginate large collections — avoid unbounded list responses
- Design sensitive endpoints to require explicit intent and narrow scopes
- Treat internal APIs with the same seriousness as public APIs — they become externally reachable through SSRF or misconfiguration
