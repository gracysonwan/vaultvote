## Security Policy

VaultVote is a hackathon prototype, not a production election system. Do not use it for a real election or store real voter information without an independent security review.

### Reporting a vulnerability

Please report suspected vulnerabilities privately to the repository maintainers rather than posting exploit details publicly. Include the affected endpoint or file, reproduction steps, impact, and a suggested mitigation when available.

### Deployment requirements

- Set `SECRET_KEY` and `ADMIN_PASSWORD` through the hosting provider's secret manager.
- Do not use the example credentials from older documentation.
- Set `COOKIE_SECURE=1` when serving over HTTPS.
- Restrict `CORS_ORIGINS` to the exact frontend origin(s).
- Use a persistent, access-controlled database volume and encrypted transport.
- Rotate credentials after demos or suspected exposure.

The application provides cryptographic hashes and an audit chain for demonstration purposes; these features do not replace a formal election audit or independent security assessment.
