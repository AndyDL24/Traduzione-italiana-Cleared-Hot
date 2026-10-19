# -*- coding: utf-8 -*-
"""Crea lo ZIP Nexus-ready della mod Cleared Hot IT."""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
PARENT = ROOT.parent  # Traduttore_CSV_XML_Portable


def read_version() -> str:
    vf = ROOT / "VERSION.txt"
    if vf.is_file():
        return vf.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    return "1.0.0"


def sync_translation() -> Path:
    """Copia l'ultima traduzione dal progetto padre se presente."""
    src_candidates = [
        PARENT / "fr-resources.assets-329.txt",
        ROOT / "data" / "it-fr-resources.txt",
    ]
    dest = ROOT / "data" / "it-fr-resources.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    for src in src_candidates:
        if src.is_file() and src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
            print(f"Traduzione aggiornata da: {src.name}")
            return dest
    if not dest.is_file():
        raise SystemExit("Manca data/it-fr-resources.txt — metti il TXT italiano in data/")
    return dest


INCLUDE = [
    "README.md",
    "CHANGELOG.md",
    "VERSION.txt",
    "requirements.txt",
    "Installa_Traduzione.bat",
    "Crea_pacchetto_Nexus.bat",
    "data/it-fr-resources.txt",
    "tools/injector_core.py",
    "tools/injector_gui.py",
    "tools/packager.py",
]


def build_zip(version: str | None = None) -> Path:
    version = version or read_version()
    sync_translation()

    dist = ROOT / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    folder_name = f"ClearedHot_Italian_Translation_v{version}"
    out = dist / f"{folder_name}.zip"
    if out.exists():
        out.unlink()

    missing = [rel for rel in INCLUDE if not (ROOT / rel).is_file()]
    if missing:
        raise SystemExit("File mancanti:\n  " + "\n  ".join(missing))

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE:
            arc = f"{folder_name}/{rel.replace(chr(92), '/')}"
            zf.write(ROOT / rel, arcname=arc)
        # nota release
        note = (
            f"Cleared Hot — Traduzione Italiana v{version}\n"
            f"Build: {date.today().isoformat()}\n"
            f"Slot lingua: Francese → Italiano\n"
        )
        zf.writestr(f"{folder_name}/RELEASE.txt", note)

    print(f"Creato: {out}")
    print(f"Dimensione: {out.stat().st_size / 1024:.1f} KB")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Packager Nexus Cleared Hot IT")
    parser.add_argument("--version", help="Override versione (default VERSION.txt)")
    args = parser.parse_args(argv)
    build_zip(args.version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
