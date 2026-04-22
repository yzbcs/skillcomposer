from __future__ import annotations

from pathlib import Path

from skill_composer.models import RawSkill


def load_skill(path: str) -> RawSkill:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Skill 文件不存在: {path}")
    content = file_path.read_text(encoding="utf-8")
    return RawSkill(
        skill_id=file_path.stem,
        content=content,
        source_path=str(file_path.resolve()),
    )


def load_skills(paths: list[str]) -> list[RawSkill]:
    return [load_skill(path) for path in paths]
