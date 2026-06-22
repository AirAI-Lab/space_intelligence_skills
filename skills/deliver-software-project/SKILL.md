---
name: deliver-software-project
description: Turn a product idea or change request into a user-centered, implemented, tested, documented, deployable, and releasable software increment. Use for greenfield projects, cross-repository features, architecture changes, bug and performance work, AI-assisted development, delivery planning, verification, deployment, release management, requirements traceability, or multi-role and multi-agent collaboration.
---

# Deliver Software Project

Deliver working software from idea through release. Treat repository evidence and executable verification as authoritative; never present plans, mocks, or unverified behavior as complete.

## Execute The Workflow

1. Inspect every affected repository, its status, current documentation, runtime topology, tests, and recent changes.
2. Translate the request into user outcomes, constraints, non-goals, risks, and observable acceptance criteria.
3. Build a traceability map from outcome to requirement, design decision, implementation location, test, deployment evidence, and release note.
4. Choose the smallest stable architecture that satisfies the outcomes. Preserve established contracts unless migration is explicit.
5. Split work by ownership boundary. For multiple agents, give disjoint write scopes and a shared protocol or schema before implementation.
6. Implement end to end. Include error, empty, loading, degraded, recovery, security, and operability behavior.
7. Verify from narrow to broad: static checks, unit tests, integration tests, realistic runtime checks, resource behavior, and user workflow validation.
8. Reconcile requirements, code, database migrations, protocols, UI, deployment configuration, documentation, and changelog.
9. Review the actual diff for correctness, simplicity, performance, security, maintainability, and unrelated changes.
10. Commit and release only the verified scope. Report failures and residual risks precisely.

Read [references/lifecycle.md](references/lifecycle.md) for stage gates, [references/collaboration.md](references/collaboration.md) for human and agent coordination, and [references/quality-gates.md](references/quality-gates.md) for verification rules.

## Maintain Project Context

Use repository files as shared memory. Prefer a short decision log, machine-readable event stream, current status, changelog, and test reports over copying conversation transcripts.

Run `scripts/snapshot-project-context.ps1` when a decision is confirmed, a verified feature lands, a release is tagged, or a downstream course or playbook needs synchronization. Consumers must distinguish `planned`, `implemented`, and `verified` states.

Do not store credentials, customer data, private endpoints, model binaries, or production secrets in skills, prompts, memory, logs, or teaching artifacts.

## Coordinate AI Tools

Give every tool the same authoritative requirement, protocol, ownership boundary, and acceptance criteria. Treat generated prompts as handoff contracts, not as evidence of completion. Require each tool to return changed files, tests run, observed outputs, unresolved issues, and assumptions.

Use an independent review pass for high-risk changes. Do not let a reviewer rewrite unrelated code or approve its own unverified claims.

## Stop Conditions

Do not deploy or release when migrations are unverified, required tests fail, compatibility is unknown, secrets are exposed, production access is ambiguous, or observed behavior contradicts the acceptance criteria. Record the blocker and preserve a recoverable workspace.
