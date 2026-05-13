from __future__ import annotations

import hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / 'reports' / 'archive_checksums.txt'
ignored_parts = {
    '.git', 'archives', '.pytest_cache', '__pycache__', '.venv', 'venv', 'build', 'dist',
    'node_modules', 'runtime', 'dist_windows', '.corelm_studio', '.corelm_studio_test',
    '.corelm_studio_dev', 'exports', 'dist-electron',
    '.variant_edit', '.variant_wheel', '.local100_edit_venv', '.local100_wheel_venv', '.local100_wheelhouse'
}
ignored_files = {'.local100_edit_demo.json', '.local100_edit_get.txt'}
lines = ['# SHA256 checksums']
for path in sorted(root.rglob('*')):
    if path.is_dir():
        continue
    if path == out:
        continue
    if any(part in ignored_parts for part in path.parts):
        continue
    if any(part.endswith('.egg-info') for part in path.parts):
        continue
    if path.name in ignored_files or path.name == '.env':
        continue
    if path.name.endswith(('.pyc', '.sqlite', '.sqlite-wal', '.sqlite-shm')):
        continue
    rel = path.relative_to(root)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    lines.append(f'{digest}  {rel.as_posix()}')
out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(out)
