# Local Product Smoke Test

Commands executed:

```bash
PYTHONPATH=. python -m corelm.cli demo --session examples/demo_session.json
PYTHONPATH=. python -m corelm.cli get --session examples/demo_session.json --branch corelm --subject project --attribute name
```

Observed result:
- current value for `corelm::project::name` = `Core LM`
- session file created at `examples/demo_session.json`
- replayable deterministic state persisted to disk
