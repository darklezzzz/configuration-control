"""Two baselines tied to actual source commits, drift report and check history."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from configuration_control.core import compare, create_baseline

out = Path(__file__).parent


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    source = root / "project"
    source.mkdir()
    (source / "app.py").write_text("value = 1\n")
    (source / "old.txt").write_text("remove me")
    git(source, "init", "-b", "main")
    git(source, "config", "user.name", "Baseline demonstration")
    git(source, "config", "user.email", "demo@example.invalid")
    git(source, "add", ".")
    git(source, "commit", "-m", "Create source configuration BL-001")
    first = root / "baselines" / "BL-001.json"
    create_baseline(source, first, "BL-001", "Reviewer", git(source, "rev-parse", "HEAD"))
    (source / "app.py").write_text("value = 2\n")
    (source / "old.txt").unlink()
    (source / "README.md").write_text("New documentation")
    result = compare(source, first, root / "checks.jsonl", root / "differences.json")
    git(source, "add", ".")
    git(source, "commit", "-m", "Prepare source configuration BL-002")
    second = first.parent / "BL-002.json"
    create_baseline(source, second, "BL-002", "Reviewer", git(source, "rev-parse", "HEAD"), first)
    for path in (first, second, root / "checks.jsonl", root / "differences.json"):
        shutil.copyfile(path, out / path.name)
    git(source, "bundle", "create", str(out / "demo-history.bundle"), "--all")
    print(result)
