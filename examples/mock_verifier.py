#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    condition = payload.get("condition", "")
    skill_paths = payload.get("skill_paths") or []
    passed = False
    if condition == "no_skill":
        passed = False
    elif condition == "stacked_skills":
        passed = len(skill_paths) >= 2
    elif condition == "synthesized_skill":
        passed = len(skill_paths) == 1
    elif condition == "oracle_skill":
        passed = len(skill_paths) == 1

    response = {
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "details": {"mock": True, "condition": condition, "skill_count": len(skill_paths)},
    }
    sys.stdout.write(json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()
