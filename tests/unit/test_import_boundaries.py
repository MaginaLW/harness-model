"""Public imports and lazy loading at the ordinary core module boundary."""

import ast
import subprocess
import sys
from pathlib import Path


def test_core_imports_do_not_load_optional_node_modules() -> None:
    script = """
import importlib
import pkgutil
import sys

import aiflow

for module in pkgutil.iter_modules(aiflow.__path__):
    if module.name != "__main__" and not module.name.startswith(("node_", "installed_")):
        importlib.import_module(f"aiflow.{module.name}")
optional = ("aiflow.node_", "aiflow.installed_")
loaded = sorted(name for name in sys.modules if name.startswith(optional))
assert not loaded, loaded
"""
    subprocess.run([sys.executable, "-c", script], check=True, timeout=30)


def test_shared_imports_use_public_symbols() -> None:
    companions = {
        ("mutation_evidence", "aiflow.mutation_runner", "_issue_runner_authorization"),
        (
            "mutation_runner",
            "aiflow.mutation_evidence",
            "_authorize_targeted_mutation_runner_launch",
        ),
    }
    root = Path(__file__).resolve().parents[2] / "src/aiflow"
    for source in root.glob("*.py"):
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ImportFrom):
                continue
            module = node.module or ""
            if node.level or module == "aiflow" or module.startswith("aiflow."):
                for name in node.names:
                    if name.name.startswith("_") and not name.name.startswith("__"):
                        assert (source.stem, module, name.name) in companions
