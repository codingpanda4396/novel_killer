"""Loader: discover and load persona prompt files."""

from __future__ import annotations

from pathlib import Path

from .persona import PersonaSpec, parse_persona_file

# Default location for persona prompts
_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts" / "readers"


def load_all_personas(prompts_dir: Path | None = None) -> list[PersonaSpec]:
    """Load all persona prompt files from the prompts/readers directory."""
    directory = prompts_dir or _PROMPTS_DIR
    if not directory.is_dir():
        return []

    personas: list[PersonaSpec] = []
    for path in sorted(directory.glob("*.md")):
        try:
            spec = parse_persona_file(path)
            personas.append(spec)
        except Exception:
            continue
    return personas


def load_persona(name: str, prompts_dir: Path | None = None) -> PersonaSpec | None:
    """Load a specific persona by name."""
    directory = prompts_dir or _PROMPTS_DIR
    path = directory / f"{name}.md"
    if not path.is_file():
        return None
    return parse_persona_file(path)
