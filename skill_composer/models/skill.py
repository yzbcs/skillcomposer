from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawSkill:
    skill_id: str
    content: str
    source_path: str | None = None


@dataclass
class ExtractedSkill:
    skill_id: str
    applicable_scenarios: list[str] = field(default_factory=list)
    core_steps: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class SelectedSkill:
    skill_id: str
    applicable_scenarios: list[str] = field(default_factory=list)
    core_steps: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class ResolvedContent:
    core_steps: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    conflicts_log: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SynthesizedSkill:
    name: str
    description: str
    content: str
