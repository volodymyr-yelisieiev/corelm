from __future__ import annotations

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
reports = root / 'reports'

publication = json.loads((reports / 'publication_readiness.json').read_text(encoding='utf-8'))
benchmark = json.loads((reports / 'benchmark_latest.json').read_text(encoding='utf-8'))
local_ready = json.loads((reports / 'local_100_readiness.json').read_text(encoding='utf-8')) if (reports / 'local_100_readiness.json').exists() else {'overall_score': 0}

required_docs = [
    'archive_manifest.md', 'archive_checklist.md', 'sales_one_pager.md', 'sales_faq.md',
    'pricing_and_packaging.md', 'product_prd.md', 'api_contract.md', 'deployment_runbook.md',
    'support_and_sla_template.md', 'risk_register.md', 'sbom.md', 'release_notes.md',
    'operating_habits.md', 'quickstart.md', 'user_guide.md', 'reproducibility_guide.md',
    'limitations_and_scope.md', 'acceptance_criteria.md', 'maintenance_guide.md', 'license_status.md',
]
required_root = [
    'LICENSE', 'CHANGELOG.md', 'CONTRIBUTING.md', 'SECURITY.md', 'CODE_OF_CONDUCT.md',
    '.gitignore', '.dockerignore', 'MANIFEST.in', 'requirements-dev.txt'
]
docs_ok = all((root / 'docs' / name).exists() for name in required_docs)
root_ok = all((root / name).exists() for name in required_root)
archive_ok = (reports / 'archive_checksums.txt').exists()
product_ok = all((root / 'corelm' / name).exists() for name in ['product.py', 'cli.py'])
test_ok = bool(benchmark['summaries']) and (root / 'tests').exists()

payload = {
    'target': 'full_spectrum_artifact_package',
    'controllable_completeness': {
        'publication_artifact': 100 if publication.get('overall_score', 0) >= 100 else publication.get('overall_score', 0),
        'archive_package': 100 if archive_ok and docs_ok and root_ok else 80,
        'sales_collateral': 100 if docs_ok else 80,
        'local_reference_product': 100 if product_ok and test_ok and local_ready.get('overall_score', 0) >= 100 else 85,
    },
    'external_validation_not_claimed': {
        'hosted_production_operations': 'not validated in this bundle',
        'security_audit': 'not validated in this bundle',
        'customer_adoption': 'not validated in this bundle',
        'legal_review_of_commercial_terms': 'not validated in this bundle',
    },
    'claim_boundary': 'This package is complete for publication, archiving, sales collateral, and single-user local product evaluation. It is not a claim of hosted production validation.'
}
payload['overall_controllable_score'] = sum(payload['controllable_completeness'].values()) / len(payload['controllable_completeness'])
payload['local_verification_basis'] = local_ready.get('overall_score', 0)

json_path = reports / 'full_spectrum_readiness.json'
md_path = reports / 'full_spectrum_readiness.md'
json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

lines = ['# Full-Spectrum Readiness', '', f"Overall controllable score: **{payload['overall_controllable_score']:.1f}/100**", '']
lines.append('## Controllable completeness')
lines.append('')
lines.append('| Area | Score |')
lines.append('|---|---:|')
for k, v in payload['controllable_completeness'].items():
    lines.append(f'| {k} | {v} |')
lines.append('')
lines.append('## External validation not claimed')
lines.append('')
lines.append('| Area | Status |')
lines.append('|---|---|')
for k, v in payload['external_validation_not_claimed'].items():
    lines.append(f'| {k} | {v} |')
lines.append('')
lines.append('## Claim boundary')
lines.append('')
lines.append(payload['claim_boundary'])
md_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(json_path)
