"""Exercise the test suite's temporary-root policy through real pytest runs."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_CONFTEST = Path(__file__).resolve().parents[1] / "conftest.py"


def _probe_root(
    directory: Path, *, basetemp: Path | None = None, temporary_parent: Path | None = None
) -> Path:
    directory.mkdir()
    (directory / "conftest.py").write_bytes(PROJECT_CONFTEST.read_bytes())
    (directory / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (directory / "test_probe.py").write_text(
        "import json, os\n"
        "from pathlib import Path\n"
        "def test_observe(tmp_path_factory):\n"
        "    root = tmp_path_factory.getbasetemp()\n"
        "    (root / 'owned.txt').write_text('owned', encoding='utf-8')\n"
        "    Path(os.environ['AIFLOW_TEMP_PROBE']).write_text(\n"
        "        json.dumps(str(root)), encoding='utf-8')\n",
        encoding="utf-8",
    )
    scratch = temporary_parent if temporary_parent is not None else directory / "environment"
    scratch.mkdir(exist_ok=True)
    legacy = directory / "legacy-numbered"
    legacy.mkdir()
    report = directory / "observed.json"
    environment = {key: os.environ[key] for key in ("PATH", "SystemRoot") if key in os.environ}
    environment.update(
        TEMP=str(scratch),
        TMP=str(scratch),
        TMPDIR=str(scratch),
        PYTEST_DEBUG_TEMPROOT=str(legacy),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1",
        AIFLOW_TEMP_PROBE=str(report),
    )
    arguments = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "-c",
        str(directory / "pytest.ini"),
        "--confcutdir",
        str(directory),
    ]
    if basetemp is not None:
        arguments.extend(["--basetemp", str(basetemp)])
    result = subprocess.run(
        [*arguments, str(directory / "test_probe.py")],
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    root = Path(json.loads(report.read_text(encoding="utf-8")))
    assert (root / "owned.txt").read_text(encoding="utf-8") == "owned"
    return root


def test_default_runs_get_distinct_owned_roots_outside_numbered_pool(tmp_path: Path) -> None:
    scratch = tmp_path / "environment"
    first = _probe_root(tmp_path / "first", temporary_parent=scratch)
    second = _probe_root(tmp_path / "second", temporary_parent=scratch)
    assert first != second
    for root, run in ((first, "first"), (second, "second")):
        assert root.parent == scratch.resolve()
        assert root.name.startswith("aiflow-pytest-")
        assert len(root.name) < 40
        assert not list((tmp_path / run / "legacy-numbered").iterdir())


def test_explicit_basetemp_is_preserved(tmp_path: Path) -> None:
    chosen = tmp_path / "explicit-root"
    observed = _probe_root(tmp_path / "run", basetemp=chosen)
    assert observed == chosen.resolve()
    assert not list((tmp_path / "run" / "environment").iterdir())
    assert not list((tmp_path / "run" / "legacy-numbered").iterdir())


def test_temp_root_creation_failure_does_not_fall_back(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = importlib.util.spec_from_file_location("isolated_project_conftest", PROJECT_CONFTEST)
    assert spec is not None and spec.loader is not None
    conftest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conftest)
    calls = 0

    def unavailable(**_kwargs: object) -> str:
        nonlocal calls
        calls += 1
        raise OSError("temporary directory unavailable")

    monkeypatch.setattr(conftest.tempfile, "mkdtemp", unavailable)
    config = SimpleNamespace(option=SimpleNamespace(basetemp=None))
    with pytest.raises(pytest.UsageError, match="Could not create an isolated test temporary root"):
        conftest.pytest_configure(config)
    assert calls == 1
    assert config.option.basetemp is None
