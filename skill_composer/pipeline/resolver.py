from __future__ import annotations

from dataclasses import asdict
from typing import Any

from skill_composer.models import ResolvedContent, SelectedSkill
from skill_composer.utils import LLMClient


class Resolver:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def resolve(self, selected_skills: list[SelectedSkill], task_query: str) -> ResolvedContent:
        # 无可合并的 skill 时返回空内容，避免发送无效请求
        if not selected_skills:
            return ResolvedContent(
                core_steps=[],
                constraints=[],
                examples=[],
                dependencies=[],
                conflicts_log=[],
            )
        payload = [asdict(skill) for skill in selected_skills]
        system_prompt = (
            "You merge multiple selected skills into one executable instruction set. "
            "Handle duplicate/conflict/dependency completion. Return strict JSON."
        )
        user_prompt = f"""
Task query:
{task_query}

Selected skills:
{payload}

Return JSON schema:
{{
  "core_steps": ["..."],
  "constraints": ["..."],
  "examples": [{{"input": "...", "output": "..."}}],
  "dependencies": ["..."],
  "conflicts_log": [
    {{
      "issue": "duplicate/conflict/phrasing",
      "source": ["skill_a", "skill_b"],
      "resolution": "how resolved"
    }}
  ]
}}

Rules:
1. Merge semantically duplicated steps/constraints.
2. Resolve conflicts by task-first strategy.
3. If uncertain, preserve both strategies using conditional branching.
4. Explicitly complete missing dependencies inferred from steps and query.
5. Output JSON object only.
        """.strip()
        data = self.llm.call_json(system_prompt, user_prompt)
        return ResolvedContent(
            core_steps=_to_str_list(data.get("core_steps")),
            constraints=_to_str_list(data.get("constraints")),
            examples=_to_example_list(data.get("examples")),
            dependencies=_to_str_list(data.get("dependencies")),
            conflicts_log=_to_dict_list(data.get("conflicts_log")),
        )


def _to_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _to_example_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _to_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
