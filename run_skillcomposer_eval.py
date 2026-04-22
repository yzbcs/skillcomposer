#!/usr/bin/env python3
"""运行 Skill Composer × ClawEvalKit 评测实验.

实验设计:
1. 原始 SkillsBench 评测 (62 个任务) → outputs/skillsbench_original/
2. 合成 Skill 评测 (62 个任务) → outputs/skillsbench_synthesized/
3. 对比 pass_rate

用法:
    # 先跑原始 benchmark
    python3 run_skillcomposer_eval.py --phase original

    # 再跑合成 skill 评测
    python3 run_skillcomposer_eval.py --phase synthesized

    # 对比结果
    python3 run_skillcomposer_eval.py --phase compare
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# 配置
SYNTHESIZED_SKILLS_DIR = "/Users/yzb/Desktop/research/exp7_skillcomposer/outputs/eval_skills"
SKILLSBENCH_DIR = "/Users/yzb/Desktop/research/exp7_skillcomposer/skillsbench"
OPENCLAWPRO_DIR = "/Users/yzb/Desktop/research/exp7_skillcomposer/ClawEvalkit_new/OpenClawPro"
SKILLCOMPOSER_EVAL_DIR = "/Users/yzb/Desktop/research/exp7_skillcomposer/ClawEvalkit_new"

# 62 个评测任务 ID (从 eval_skills 目录获取)
EVAL_TASK_IDS = [
    "adaptive-cruise-control", "civ6-adjacency-optimizer", "crystallographic-wyckoff-position-analysis",
    "dapt-intrusion-detection", "dynamic-object-aware-egomotion", "earthquake-phase-association",
    "edit-pdf", "energy-ac-optimal-power-flow", "energy-market-pricing", "exceltable-in-ppt",
    "exoplanet-detection-period", "financial-modeling-qa", "find-topk-similiar-chemicals",
    "fix-build-agentops", "fix-build-google-auto", "fix-druid-loophole-cve", "fix-erlang-ssh-cve",
    "fix-visual-stability", "flink-query", "flood-risk-analysis", "glm-lake-mendota",
    "gravitational-wave-detection", "grid-dispatch-operator", "hvac-control",
    "invoice-fraud-detection", "jpg-ocr-stat", "lake-warming-attribution", "latex-formula-extraction",
    "lean4-proof", "manufacturing-equipment-maintenance", "mario-coin-counting", "mars-clouds-clustering",
    "mhc-layer-impl", "multilingual-video-dubbing", "organize-messy-files", "paper-anonymizer",
    "parallel-tfidf-search", "pdf-excel-diff", "pedestrian-traffic-counting", "pg-essay-to-audiobook",
    "powerlifting-coef-calc", "python-scala-translation", "r2r-mpc-control", "react-performance-debugging",
    "sales-pivot-analysis", "scheduling-email-assistant", "sec-financial-report", "seismic-phase-picking",
    "setup-fuzzing-py", "simpo-code-reproduction", "software-dependency-audit", "speaker-diarization-subtitles",
    "spring-boot-jakarta-migration", "suricata-custom-exfil", "syzkaller-ppdev-syzlang",
    "threejs-structure-parser", "threejs-to-obj", "travel-planning", "trend-anomaly-causal-inference",
    "video-filler-word-remover", "video-silence-remover", "xlsx-recover-data"
]

MODEL = "minimax-m2.7"
TASK_IDS_STR = ",".join(EVAL_TASK_IDS)


def run_original():
    """运行原始 SkillsBench 评测 (使用原始 skills)。"""
    print("=" * 60)
    print("Phase 1: 运行原始 SkillsBench (62 tasks)")
    print("=" * 60)

    env = os.environ.copy()
    env["SKILLSBENCH_DIR"] = SKILLSBENCH_DIR
    env["OPENCLAWPRO_DIR"] = OPENCLAWPRO_DIR

    cmd = [
        "/Users/yzb/anaconda3/envs/skillcomposer/bin/python3", "run.py",
        "--bench", "skillsbench",
        "--model", MODEL,
        "--docker",
        "--force",
        "--output-dir", "outputs/skillsbench_original",
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=SKILLCOMPOSER_EVAL_DIR, env=env)
    return result.returncode


def run_synthesized():
    """运行合成 Skill 评测 (使用合成 SKILL.md 替换原始 skills)。"""
    print("=" * 60)
    print("Phase 2: 运行合成 Skill 评测 (62 tasks)")
    print("=" * 60)

    env = os.environ.copy()
    env["SKILLSBENCH_DIR"] = SKILLSBENCH_DIR
    env["OPENCLAWPRO_DIR"] = OPENCLAWPRO_DIR
    env["SKILLCOMPOSER_EVAL_SKILLS_DIR"] = SYNTHESIZED_SKILLS_DIR
    env["SKILLCOMPOSER_EVAL_TASK_IDS"] = TASK_IDS_STR

    cmd = [
        "/Users/yzb/anaconda3/envs/skillcomposer/bin/python3", "run.py",
        "--bench", "skillcomposer-eval",
        "--model", MODEL,
        "--docker",
        "--force",
        "--output-dir", "outputs/skillsbench_synthesized",
    ]

    print(f"Running: {' '.join(cmd)}")
    print(f"SKILLCOMPOSER_EVAL_SKILLS_DIR={SYNTHESIZED_SKILLS_DIR}")
    print(f"SKILLCOMPOSER_EVAL_TASK_IDS={len(EVAL_TASK_IDS)} tasks")
    result = subprocess.run(cmd, cwd=SKILLCOMPOSER_EVAL_DIR, env=env)
    return result.returncode


def compare():
    """对比原始和合成 skill 的评测结果。"""
    print("=" * 60)
    print("Phase 3: 对比结果")
    print("=" * 60)

    original_report = Path(SKILLCOMPOSER_EVAL_DIR) / "outputs" / "skillsbench_original" / "skillsbench" / f"{MODEL}.json"
    synth_report = Path(SKILLCOMPOSER_EVAL_DIR) / "outputs" / "skillsbench_synthesized" / "skillsbench" / f"{MODEL}.json"

    if not original_report.exists():
        print(f"❌ Original report not found: {original_report}")
        return
    if not synth_report.exists():
        print(f"❌ Synthesized report not found: {synth_report}")
        return

    orig_data = json.loads(original_report.read_text())
    synth_data = json.loads(synth_report.read_text())

    print(f"\n原始 SkillsBench: {orig_data.get('passed', 0)}/{orig_data.get('total', 0)} passed, score={orig_data.get('score', 0)}%")
    print(f"合成 Skill 评测:  {synth_data.get('passed', 0)}/{synth_data.get('total', 0)} passed, score={synth_data.get('score', 0)}%")

    # 计算 improvement
    orig_pass = orig_data.get("passed", 0)
    synth_pass = synth_data.get("passed", 0)
    diff = synth_pass - orig_pass
    print(f"\n差异: {diff:+d} passed ({(diff / orig_data.get('total', 1)) * 100:+.1f}%)")

    # 写入对比报告
    compare_result = {
        "original": orig_data,
        "synthesized": synth_data,
        "improvement": diff,
        "improvement_pct": round((diff / orig_data.get('total', 1)) * 100, 2) if orig_data.get('total', 0) > 0 else 0
    }

    compare_out = Path(SKILLCOMPOSER_EVAL_DIR) / "outputs" / "skillcomposer_compare.json"
    compare_out.write_text(json.dumps(compare_result, indent=2, ensure_ascii=False))
    print(f"\n对比报告已保存到: {compare_out}")


def main():
    parser = argparse.ArgumentParser(description="Skill Composer × ClawEvalKit 评测实验")
    parser.add_argument("--phase", choices=["original", "synthesized", "compare", "all"],
                        default="all", help="运行阶段: original(跑原始), synthesized(跑合成), compare(对比结果), all(全部)")
    args = parser.parse_args()

    if args.phase in ("original", "all"):
        rc = run_original()
        if rc != 0:
            print(f"❌ Original phase failed with return code {rc}")
            sys.exit(rc)

    if args.phase in ("synthesized", "all"):
        rc = run_synthesized()
        if rc != 0:
            print(f"❌ Synthesized phase failed with return code {rc}")
            sys.exit(rc)

    if args.phase == "compare":
        compare()


if __name__ == "__main__":
    main()