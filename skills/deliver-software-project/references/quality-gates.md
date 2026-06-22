# Quality Gates

## Code

- Correct ownership and lifecycle; no hidden global state or unbounded queues.
- Explicit timeouts, retries, idempotency and recovery where external systems are involved.
- Bounded CPU, memory, storage, network and concurrency behavior.
- Stable contracts and migrations with rollback or compatibility strategy.
- Clear errors and observable runtime state.

## User Experience

- Complete primary workflow without command-line intervention unless the product is a CLI.
- Accurate loading, empty, offline, degraded, error and recovery states.
- Responsive layouts, accessible controls and no duplicate workflows.
- User-facing language explains outcomes and actions rather than internal mechanisms.

## Verification

- Unit tests for decisions and edge cases.
- Integration tests for database, messaging, storage and protocol boundaries.
- Realistic end-to-end validation for the primary workflow.
- Performance and long-running tests when resources, streaming, concurrency or hardware matter.
- Security checks for authentication, authorization, input size, paths, secrets and logging.

Never convert a failed or skipped check into a passing statement. Record the environment and exact limitation.
