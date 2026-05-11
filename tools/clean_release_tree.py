from __future__ import annotations

import os
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
remove_dirs = {
    '.venv', 'venv', '.pytest_cache', 'build', 'dist', 'dist-electron',
    'node_modules', 'dist_windows', '.corelm_studio', '.corelm_studio_test',
    '.corelm_studio_dev', 'exports',
    '.local100_edit_venv', '.local100_wheel_venv', '.local100_wheelhouse',
    '.variant_edit', '.variant_wheel',
}
remove_files = {
    '.local100_edit_demo.json', '.local100_edit_get.txt',
    '.local100_wheel_demo.json', '.local100_wheel_get.txt',
}

for current, dirs, files in os.walk(root, topdown=False):
    current_path = Path(current)
    for name in files:
        path = current_path / name
        if name in remove_files or name == '.env' or name.endswith('.pyc') or name.endswith('.sqlite') or name.endswith('.sqlite-wal') or name.endswith('.sqlite-shm'):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
    for name in dirs:
        path = current_path / name
        if name in remove_dirs or name == '__pycache__' or name.endswith('.egg-info'):
            shutil.rmtree(path, ignore_errors=True)

print(root)
