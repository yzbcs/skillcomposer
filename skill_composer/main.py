from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from skill_composer.config import ComposerConfig
from skill_composer.eval import (
    CommandVerificationBackend,
    DummyVerificationBackend,
    EvaluationCondition,
    Evaluator,
)
from skill_composer.eval.adapters import (
    ConstructedBenchmarkAdapter,
    SkillsBenchAdapter,
    TerminalBenchAdapter,
    ToolBenchAdapter,
)
from skill_composer.eval.backends import LLMJudgeVerificationBackend, ScriptExecutionBackend, HarborVerificationBackend
from skill_composer.models import SynthesizedSkill
from skill_composer.pipeline import Compressor, Extractor, Resolver, Selector
from skill_composer.utils import LLMClient, load_skills, write_synthesized_skill
from skill_composer.utils.llm_client import LLMRequestConfig

DEFAULT_CONFIG_PATH = "config/config.yaml"


def compose_skill(
    task_query: str,
    skill_paths: list[str],
    output_path: str,
    *,
    settings: ComposerConfig | None = None,
) -> SynthesizedSkill:
    cfg = settings or _load_default_settings()

    raw_skills = load_skills(skill_paths)
    if not raw_skills:
        raise ValueError("`skill_paths` 不能为空。")

    llm = LLMClient(
        LLMRequestConfig(
            model=cfg.model,
            api_key=cfg.api_key,
            base_url=cfg.base_url,
            timeout_sec=cfg.timeout_sec,
            max_retries=cfg.max_retries,
            max_output_tokens=cfg.max_output_tokens,
            temperature=cfg.temperature,
        )
    )
    extractor = Extractor(llm)
    selector = Selector(llm)
    resolver = Resolver(llm)
    compressor = Compressor(llm, cfg)

    try:
        extracted = [extractor.extract(item) for item in raw_skills]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"extract 阶段失败: {exc}") from exc

    try:
        selected = [selector.select(item, task_query) for item in extracted]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"select 阶段失败: {exc}") from exc

    try:
        resolved = resolver.resolve(selected, task_query)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"resolve 阶段失败: {exc}") from exc

    try:
        synthesized = compressor.compress(resolved, task_query)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"compress 阶段失败: {exc}") from exc

    write_synthesized_skill(synthesized, output_path)
    return synthesized


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query-specific skill composition framework")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compose_parser = subparsers.add_parser("compose", help="Compose a synthesized skill")
    compose_parser.add_argument("--task-query", required=True, help="Current task query")
    compose_parser.add_argument("--skills", nargs="+", required=True, help="Candidate skill files")
    compose_parser.add_argument(
        "--output",
        default="outputs/synthesized.SKILL.md",
        help="Output SKILL.md path",
    )
    _add_model_args(compose_parser)

    eval_parser = subparsers.add_parser("evaluate", help="Run benchmark evaluation")
    eval_parser.add_argument(
        "--dataset",
        required=True,
        help="Dataset or tasks directory path (format depends on --adapter)",
    )
    eval_parser.add_argument(
        "--compose-output-dir",
        default="outputs/eval_skills",
        help="Directory to write synthesized skills",
    )
    eval_parser.add_argument(
        "--report",
        default="outputs/eval_report.json",
        help="Evaluation summary output path",
    )
    eval_parser.add_argument(
        "--conditions",
        nargs="*",
        choices=[item.value for item in EvaluationCondition],
        default=[item.value for item in EvaluationCondition],
        help="Evaluation conditions",
    )
    eval_parser.add_argument(
        "--verify-cmd",
        nargs="+",
        help="External verification command (use with dummy backend). "
        "Reads task payload JSON from stdin and returns result JSON to stdout.",
    )
    eval_parser.add_argument(
        "--adapter",
        default="constructed",
        choices=["constructed", "toolbench", "skillsbench", "terminal_bench"],
        help="Benchmark adapter to use (default: constructed)",
    )
    eval_parser.add_argument(
        "--backend",
        default="llm_judge",
        choices=["llm_judge", "script_execution", "dummy", "command", "harbor"],
        help="Verification backend to use (default: llm_judge)",
    )
    eval_parser.add_argument(
        "--verify-script",
        help="Path to claweval_verify.py script (for harbor backend)",
    )
    eval_parser.add_argument(
        "--task-root",
        help="Path to skillsbench tasks root (for harbor backend)",
    )
    eval_parser.add_argument(
        "--task", "-t",
        help="Run a specific task by ID (comma-separated for multiple)",
    )
    _add_model_args(eval_parser)
    return parser.parse_args()


