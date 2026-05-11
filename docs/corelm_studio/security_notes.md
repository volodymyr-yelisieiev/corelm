# Security Notes

- Core LM Studio is local-first and single-user by default.
- Secrets are not stored in workflow JSON, chat messages, logs, crash reports, or
  ledger metadata.
- The sidecar redacts common API key, bearer token, token, secret, password, and
  OpenAI-style key patterns before storing chat and metadata.
- SQLite stores secret metadata only. A Windows production build should route raw
  secrets through Windows Credential Manager or another OS-backed secure store.
- Shell capture and shell outbound are mock-only unless `allow_exec=true` is set
  explicitly in connector config.
- External network connectors are opt-in. Deterministic mocks are preferred for
  sample workflows and tests.
