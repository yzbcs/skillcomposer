from __future__ import annotations

import json
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, List


class EvaluationCondition(str, Enum):
    NO_SKILL = "no_skill"
    STACKED_SKILLS = "stacked_skills"
    SYNTHESIZED_SKILL = "synthesized_skill"
    ORACLE_SKILL = "oracle_skill"


@dataclass
class TaskCase:
    task_id: str
    query: str
    candidate_skill_paths: list[str] = field(default_factory=list)
    oracle_skill_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CaseEvaluation:
    task_id: str
    condition: str
    status: str
    passed: bool | None
    score: float | None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationSummary:
    benchmark: str
    total_cases: int
    processed_cases: int
    pass_rate: dict[str, float]
    normalized_gain: float | None
    results: list[CaseEvaluation]

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.benchmark,
            "total_cases": self.total_cases,
            "processed_cases": self.processed_cases,
            "pass_rate": self.pass_rate,
            "normalized_gain": self.normalized_gain,
            "results": [asdict(item) for item in self.results],
        }


class BenchmarkAdapter(ABC):
    name: str

    @abstractmethod
    def iter_cases(self) -> Iterable[TaskCase]:
        raise NotImplementedError

    def resolve_skills_for_condition(
        self,
        case: TaskCase,
        condition: EvaluationCondition,
        synthesized_skill_path: str | None,
    ) -> list[str] | None:
        if condition == EvaluationCondition.NO_SKILL:
            return []
        if condition == EvaluationCondition.STACKED_SKILLS:
            return case.candidate_skill_paths
        if condition == EvaluationCondition.SYNTHESIZED_SKILL:
            return [synthesized_skill_path] if synthesized_skill_path else None
        if condition == EvaluationCondition.ORACLE_SKILL:
            return [case.oracle_skill_path] if case.oracle_skill_path else None
        return None


class VerificationBackend(ABC):
    name: str

    @abstractmethod
    def evaluate_case(
        self,
        case: TaskCase,
        condition: EvaluationCondition,
        skill_paths: list[str],
    ) -> tuple[bool, float | None, dict[str, Any]]:
        raise NotImplementedError


class DummyVerificationBackend(VerificationBackend):
    name = "dummy"

    def evaluate_case(
        self,
        case: TaskCase,
        condition: EvaluationCondition,
        skill_paths: list[str],
    ) -> tuple[bool, float | None, dict[str, Any]]:
        details = {
            "note": "未提供真实验证执行器，仅返回占位结果。",
            "task_id": case.task_id,
            "condition": condition.value,
            "skill_paths": skill_paths,
        }
        return False, None, details


class CommandVerificationBackend(VerificationBackend):
    name = "command"

    def __init__(self, command: list[str], timeout_sec: int = 600):
        if not command:
            raise ValueError("`command` 不能为空。")
        self.command = command
        self.timeout_sec = timeout_sec

    def evaluate_case(
        self,
        case: TaskCase,
        condition: EvaluationCondition,
        skill_paths: list[str],
    ) -> tuple[bool, float | None, dict[str, Any]]:
        payload = {
            "task_id": case.task_id,
            "query": case.query,
            "condition": condition.value,
            "skill_paths": skill_paths,
            "metadata": case.metadata,
        }
        proc = subprocess.run(
            self.command,
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=self.timeout_sec,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "验证命令执行失败: "
                f"cmd={' '.join(self.command)}; stderr={proc.stderr.strip()}"
            )
        try:
            result = json.loads(proc.stdout.strip())
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"验证命令 stdout 不是 JSON: {proc.stdout[:300]}"
            ) from exc

        passed = bool(result.get("passed", False))
        score_val = result.get("score")
        score = float(score_val) if isinstance(score_val, (int, float)) else None
        details = result.get("details") if isinstance(result.get("details"), dict) else {}
        return passed, score, details


ComposeFn = Callable[[str, List[str], str], Any]


