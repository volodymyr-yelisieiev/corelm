# Security Policy

## Scope

This bundle is a local, single-user reference product and research artifact.
It is not a hosted multi-tenant service. Security posture is therefore limited
to local-file handling, deterministic replay, and packaging hygiene.

## Supported line

- 1.3.x: supported for local evaluation and archival use
- earlier versions: unsupported

## What to report

Please report:
- unsafe file writes or path traversal
- session corruption or replay mismatch
- packaging defects that expose unintended files
- command-line behaviors that write outside the requested session path

## What is out of scope

- cloud isolation
- network perimeter security
- IAM / RBAC
- customer data residency
- external dependency supply-chain attestations

## Reporting path

Use a private channel with a minimal reproduction, affected version, expected
behavior, actual behavior, and whether the issue changes any benchmark claim.

## Response posture

The priority order is:
1. deterministic data integrity
2. archive/replay correctness
3. session file safety
4. packaging cleanliness
