#!/usr/bin/env python3
"""Print PATH / cwd diagnostics (run from repo root: python3 scripts/check_toolchain.py)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def main() -> int:
    cwd = Path.cwd()
    looks_inner = (cwd / "__init__.py").is_file() and (cwd / "models").is_dir() and not (cwd / "pyproject.toml").is_file()
    data = {
        "cwd": str(cwd),
        "which_python": shutil.which("python"),
        "which_python3": shutil.which("python3"),
        "which_pip": shutil.which("pip"),
        "which_pip3": shutil.which("pip3"),
        "pyproject_in_cwd": (cwd / "pyproject.toml").is_file(),
        "looks_like_inner_package_only": looks_inner,
    }
    print(json.dumps(data, indent=2))
    if looks_inner:
        print(
            "\nWarning: cwd looks like the inner `ren_econ` Python package (no pyproject.toml here). "
            "cd to the repository root (the directory that contains pyproject.toml).",
            file=sys.stderr,
        )
        return 1
    if not data["pyproject_in_cwd"]:
        print("\nWarning: pyproject.toml not in cwd — run from repository root.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
