from __future__ import annotations

from typing import Any

from skill_composer.models import ExtractedSkill, RawSkill
from skill_composer.utils import LLMClient


class Extractor:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def extract(self, raw_skill: RawSkill) -> ExtractedSkill:
        system_prompt = (
            "You are an information extraction engine for agent skills. "
            "Return strict JSON only."
        )
        user_prompt = f"""
Task: Extract structured fields from the skill markdown.

skill_id: {raw_skill.skill_id}

Required JSON schema:
{{
  "applicable_scenarios": ["..."],
  "core_steps": ["..."],
  "constraints": ["..."],
  "examples": [{{"input": "...", "output": "..."}}],
  "dependencies": ["..."]
}}

Rules:
1. If missing, return [].
2. Keep `core_steps` in execution order.
3. Output JSON object only.

SKILL CONTENT:
{raw_skill.content}
        """.strip()
        data = self.llm.call_json(system_prompt, user_prompt)
        return ExtractedSkill(
            skill_id=raw_skill.skill_id,
            applicable_scenarios=_to_str_list(data.get("applicable_scenarios")),
            core_steps=_to_str_list(data.get("core_steps")),
            constraints=_to_str_list(data.get("constraints")),
            examples=_to_example_list(data.get("examples")),
            dependencies=_to_str_list(data.get("dependencies")),
        )


def _to_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned:
                result.append(cleaned)
    return result


def _to_example_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    examples: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            examples.append(item)
    return examples
