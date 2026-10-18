"""Stage a root-layout integration under its HA domain for CI validation."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> None:
    """Create an isolated test project without changing release packaging."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    destination = args.destination.resolve()
    if destination == source or source in destination.parents:
        parser.error("destination must be outside the repository")
    if destination.exists():
        parser.error("destination must not already exist")

    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    domain = manifest["domain"]
    integration = destination / "custom_components" / domain
    integration.mkdir(parents=True)
    for path in sorted(source.glob("*.py")):
        shutil.copy2(path, integration / path.name)
    for filename in ("manifest.json", "strings.json"):
        shutil.copy2(source / filename, integration / filename)
    for dirname in ("translations", "brand"):
        shutil.copytree(source / dirname, integration / dirname)
    shutil.copytree(
        source / "tests",
        destination / "tests",
        ignore=shutil.ignore_patterns("__pycache__", "*.py[co]", ".pytest_cache"),
    )
    shutil.copy2(source / "pyproject.toml", destination / "pyproject.toml")
    print(f"Prepared checks in {destination}")


if __name__ == "__main__":
    main()
