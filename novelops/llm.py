from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ConfigError, read_json
from .paths import CONFIG_DIR


STAGES = {
    "planner",
    "chapter_intent",
    "scene_chain",
    "draft_v1",
    "commercial_rewrite",
    "humanize",
    "reviewer",
    "revision",
    "scout",
}


@dataclass(frozen=True)
class LLMSettings:
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    base_url: str | None = None
    api_key_env: str = "OPENAI_API_KEY"
    api_key: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4000
    timeout: float | None = 120.0
    retries: int = 0
    response_format: dict[str, Any] | None = None

    @property
    def resolved_api_key(self) -> str | None:
        return self.api_key or os.getenv(self.api_key_env)

    def masked(self) -> dict[str, Any]:
        data = {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
            "api_key": "***" if self.resolved_api_key else None,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "retries": self.retries,
            "response_format": self.response_format,
        }
        return {key: value for key, value in data.items() if value is not None}


def _config_path() -> Path:
    return Path(os.getenv("NOVELOPS_MODEL_CONFIG", CONFIG_DIR / "models.json"))


def load_model_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or _config_path()
    if not config_path.exists():
        return {}
    return read_json(config_path)


def settings_for_stage(stage: str | None = None, path: Path | None = None) -> LLMSettings:
    stage_name = stage or "draft_v1"
    config = load_model_config(path)
    defaults = dict(config.get("defaults", {}))
    role = _role_for_stage(stage_name)
    role_config = dict(config.get(role, {})) if role else {}
    stage_config = dict(config.get(stage_name, {}))
    merged = defaults | role_config | stage_config
    merged = _apply_env_fallbacks(merged)
    allowed = {field.name for field in LLMSettings.__dataclass_fields__.values()}
    filtered = {key: value for key, value in merged.items() if key in allowed}
    return LLMSettings(**filtered)


def has_live_config(stage: str | None = None, path: Path | None = None) -> bool:
    settings = settings_for_stage(stage, path)
    return bool(settings.model and settings.resolved_api_key)


def _role_for_stage(stage: str) -> str | None:
    if stage in {"chapter_intent", "scene_chain", "planner"}:
        return "planner"
    if stage in {"draft_v1", "commercial_rewrite", "humanize", "revision"}:
        return "generator"
    if stage == "reviewer":
        return "reviewer"
    if stage == "scout":
        return "scout"
    return None


def _first_env(names: list[str]) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _apply_env_fallbacks(config: dict[str, Any]) -> dict[str, Any]:
    merged = dict(config)
    if not merged.get("api_key"):
        merged["api_key"] = _first_env(["NOVELOPS_API_KEY", "OPENAI_API_KEY", "API_KEY"])
    if not merged.get("base_url"):
        merged["base_url"] = _first_env(["NOVELOPS_BASE_URL", "OPENAI_BASE_URL", "BASE_URL"])
    if not merged.get("model"):
        merged["model"] = _first_env(["NOVELOPS_MODEL", "OPENAI_MODEL", "MODEL"])
    return merged


def _mock_response(prompt: str, stage: str | None = None) -> str:
    stage_name = stage or "draft_v1"
    if stage_name in {"chapter_intent", "scene_chain", "reviewer"}:
        if stage_name == "reviewer":
            return json.dumps(
                {
                    "score": 86,
                    "passed": True,
                    "issues": [],
                    "recommendations": ["保持章尾钩子清晰。"],
                    "scores": {
                        "hook": 88,
                        "conflict": 84,
                        "consistency": 86,
                        "continuity": 86,
                        "ai_trace": 90,
                        "retention": 85,
                        "risk": 92,
                    },
                    "revision_tasks": [],
                    "suggested_action": "accept",
                },
                ensure_ascii=False,
            )
        return json.dumps({"mock": True, "stage": stage_name, "summary": prompt[:120]}, ensure_ascii=False)
    return "NO_LLM_MOCK: " + prompt[:200].strip()


def _redact(text: str, secret: str | None) -> str:
    if secret:
        text = text.replace(secret, "***")
    return re.sub(r"(api[_-]?key[\"'=:\s]+)[^,\s}]+", r"\1***", text, flags=re.I)


def _response_format(schema: dict[str, Any] | None) -> dict[str, Any]:
    if not schema:
        return {"type": "json_object"}
    if schema.get("type") in {"json_object", "json_schema"}:
        return schema
    return {
        "type": "json_schema",
        "json_schema": {
            "name": str(schema.get("title") or "novelops_response"),
            "strict": True,
            "schema": schema,
        },
    }


class LLMClient:
    def __init__(
        self,
        settings: LLMSettings | None = None,
        no_llm: bool = False,
        config_path: Path | None = None,
    ) -> None:
        self.settings = settings
        self.no_llm = no_llm
        self.config_path = config_path
        self.last_fallback_reason: str | None = None
        self.last_used_mock: bool = False
        self.live_call_count = 0

    def settings_for(self, stage: str | None = None) -> LLMSettings:
        return self.settings or settings_for_stage(stage, self.config_path)

    def complete(
        self,
        prompt: str,
        system: str | None = None,
        stage: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        self.last_fallback_reason = None
        self.last_used_mock = False
        if self.no_llm:
            return self._fallback(prompt, stage, "no_llm")

        settings = self.settings_for(stage)
        api_key = settings.resolved_api_key
        if not api_key:
            return self._fallback(prompt, stage, f"missing_api_key:{settings.api_key_env}")

        try:
            from openai import OpenAI
        except ImportError as exc:
            return self._fallback(prompt, stage, f"missing_openai_sdk:{exc}")

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        client_kwargs: dict[str, Any] = {
            "api_key": api_key,
            "timeout": settings.timeout,
            "max_retries": max(0, int(settings.retries)),
        }
        if settings.base_url:
            client_kwargs["base_url"] = settings.base_url

        kwargs: dict[str, Any] = {
            "model": settings.model,
            "messages": messages,
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens,
        }
        final_response_format = response_format or settings.response_format
        if final_response_format:
            kwargs["response_format"] = final_response_format

        try:
            response = OpenAI(**client_kwargs).chat.completions.create(**kwargs)
            content = str(response.choices[0].message.content or "").strip()
            if not content:
                return self._fallback(prompt, stage, "empty_llm_response")
            self.live_call_count += 1
            return content
        except Exception as exc:
            masked = settings.masked()
            reason = f"llm_call_failed:{masked}:{_redact(str(exc), api_key)}"
            return self._fallback(prompt, stage, reason)

    def complete_json(
        self,
        prompt: str,
        system: str | None = None,
        stage: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response_format = _response_format(schema)
        raw = self.complete(prompt, system=system, stage=stage, response_format=response_format)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, flags=re.S)
            if not match:
                raise ConfigError(f"LLM returned invalid JSON for {stage or 'unknown'}: {raw[:300]}")
            try:
                value = json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise ConfigError(f"LLM returned invalid JSON for {stage or 'unknown'}: {exc}") from exc
        if not isinstance(value, dict):
            raise ConfigError(f"LLM JSON for {stage or 'unknown'} must be an object.")
        return value

    def _fallback(self, prompt: str, stage: str | None, reason: str) -> str:
        self.last_fallback_reason = reason
        self.last_used_mock = True
        return _mock_response(prompt, stage)
