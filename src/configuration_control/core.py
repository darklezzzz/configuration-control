"""Filesystem baseline identification, immutable snapshots and audit history."""

import fnmatch
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_EXCLUDES = {".git", "__pycache__", "venv", ".venv", ".pytest_cache", ".ruff_cache"}


def scan(directory, excludes=()):
    root = Path(directory).resolve()
    if not root.is_dir():
        raise ValueError("Каталог не найден")
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_symlink() or any(part in DEFAULT_EXCLUDES for part in relative.parts):
            continue
        if any(
            fnmatch.fnmatch(relative.as_posix(), pattern)
            or relative.as_posix().startswith(pattern.rstrip("/") + "/")
            for pattern in excludes
        ):
            continue
        if path.is_file():
            content = path.read_bytes()
            result[relative.as_posix()] = {
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
    return result


def read_baseline(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("items"), dict)
            or not value.get("id")
            or not isinstance(value.get("excludes"), list)
        ):
            raise ValueError("Неверная структура baseline")
        for name, item in value["items"].items():
            if not isinstance(name, str) or not isinstance(item, dict) or "sha256" not in item:
                raise ValueError("Неверная конфигурационная единица")
        return value
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Baseline отсутствует или повреждена") from exc


def create_baseline(directory, snapshot, ident, approver, commit_hash, previous=None, excludes=()):
    if not all(isinstance(v, str) and v.strip() for v in (ident, approver, commit_hash)):
        raise ValueError("ID, утверждающий и Git commit hash обязательны")
    import re

    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit_hash):
        raise ValueError("Нужен полный SHA Git-коммита")
    root, target = Path(directory).resolve(), Path(snapshot).resolve()
    prior = read_baseline(previous) if previous else None
    if prior and prior["id"] == ident:
        raise ValueError("Новой baseline нужен уникальный ID")
    for sibling in target.parent.glob("*.json"):
        try:
            existing = json.loads(sibling.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(existing, dict) and existing.get("id") == ident:
            raise ValueError("ID baseline уже зарегистрирован")
    ignore = list(excludes)
    # Snapshot storage is configuration metadata, not a managed source tree.
    if target.is_relative_to(root):
        if target.parent != root:
            ignore.append(target.parent.relative_to(root).as_posix())
        else:
            ignore.append(target.relative_to(root).as_posix())
    if previous and Path(previous).resolve().is_relative_to(root):
        ignore.append(Path(previous).resolve().relative_to(root).as_posix())
    files = scan(root, ignore)
    items = {}
    for name, data in files.items():
        old = prior["items"].get(name) if prior else None
        version = old.get("version", "1.0.0") if old else "1.0.0"
        if old and old["sha256"] != data["sha256"]:
            major, minor, patch = map(int, version.split("."))
            version = f"{major}.{minor}.{patch + 1}"
        items[name] = dict(
            data, id="CI-" + hashlib.sha256(name.encode()).hexdigest()[:12], version=version
        )
    value = {
        "id": ident,
        "date": datetime.now(timezone.utc).isoformat(),
        "approver": approver,
        "commit_hash": commit_hash,
        "previous": prior["id"] if prior else None,
        "excludes": ignore,
        "items": items,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
    except FileExistsError as exc:
        raise ValueError("Утверждённую baseline нельзя перезаписывать") from exc
    return value


def compare(directory, snapshot, history=None, report=None):
    baseline = read_baseline(snapshot)
    ignore = list(baseline["excludes"])
    root = Path(directory).resolve()
    for output in (history, report):
        if output and Path(output).resolve().is_relative_to(root):
            ignore.append(Path(output).resolve().relative_to(root).as_posix())
    current, old = scan(root, ignore), baseline["items"]
    result = {
        "baseline": baseline["id"],
        "date": datetime.now(timezone.utc).isoformat(),
        "added": sorted(current.keys() - old.keys()),
        "removed": sorted(old.keys() - current.keys()),
        "changed": sorted(
            k for k in current.keys() & old.keys() if current[k]["sha256"] != old[k]["sha256"]
        ),
    }
    if report:
        Path(report).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if history:
        with Path(history).open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
    return result
