from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .product import CoreLMProduct


def _load_or_new(session: Path, seed: int = 0) -> CoreLMProduct:
    if session.exists():
        return CoreLMProduct.load_session(session)
    product = CoreLMProduct(seed=seed)
    product.save_session(session)
    return product


def cmd_ingest(args: argparse.Namespace) -> int:
    session = Path(args.session)
    product = _load_or_new(session, seed=args.seed)
    product.ingest_fact(
        branch=args.branch,
        subject=args.subject,
        attribute=args.attribute,
        value=args.value,
        text=args.text,
        tags=args.tag,
    )
    product.save_session(session)
    print(json.dumps({'status': 'ok', 'digest': product.kernel.digest()}, ensure_ascii=False))
    return 0


def cmd_correct(args: argparse.Namespace) -> int:
    session = Path(args.session)
    product = _load_or_new(session, seed=args.seed)
    product.correct_fact(
        branch=args.branch,
        subject=args.subject,
        attribute=args.attribute,
        value=args.value,
        text=args.text,
        tags=args.tag,
    )
    product.save_session(session)
    print(json.dumps({'status': 'ok', 'digest': product.kernel.digest()}, ensure_ascii=False))
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    product = CoreLMProduct.load_session(args.session)
    print(product.get_value(args.branch, args.subject, args.attribute))
    return 0


def cmd_provenance(args: argparse.Namespace) -> int:
    product = CoreLMProduct.load_session(args.session)
    print(product.get_provenance(args.branch, args.subject, args.attribute))
    return 0


def cmd_list_branch(args: argparse.Namespace) -> int:
    product = CoreLMProduct.load_session(args.session)
    print(product.list_branch(args.branch))
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    session = Path(args.session)
    product = CoreLMProduct(seed=args.seed)
    product.ingest_fact('corelm', 'project', 'name', 'Core LM', text='Final project name is Core LM.')
    product.ingest_fact('corelm', 'pipeline', 'order', 'E -> N -> T -> Q -> K', text='Canonical pipeline is E -> N -> T -> Q -> K.')
    product.ingest_fact('corelm', 'llm', 'role', 'excitation source only', text='LLM is only an excitation source, not the truth store.')
    product.correct_fact('ops', 'api', 'port', '9090', text='Correction: API port is 9090.')
    product.save_session(session)
    print(json.dumps(product.export_state(), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='corelm', description='Core LM local reference product CLI')
    sub = parser.add_subparsers(dest='cmd', required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--session', required=True)
    common.add_argument('--seed', type=int, default=0)

    fact_common = argparse.ArgumentParser(add_help=False, parents=[common])
    fact_common.add_argument('--branch', required=True)
    fact_common.add_argument('--subject', required=True)
    fact_common.add_argument('--attribute', required=True)
    fact_common.add_argument('--value', required=True)
    fact_common.add_argument('--text')
    fact_common.add_argument('--tag', action='append', default=[])

    p = sub.add_parser('ingest', parents=[fact_common], help='ingest a fact')
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser('correct', parents=[fact_common], help='correct a fact')
    p.set_defaults(func=cmd_correct)

    p = sub.add_parser('get', parents=[common], help='query a value')
    p.add_argument('--branch', required=True)
    p.add_argument('--subject', required=True)
    p.add_argument('--attribute', required=True)
    p.set_defaults(func=cmd_get)

    p = sub.add_parser('provenance', parents=[common], help='query provenance')
    p.add_argument('--branch', required=True)
    p.add_argument('--subject', required=True)
    p.add_argument('--attribute', required=True)
    p.set_defaults(func=cmd_provenance)

    p = sub.add_parser('list-branch', parents=[common], help='list current branch facts')
    p.add_argument('--branch', required=True)
    p.set_defaults(func=cmd_list_branch)

    p = sub.add_parser('demo', parents=[common], help='create a demo session')
    p.set_defaults(func=cmd_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
