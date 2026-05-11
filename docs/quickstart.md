# Quickstart

## Runtime-only local use

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install .
corelm demo --session examples/demo_session.json
corelm get --session examples/demo_session.json --branch corelm --subject project --attribute name
```

## Development / validation use

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
make release-check
```

## Minimal Python usage

```python
from corelm import CoreLMProduct

product = CoreLMProduct(seed=0)
product.ingest_fact('corelm', 'project', 'name', 'Core LM')
product.correct_fact('ops', 'api', 'port', '9090')
print(product.get_value('corelm', 'project', 'name'))
print(product.get_provenance('ops', 'api', 'port'))
```

## Where to look next

- `docs/user_guide.md`
- `docs/reproducibility_guide.md`
- `docs/limitations_and_scope.md`
- `examples/demo_commands.sh`
