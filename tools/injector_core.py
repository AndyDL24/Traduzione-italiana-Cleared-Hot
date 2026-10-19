# -*- coding: utf-8 -*-
"""Core: trova Cleared Hot, backup, inject IT nello slot FR, verify, restore."""

from __future__ import annotations

import re
import shutil
import winreg
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

LogFn = Callable[[str], None]

ASSET_NAME = "resources.assets"
TEXTASSET_SLOT = "fr"
BACKUP_SUFFIX = ".clearedhot_it_backup"
VERSION_MARKER = "CAMBIA ELICOTTERO"
PLAY_IT = '"MAINMENU_PLAY_BUTTON" = "Giocare"'
PLAY_FR = '"MAINMENU_PLAY_BUTTON" = "Jouer"'


@dataclass
class InjectResult:
    ok: bool
    message: str
    assets_path: Optional[Path] = None
    backup_path: Optional[Path] = None


def _log(log: Optional[LogFn], msg: str) -> None:
    if log:
        log(msg)


def mod_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_translation_path() -> Path:
    return mod_root() / "data" / "it-fr-resources.txt"


def normalize_unity_text(text: str) -> str:
    """Unity TextAsset di Cleared Hot usa CRLF."""
    text = text.lstrip("\ufeff")
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


def find_steam_libraries() -> list[Path]:
    roots: list[Path] = []
    for hive, sub in (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
    ):
        try:
            with winreg.OpenKey(hive, sub) as key:
                steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
                p = Path(str(steam_path))
                if p.is_dir():
                    roots.append(p)
        except OSError:
            pass

    libs: list[Path] = []
    seen: set[str] = set()
    for steam in roots:
        candidates = [
            steam / "steamapps",
            steam / "SteamApps",
        ]
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        if not vdf.exists():
            vdf = steam / "SteamApps" / "libraryfolders.vdf"
        if vdf.exists():
            raw = vdf.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r'"path"\s+"([^"]+)"', raw, re.I):
                candidates.append(Path(m.group(1).replace("\\\\", "\\")) / "steamapps")
        for c in candidates:
            key = str(c.resolve()) if c.exists() else str(c)
            if key in seen:
                continue
            seen.add(key)
            if c.is_dir():
                libs.append(c)
    return libs


def find_game_data_dir(manual: Optional[Path] = None) -> Optional[Path]:
    """Ritorna cartella ClearedHot_Data oppure None."""
    if manual:
        p = Path(manual)
        if (p / ASSET_NAME).is_file():
            return p
        if (p / "ClearedHot_Data" / ASSET_NAME).is_file():
            return p / "ClearedHot_Data"
        if p.name.lower() == "clearedhot" and (p / "ClearedHot_Data" / ASSET_NAME).is_file():
            return p / "ClearedHot_Data"
        return None

    for lib in find_steam_libraries():
        candidate = lib / "common" / "ClearedHot" / "ClearedHot_Data"
        if (candidate / ASSET_NAME).is_file():
            return candidate

    for guess in (
        Path(r"D:\SteamLibrary\steamapps\common\ClearedHot\ClearedHot_Data"),
        Path(r"C:\Program Files (x86)\Steam\steamapps\common\ClearedHot\ClearedHot_Data"),
        Path(r"C:\Program Files\Steam\steamapps\common\ClearedHot\ClearedHot_Data"),
    ):
        if (guess / ASSET_NAME).is_file():
            return guess
    return None


def backup_path_for(assets: Path) -> Path:
    return assets.with_name(assets.name + BACKUP_SUFFIX)


def ensure_backup(assets: Path, log: Optional[LogFn] = None) -> Path:
    bak = backup_path_for(assets)
    if bak.exists():
        _log(log, f"Backup già presente: {bak.name}")
        return bak
    shutil.copy2(assets, bak)
    _log(log, f"Backup creato: {bak.name}")
    return bak


def restore_backup(assets: Path, log: Optional[LogFn] = None) -> InjectResult:
    bak = backup_path_for(assets)
    if not bak.is_file():
        return InjectResult(False, f"Nessun backup trovato: {bak.name}", assets, bak)
    shutil.copy2(bak, assets)
    _log(log, "Ripristinato resources.assets dal backup.")
    return InjectResult(True, "Ripristino completato.", assets, bak)


def _load_unitypy():
    try:
        import UnityPy
        from UnityPy.enums import ClassIDType
    except ImportError as e:
        raise RuntimeError(
            "Manca UnityPy. Installa con: pip install UnityPy"
        ) from e
    return UnityPy, ClassIDType


