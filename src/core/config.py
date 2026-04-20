"""Configuration management for Derek Agent Runner."""

import logging
import os
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import yaml
from agno.utils.log import logger as agno_logger
from pydantic import BaseModel, Field

# Re-export Agno logger for backward compatibility
logger = agno_logger


class WebSearchConfig(BaseModel):
    """Global web search tool configuration."""

    provider: str = "duckduckgo"
    api_key: str | None = None
    backend: str | None = None


class AgentSearchConfig(BaseModel):
    """Per-agent web search overrides."""

    enabled: bool = True
    provider: str | None = None
    api_key: str | None = None


class AgentShellConfig(BaseModel):
    """Per-agent shell tool overrides."""

    enabled: bool = True
    base_dir: str | None = None


class AgentFileConfig(BaseModel):
    """Per-agent file tool overrides."""

    enabled: bool = True
    base_dir: str | None = None


class AgentCrawlerConfig(BaseModel):
    """Per-agent crawler tool overrides."""

    enabled: bool = True
    output_format: str = "markdown"  # txt, json, xml, markdown, csv, html
    target_language: str | None = None  # ISO 639-1 format, e.g., "zh", "en"
    max_urls: int = 10  # Max URLs to crawl per request


class AgentPythonConfig(BaseModel):
    """Per-agent Python tool overrides."""

    enabled: bool = True
    base_dir: str | None = None
    allow_package_installation: bool = True


class AgentReasoningConfig(BaseModel):
    """Per-agent reasoning tool overrides."""

    enabled: bool = True


class AgentCalculatorConfig(BaseModel):
    """Per-agent calculator tool overrides."""

    enabled: bool = True


class AgentGrepConfig(BaseModel):
    """Per-agent grep tool overrides."""

    enabled: bool = True
    base_dir: str | None = None
    max_results: int = 250
    timeout_seconds: int = 20


class MCPConfig(BaseModel):
    """MCP Server configuration."""

    name: str
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    transport: str = "stdio"


class AgentConfig(BaseModel):
    """Agent configuration."""

    model_config = {"extra": "ignore"}

    id: str
    name: str
    model: str = "openai:gpt-4o"
    system_prompt: str = "You are a helpful assistant."
    description: str | None = None
    skills: list[str] = Field(default_factory=list)
    mcp_servers: list[MCPConfig] = Field(default_factory=list)
    inherit_default_skills: bool = True
    inherit_default_mcp: bool = True
    search: AgentSearchConfig = Field(default_factory=AgentSearchConfig)
    shell: AgentShellConfig = Field(default_factory=AgentShellConfig)
    file: AgentFileConfig = Field(default_factory=AgentFileConfig)
    crawler: AgentCrawlerConfig = Field(default_factory=AgentCrawlerConfig)
    python: AgentPythonConfig = Field(default_factory=AgentPythonConfig)
    reasoning: AgentReasoningConfig = Field(default_factory=AgentReasoningConfig)
    calculator: AgentCalculatorConfig = Field(default_factory=AgentCalculatorConfig)
    grep: AgentGrepConfig = Field(default_factory=AgentGrepConfig)
    working_dir: str | None = None
    add_datetime_to_context: bool = True
    timezone: str = "Asia/Taipei"


class StorageConfig(BaseModel):
    """Storage configuration."""

    type: str = "sqlite"
    path: str | None = None
    url: str | None = None


class UIConfig(BaseModel):
    """UI configuration."""

    theme: str = "dark"
    language: str = "zh-TW"
    show_token_usage: bool = True
    mcp_activity_display_mode: str = "inline"


class TitleGenerationConfig(BaseModel):
    """Title generation configuration."""

    enabled: bool = True
    model: str | None = None  # e.g., "openai:gpt-4o-mini", None uses current agent model
    max_length: int = 20  # Max characters for generated title


class ContextCompressionConfig(BaseModel):
    """Context compression configuration."""

    enabled: bool = True              # Enable automatic context compression
    auto_trigger: bool = True         # Auto-trigger or manual only
    threshold_percent: int = 50       # Threshold percentage (1-100)
    summary_model: str | None = None  # Model for summarization, None uses current agent model
    max_summary_tokens: int = 500     # Max tokens for summary


class ConsoleLoggingConfig(BaseModel):
    """Console logging configuration."""

    enabled: bool = True
    color: bool = True               # Use Rich colored output


