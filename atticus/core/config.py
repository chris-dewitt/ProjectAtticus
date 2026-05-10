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


class MemoryConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    backend: str = "sqlite"
    sqlite_path: str = "data/atticus_memory.sqlite3"
    allow_forget: bool = True


class VoiceConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    spoken_responses: bool = False
    muted: bool = False
    tts_engine: str = "pyttsx3"
    tts_rate: int | None = None


class ToolsConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    assistant: AssistantConfig = Field(default_factory=AssistantConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)


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
