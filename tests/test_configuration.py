import pytest
from configuration_control.core import compare, create_baseline, read_baseline, scan


@pytest.fixture
def sample(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "a.txt").write_text("alpha")
    snap = tmp_path / "baselines" / "BL-001.json"
    create_baseline(root, snap, "BL-001", "Reviewer", "a" * 40)
    return root, snap


def test_empty(tmp_path):
    assert scan(tmp_path) == {}


def test_identification(sample):
    root, snap = sample
    item = read_baseline(snap)["items"]["a.txt"]
    assert item["size"] == 5 and len(item["sha256"]) == 64 and item["id"]
    assert compare(root, snap)["changed"] == []


def test_changed_same_size(sample):
    root, snap = sample
    (root / "a.txt").write_text("bravo")
    assert compare(root, snap)["changed"] == ["a.txt"]


def test_added_removed(sample):
    root, snap = sample
    (root / "a.txt").unlink()
    (root / "b.txt").write_text("new")
    report = compare(root, snap)
    assert report["added"] == ["b.txt"] and report["removed"] == ["a.txt"]


def test_exclusions(tmp_path):
    for name in (".git", "__pycache__", "venv", ".venv", "private"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "file").write_text("ignore")
    assert scan(tmp_path, ["private"]) == {}


def test_missing_baseline(tmp_path):
    with pytest.raises(ValueError):
        compare(tmp_path, tmp_path / "missing")


def test_corrupt_baseline(tmp_path):
    path = tmp_path / "bad"
    path.write_text("{")
    with pytest.raises(ValueError):
        read_baseline(path)


def test_snapshot_excluded(tmp_path):
    snap = tmp_path / "metadata" / "BL-001.json"
    create_baseline(tmp_path, snap, "BL-001", "Reviewer", "b" * 40)
    assert read_baseline(snap)["items"] == {}
    assert compare(tmp_path, snap)["added"] == []


def test_immutable(sample):
    root, snap = sample
    original = snap.read_bytes()
    with pytest.raises(ValueError):
        create_baseline(root, snap, "BL-002", "Reviewer", "b" * 40)
    assert snap.read_bytes() == original


def test_baseline_chain(sample):
    root, snap = sample
    second = snap.parent / "BL-002.json"
    assert (
        create_baseline(root, second, "BL-002", "Reviewer", "b" * 40, snap)["previous"] == "BL-001"
    )
    with pytest.raises(ValueError):
        create_baseline(root, snap.parent / "dup.json", "BL-002", "Reviewer", "b" * 40)


def test_history(sample, tmp_path):
    root, snap = sample
    history = root / "checks.jsonl"
    compare(root, snap, history=history)
    assert compare(root, snap, history=history)["added"] == []
    assert len(history.read_text().splitlines()) == 2


def test_changed_unit_increments_version(sample):
    root, snap = sample
    (root / "a.txt").write_text("updated")
    second = create_baseline(
        root, snap.parent / "BL-002.json", "BL-002", "Reviewer", "b" * 40, snap
    )
    assert second["items"]["a.txt"]["version"] == "1.0.1"
    assert second["items"]["a.txt"]["id"] == read_baseline(snap)["items"]["a.txt"]["id"]
