# Skill Composer

Query-specific skill composition 框架：针对当前 task query 与候选 skills，执行 `Extract → Select → Resolve → Compress` 四步，生成更短、更可执行的 synthesized `SKILL.md`。

## 1. 项目结构

```text
exp7_skillcomposer/
├── README.md
├── requirements.txt
├── config/
│   └── config.yaml              # 模型配置（API key、base_url、参数等）
├── skillsbench/                 # SkillsBench benchmark 数据（git clone）
│   └── tasks/                   # 89 个 task，每个含 instruction.md + environment/skills/
├── dataset/
│   └── constructed/             # 自构造 demo 数据（3-5 个简单 task）
├── outputs/                     # 运行产物（自动生成）
│   └── eval_skills/             # 每个 task 合成后的 SKILL.md
├── docs/                        # 设计文档
│   └── task1/
│       └── constructed_benchmark_design.md
└── skill_composer/
    ├── __init__.py
    ├── config.py
    ├── main.py                  # CLI 入口（compose / evaluate）
    ├── models/
    │   └── skill.py             # RawSkill / ExtractedSkill / SelectedSkill 等
    ├── pipeline/
    │   ├── extractor.py         # Extract：结构化提取 raw skill 字段
    │   ├── selector.py           # Select：基于 task relevance 过滤 items
    │   ├── resolver.py           # Resolve：合并重复、解决冲突、补全依赖
    │   └── compressor.py        # Compress：压缩为最终 SKILL.md
    ├── utils/
    │   ├── llm_client.py        # OpenAI-compatible API 调用 + JSON 解析
    │   ├── skill_loader.py       # 加载 SKILL.md 文件
    │   └── skill_writer.py       # 写出合成后的 SKILL.md
    └── eval/
        ├── evaluator.py         # 评测核心（Evaluator / BenchmarkAdapter / VerificationBackend）
        ├── adapters/             # Benchmark 适配器
        │   ├── constructed_benchmark.py   # 自构造 demo
        │   ├── toolbench_adapter.py       # ToolBench 数据集
        │   ├── skillsbench_adapter.py     # SkillsBench tasks/
        │   └── terminal_bench_adapter.py # Terminal-Bench（占位）
        └── backends/            # 验证后端
            ├── llm_judge_backend.py       # LLM-as-Judge（默认）
            └── constructed_judge.py       # 脚本执行验证
```

## 2. 环境准备

```bash
cd /Users/yzb/Desktop/research/exp7_skillcomposer
conda activate skillcomposer
pip install -r requirements.txt
```

依赖：PyYAML, pytest, tqdm, pandas

## 3. 模型配置

代码使用 OpenAI-compatible chat completions 接口，支持任意兼容服务。

`config/config.yaml`：

```yaml
model: astron-code-latest
api_key: "your_api_key"
base_url: https://maas-coding-api.cn-huabei-1.xf-yun.com/v2
max_output_tokens: 2000
compress_ratio_target: 0.5
timeout_sec: 90
max_retries: 2
temperature: 0.0
```

覆盖优先级：YAML → 环境变量 → CLI 参数

## 4. 运行 Compose（单次合成）

```bash
python -m skill_composer.main compose \
  --config config/config.yaml \
  --task-query "Build a data cleaning pipeline for CSV files" \
  --skills skills/a.SKILL.md skills/b.SKILL.md \
  --output outputs/synthesized.SKILL.md
```

输出：终端打印 `SynthesizedSkill` JSON + 写入 `outputs/synthesized.SKILL.md`

## 5. 运行 Evaluate（批量评测）

### 评测流程

```
Task Query + Candidate Skills
        ↓
compose_skill() → 合成 SKILL.md
        ↓
VerificationBackend → 返回 passed/score
        ↓
Evaluator 汇总 pass_rate + normalized_gain
```

### 评测命令

