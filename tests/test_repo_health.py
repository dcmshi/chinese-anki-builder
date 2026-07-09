"""Repo-wide health checks.

Regression net for defects that individual unit tests won't catch, e.g. a
syntax error in a script that no test imports (analyze_coverage.py once
shipped with an unterminated string literal).
"""

import py_compile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories containing first-party Python code (skips .venv, data, output).
SOURCE_DIRS = ["extract", "process", "translate", "anki", "tts", "utils", "tests"]


def _all_python_files():
    files = list(REPO_ROOT.glob("*.py"))
    for d in SOURCE_DIRS:
        files.extend((REPO_ROOT / d).rglob("*.py"))
    return sorted(files)


@pytest.mark.parametrize(
    "path", _all_python_files(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_python_file_compiles(path):
    """Every first-party Python file must at least be syntactically valid."""
    py_compile.compile(str(path), doraise=True)
