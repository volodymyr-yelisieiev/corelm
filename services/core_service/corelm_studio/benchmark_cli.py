from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .benchmarking import BenchmarkEngine, report_as_text
from .direct_runtime import direct_runtime_registry
from .studio_core import StudioCore


def _core(args: argparse.Namespace) -> StudioCore:
    return StudioCore(db_path=args.db_path)


def cmd_list_adapters(args: argparse.Namespace) -> int:
    print(json.dumps(direct_runtime_registry().adapters(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_list_models(args: argparse.Namespace) -> int:
    print(json.dumps(direct_runtime_registry().list_models(args.adapter_id), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_list_profiles(args: argparse.Namespace) -> int:
    core = _core(args)
    try:
        engine = BenchmarkEngine(core)
        print(json.dumps(engine.list_profiles(), ensure_ascii=False, indent=2, sort_keys=True))
    finally:
        core.close()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    core = _core(args)
    try:
        engine = BenchmarkEngine(core)
        if args.profile_json:
            profile = json.loads(Path(args.profile_json).read_text(encoding="utf-8"))
            report = engine.run_profile(profile, args.session_id, args.branch, args.report_dir)
        else:
            report = engine.run_profile_id(args.profile_id, args.session_id, args.branch, args.report_dir)
        fmt = args.format
        print(report_as_text(report, fmt))
        passed = bool(report.get("summary", {}).get("verdict", {}).get("passed"))
        strict_result = bool(report.get("summary", {}).get("strict_result"))
        if args.require_strict and not strict_result:
            return 2
        return 0 if passed else 1
    finally:
        core.close()


def cmd_export(args: argparse.Namespace) -> int:
    core = _core(args)
    try:
        run = core.db.get_benchmark_run(args.run_id)
        if not run:
            print(f"benchmark run not found: {args.run_id}", file=sys.stderr)
            return 1
        print(report_as_text(run.get("report") or {}, args.format))
    finally:
        core.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="corelm-studio-bench", description="Core LM Studio direct runtime benchmark CLI")
    parser.add_argument("--db-path", default=None, help="SQLite database path; defaults to CORELM_STUDIO_DATA_DIR/corelm_studio.sqlite")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("adapters", help="list direct runtime adapters")
    p.set_defaults(func=cmd_list_adapters)

    p = sub.add_parser("models", help="list discovered local direct-runtime models")
    p.add_argument("--adapter-id")
    p.set_defaults(func=cmd_list_models)

    p = sub.add_parser("profiles", help="list benchmark profiles")
    p.set_defaults(func=cmd_list_profiles)

    p = sub.add_parser("run", help="run a saved profile or profile JSON")
    p.add_argument("--profile-id", default="builtin-runtime-conformance")
    p.add_argument("--profile-json")
    p.add_argument("--session-id", default="default")
    p.add_argument("--branch", default="corelm")
    p.add_argument("--format", choices=["json", "markdown", "md", "csv"], default="json")
    p.add_argument("--report-dir", default=None)
    p.add_argument("--require-strict", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("export", help="export a persisted benchmark report")
    p.add_argument("run_id")
    p.add_argument("--format", choices=["json", "markdown", "md", "csv"], default="json")
    p.set_defaults(func=cmd_export)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
