from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def write_json(path: str | Path, payload: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def write_markdown(path: str | Path, payload: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append(f"# Core LM Publication Benchmark Report")
    lines.append("")
    lines.append(f"Generated systems: {', '.join(payload['systems'])}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| System | Passed | Accuracy | Determinism | Provenance | Violations | Max Norm | Facts | Memory Words |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for summary in payload["summaries"]:
        lines.append(
            f"| {summary['system']} | {summary['passed_scenarios']}/{summary['scenarios']} | "
            f"{summary['query_accuracy']:.3f} | {summary['replay_determinism']:.3f} | "
            f"{summary['provenance_coverage']:.3f} | {summary['invariant_violation_rate']:.3f} | "
            f"{summary['max_state_norm']:.3f} | {summary['total_durable_facts']} | {summary['approx_memory_words']} |"
        )
    lines.append("")
    lines.append("## Scenario results")
    lines.append("")
    for row in payload["scenario_rows"]:
        lines.append(f"### {row['scenario']}")
        lines.append("")
        lines.append("| System | Accuracy | Passed | Determinism | Provenance | Violations |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for result in row["results"]:
            lines.append(
                f"| {result['system']} | {result['accuracy']:.3f} | "
                f"{'yes' if result['passed'] else 'no'} | {result['determinism']:.3f} | "
                f"{result['provenance_coverage']:.3f} | {result['invariant_violation_rate']:.3f} |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
