"""LLM-as-Judge 验证后端。

将 task query + 合成 skill 内容发给 LLM judge，
由 judge 判断合成 skill 是否能引导 agent 正确解决任务。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from skill_composer.eval.evaluator import EvaluationCondition, TaskCase, VerificationBackend
from skill_composer.utils import LLMClient
from skill_composer.utils.llm_client import LLMRequestConfig


class LLMJudgeVerificationBackend(VerificationBackend):
    """用 LLM 作为 judge 评估合成 skill 质量。

    对比 task query 和 skill 内容，LLM judge 输出：
    - passed: skill 是否能帮助解决 task
    - score: 0.0-1.0 质量分
    - 各维度细项分
    """

    name: str = "llm_judge"

    def __init__(
        self,
        judge_model: str,
        judge_api_key: str,
        judge_base_url: str,
        timeout_sec: int = 90,
    ):
        self.judge_model = judge_model
        self.judge_api_key = judge_api_key
        self.judge_base_url = judge_base_url
        self.timeout_sec = timeout_sec
        self.llm_client = LLMClient(
            LLMRequestConfig(
                model=judge_model,
                api_key=judge_api_key,
                base_url=judge_base_url,
                timeout_sec=timeout_sec,
            )
        )

    def evaluate_case(
        self,
        case: TaskCase,
        condition: EvaluationCondition,
        skill_paths: list[str],
    ) -> tuple[bool, float | None, dict[str, Any]]:
        """让 LLM judge 评估 skill 内容是否能引导 agent 解决 task。"""
        # 读取 skill 内容
        skill_contents: list[str] = []
        for path_str in skill_paths:
            path = Path(path_str)
            if path.exists():
                skill_contents.append(path.read_text(encoding="utf-8"))
            else:
                skill_contents.append(f"[Skill not found: {path_str}]")

        skill_text = "\n\n---\n\n".join(skill_contents)

        system_prompt = (
            "You are an expert evaluator for AI agent skills. "
            "Given a task query and a skill document, judge whether the skill "
            "is likely to help an agent successfully complete the task. "
            "Return strict JSON."
        )
        user_prompt = f"""Task Query:
{case.query}

Skill Content:
{skill_text}

Evaluation Criteria:
1. Completeness: Does the skill cover all steps needed to complete the task?
2. Correctness: Are the instructions accurate and executable?
3. Relevance: Does the skill directly address the task requirements?
4. Clarity: Are instructions clear and unambiguous?

Return JSON:
{{
  "passed": true or false,
  "score": 0.0 to 1.0,
  "reasoning": "brief explanation",
  "completeness": 0.0 to 1.0,
  "correctness": 0.0 to 1.0,
  "relevance": 0.0 to 1.0,
  "clarity": 0.0 to 1.0
}}"""

        try:
            result = self.llm_client.call_json(system_prompt, user_prompt)
            passed = bool(result.get("passed", False))
            score = float(result.get("score", 0.0))
            details = {
                "reasoning": result.get("reasoning", ""),
                "completeness": result.get("completeness"),
                "correctness": result.get("correctness"),
                "relevance": result.get("relevance"),
                "clarity": result.get("clarity"),
                "condition": condition.value,
                "skill_paths": skill_paths,
            }
            return passed, score, details
        except Exception as exc:
            return False, 0.0, {"error": str(exc), "condition": condition.value}
