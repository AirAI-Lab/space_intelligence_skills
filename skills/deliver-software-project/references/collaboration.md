# Collaboration

## Roles

- Product owns user outcome, scope and acceptance.
- UX owns workflow clarity, accessibility and state behavior.
- Software owns contracts, implementation and maintainability.
- Algorithm owns data, model metrics, limits and reproducibility.
- Hardware owns device capability, resource limits and environmental validation.
- Operations owns deployment, observability, backup, rollback and incident response.
- Security owns trust boundaries, credentials, authorization and auditability.

## Multi-Agent Contract

Before parallel work, publish:

- authoritative requirements and protocol version;
- repository and file ownership;
- shared schemas and compatibility rules;
- test fixtures and acceptance criteria;
- integration order and conflict owner.

Agents must not overwrite unrelated work. Every handoff reports changed files, commands, observed results, assumptions and blockers. Merge only after integration tests use the combined changes.

## AI Prompt Contract

A development prompt must state the goal, current evidence, constraints, non-goals, affected repositories, required implementation, acceptance tests, safety boundaries and completion report. Avoid prescribing speculative code before the repository is inspected.
