"""PersonaSpec: parsed from persona prompt markdown frontmatter."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PersonaSpec:
    """Specification for a reader persona, parsed from markdown frontmatter."""
    name: str
    display_name: str
    scoring_dimensions: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    weight: float = 1.0
    version: str = "v1"
    system_prompt: str = ""


def parse_persona_file(path: Path) -> PersonaSpec:
    """Parse a persona prompt markdown file with YAML frontmatter.

    Expected format:
        ---
        name: reader_fast_food
        display_name: 快餐读者
        scoring_dimensions: [pacing, hook_strength, shuang_release, retention_to_next]
        red_flags:
          - 大段心理描写超过 3 段
        weight: 1.0
        ---

        System prompt text here...
    """
    text = path.read_text(encoding="utf-8")
    return parse_persona_text(text, path.stem)


def parse_persona_text(text: str, fallback_name: str = "unknown") -> PersonaSpec:
    """Parse persona spec from markdown text with frontmatter."""
    name = fallback_name
    display_name = fallback_name
    scoring_dimensions: list[str] = []
    red_flags: list[str] = []
    weight = 1.0
    version = "v1"
    system_prompt = ""

    # Parse frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if fm_match:
        frontmatter = fm_match.group(1)
        system_prompt = fm_match.group(2).strip()

        lines = frontmatter.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            i += 1
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()

                if key == "name":
                    name = value
                elif key == "display_name":
                    display_name = value
                elif key == "weight":
                    try:
                        weight = float(value)
                    except ValueError:
                        pass
                elif key == "version":
                    version = value
                elif key == "scoring_dimensions":
                    scoring_dimensions = _parse_list_value(value)
                elif key == "red_flags":
                    if value:
                        # Inline list
                        red_flags = _parse_list_value(value)
                    else:
                        # Multi-line list: collect following "- " lines
                        red_flags = []
                        while i < len(lines):
                            next_line = lines[i].strip()
                            if next_line.startswith("- "):
                                red_flags.append(next_line[2:].strip())
                                i += 1
                            else:
                                break
    else:
        system_prompt = text.strip()

    return PersonaSpec(
        name=name,
        display_name=display_name,
        scoring_dimensions=scoring_dimensions,
        red_flags=red_flags,
        weight=weight,
        version=version,
        system_prompt=system_prompt,
    )


def _parse_list_value(value: str) -> list[str]:
    """Parse a YAML list value like '[a, b, c]' or 'a, b, c'."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [item.strip().strip('"').strip("'") for item in value.split(",") if item.strip()]
