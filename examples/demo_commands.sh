#!/usr/bin/env bash
set -euo pipefail

SESSION=${1:-examples/demo_session.json}

corelm demo --session "$SESSION"
corelm ingest --session "$SESSION" --branch corelm --subject truth --attribute store --value "core state"
corelm correct --session "$SESSION" --branch ops --subject api --attribute port --value "9090"
corelm get --session "$SESSION" --branch corelm --subject truth --attribute store
corelm provenance --session "$SESSION" --branch ops --subject api --attribute port
corelm list-branch --session "$SESSION" --branch corelm
