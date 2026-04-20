# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

If you discover a security vulnerability, please report it responsibly:

1. **Email:** [Jan-Philipp.Praetorius@hkcmanagement.de](mailto:Jan-Philipp.Praetorius@hkcmanagement.de) with subject `[SECURITY] <brief description>`
2. **Include in your report:**
   - A description of the vulnerability and its potential impact
   - Steps to reproduce or a proof-of-concept (if safe to share)
   - Any suggested mitigation or fix

### What to expect

- We will acknowledge your report within **48 hours**.
- We aim to provide a fix or workaround within **14 days** for critical issues.
- We will credit you in the release notes (unless you prefer to remain anonymous).
- We will not take legal action against researchers who follow responsible disclosure.

## Scope

The following are **in scope**:

- Authentication and authorisation bypasses
- Remote code execution
- SQL injection, XSS, CSRF, and other OWASP Top 10 issues
- Sensitive data exposure
- Insecure default configurations

The following are **out of scope**:

- Denial-of-service attacks
- Issues in third-party dependencies (please report to the upstream project)
- Social engineering or phishing

## Security Best Practices for Contributors

When contributing to this project, please follow these practices:

- Never commit secrets, credentials, or API keys to the repository.
- Use `.env.example` to document required environment variables; never commit `.env`.
- Run `pre-commit` hooks locally — they include secret detection (`gitleaks`).
- Validate and sanitise all user input at system boundaries.
- Follow the principle of least privilege for any new service or role.
- Keep dependencies up to date and review `CHANGELOG`s before bumping major versions.
