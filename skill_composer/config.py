from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


@dataclass
class ComposerConfig:
    model: str
    api_key: str
    base_url: str
    max_output_tokens: int
    compress_ratio_target: float
    timeout_sec: int
    max_retries: int
    temperature: float

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "ComposerConfig":
        if yaml is None:
            raise ImportError("缺少依赖 `PyYAML`，请先安装后再使用 YAML 配置。")
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError("配置文件不存在: {}".format(yaml_path))
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise ValueError("YAML 根节点必须是对象（key-value）。")
        normalized = cls._normalize(raw)
        missing = cls._missing_keys(normalized)
        if missing:
            raise ValueError(
                "配置缺少必填字段: {}。请在 YAML 中补齐。".format(", ".join(missing))
            )
        return cls(**normalized)

    @classmethod
    def from_yaml_if_exists(cls, yaml_path: str) -> "ComposerConfig":
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError("配置文件不存在: {}".format(yaml_path))
        return cls.from_yaml(str(path))

    def with_env_overrides(self) -> "ComposerConfig":
        env_updates: dict[str, Any] = {
            "model": os.getenv("SKILL_COMPOSER_MODEL"),
            "api_key": os.getenv("SKILL_COMPOSER_API_KEY"),
            "base_url": os.getenv("SKILL_COMPOSER_BASE_URL"),
            "max_output_tokens": os.getenv("SKILL_COMPOSER_MAX_OUTPUT_TOKENS"),
            "compress_ratio_target": os.getenv("SKILL_COMPOSER_COMPRESS_RATIO_TARGET"),
            "timeout_sec": os.getenv("SKILL_COMPOSER_TIMEOUT_SEC"),
            "max_retries": os.getenv("SKILL_COMPOSER_MAX_RETRIES"),
            "temperature": os.getenv("SKILL_COMPOSER_TEMPERATURE"),
        }
        normalized = self._normalize(env_updates, drop_none=True)
        return replace(self, **normalized)

    def with_overrides(self, **kwargs: Any) -> "ComposerConfig":
        normalized = self._normalize(kwargs, drop_none=True)
        return replace(self, **normalized)

    @staticmethod
    def _normalize(values: dict[str, Any], *, drop_none: bool = False) -> dict[str, Any]:
        allowed = {
            "model",
            "api_key",
            "base_url",
            "max_output_tokens",
            "compress_ratio_target",
            "timeout_sec",
            "max_retries",
            "temperature",
        }
        cleaned: dict[str, Any] = {}
        for key, value in values.items():
            if key not in allowed:
                continue
            if drop_none and value is None:
                continue

            if key in {"model", "api_key", "base_url"}:
                if value is None:
                    continue
                cleaned[key] = str(value)
            elif key in {"max_output_tokens", "timeout_sec", "max_retries"}:
                if value is None:
                    continue
                cleaned[key] = int(value)
            elif key in {"compress_ratio_target", "temperature"}:
                if value is None:
                    continue
                cleaned[key] = float(value)
        return cleaned

    @staticmethod
    def _missing_keys(values: dict[str, Any]) -> list[str]:
        required = [
            "model",
            "api_key",
            "base_url",
            "max_output_tokens",
            "compress_ratio_target",
            "timeout_sec",
            "max_retries",
            "temperature",
        ]
        return [key for key in required if key not in values]

    def validate(self) -> None:
        if not self.model:
            raise ValueError("`model` 不能为空。")
        if not self.base_url:
            raise ValueError("`base_url` 不能为空。")
        if self.max_output_tokens <= 0:
            raise ValueError("`max_output_tokens` 必须大于 0。")
        if not 0 <= self.compress_ratio_target <= 1:
            raise ValueError("`compress_ratio_target` 必须位于 [0, 1]。")
        if self.timeout_sec <= 0:
            raise ValueError("`timeout_sec` 必须大于 0。")
        if self.max_retries < 0:
            raise ValueError("`max_retries` 不能小于 0。")
        if not 0 <= self.temperature <= 2:
            raise ValueError("`temperature` 必须位于 [0, 2]。")
