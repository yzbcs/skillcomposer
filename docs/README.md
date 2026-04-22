# Skill Composer 实验进展

## 实验概述

**目标**：通过 ClawEvalKit Docker 执行流程，对比 `stacked_skills` 和 `synthesized_skill` 在 SkillsBench 真实任务上的完成率。

**Pipeline**: Extract → Select → Resolve → Compress

## Round 1: Harbor Backend 集成与调试

### 设计动机
之前的 `llm_judge` 评测只能评估 SKILL.md 质量，无法测量真实任务完成率。需要通过 Docker 执行来运行真实评测。

### 关键修复

1. **`tasks_dir` 未定义** (`claweval_verify.py:411`)
   - 问题：`main()` 中 `run_agent_turns(tasks_dir=tasks_dir)` 使用了未定义的变量
   - 修复：添加 `tasks_dir = task_dir.parent`

2. **Python 路径错误** (`harbor_backend.py:122`)
   - 问题：subprocess 调用 `python3` 指向系统 Python 3.7（太旧），导致 SSL/urllib 行为不同
   - 修复：改用 `sys.executable` 确保使用 skillcomposer conda 环境 (Python 3.10.18)

3. **缺少 `import sys`** (`claweval_verify.py:48`)
   - 问题：调试输出使用 `file=sys.stderr` 但未导入 sys
   - 修复：添加 `import sys`

4. **LLM 首调用延迟** (`claweval_verify.py:153`)
   - 问题：MiniMax API 首调用耗时 140-280 秒（连接建立开销），默认超时 90s 不够
   - 修复：`timeout_sec` 默认值从 90s 增加到 600s

### 结果数据

| 任务 | 条件 | 轮数 | Pytest | 通过率 |
|------|------|------|--------|--------|
| adaptive-cruise-control | stacked_skills | 3 | 1/12 | 8.3% |
| adaptive-cruise-control | synthesized_skill | (待测) | - | - |

### 核心发现

1. **Docker 集成正常**：container 启动、文件拷贝、pytest 执行均工作正常
2. **MiniMax API 首调用慢**：~140-280s（prob. 代理连接建立），后续调用 ~7-8s
3. **任务难度高**：`adaptive-cruise-control` 需要实现 PID 控制器和仿真，LLM 难以一次生成正确代码

## 代码产物

- `scripts/claweval_verify.py` - Docker 执行 + LLM agent 评测脚本
- `skill_composer/eval/backends/harbor_backend.py` - HarborVerificationBackend
- `outputs/eval_skills/` - 合成技能输出目录
- `outputs/eval_report_harbor.json` - 评测报告

## 下一步计划

1. **多任务评测**：运行 5-10 个不同类型的任务获取统计显著的 pass_rate 对比
2. **任务筛选**：优先选择文件生成类任务（如 edit-pdf, citation-check）而非复杂仿真任务
3. **优化 LLM agent**：当前 agent 实现过于简单，考虑增加代码执行反馈
4. **warm-up 调用**：在评测前先做一个 dummy LLM 调用预热 API 连接
