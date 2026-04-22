from __future__ import annotations

import re
from typing import Any

from skill_composer.config import ComposerConfig
from skill_composer.models import ResolvedContent, SynthesizedSkill
from skill_composer.utils import LLMClient, render_skill_markdown


class Compressor:
    def __init__(self, llm_client: LLMClient, config: ComposerConfig):
        self.llm = llm_client
        self.config = config

    def compress(self, resolved: ResolvedContent, task_query: str) -> SynthesizedSkill:
        system_prompt = (
            "You write compact executable SKILL.md content. Keep high executability. "
            "Remove redundant explanation. Return strict JSON."
        )
        user_prompt = f"""
Task query:
{task_query}

Resolved content:
{{
  "core_steps": {resolved.core_steps},
  "constraints": {resolved.constraints},
  "examples": {resolved.examples},
  "dependencies": {resolved.dependencies}
}}

Compression target:
- Ratio target: {self.config.compress_ratio_target:.2f}
- Keep only critical and executable information.

Return JSON schema:
{{
  "name": "short-action-name",
  "description": "one-line description",
  "core_steps": ["..."],
  "constraints": ["..."],
  "dependencies": ["..."],
  "examples": [{{"input": "...", "output": "..."}}]
}}

Rules:
1. name: 2-4 lowercase English words separated by spaces, action-oriented (e.g. "search and save news", "read file and summarize"). Do NOT echo the task query verbatim.
2. description: concise one-linger describing what this skill does.
3. Keep step order.
4. Keep representative 1-2 examples if available.
5. Output JSON object only.
        """.strip()
        data = self.llm.call_json(
            system_prompt,
            user_prompt,
            max_output_tokens=self.config.max_output_tokens,
        )
        name = _sanitize_name(str(data.get("name", "")).strip() or "synthesized-skill")
        description = str(data.get("description", "")).strip() or "Task-oriented composed skill."

        # 仅在 LLM 未提供（None/missing）时才回退；显式返回 [] 时保留空列表
        _core_steps = data.get("core_steps")
        core_steps = _to_str_list(_core_steps) if _core_steps is not None else resolved.core_steps
        _constraints = data.get("constraints")
        constraints = _to_str_list(_constraints) if _constraints is not None else resolved.constraints
        _deps = data.get("dependencies")
        dependencies = _to_str_list(_deps) if _deps is not None else resolved.dependencies
        _examples = data.get("examples")
        examples = _to_example_list(_examples) if _examples is not None else resolved.examples[:2]

        markdown = render_skill_markdown(
            name=name,
            description=description,
            core_steps=core_steps,
            constraints=constraints,
            dependencies=dependencies,
            examples=examples[:2],
        )
        return SynthesizedSkill(name=name, description=description, content=markdown)


def _sanitize_name(name: str) -> str:
    # 允许字母数字和空格，移除非法字符，保留大小写和空格
    cleaned = re.sub(r"[^a-zA-Z0-9 ]", "", name).strip()
    return cleaned or "synthesized-skill"


def _to_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _to_example_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
