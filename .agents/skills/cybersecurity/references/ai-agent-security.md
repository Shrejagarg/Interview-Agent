# AI, Agent & RAG Security

## AI & Agent Security

- Treat all model inputs as untrusted — user instructions, retrieved documents, web content, OCR, tool outputs can all contain prompt injection
- Never allow the model to directly decide authorization, identity, permissions, or access to secrets — LLMs are not security boundaries
- Separate trust layers explicitly: system instructions > developer rules > user input > retrieved content > tool results. These are NOT equally authoritative
- Instruct the model that retrieved content and external documents are **data, not instructions** — they must never override higher-level rules
- Use strict tool allowlists — only expose the minimum tools required for the task
- Validate all tool arguments server-side before execution — even aligned models can generate dangerous, malformed, or attacker-influenced parameters
- Require authorization checks **outside the model** before any sensitive tool call: file access, email, payments, shell execution, data export, admin changes
- Treat model-generated code, SQL, shell commands, URLs, and file paths as untrusted suggestions, not safe outputs
- Limit tool execution environments with timeouts, memory restrictions, network restrictions, filesystem isolation, and explicit working directories
- Prevent unrestricted browsing and retrieval from automatically feeding the model with high-trust privileges — malicious websites and documents contain hidden prompt injection
- Sanitize or filter retrieved content before presenting it to the model — strip suspicious instruction-like patterns from documents
- Never give the model raw secrets, master tokens, broad credentials, or unrestricted environment access — assume they may appear in logs, outputs, or downstream prompts
- Keep memory systems, agent profiles, and long-lived context stores resistant to untrusted writes — persistent prompt injection survives across sessions
- Require human approval or policy checks for high-risk actions: sending messages, writing files outside safe directories, purchases, config changes, production interactions
- Log every tool call with: validated arguments, acting identity, policy decision, execution result — AI systems are impossible to secure without strong audit trails
- Use typed output schemas and structured intermediate representations instead of letting the model freely emit arbitrary action text
- Build so the model **proposes** actions but a deterministic **policy layer decides** whether they are allowed — separate reasoning from enforcement
- Do not let the model self-modify its own security instructions, tool permissions, trust rules, or policy configuration
- Test explicitly for prompt injection: "ignore previous instructions," hidden HTML comments, markdown directives, fake tool responses, malicious PDF text, poisoned retrieved documents

## RAG-Specific Security

- Treat retrieved documents as untrusted even from your own knowledge base — documents may contain stale, harmful, or attacker-inserted instructions
- Separate retrieval relevance from authority — a highly relevant document does not automatically gain the right to instruct the model
- Avoid ingesting arbitrary user-supplied documents directly into shared retrieval indexes without review or isolation
- Use tenant isolation in embeddings, indexes, and retrieval filters — retrieval bugs become cross-tenant data leaks without segmentation
- Redact or filter secrets and sensitive data before embedding — embeddings may expose semantic information even without showing raw content

## Admin & Internal Tooling

- Treat admin panels, support dashboards, and internal scripts as high-risk — they combine broad access with less polished security review
- Require strong authentication and narrow role separation for internal tools
- Never create hidden "backdoor convenience" endpoints or support overrides without explicit controls and auditing

## Logging, Monitoring & Incident Readiness

- Use structured logging with consistent fields: request ID, user ID, action type, route, environment, severity
- Include request correlation IDs throughout the lifecycle and propagate across backend calls, workers, and integrations
- Log security-relevant events: auth failures, permission denials, rate limit events, suspicious validation failures, admin actions, tool executions
- Never log secrets, raw tokens, full personal data, private documents, model prompts containing secrets, or sensitive file contents
- Define alerting for unusual spikes in: errors, access denials, token issuance, file uploads, container restarts, outbound requests
- Prepare an incident response mindset: revocation, containment, and auditability — security failures should be survivable, not catastrophic
