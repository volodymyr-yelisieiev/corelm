# Product Requirements Document

## Product definition

Core LM Local Reference Product is a single-user deterministic memory system
with structured fact ingestion, provenance-aware querying, replay verification,
and session persistence.

## Primary user
Technical evaluator who needs a concrete local artifact instead of a slide deck.

## Core user flows
1. Install package.
2. Ingest facts and corrections.
3. Query current values and provenance.
4. Persist session to disk.
5. Re-load session and verify replay digest.

## Functional requirements
- structured ingestion by branch / subject / attribute / value
- correction handling by slot supersession
- branch listing
- provenance lookup
- deterministic replay
- JSON session export
- CLI entrypoint

## Non-functional requirements
- Python 3.10+
- no hidden network dependency
- reproducible tests
- bounded local state

## Out of scope
- natural-language extraction from arbitrary user text
- multi-user concurrency
- hosted API service
- auth / billing / tenancy
