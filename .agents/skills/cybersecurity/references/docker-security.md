# Docker, Infrastructure & Supply Chain Security

## Docker & Container Hardening

- Use minimal base images and pin explicit versions (e.g., `python:3.12.3-slim-bookworm`) — never use `latest`
- Run containers as non-root users — compromised processes should not have root privileges
- Use read-only filesystems where practical — mount writable paths explicitly and minimally
- Drop ALL Linux capabilities (`cap_drop: [ALL]`) and add back only what is strictly required
- Enable no-new-privileges protection (`security_opt: [no-new-privileges:true]`)
- Never run containers with `privileged: true` unless unavoidable and reviewed
- Never mount the Docker socket (`/var/run/docker.sock`) into application containers — this grants host-level control
- Avoid mounting sensitive host directories or the root filesystem into containers
- Segment services into separate Docker networks — only allow minimum communication paths
- Do not expose internal service ports publicly (databases, queues, admin tools, observability)
- Apply CPU, memory, file descriptor, and process limits to all containers
- Use health checks and restart policies — but do not mask repeated crash loops from exploitation
- Build images using multi-stage builds — no compilers, package managers, or build tools in the runtime image
- Scan images regularly for vulnerabilities and outdated packages (trivy, grype)
- Keep Docker Compose production-aware — no dev shortcuts in production (broad mounts, debug ports, weak secrets, permissive env flags)

## Infrastructure & Network

- Terminate TLS correctly and enforce HTTPS everywhere external traffic is accepted
- Place reverse proxies or gateways in front of application services to centralize TLS, rate limiting, IP filtering, and security headers
- Restrict outbound network access for services that do not need broad internet connectivity — prevents data exfiltration and C2 traffic
- Protect admin panels and internal tools behind stronger access controls than public routes
- Separate development, staging, and production credentials and environments completely

## Dependencies & Supply Chain

- Pin dependency versions and use lockfiles for reproducible, auditable builds
- Regularly scan dependencies for known vulnerabilities — review transitive dependencies too
- Prefer mature, maintained, well-reviewed libraries over obscure packages with unclear ownership
- Verify third-party packages, Docker images, browser libraries, and AI tooling dependencies before introducing them
- Remove unused dependencies aggressively — every dependency increases attack surface and review cost
