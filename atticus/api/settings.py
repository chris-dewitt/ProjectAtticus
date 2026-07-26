"""Read-only settings surface for Track A GUI / Track B operators."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from atticus.core.errors import AtticusError
from atticus.core.telemetry import get_telemetry


class SettingsUpdateDenied(AtticusError):
    code = "settings_update_denied"
    status_code = 403


class SettingsPatchRequest(BaseModel):
    """Only non-secret operator toggles are mutable via API."""

    model_config = ConfigDict(extra="forbid")
    spoken_responses: bool | None = None
    muted: bool | None = None
    default_mode: str | None = Field(default=None, max_length=64)
    default_provider: str | None = Field(default=None, max_length=32)
    ui_enabled: bool | None = None
    docs_enabled: bool | None = None


def build_settings_router() -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["settings"])

    @router.get("/settings")
    async def get_settings(request: Request) -> dict[str, Any]:
        cfg = request.app.state.config
        return {
            "assistant": {
                "name": cfg.assistant.name,
                "user_address": cfg.assistant.user_address,
                "default_mode": cfg.assistant.default_mode,
                "default_provider": cfg.providers.routing.default_provider,
            },
            "privacy": {
                "memory_enabled": cfg.privacy.memory_enabled,
                "store_raw_conversations": cfg.privacy.store_raw_conversations,
                "store_summaries": cfg.privacy.store_summaries,
                "ask_before_sending_files_to_cloud": cfg.privacy.ask_before_sending_files_to_cloud,
            },
            "voice": {
                "spoken_responses": cfg.voice.spoken_responses,
                "muted": cfg.voice.muted,
                "tts_engine": cfg.voice.tts_engine,
                "stt_engine": cfg.voice.stt_engine,
            },
            "api": {
                "host": cfg.api.host,
                "port": cfg.api.port,
                "ui_enabled": cfg.api.ui_enabled,
                "docs_enabled": cfg.api.docs_enabled,
                "auth_required": bool(cfg.api.api_token_env),
                "rate_limit_per_minute": cfg.api.rate_limit_per_minute,
            },
            "providers": {
                "automatic": cfg.providers.routing.automatic,
                "default_provider": cfg.providers.routing.default_provider,
                "allow_manual_override": cfg.providers.routing.allow_manual_override,
                "fallback_order": list(cfg.providers.routing.fallback_order),
                "openai_enabled": cfg.providers.openai.enabled,
                "anthropic_enabled": cfg.providers.anthropic.enabled,
                "gemini_enabled": cfg.providers.gemini.enabled,
            },
            "sandbox": {
                "enabled": cfg.sandbox.enabled,
                "timeout_seconds": cfg.sandbox.timeout_seconds,
                "allow_shell": cfg.sandbox.allow_shell,
            },
            "telemetry": {
                "enabled": cfg.telemetry.enabled,
                "service_name": cfg.telemetry.service_name,
                "environment": cfg.telemetry.environment,
                "otel_exporter": cfg.telemetry.otel_exporter,
            },
        }

    @router.patch("/settings")
    async def patch_settings(request: Request, body: SettingsPatchRequest) -> dict[str, Any]:
        cfg = request.app.state.config
        changed: list[str] = []
        if body.spoken_responses is not None:
            cfg.voice.spoken_responses = body.spoken_responses
            changed.append("voice.spoken_responses")
        if body.muted is not None:
            cfg.voice.muted = body.muted
            changed.append("voice.muted")
        if body.default_mode is not None:
            cfg.assistant.default_mode = body.default_mode
            changed.append("assistant.default_mode")
        if body.default_provider is not None:
            key = body.default_provider.lower()
            if key not in {"openai", "anthropic", "gemini", "mock"}:
                raise SettingsUpdateDenied("Unsupported default_provider.")
            if not cfg.providers.routing.allow_manual_override and key != cfg.providers.routing.default_provider:
                raise SettingsUpdateDenied("Manual provider override disabled.")
            cfg.providers.routing.default_provider = key
            request.app.state.default_provider = key
            changed.append("providers.routing.default_provider")
        if body.ui_enabled is not None:
            cfg.api.ui_enabled = body.ui_enabled
            changed.append("api.ui_enabled")
        if body.docs_enabled is not None:
            cfg.api.docs_enabled = body.docs_enabled
            changed.append("api.docs_enabled")
        if not changed:
            raise SettingsUpdateDenied("No mutable settings provided.")
        get_telemetry().emit("api.settings_patched", fields=changed)
        return {"changed": changed, "settings": (await get_settings(request))}

    return router