```bash
# SkillsBench（62 个 task，候选 ≥2 个 skills）
python -m skill_composer.main evaluate \
  --dataset skillsbench/tasks \
  --adapter skillsbench \
  --backend llm_judge \
  --config config/config.yaml \
  --compose-output-dir outputs/eval_skills \
  --report outputs/eval_report.json \
  --conditions stacked_skills synthesized_skill

# 自构造 demo（无真实验证，用于快速验证 pipeline）
python -m skill_composer.main evaluate \
  --adapter constructed \
  --backend dummy
```

### 支持的 Adapter

| Adapter | 数据来源 | 说明 |
|---------|---------|------|
| `constructed` | `dataset/constructed/tasks.jsonl` | 自构造 demo task |
| `toolbench` | `dataset/toolbench.jsonl` | Stanford ToolBench API 调用任务 |
| `skillsbench` | `skillsbench/tasks/` | SkillsBench benchmark（过滤 ≥2 skills 的 task）|
| `terminal_bench` | `terminal-bench/tasks/` | Terminal-Bench（占位，需 Docker）|

### 支持的 Backend

| Backend | 验证方式 | 说明 |
|---------|---------|------|
| `llm_judge`（默认）| LLM 评估 skill 质量 | 快速，无需环境配置 |
| `dummy` | 占位，不做真实验证 | 用于 pipeline 测试 |
| `command` | 外部命令（`--verify-cmd`）| 需要实现 JSON 接口 |
| `script_execution` | 执行验证脚本 | 需要每个 task 有 `_verify.py` |

### 评测条件

| 条件 | 说明 |
|------|------|
| `no_skill` | 不用任何 skill，作为 baseline |
| `stacked_skills` | 直接拼接所有候选 skill |
| `synthesized_skill` | 框架合成的 skill |
| `oracle_skill` | 人工最优 skill（仅当数据集中有 oracle 时）|

### 输出指标

```json
{
  "benchmark": "skillsbench",
  "total_cases": 62,
  "pass_rate": {
    "no_skill": 0.0,
    "stacked_skills": 0.67,
    "synthesized_skill": 0.72
  },
  "normalized_gain": 0.15,
  "results": [...]
}
```

- `pass_rate`：各条件下 LLM judge 认为 skill 能解决 task 的比例
- `normalized_gain`：合成优于 stacked 的程度，oracle 存在时为 `(synth-stacked)/(oracle-stacked)`，否则为 `(synth-stacked)/stacked`

### `--verify-cmd` 接口约定

外部命令通过 stdin/stdout 交换 JSON：

```json
// stdin 接收
{"task_id": "...", "query": "...", "condition": "...", "skill_paths": [...], "metadata": {}}

// stdout 返回
{"passed": true, "score": 0.85, "details": {...}}
```

## 6. 四步合成流程

```
Extract → Select → Resolve → Compress
```

### Extract
读取原始 SKILL.md，用 LLM 将 unstructured 内容提取为结构化字段：
`applicable_scenarios`、`core_steps`、`constraints`、`examples`、`dependencies`

### Select
将结构化内容按 task query 做 relevance 过滤，每条 item 独立判断 keep/drop

### Resolve
合并重复语义项、解决冲突（task-first 策略 + conditional branching）、补全隐式依赖

### Compress
将合并结果压缩为目标长度的 SKILL.md，保留核心可执行指令

## 7. 注意事项

- `llm_judge` 评估的是 **skill 质量**（完整性、正确性、相关性），不是真实任务完成率
- 真实任务完成率需要 Docker 容器执行（如 E2B 沙盒）
- SkillsBench 中候选 skill < 2 的 task 被自动过滤（无法测试组合效果）
- 论文中应说明评估指标的代理性质（judge 评估 vs 实际执行）

## 8. 扩展建议

- 新 benchmark：继承 `BenchmarkAdapter` 实现 `iter_cases()`
- 新验证后端：继承 `VerificationBackend` 实现 `evaluate_case()`
- 消融实验：构造不同的 `compose_fn`（如跳过 Select/Resolve/Compress）复用同一 `Evaluator`
