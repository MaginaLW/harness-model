"""Contract tests enforcing module import boundaries and public interfaces."""

import ast
import subprocess
import sys
from pathlib import Path

HEAVY_MODULES = {
    "aiflow.node_execution",
    "aiflow.node_verification",
    "aiflow.installed_mutations",
    "aiflow.installed_probe",
}

FORBIDDEN_STEMS = {
    "node_execution",
    "node_verification",
    "installed_mutations",
    "installed_probe",
}

# The internal mutual authorization handshake between mutation_evidence and
# mutation_runner is tested in test_mutation_runner.py:192 and forms a closed companion pair.
MUTUAL_COMPANION_PAIRS = {
    ("mutation_evidence.py", "mutation_runner"),
    ("mutation_runner.py", "mutation_evidence"),
}


def test_core_modules_do_not_import_heavy_modules() -> None:
    """Verify that importing core modules does not pull heavy modules into sys.modules."""
    src_dir = Path(__file__).resolve().parents[2] / "src" / "aiflow"
    modules_to_test = sorted(
        [
            f"aiflow.{p.stem}"
            for p in src_dir.glob("*.py")
            if p.stem not in FORBIDDEN_STEMS
            and not p.name.startswith("installed_")
            and not p.name.startswith("node_")
            and p.name not in {"__init__.py", "__main__.py"}
        ]
    )
    code = f"""
import sys
for mod in {modules_to_test!r}:
    __import__(mod)
heavy = {HEAVY_MODULES!r}
leaked = heavy.intersection(sys.modules.keys())
if leaked:
    print(f"Leaked heavy modules: {{leaked}}", file=sys.stderr)
    sys.exit(1)
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"Import boundary breach: {result.stderr}"


def test_no_top_level_heavy_imports_in_core_ast() -> None:
    """Statically verify via AST that no core module has top-level imports of heavy modules."""
    src_dir = Path(__file__).resolve().parents[2] / "src" / "aiflow"
    core_files = [
        f
        for f in src_dir.glob("*.py")
        if f.stem not in FORBIDDEN_STEMS
        and not f.name.startswith("installed_")
        and not f.name.startswith("node_")
    ]

    for py_file in core_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in tree.body:  # Only check top-level statements
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    mod_tail = node.module.split(".")[-1]
                    assert mod_tail not in FORBIDDEN_STEMS, (
                        f"Forbidden top-level import in {py_file.name}:{node.lineno}: "
                        f"from {node.module} import ..."
                    )
                for alias in node.names:
                    assert alias.name not in FORBIDDEN_STEMS, (
                        f"Forbidden top-level import in {py_file.name}:{node.lineno}: "
                        f"from {node.module} import {alias.name}"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    mod_tail = alias.name.split(".")[-1]
                    assert mod_tail not in FORBIDDEN_STEMS, (
                        f"Forbidden top-level import in {py_file.name}:{node.lineno}: "
                        f"import {alias.name}"
                    )


def test_no_cross_module_private_imports() -> None:
    """Verify that no aiflow module imports private symbols from another aiflow module."""
    src_dir = Path(__file__).resolve().parents[2] / "src" / "aiflow"
    for py_file in src_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (
                (node.module and node.module.startswith("aiflow")) or node.level > 0
            ):
                target_stem = node.module.split(".")[-1] if node.module else ""
                if (py_file.name, target_stem) in MUTUAL_COMPANION_PAIRS:
                    continue
                for alias in node.names:
                    assert not (alias.name.startswith("_") and not alias.name.startswith("__")), (
                        f"Private symbol import in {py_file.name}:{node.lineno}: "
                        f"from {node.module or '.'} import {alias.name}"
                    )
