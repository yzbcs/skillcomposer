from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class LLMClientError(RuntimeError):
    pass


@dataclass
class LLMRequestConfig:
    model: str
    api_key: str
    base_url: str
    timeout_sec: int = 90
    max_retries: int = 2
    max_output_tokens: int = 2000
    temperature: float = 0.0


class LLMClient:
    def __init__(self, cfg: LLMRequestConfig):
        if not cfg.api_key:
            raise ValueError(
                "缺少 API key。请设置 `SKILL_COMPOSER_API_KEY`，"
                "或在 ComposerConfig 中传入 api_key。"
            )
        self.cfg = cfg
        self.endpoint = cfg.base_url.rstrip("/") + "/chat/completions"

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        expect_json: bool = False,
        max_output_tokens: int | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "temperature": self.cfg.temperature,
            "max_tokens": max_output_tokens or self.cfg.max_output_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        payload_variants = [dict(payload)]
        if expect_json:
            payload_with_json_mode = dict(payload)
            payload_with_json_mode["response_format"] = {"type": "json_object"}
            payload_variants = [payload_with_json_mode, payload]

        last_exc: Exception | None = None
        for attempt in range(self.cfg.max_retries + 1):
            for variant_idx, variant in enumerate(payload_variants):
                try:
                    data = self._request(variant)
                    return self._extract_content(data)
                except LLMClientError as exc:
                    last_exc = exc
                    unsupported_json_mode = (
                        expect_json
                        and variant_idx == 0
                        and "response_format" in variant
                        and _looks_like_unsupported_json_mode(str(exc))
                    )
                    if unsupported_json_mode:
                        continue
                    if attempt >= self.cfg.max_retries and variant_idx == len(payload_variants) - 1:
                        raise LLMClientError(f"LLM 调用失败: {exc}") from exc
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if attempt >= self.cfg.max_retries and variant_idx == len(payload_variants) - 1:
                        raise LLMClientError(f"LLM 调用失败: {exc}") from exc
            time.sleep(1.5 * (attempt + 1))

        raise LLMClientError(f"LLM 调用失败且超过重试次数。最后错误: {last_exc}")

    def call_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_output_tokens: int | None = None,
    ) -> dict[str, Any]:
        last_exc: Exception | None = None
        raw = ""
        for attempt in range(self.cfg.max_retries + 1):
            raw = self.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                expect_json=True,
                max_output_tokens=max_output_tokens,
            )
            try:
                return self._parse_json(raw)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt >= self.cfg.max_retries:
                    break
                time.sleep(1.2 * (attempt + 1))

        if raw.strip():
            # 修复流程改用 expect_json=False，避免 response_format 参数再次导致问题
            repaired = self.call(
                system_prompt="You repair malformed JSON. Return one valid JSON object only. Do not add explanations.",
                user_prompt=f"The following text is intended to be a JSON object but may be malformed.\nRepair it into valid JSON without changing the meaning.\n\nMalformed text:\n{raw}",
                expect_json=False,
                max_output_tokens=max_output_tokens,
            )
            try:
                return self._parse_json(repaired)
            except Exception as exc:  # noqa: BLE001
                raise LLMClientError(
                    f"JSON 解析失败，且修复失败。原始输出片段: {raw[:200]}"
                ) from exc

        raise LLMClientError(f"JSON 解析失败。最后错误: {last_exc}")

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.cfg.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.cfg.timeout_sec) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise LLMClientError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LLMClientError(f"网络错误: {exc}") from exc

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise LLMClientError(f"响应非 JSON: {response_body[:300]}") from exc

    @staticmethod
    def _extract_content(response: dict[str, Any]) -> str:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMClientError(f"响应缺少 `choices`: {response}")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise LLMClientError(f"LLM 返回空 content: {message}")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
            if chunks:
                return "\n".join(chunks)
        raise LLMClientError(f"无法解析响应 content: {message}")

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        text = text.strip()
        if not text:
            raise LLMClientError("LLM 返回空字符串，无法解析 JSON。")

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # 贪婪匹配 `.*`，确保捕获嵌套对象的最外层 `}`，而非第一个 `}`
        fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
        if fence_match:
            try:
                parsed = json.loads(fence_match.group(1))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed

        raise LLMClientError(f"JSON 解析失败: {text[:300]}")

    def _repair_json_with_llm(
        self,
        *,
        raw_text: str,
        max_output_tokens: int | None = None,
    ) -> str:
        repair_system = (
            "You repair malformed JSON. Return one valid JSON object only. "
            "Do not add explanations."
        )
        repair_user = f"""
The following text is intended to be a JSON object but may be malformed.
Repair it into valid JSON without changing the meaning.

Malformed text:
{raw_text}
        """.strip()
        return self.call(
            system_prompt=repair_system,
            user_prompt=repair_user,
            expect_json=False,
            max_output_tokens=max_output_tokens,
        )


def _looks_like_unsupported_json_mode(error_text: str) -> bool:
    lowered = error_text.lower()
    keywords = [
        "response_format",
        "json_object",
        "unsupported",
        "not supported",
        "invalid parameter",
        "unknown parameter",
    ]
    return any(keyword in lowered for keyword in keywords)
