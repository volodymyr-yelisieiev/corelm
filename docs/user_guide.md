# User Guide

## Core model

Core LM stores durable truth in structured state, not in raw prompt text.
Text can be ingested, but only annotated claims become durable facts.
Corrections supersede prior facts instead of silently overwriting history.

## Primary workflows

### 1. Ingest a fact

```bash
corelm ingest --session session.json --branch corelm --subject project --attribute name --value "Core LM"
```

### 2. Correct a fact

```bash
corelm correct --session session.json --branch ops --subject api --attribute port --value "9090"
```

### 3. Query current value

```bash
corelm get --session session.json --branch ops --subject api --attribute port
```

### 4. Query provenance

```bash
corelm provenance --session session.json --branch ops --subject api --attribute port
```

### 5. List a branch

```bash
corelm list-branch --session session.json --branch corelm
```

## Session model

A session JSON file stores:
- seed
- append-only event list
- kernel snapshot
- digest
- summary stats

## Operational habits

- keep one session file per evaluation thread
- use explicit branches for unrelated topics
- correct facts instead of editing history
- run replay verification before shipping a demo artifact
- preserve the frozen benchmark directory unchanged
