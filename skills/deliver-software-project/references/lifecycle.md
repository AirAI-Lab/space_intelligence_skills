# Delivery Lifecycle

## Gates

| Gate | Required evidence |
|---|---|
| Discover | Users, problem, value, constraints, existing alternatives |
| Define | Acceptance criteria, non-goals, risks, affected repositories |
| Design | Contracts, data ownership, failure behavior, migration and rollback |
| Build | Scoped diff, compatibility, observability and secure defaults |
| Verify | Automated tests plus realistic user and runtime checks |
| Release | Migration order, configuration, rollback, changelog and version |
| Operate | Health, metrics, alerts, support procedure and incident evidence |
| Learn | Verified outcomes, defects, reusable decisions and training impact |

Never advance a gate using prose alone when executable or observable evidence is available.

## Product Discipline

Prioritize usable, reliable, efficient, secure workflows over feature count. Hide technical complexity from ordinary users while preserving advanced diagnostics for operators. Remove obsolete or conflicting behavior when migration is explicit and tested.

## Traceability

For every material requirement, record:

```text
user outcome -> acceptance criterion -> design decision -> code/data/protocol
-> automated test -> runtime evidence -> documentation -> release
```

Mark each link as planned, implemented, verified, or released.
