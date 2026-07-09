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


def test_wheel_config_ships_all_first_party_code():
    """Regression: the wheel once omitted translate/ and main.py, so the
    installed anki-chinese entry point failed with ImportError (masked
    locally by uv's editable install)."""
    tomllib = pytest.importorskip("tomllib")  # Python 3.11+

    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    wheel = config["tool"]["hatch"]["build"]["targets"]["wheel"]
    included = set(
        wheel.get("only-include", [])
        + wheel.get("packages", [])
        + wheel.get("include", [])
    )

    # Every top-level package (dir with __init__.py) except tests must ship.
    packages = {
        d.name
        for d in REPO_ROOT.iterdir()
        if d.is_dir() and (d / "__init__.py").exists() and d.name != "tests"
    }
    missing = packages - included
    assert not missing, f"packages missing from wheel config: {sorted(missing)}"

    # Modules referenced by console-script entry points must ship too.
    for script in config["project"].get("scripts", {}).values():
        module = script.split(":")[0]
        assert module in included or f"{module}.py" in included, (
            f"entry-point module '{module}' not included in wheel"
        )
