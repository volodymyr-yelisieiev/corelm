from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime" / "python-win"
WHEELHOUSE = ROOT / "runtime" / "wheelhouse-win"
PYTHON_VERSION = "3.11.9"
EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return
    with urllib.request.urlopen(url, timeout=120) as response:
        target.write_bytes(response.read())


def run_pip_download() -> None:
    WHEELHOUSE.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--only-binary=:all:",
            "--implementation",
            "cp",
            "--python-version",
            "311",
            "--abi",
            "cp311",
            "--platform",
            "win_amd64",
            "--dest",
            str(WHEELHOUSE),
            "-r",
            str(ROOT / "requirements.txt"),
        ],
        check=True,
    )


def unpack_runtime() -> None:
    marker = RUNTIME / ".corelm_python_ready"
    if marker.exists() and (RUNTIME / "python.exe").exists():
        return
    if RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    embed_zip = ROOT / "runtime" / f"python-{PYTHON_VERSION}-embed-amd64.zip"
    download(EMBED_URL, embed_zip)
    with zipfile.ZipFile(embed_zip) as archive:
        archive.extractall(RUNTIME)

    site_packages = RUNTIME / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    run_pip_download()
    for wheel in sorted(WHEELHOUSE.glob("*.whl")):
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(site_packages)

    pth = RUNTIME / "python311._pth"
    pth.write_text(
        "python311.zip\n"
        ".\n"
        "..\n"
        "Lib/site-packages\n"
        "\n"
        "import site\n",
        encoding="utf-8",
    )
    marker.write_text("Core LM Studio Windows embedded Python runtime prepared.\n", encoding="utf-8")


def main() -> None:
    unpack_runtime()
    print(f"Prepared Windows Python runtime at {RUNTIME}")


if __name__ == "__main__":
    main()
