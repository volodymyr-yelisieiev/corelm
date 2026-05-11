# API Contract

## Python API

```python
from corelm import CoreLMProduct

product = CoreLMProduct(seed=0)
product.ingest_fact('corelm', 'project', 'name', 'Core LM')
product.correct_fact('ops', 'api', 'port', '9090')
product.get_value('corelm', 'project', 'name')
product.get_provenance('ops', 'api', 'port')
product.list_branch('corelm')
product.save_session('session.json')
```

## CLI

```bash
python -m corelm.cli ingest --session session.json --branch corelm --subject project --attribute name --value "Core LM"
python -m corelm.cli get --session session.json --branch corelm --subject project --attribute name
python -m corelm.cli provenance --session session.json --branch corelm --subject project --attribute name
python -m corelm.cli list-branch --session session.json --branch corelm
```