class FileLoggingConfig(BaseModel):
    """File logging configuration."""

    enabled: bool = False
    path: str | None = None          # Log file path, None uses default
    max_bytes: int = 10_485_760      # 10MB rotation size
    backup_count: int = 5            # Number of backup files to keep


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "info"              # debug | info | warning | error
    console: ConsoleLoggingConfig = Field(default_factory=ConsoleLoggingConfig)
    file: FileLoggingConfig = Field(default_factory=FileLoggingConfig)

    def get_level(self) -> int:
        """Get logging level as int."""
        levels = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
        }
        return levels.get(self.level.lower(), logging.INFO)


class Settings(BaseModel):
    """Global settings."""

    user_id: str = "default"
    default_agent: str = "default"
    storage: StorageConfig = Field(default_factory=StorageConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    web_search: WebSearchConfig = Field(default_factory=WebSearchConfig)
    title_generation: TitleGenerationConfig = Field(default_factory=TitleGenerationConfig)
    context_compression: ContextCompressionConfig = Field(default_factory=ContextCompressionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class Config:
    """Main configuration manager."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize configuration manager.

        Args:
            config_dir: Custom configuration directory. If None, uses platform default.
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        elif env_dir := os.environ.get("DEREK_AGENT_CONFIG_DIR"):
            self.config_dir = Path(env_dir)
        else:
            self.config_dir = Path.home() / ".derek-agent"

        self.data_dir = self.config_dir / "data"
        self.config_file = self.config_dir / "settings.yaml"
        self.agents_file = self.config_dir / "agents.yaml"

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize default storage path if not set
        self._settings: Settings | None = None
        self._agents: list[AgentConfig] | None = None

    @property
    def settings(self) -> Settings:
        """Get global settings."""
        if self._settings is None:
            self._settings = self._load_settings()
        return self._settings

    @property
    def agents(self) -> list[AgentConfig]:
        """Get all agent configurations."""
        if self._agents is None:
            self._agents = self._load_agents()
        return self._agents

    def get_agent(self, agent_id: str) -> AgentConfig | None:
        """Get agent configuration by ID."""
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        return None

    def _load_settings(self) -> Settings:
        """Load settings from YAML file."""
        if not self.config_file.exists():
            # Create default settings
            default_storage = StorageConfig(
                type="sqlite",
                path=str(self.data_dir / "derek-agent.db")
            )
            settings = Settings(storage=default_storage)
            self._save_settings(settings)
            return settings

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return Settings(**data)
        except Exception as e:
            logger.warning(f"Failed to load settings: {e}. Using defaults.")
            default_storage = StorageConfig(
                type="sqlite",
                path=str(self.data_dir / "derek-agent.db")
            )
            return Settings(storage=default_storage)

    def _save_settings(self, settings: Settings) -> None:
        """Save settings to YAML file."""
        with open(self.config_file, "w", encoding="utf-8") as f:
            yaml.dump(settings.model_dump(), f, allow_unicode=True, sort_keys=False)

    def _load_agents(self) -> list[AgentConfig]:
        """Load agent configurations from YAML file with inheritance."""
        if not self.agents_file.exists():
            # Create default agents
            default_agents = self._create_default_agents()
            self._save_agents(default_agents)
            return default_agents

        try:
            with open(self.agents_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            agents_data = data.get("agents", [])
            agents = [AgentConfig(**agent_data) for agent_data in agents_data]
            agents = self._apply_skill_inheritance(agents)
            return self._apply_mcp_inheritance(agents)
        except Exception as e:
            logger.warning(f"Failed to load agents: {e}. Using defaults.")
            return self._create_default_agents()

    def _apply_skill_inheritance(self, agents: list[AgentConfig]) -> list[AgentConfig]:
        default_agent = None
        for agent in agents:
            if agent.id == "default":
                default_agent = agent
                break

        if not default_agent or not default_agent.skills:
            return agents

        for agent in agents:
            if agent.id == "default":
                continue
            if not agent.inherit_default_skills:
                continue

            for default_skill in default_agent.skills:
                if default_skill not in agent.skills:
                    agent.skills.append(default_skill)

        return agents

    def _apply_mcp_inheritance(self, agents: list[AgentConfig]) -> list[AgentConfig]:
        """Apply MCP server inheritance from default agent to other agents.

        Rules:
        - If inherit_default_mcp is False, no inheritance
        - If an agent has an MCP server with same name as default, that server is not inherited
        - Other MCP servers from default are inherited
        """
        default_agent = None
        for agent in agents:
            if agent.id == "default":
                default_agent = agent
                break

        if not default_agent or not default_agent.mcp_servers:
            return agents

        default_mcp_names = {mcp.name for mcp in default_agent.mcp_servers}

        for agent in agents:
            if agent.id == "default":
                continue
            if not agent.inherit_default_mcp:
                continue

            # Get names of MCP servers this agent already has
            agent_mcp_names = {mcp.name for mcp in agent.mcp_servers}

            # Inherit MCP servers from default that agent doesn't have
            for default_mcp in default_agent.mcp_servers:
                if default_mcp.name not in agent_mcp_names:
                    agent.mcp_servers.append(default_mcp)

        return agents

    def _save_agents(self, agents: list[AgentConfig]) -> None:
        """Save agents to YAML file."""
        data = {"agents": [agent.model_dump() for agent in agents]}
        with open(self.agents_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def _create_default_agents(self) -> list[AgentConfig]:
        """Create default agent configurations."""
        return [
            AgentConfig(
                id="default",
                name="通用助手",
                model="openai:gpt-4o",
                system_prompt="你是一個有用的 AI 助手。請用繁體中文回答。",
                description="適合各種日常任務的通用助手",
                skills=[],
                mcp_servers=[],
            ),
            AgentConfig(
                id="coder",
                name="程式助手",
                model="openai:gpt-4o",
                system_prompt="你是一個專業的程式開發助手，擅長寫出高品質、可維護的程式碼。請用繁體中文回答。",
                description="專注於程式開發和程式碼審查",
                skills=[],
                mcp_servers=[],
            ),
        ]

    def reload(self) -> None:
        """Reload all configurations from disk."""
        self._settings = None
        self._agents = None

    def save_agent(self, agent: AgentConfig) -> None:
        """Save or update an agent configuration."""
        agents = self.agents
        # Update existing or add new
        for i, existing in enumerate(agents):
            if existing.id == agent.id:
                agents[i] = agent
                break
        else:
            agents.append(agent)
        self._save_agents(agents)
        self._agents = agents

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent configuration."""
        agents = self.agents
        original_count = len(agents)
        agents = [a for a in agents if a.id != agent_id]
        if len(agents) < original_count:
            self._save_agents(agents)
            self._agents = agents
            return True
        return False


# Global config instance with thread-safe lock
_config: Config | None = None
_config_lock = threading.Lock()


def get_config(config_dir: Path | None = None) -> Config:
    """Get global config instance (thread-safe)."""
    global _config
    if _config is None or config_dir is not None:
        with _config_lock:
            # Double-checked locking pattern
            if _config is None or config_dir is not None:
                _config = Config(config_dir)
    return _config


def reload_config() -> None:
    """Reload global config."""
    global _config
    with _config_lock:
        if _config:
            _config.reload()


def setup_logging(config: LoggingConfig | None = None, config_dir: Path | None = None) -> None:
    """Setup logging based on configuration.

    Configures both console (RichHandler) and file (RotatingFileHandler) logging
    based on the provided settings.

    Args:
        config: Logging configuration. If None, uses default from get_config().
        config_dir: Configuration directory for default log path. If None, uses get_config().config_dir.
    """
    if config is None:
        config = get_config().settings.logging

    if config_dir is None:
        config_dir = get_config().config_dir

    # Get the Agno logger
    from agno.utils.log import LOGGER_NAME

    _logger = logging.getLogger(LOGGER_NAME)
    _logger.setLevel(config.get_level())

    # Clear existing handlers to avoid duplicates
    _logger.handlers = []

    # Console logging with RichHandler
    if config.console.enabled:
        from rich.logging import RichHandler

        console_handler = RichHandler(
            show_time=False,
            rich_tracebacks=False,
            show_path=True if os.environ.get("AGNO_API_RUNTIME") == "dev" else False,
            tracebacks_show_locals=False,
        )
        console_handler.setLevel(config.get_level())
        console_handler.setFormatter(logging.Formatter("%(message)s"))
        _logger.addHandler(console_handler)

    # File logging with RotatingFileHandler
    if config.file.enabled:
        log_path = Path(config.file.path) if config.file.path else None

        if log_path is None:
            # Default log path: {config_dir}/logs/derek-agent.log
            log_path = config_dir / "logs" / "derek-agent.log"

        # Ensure log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=config.file.max_bytes,
            backupCount=config.file.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(config.get_level())
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        _logger.addHandler(file_handler)

    logger.info(f"Logging configured: level={config.level}, console={config.console.enabled}, file={config.file.enabled}")
