"""SkillsBench 适配器。

任务结构：
tasks/<task-id>/
├── instruction.md              → query
├── environment/skills/          → candidate_skill_paths
│   └── skill-name/SKILL.md
├── solution/solve.sh           → oracle（占位，未构建为 SKILL.md）
└── tests/test_outputs.py

前置依赖：
- git clone https://github.com/benchflow-ai/skillsbench
- 需要安装 harbor + Docker 执行验证（可选）

验证通过 LLMJudgeVerificationBackend 或 HarborVerificationBackend。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from skill_composer.eval.evaluator import BenchmarkAdapter, TaskCase


class SkillsBenchAdapter(BenchmarkAdapter):
    name = "skillsbench"

    def __init__(self, tasks_dir: str):
        self.tasks_dir = Path(tasks_dir)
        if not self.tasks_dir.exists():
            raise FileNotFoundError(f"SkillsBench tasks dir not found: {self.tasks_dir}")
        self.cases: list[TaskCase] = self._load_cases()

    def _load_cases(self) -> list[TaskCase]:
        cases = []
        skipped = 0
        for task_path in sorted(self.tasks_dir.iterdir()):
            if not task_path.is_dir():
                continue
            instruction_file = task_path / "instruction.md"
            if not instruction_file.exists():
                continue

            instruction = instruction_file.read_text(encoding="utf-8")
            skill_dir = task_path / "environment" / "skills"
            skill_paths = []
            if skill_dir.exists():
                skill_paths = [str(p) for p in skill_dir.glob("*/SKILL.md")]

            # 过滤掉候选 skill 数量 < 2 的 task（无法测试组合效果）
            if len(skill_paths) < 2:
                skipped += 1
                continue

            # oracle_skill_path：solution/solve.sh 是 shell 脚本，暂不构建为 SKILL.md
            oracle_path = str(task_path / "solution" / "solve.sh")

            cases.append(TaskCase(
                task_id=task_path.name,
                query=instruction,
                candidate_skill_paths=skill_paths,
                oracle_skill_path=oracle_path,
            ))

        print(f"SkillsBench: loaded {len(cases)} tasks (skipped {skipped} with < 2 skills)")
        return cases

    def iter_cases(self) -> Any:
        return iter(self.cases)
