from __future__ import annotations

import json
from typing import Any

from skill_composer.models import ExtractedSkill, SelectedSkill
from skill_composer.utils import LLMClient


class Selector:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def select(self, extracted: ExtractedSkill, task_query: str) -> SelectedSkill:
        indexed_payload = {
            "applicable_scenarios": _to_indexed(extracted.applicable_scenarios),
            "core_steps": _to_indexed(extracted.core_steps),
            "constraints": _to_indexed(extracted.constraints),
            "examples": _to_indexed(extracted.examples),
            "dependencies": _to_indexed(extracted.dependencies),
        }
        payload_json = json.dumps(indexed_payload, ensure_ascii=False, indent=2)

        system_prompt = (
            "You are a relevance filter for skills. "
            "Decide item-level keep/drop for a given task. Return strict JSON."
        )
        user_prompt = f"""
Task query:
{task_query}

Skill ID: {extracted.skill_id}

Input items (with stable ids):
{payload_json}

Return JSON:
{{
  "applicable_scenarios_keep_ids": [0],
  "core_steps_keep_ids": [0, 2],
  "constraints_keep_ids": [],
  "examples_keep_ids": [1],
  "dependencies_keep_ids": [0]
}}

Rules:
1. Use hard filtering at item level.
2. Keep only items that are directly useful for solving the task.
3. If no items should be kept for a field, return [] for that field.
4. Output JSON object only.
        """.strip()

        decision = self.llm.call_json(system_prompt, user_prompt)
        return SelectedSkill(
            skill_id=extracted.skill_id,
            applicable_scenarios=_apply_decision(
                extracted.applicable_scenarios, decision.get("applicable_scenarios_keep_ids")
            ),
            core_steps=_apply_decision(extracted.core_steps, decision.get("core_steps_keep_ids")),
            constraints=_apply_decision(extracted.constraints, decision.get("constraints_keep_ids")),
            examples=_apply_decision(extracted.examples, decision.get("examples_keep_ids")),
            dependencies=_apply_decision(extracted.dependencies, decision.get("dependencies_keep_ids")),
        )


def _to_indexed(items: list[Any]) -> list[dict[str, Any]]:
    return [{"id": idx, "value": value} for idx, value in enumerate(items)]


def _apply_decision(items: list[Any], kept_ids: Any) -> list[Any]:
    if not items:
        return []
    if not isinstance(kept_ids, list):
        return items

    keep_ids: set[int] = set()
    for idx in kept_ids:
        if isinstance(idx, int):
            keep_ids.add(idx)

    # 空列表表示模型明确选择“都不保留”；缺失字段才回退到原始项
    if not keep_ids:
        return []

    return [item for idx, item in enumerate(items) if idx in keep_ids]
