from __future__ import annotations

import os
import warnings
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

from atticus.core.errors import ConfigurationError


class AssistantConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = "Atticus"
    user_address: str = "Boss"
    default_mode: str = "default"
    default_provider: str = "openai"
    repo_path: str | None = None


class ProviderOpenAIConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"
    timeout_seconds: int = 60


class ProviderAnthropicConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    model: str = "claude-3-5-sonnet-latest"
    api_key_env: str = "ANTHROPIC_API_KEY"
    timeout_seconds: int = 60


class ProviderGeminiConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    model: str = "gemini-1.5-flash"
    api_key_env: str = "GEMINI_API_KEY"
    timeout_seconds: int = 60


class ProvidersRoutingConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    automatic: bool = True
    default_provider: str = "openai"
    allow_manual_override: bool = True


class ProvidersConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    routing: ProvidersRoutingConfig = Field(default_factory=ProvidersRoutingConfig)
    openai: ProviderOpenAIConfig = Field(default_factory=ProviderOpenAIConfig)
    anthropic: ProviderAnthropicConfig = Field(default_factory=ProviderAnthropicConfig)
    gemini: ProviderGeminiConfig = Field(default_factory=ProviderGeminiConfig)


class PrivacyConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    memory_enabled: bool = True
    store_raw_conversations: bool = False
    store_summaries: bool = True
    ask_before_sending_files_to_cloud: bool = True
    ask_before_open_url: bool = True


class MemoryConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    backend: str = "sqlite"
    sqlite_path: str = "data/atticus_memory.sqlite3"
    allow_forget: bool = True
    auto_summarize: bool = True
    """When true, write local session summaries periodically and on exit (never raw transcripts)."""
    auto_summarize_every_n_turns: int = 6
    """User turns between automatic summary writes; also summarizes on clean /exit when due."""
    summary_max_chars: int = 900


class VoiceConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    spoken_responses: bool = False
    muted: bool = False
    tts_engine: str = "pyttsx3"
    tts_rate: int | None = None
    # Phase 4 — local STT (Vosk + microphone)
    stt_engine: str = "none"
    """none | vosk | local (local is treated as vosk)."""
    push_to_talk_default_seconds: float = 8.0
    vosk_model_path: str | None = None
    """Directory containing Vosk model (e.g. vosk-model-small-en-us-0.15)."""
    microphone_device: str | None = None
    """Optional sounddevice device name or integer index as string."""
    sample_rate_hz: int = 16000
    # Phase 5 — wake phrase (still local; no cloud audio)
    wake_listen_seconds: float = 12.0
    wake_command_seconds: float = 10.0
    wake_phrases: list[str] = Field(
        default_factory=lambda: [
            "Atticus",
            "Hey Atticus",
            "Atticus please",
            "Atticus, old son",
        ]
    )
    wake_sensitivity: float = 0.35
    """0=lenient substring match, 1=stricter (reserved for future scoring)."""


class ToolsShellConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    require_confirmation: bool = True
    allow_patch_apply: bool = True
    allow_test_commands: bool = True
    test_timeout_seconds: int = 120


class ToolsFilesConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    require_confirmation_for_edits: bool = True
    max_read_bytes: int = 400_000
    max_search_files: int = 2000


class ToolsBrowserConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    require_confirmation: bool = True
    allowed_hosts: list[str] = Field(default_factory=list)
    """Empty = any non-local http(s) host after approval; non-empty = host allowlist."""
    max_response_bytes: int = 500_000
    citation_dir: str = "data/citations"
    user_agent: str = "ProjectAtticus/1.0 (+local; Boss-approved fetch)"


class ToolsEmailConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    require_confirmation_for_send: bool = True
    # Gmail OAuth (optional ``.[gmail]`` extra)
    gmail_client_secrets_path: str | None = None
    """Path to Google OAuth desktop client secrets JSON (never commit real secrets)."""
    gmail_token_path: str = "data/gmail_token.json"
    """Cached user token path (under data/; gitignored)."""
    gmail_inbox_limit: int = 10
    gmail_scopes_readonly: list[str] = Field(
        default_factory=lambda: ["https://www.googleapis.com/auth/gmail.readonly"]
    )
    gmail_scopes_compose: list[str] = Field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.compose",
        ]
    )


class ToolsCalendarConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    require_confirmation_for_write: bool = True
    client_secrets_path: str | None = None
    """OAuth desktop client JSON; falls back to tools.email.gmail_client_secrets_path when null."""
    token_path: str = "data/calendar_token.json"
    calendar_id: str = "primary"
    list_days: int = 7
    max_events: int = 20
    scopes_readonly: list[str] = Field(
        default_factory=lambda: ["https://www.googleapis.com/auth/calendar.readonly"]
    )
    scopes_write: list[str] = Field(
        default_factory=lambda: ["https://www.googleapis.com/auth/calendar.events"]
    )


class ToolsGitHubConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    token_env: str = "GITHUB_TOKEN"
    repo_list_limit: int = 25
    pr_list_limit: int = 20


class ToolsConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    approved_paths: list[str] = Field(default_factory=list)
    shell: ToolsShellConfig = Field(default_factory=ToolsShellConfig)
    files: ToolsFilesConfig = Field(default_factory=ToolsFilesConfig)
    browser: ToolsBrowserConfig = Field(default_factory=ToolsBrowserConfig)
    email: ToolsEmailConfig = Field(default_factory=ToolsEmailConfig)
    calendar: ToolsCalendarConfig = Field(default_factory=ToolsCalendarConfig)
    github: ToolsGitHubConfig = Field(default_factory=ToolsGitHubConfig)


class ApiConfig(BaseModel):
    """Optional Track B local HTTP API (health/readiness in M0)."""

    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    docs_enabled: bool = False


class TelemetryConfig(BaseModel):
    """Lightweight telemetry hooks; OTel exporter is deferred."""

    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    service_name: str = "project-atticus"
    environment: str = "local"
    log_level: str = "INFO"
    emit_stderr: bool = False
    redact_keys: list[str] = Field(
        default_factory=lambda: [
            "api_key",
            "authorization",
            "password",
            "secret",
            "token",
            "access_token",
            "refresh_token",
            "client_secret",
        ]
    )


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    assistant: AssistantConfig = Field(default_factory=AssistantConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)


def resolve_config_path() -> Path:
    raw = os.environ.get("ATTICUS_CONFIG_PATH", "config/atticus.yaml")
    return Path(raw).expanduser()


def load_app_config(*, config_path: Path | None = None) -> tuple[AppConfig, Path]:
    """Load YAML config; merge with environment (.env loaded first). Returns resolved file path."""
    load_dotenv()
    path = (config_path or resolve_config_path()).expanduser()
    if not path.is_file():
        example = Path("config/atticus.example.yaml")
        if example.is_file():
            warnings.warn(
                "config/atticus.yaml not found; using config/atticus.example.yaml. "
                "Copy the example to config/atticus.yaml for local overrides.",
                stacklevel=2,
            )
            path = example.resolve()
        else:
            raise ConfigurationError(
                f"Config file not found: {path}. Copy config/atticus.example.yaml to config/atticus.yaml."
            )
    else:
        path = path.resolve()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in {path}: {exc}") from exc
    try:
        return AppConfig.model_validate(data), path
    except Exception as exc:
        raise ConfigurationError(f"Invalid config structure in {path}: {exc}") from exc


def load_config(*, config_path: Path | None = None) -> AppConfig:
    """Backward-compatible helper returning only the parsed config."""
    return load_app_config(config_path=config_path)[0]


def resolve_repo_root(cfg: AppConfig, *, config_file: Path | None = None) -> Path:
    """Directory containing prompts/ and docs/; used to load persona files."""
    env_root = os.environ.get("ATTICUS_REPO_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    if cfg.assistant.repo_path:
        return Path(cfg.assistant.repo_path).expanduser().resolve()
    if config_file is not None:
        # config/atticus.yaml -> repo root is parent of config/
        if config_file.name and config_file.parent.name.lower() == "config":
            return config_file.parent.parent.resolve()
    return Path.cwd().resolve()