def _add_model_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        help="YAML config path (default: config/config.yaml)",
    )
    parser.add_argument("--model", help="Model name override")
    parser.add_argument("--api-key", help="API key override")
    parser.add_argument("--base-url", help="OpenAI-compatible base URL override")
    parser.add_argument("--max-output-tokens", type=int, help="Max output tokens override")
    parser.add_argument("--compress-ratio-target", type=float, help="Compress ratio override")
    parser.add_argument("--timeout-sec", type=int, help="Request timeout seconds override")
    parser.add_argument("--max-retries", type=int, help="Retry count override")
    parser.add_argument("--temperature", type=float, help="Sampling temperature override")


def _settings_from_args(args: argparse.Namespace) -> ComposerConfig:
    config_path = args.config or DEFAULT_CONFIG_PATH
    cfg = ComposerConfig.from_yaml(config_path)
    cfg = cfg.with_env_overrides()
    updates: dict[str, Any] = {
        "model": args.model,
        "api_key": args.api_key,
        "base_url": args.base_url,
        "max_output_tokens": args.max_output_tokens,
        "compress_ratio_target": args.compress_ratio_target,
        "timeout_sec": args.timeout_sec,
        "max_retries": args.max_retries,
        "temperature": args.temperature,
    }
    cfg = cfg.with_overrides(**updates)
    cfg.validate()
    return cfg


def _load_default_settings() -> ComposerConfig:
    cfg = ComposerConfig.from_yaml_if_exists(DEFAULT_CONFIG_PATH).with_env_overrides()
    cfg.validate()
    return cfg


def _run_compose(args: argparse.Namespace) -> None:
    cfg = _settings_from_args(args)
    synthesized = compose_skill(
        task_query=args.task_query,
        skill_paths=args.skills,
        output_path=args.output,
        settings=cfg,
    )
    print(json.dumps(asdict(synthesized), ensure_ascii=False, indent=2))


def _run_evaluate(args: argparse.Namespace) -> None:
    cfg = _settings_from_args(args)

    # 选择 BenchmarkAdapter
    if args.adapter == "constructed":
        adapter = ConstructedBenchmarkAdapter(
            tasks_jsonl="dataset/constructed/tasks.jsonl",
            skills_dir="dataset/constructed/skills",
        )
    elif args.adapter == "toolbench":
        adapter = ToolBenchAdapter(
            dataset_path=args.dataset,
            skills_output_dir="outputs/toolbench_skills",
        )
    elif args.adapter == "skillsbench":
        adapter = SkillsBenchAdapter(tasks_dir=args.dataset)
    elif args.adapter == "terminal_bench":
        adapter = TerminalBenchAdapter(tasks_dir=args.dataset)
    else:
        raise ValueError(f"Unknown adapter: {args.adapter}")

    # 选择 VerificationBackend
    if args.backend == "llm_judge":
        backend = LLMJudgeVerificationBackend(
            judge_model=cfg.model,
            judge_api_key=cfg.api_key,
            judge_base_url=cfg.base_url,
            timeout_sec=cfg.timeout_sec,
        )
    elif args.backend == "script_execution":
        backend = ScriptExecutionBackend(verify_scripts_dir="dataset/constructed/verify_scripts")
    elif args.backend == "command":
        backend = CommandVerificationBackend(args.verify_cmd) if args.verify_cmd else DummyVerificationBackend()
    elif args.backend == "harbor":
        backend = HarborVerificationBackend(
            verify_script=args.verify_script,
            task_root=args.task_root,
            timeout_sec=cfg.timeout_sec,
            model=cfg.model,
            api_key=cfg.api_key,
            api_url=cfg.base_url,
        )
    else:
        backend = DummyVerificationBackend()

    def compose_fn(task_query: str, skill_paths: list[str], output_path: str) -> Any:
        return compose_skill(
            task_query=task_query,
            skill_paths=skill_paths,
            output_path=output_path,
            settings=cfg,
        )

    evaluator = Evaluator(adapter=adapter, backend=backend, compose_fn=compose_fn)
    conditions = [EvaluationCondition(cond) for cond in args.conditions]
    task_ids = None
    if args.task:
        task_ids = [t.strip() for t in args.task.split(",")]
    summary = evaluator.run(
        output_dir=args.compose_output_dir,
        conditions=conditions,
        report_path=args.report,
        task_ids=task_ids,
    )

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))


def main() -> None:
    args = _parse_args()
    if args.command == "compose":
        _run_compose(args)
        return
    if args.command == "evaluate":
        _run_evaluate(args)
        return
    raise ValueError(f"未知命令: {args.command}")


if __name__ == "__main__":
    main()