def inject_italian(
    assets_path: Path,
    translation_path: Path,
    *,
    rename_fr_label: bool = True,
    log: Optional[LogFn] = None,
) -> InjectResult:
    UnityPy, ClassIDType = _load_unitypy()

    if not assets_path.is_file():
        return InjectResult(False, f"File assets non trovato: {assets_path}")
    if not translation_path.is_file():
        return InjectResult(False, f"Traduzione non trovata: {translation_path}")

    text = normalize_unity_text(translation_path.read_text(encoding="utf-8-sig"))
    if VERSION_MARKER not in text and "Giocare" not in text:
        _log(log, "Avviso: il TXT non sembra italiano (marker hangar/menu assenti).")

    bak = ensure_backup(assets_path, log)
    _log(log, f"Carico {assets_path.name} …")
    env = UnityPy.load(str(assets_path))

    fr_obj = None
    lang_obj = None
    for obj in env.objects:
        if obj.type != ClassIDType.TextAsset:
            continue
        data = obj.read()
        name = data.m_Name or ""
        if name == TEXTASSET_SLOT:
            fr_obj = (obj, data)
        elif name == "LanguageNames":
            lang_obj = (obj, data)

    if fr_obj is None:
        return InjectResult(False, "TextAsset 'fr' non trovato in resources.assets.", assets_path, bak)

    obj, data = fr_obj
    old_len = len(data.m_Script or "")
    data.m_Script = text
    data.save()
    _log(log, f"Slot '{TEXTASSET_SLOT}' (path_id={obj.path_id}): {old_len} -> {len(text)} byte")

    if rename_fr_label and lang_obj is not None:
        _, ldata = lang_obj
        script = ldata.m_Script or ""
        new_script, n = re.subn(
            r'("LANGUAGE_FR_NAME"\s*=\s*")[^"]*(")',
            r'\1Italiano\2',
            script,
            count=1,
        )
        if n:
            ldata.m_Script = new_script
            ldata.save()
            _log(log, "Etichetta menu: Francais -> Italiano")
        else:
            _log(log, "LanguageNames: LANGUAGE_FR_NAME non trovato, salto rename.")

    blob = env.file.save()
    assets_path.write_bytes(blob)
    _log(log, f"Scritto {assets_path.name} ({len(blob)} byte)")

    verify = verify_injection(assets_path, log=log)
    if not verify.ok:
        return InjectResult(False, verify.message, assets_path, bak)
    return InjectResult(True, "Iniezione completata e verificata.", assets_path, bak)


def verify_injection(assets_path: Path, log: Optional[LogFn] = None) -> InjectResult:
    UnityPy, ClassIDType = _load_unitypy()
    env = UnityPy.load(str(assets_path))
    fr_script = None
    label = None
    failed = 0
    for obj in env.objects:
        if obj.type != ClassIDType.TextAsset:
            continue
        try:
            data = obj.read()
        except Exception:
            failed += 1
            continue
        if data.m_Name == TEXTASSET_SLOT:
            fr_script = data.m_Script or ""
        elif data.m_Name == "LanguageNames":
            label = data.m_Script or ""

    if failed:
        return InjectResult(False, f"Verify fallita: {failed} TextAsset illeggibili.", assets_path)
    if fr_script is None:
        return InjectResult(False, "Verify: slot 'fr' assente.", assets_path)

    checks = []
    if VERSION_MARKER in fr_script:
        checks.append("hangar IT ok")
    else:
        return InjectResult(False, f"Verify: manca marker '{VERSION_MARKER}' nello slot fr.", assets_path)
    if PLAY_IT in fr_script or "Giocare" in fr_script:
        checks.append("menu IT ok")
    if PLAY_FR in fr_script:
        _log(log, "Avviso: residuo 'Jouer' ancora presente nello slot fr.")
    if label and "Italiano" in label:
        checks.append("etichetta Italiano")
    _log(log, "Verify: " + ", ".join(checks))
    return InjectResult(True, "Verifica OK.", assets_path)


def status_summary(assets_path: Path) -> str:
    try:
        UnityPy, ClassIDType = _load_unitypy()
    except RuntimeError as e:
        return str(e)
    if not assets_path.is_file():
        return "resources.assets non trovato."
    env = UnityPy.load(str(assets_path))
    for obj in env.objects:
        if obj.type != ClassIDType.TextAsset:
            continue
        data = obj.read()
        if data.m_Name != TEXTASSET_SLOT:
            continue
        s = data.m_Script or ""
        if VERSION_MARKER in s or "Giocare" in s:
            return "Stato: italiano già installato nello slot Francese."
        if "Jouer" in s or "CHANGER" in s:
            return "Stato: francese originale (traduzione non installata)."
        return "Stato: slot fr presente, lingua non riconosciuta."
    return "Stato: TextAsset 'fr' non trovato."
