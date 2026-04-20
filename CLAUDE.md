# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run a single test file
uv run pytest tests/test_storage_migration.py

# Run TUI (uses .derek-agent config directory when run from repo)
./script/server

# Or with explicit config dir
DEREK_AGENT_CONFIG_DIR=.derek-agent uv run python main.py

# CLI wizards
uv run python main.py models          # Configure AI model providers
uv run python main.py tools websearch # Configure web search
```

## Architecture

### Core Principle: Engine / Interface Separation

The `src/core/` modules are the engine layer — they have no Textual/TUI imports. `src/interface/` is the TUI layer that depends on core. This boundary must be preserved: core cannot import interface.

### Agent Execution Flow

1. `AgentRunner` (`src/core/agent_runner.py`) is the main orchestrator
2. It uses `AgentManager` to create/load `AgentInstance` wrappers around Agno `Agent`
3. `AgentManager.create_agent()` assembles tools from factories in `src/tools/` (web_search, shell, file, crawler)
4. MCP servers are connected via `MCPClientManager` and passed to Agno as `MCPTools`
5. Conversations are persisted via `ConversationManager` + `BaseStorage` (SQLAlchemy/SQLite)

### Tool Factories

Tools follow a factory pattern in `src/tools/`:
- Each factory (`create_shell_tool`, `create_file_tool`, etc.) receives agent config and returns an Agno tool or `None` if disabled
- Factories are called in `AgentManager.create_agent()` and assembled into a tool list passed to the Agno `Agent`

### Storage Layer

`BaseStorage` (`src/storage/base.py`) is the abstract interface. `SQLAlchemyStorage` (`src/storage/sqlalchemy_storage.py`) is the primary implementation using SQLAlchemy + aiosqlite. Legacy `sqlite.py` exists for compatibility.

Models are in `src/storage/models.py` (SQLAlchemy ORM). Migrations use Alembic (`migrations/`).

### Configuration System

YAML-based config in three files under `.derek-agent/`:
- `settings.yaml` — global settings (storage, UI, web search defaults)
- `agents.yaml` — agent definitions (model, system prompt, MCP servers, skills)
- `providers.yaml` — API credentials

Config resolution order:
1. `DEREK_AGENT_CONFIG_DIR` env var
2. `~/.derek-agent/` (production default)
3. `.derek-agent/` (repo dev default via `script/server`)

The `Config` class (`src/core/config.py`) provides Pydantic-validated access with inheritance support (default agent's skills/MCP servers can be inherited by other agents).

### Skills System

`src/core/skills.py` — skills are loaded from three directories with different visibility rules:
- **Builtin**: `src/skills/builtin/` — automatically loaded for all agents
- **User**: `~/.derek-agent/skills/` or `.derek-agent/skills/` (repo-specific)
- **Project**: `<working_dir>/.derek-agent/skills/`

User/project skills require explicit listing in `agents.yaml`. Builtin skills are always loaded.

### MCP Client

`MCPClientManager` (`src/core/mcp_client.py`) manages stdio MCP server connections. It resolves tool names using prefix convention `{server_name}_{tool_name}`. Global singleton via `get_mcp_manager()`.

### Context Compression

`CompressionManager` (`src/core/compression_manager.py`) handles context window management. When conversation exceeds ~50% of model context window, it generates a summary using LLM and replaces archived messages with the summary.

### Interface (TUI)

Textual-based. Key files:
- `src/interface/app.py` — main `DerekAgentApp` with key bindings
- `src/interface/screens/chat_screen.py` — main chat UI
- `src/interface/screens/agent_select.py` — agent switcher
- `src/interface/screens/history_screen.py` — conversation history

The interface communicates with the engine via `AgentRunner` which is instantiated on mount.

### Global Singletons

Several globals exist (`_manager`, `_runner`, `_config`) accessed via getter functions. These are NOT thread-safe — concurrent access during initialization may create multiple instances. This is acceptable for single-threaded CLI/TUI usage but would need locking if used in a multi-threaded context.

## Key Patterns

- **Model string format**: `provider:model_id` (e.g., `openai:gpt-4o`, `anthropic:claude-3-5-sonnet`)
- **Tool name resolution**: MCP tools use `{server_name}_{tool_name}` prefix; builtin tools have their own prefixes (`shell_tools_`, `file_tools_`, `duckduckgo_`, etc.)
- **Agent instance cleanup**: `AgentInstance.cleanup()` closes all MCP connections; always call via `AgentManager.unload_agent()` or `unload_all()`
