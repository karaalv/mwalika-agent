# API Security Architecture

## Overview

Mwalika implements a layered security architecture designed to ensure availability, integrity, and regulatory compliance while remaining publicly accessible.

The architecture consists of:

1. **Edge-Level Security**
   AWS CloudFront acts as a reverse proxy and is protected by AWS WAF. This layer provides DDoS mitigation, IP filtering, rate-based rules, and request inspection before traffic reaches the application.

2. **Application-Level Security**
   Implemented within backend services, including authentication, input validation, monitoring, rate limiting, and abuse detection controls.

Mwalika is intentionally designed as a publicly accessible discovery service. As such, the primary security risk is abuse and resource exhaustion rather than unauthorised access to sensitive data. Access remains authenticated and controlled, but the dominant threat model is automated misuse rather than data exfiltration.

Security and data handling practices align with the Kenya Data Protection Act, 2019 (KDPA), particularly the principles of:

- Lawfulness, fairness and transparency
- Purpose limitation
- Data minimisation
- Storage limitation
- Integrity and confidentiality
- Accountability

## Threat Model

### Primary Risks

- Automated scraping and API abuse
- DDoS and traffic flooding
- Abuse of LLM token usage
- WebSocket flooding and connection exhaustion
- Injection attempts and malformed payloads

The system mitigates these risks through layered edge protection and strict application-level controls.

### Secondary Risks

- Token theft or misuse
- Cross-site scripting (XSS)
- Cross-site request forgery (CSRF)
- Dependency vulnerabilities
- Data leakage through logging or monitoring systems

## Edge-Level Security

- AWS CloudFront reverse proxy
- AWS WAF rate-based and IP filtering rules
- DDoS protection at the infrastructure layer
- Request inspection and early rejection of malicious traffic

Edge protection reduces application attack surface and preserves availability.

## Application-Level Security

### Authentication Model

Mwalika uses a token-based authentication model primarily for usage tracking and abuse prevention.

- A `front-end-token` authenticates the client server to the backend.
- A `refresh-token` (7-day expiry) is issued via secure, HTTP-only cookie.
- A short-lived `access-token` (5 minutes) is issued and stored only in memory on the client side and is used for API requests as a Bearer token in the Authorization header.

This design:

- Reduces CSRF exposure
- Limits token replay risk
- Enables fine-grained rate enforcement
- Maintains open public access while protecting system integrity

### Abuse Monitoring

The system monitors:

- IP address activity
- Token usage patterns
- Request frequency and behavioural anomalies
- Payload size and token counts
- WebSocket handshake and message frequency

Escalation policies allow temporary or permanent blocking based on severity.

Abuse prevention is the dominant security control given the public-facing architecture.

### Rate Limiting

Rate limits are enforced at:

- Edge level (AWS WAF)
- Application level (per IP, token, and endpoint)

Additional controls include:

- Token usage caps for LLM interactions
- Payload size restrictions
- WebSocket handshake and message limits
- Idle timeout enforcement

## WebSocket Security Controls

- Maximum message size: 16KB
- Daily token usage cap: 50,000 tokens per user ID
- Idle timeout: 5 minutes
- Close codes used:
  - 1000 – Normal closure
  - 1008 – Policy violation
  - 1011 – Internal server error

These controls prevent streaming abuse while maintaining responsiveness.

## Data Privacy and Compliance

### Data Controller Role

Under the Kenya Data Protection Act (2019), Mwalika acts as the Data Controller for monitoring and operational data.

OpenAI and Sentry act as Data Processors.

### Lawful Basis

Processing is based on legitimate interest for:

- Abuse prevention
- System security
- Operational analytics

### Data Minimisation

Mwalika does not collect:

- Names
- National ID numbers
- Phone numbers
- Email addresses
- Financial information

Only operational metadata such as IP addresses and token usage patterns are processed.

This aligns with the KDPA principle of data minimisation.

### Data Retention

Operational data is automatically deleted after 7 days of inactivity.

Blocked entities are retained only for the duration of the block to prevent abuse evasion.

This aligns with the KDPA storage limitation principle.

### Data Security

- HTTPS and WSS enforce TLS encryption in transit (default AWS configuration).
- MongoDB Atlas provides encryption at rest and network isolation by default.
- Secrets are stored in AWS Secrets Manager (encrypted via AWS KMS by default).
- Least-privilege access is enforced via AWS IAM and database access controls.

## Cross-Border Data Transfers

OpenAI processing may occur outside Kenya. However:

- No personally identifiable information (PII) is transmitted.
- Data sent is limited to user-generated prompts.
- The system is designed to support future self-hosted LLM deployment to eliminate cross-border risk.

Infrastructure components are hosted in AWS Africa (af-south-1), with future localisation potential as Kenyan AWS zones expand.

## Incident Response and Accountability

### Monitoring and Alerts

- Real-time error monitoring via Sentry
- Infrastructure alerts via AWS CloudWatch
- Automated restart of failed pods (Kubernetes self-healing)

### Breach Response

In the event of a security incident:

- Logs are reviewed immediately
- Impact scope is assessed
- Mitigation measures are applied
- Notification procedures follow KDPA breach reporting obligations where applicable

### Governance and Accountability

- Infrastructure managed as code (Terraform)
- Role-Based Access Control (RBAC) across systems
- Least-privilege IAM policies
- Version-controlled documentation
- Defined ownership of operational responsibility

## Future Security Hardening

Planned enhancements include:

- Automated dependency vulnerability scanning
- Container image hardening
- Security header enforcement (CSP, HSTS)
- Expanded audit logging for administrative actions
- Migration to fully self-hosted LLM infrastructure

These measures will further strengthen resilience while maintaining system simplicity and clarity.
