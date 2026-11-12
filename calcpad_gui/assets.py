"""Locate existing project logos; never create or overwrite user assets."""
from pathlib import Path


def find_logo() -> Path | None:
    """Prefer SVG then PNG in project, legacy parent and package assets."""
    package = Path(__file__).resolve().parent
    for directory in (package.parent / "assets", package.parent.parent / "assets", package / "assets"):
        for name in ("calcpadce-logo.svg", "calcpadce-logo.png"):
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None
