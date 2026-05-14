# Compression Inspector

The desktop Compression Inspector opens from Console mode, History, ledger
items, chat messages, Flow Studio run details, and Benchmark Studio trial
metadata when compression metadata is available.

It displays:

- raw input, sanitized text, cleaned text, deduped text, and canonical text;
- digest, compression ratio, raw/canonical lengths, and token proxies;
- applied pipeline steps and transform badges;
- structured extraction annotations;
- contradiction candidates;
- raw-to-canonical diff;
- quick compare between two compression packets.

The API lookup route is:

```text
GET /api/compression?session_id=default&target_type=<type>&target_id=<id>
```

Supported target types are `chat_message`, `ledger_entry`, and `workflow_run`.
Ledger metadata keeps the raw pre-commit payload redacted for safety; chat and
preview packets expose the sanitized raw payload captured before canonical
commit.