class Evaluator:
    def __init__(
        self,
        *,
        adapter: BenchmarkAdapter,
        backend: VerificationBackend,
        compose_fn: ComposeFn,
    ):
        self.adapter = adapter
        self.backend = backend
        self.compose_fn = compose_fn

    def _save_intermediate(
        self,
        report_path: Path | None,
        all_cases: list,
        results: list[CaseEvaluation],
    ) -> None:
        """增量保存：每完成一个 case 立即写盘，避免中断丢失数据。"""
        if report_path is None:
            return
        pass_rate = _compute_pass_rate(results)
        summary = EvaluationSummary(
            benchmark=self.adapter.name,
            total_cases=len(all_cases),
            processed_cases=len({item.task_id for item in results}),
            pass_rate=pass_rate,
            normalized_gain=None,
            results=results,
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def run(
        self,
        *,
        output_dir: str,
        conditions: list[EvaluationCondition] | None = None,
        report_path: str | None = None,
        task_ids: list[str] | None = None,
    ) -> EvaluationSummary:
        conds = conditions or [
            EvaluationCondition.NO_SKILL,
            EvaluationCondition.STACKED_SKILLS,
            EvaluationCondition.SYNTHESIZED_SKILL,
            EvaluationCondition.ORACLE_SKILL,
        ]
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        results: list[CaseEvaluation] = []
        cases = list(self.adapter.iter_cases())
        if task_ids:
            cases = [c for c in cases if c.task_id in task_ids]

        for case in cases:
            safe_task_id = _safe_filename(case.task_id)
            synthesized_path = str(out_dir / f"{safe_task_id}.SKILL.md")
            for cond in conds:
                try:
                    resolved_synth_path = None
                    if cond == EvaluationCondition.SYNTHESIZED_SKILL:
                        self.compose_fn(case.query, case.candidate_skill_paths, synthesized_path)
                        resolved_synth_path = synthesized_path

                    skill_paths = self.adapter.resolve_skills_for_condition(
                        case=case,
                        condition=cond,
                        synthesized_skill_path=resolved_synth_path,
                    )
                    if skill_paths is None:
                        results.append(
                            CaseEvaluation(
                                task_id=case.task_id,
                                condition=cond.value,
                                status="skipped",
                                passed=None,
                                score=None,
                                details={"reason": "missing_skill_for_condition"},
                            )
                        )
                        continue

                    passed, score, details = self.backend.evaluate_case(case, cond, skill_paths)
                    # 检查 backend 是否标记为 skipped
                    if details.get("status") == "skipped":
                        results.append(
                            CaseEvaluation(
                                task_id=case.task_id,
                                condition=cond.value,
                                status="skipped",
                                passed=None,
                                score=None,
                                details=details,
                            )
                        )
                    else:
                        results.append(
                            CaseEvaluation(
                                task_id=case.task_id,
                                condition=cond.value,
                                status="ok",
                                passed=passed,
                                score=score,
                                details=details,
                            )
                        )
                except Exception as exc:  # noqa: BLE001
                    results.append(
                        CaseEvaluation(
                            task_id=case.task_id,
                            condition=cond.value,
                            status="error",
                            passed=False,
                            score=None,
                            details={"error": str(exc)},
                        )
                    )

            # 增量保存：每完成一个 case 立即写盘
            self._save_intermediate(Path(report_path) if report_path else None, cases, results)

        pass_rate = _compute_pass_rate(results)
        normalized_gain = _compute_normalized_gain(pass_rate)
        final_summary = EvaluationSummary(
            benchmark=self.adapter.name,
            total_cases=len(cases),
            processed_cases=len({item.task_id for item in results}),
            pass_rate=pass_rate,
            normalized_gain=normalized_gain,
            results=results,
        )
        if report_path:
            final_path = Path(report_path)
            final_path.parent.mkdir(parents=True, exist_ok=True)
            final_path.write_text(
                json.dumps(final_summary.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return final_summary


def _compute_pass_rate(results: list[CaseEvaluation]) -> dict[str, float]:
    buckets: dict[str, list[bool]] = {}
    for row in results:
        if row.status != "ok" or row.passed is None:
            continue
        buckets.setdefault(row.condition, []).append(bool(row.passed))
    out: dict[str, float] = {}
    for cond, values in buckets.items():
        out[cond] = sum(1 for v in values if v) / len(values) if values else 0.0
    return out


def _compute_normalized_gain(pass_rate: dict[str, float]) -> float | None:
    stacked = pass_rate.get(EvaluationCondition.STACKED_SKILLS.value)
    synthesized = pass_rate.get(EvaluationCondition.SYNTHESIZED_SKILL.value)
    oracle = pass_rate.get(EvaluationCondition.ORACLE_SKILL.value)
    if stacked is None or synthesized is None:
        return None

    EPSILON = 1e-9
    if oracle is not None and abs(oracle - stacked) > EPSILON:
        return (synthesized - stacked) / (oracle - stacked)
    if abs(stacked) < EPSILON:
        return synthesized if abs(synthesized) > EPSILON else 0.0
    return (synthesized - stacked) / stacked


def _safe_filename(value: str) -> str:
    clean = "".join(
        ch if (ch.isalnum() or ch in ("-", "_")) else "_"
        for ch in value
    )
    clean = re.sub(r"_+", "_", clean).strip("_")
    return clean or "task"
