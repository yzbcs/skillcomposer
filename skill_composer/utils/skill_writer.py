from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skill_composer.models import SynthesizedSkill


def render_skill_markdown(
    *,
    name: str,
    description: str,
    core_steps: list[str],
    constraints: list[str],
    dependencies: list[str],
    examples: list[dict[str, Any]],
) -> str:
    lines: list[str] = [
        "---",
        f"name: {name}",
        f"description: {description}",
        "---",
        "## Steps",
    ]
    if core_steps:
        lines.extend([f"{idx}. {step}" for idx, step in enumerate(core_steps, start=1)])
    else:
        lines.append("- N/A")

    lines.append("## Constraints")
    if constraints:
        lines.extend([f"- {item}" for item in constraints])
    else:
        lines.append("- N/A")

    lines.append("## Dependencies")
    if dependencies:
        lines.extend([f"- {item}" for item in dependencies])
    else:
        lines.append("- N/A")

    lines.append("## Examples")
    if examples:
        for idx, example in enumerate(examples[:2], start=1):
            example_text = json.dumps(example, ensure_ascii=False)
            lines.append(f"- Example {idx}: {example_text}")
    else:
        lines.append("- N/A")

    return "\n".join(lines).strip() + "\n"


def write_synthesized_skill(synthesized: SynthesizedSkill, output_path: str) -> str:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(synthesized.content, encoding="utf-8")
    return str(out.resolve())
