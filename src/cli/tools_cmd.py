"""Interactive `derek-agent tools` subcommands."""

from __future__ import annotations

import os
import sys

from ..tools.web_search import SUPPORTED_PROVIDERS, WEBSEARCH_BACKENDS

# ── ANSI helpers ──────────────────────────────────────────────────────────────

_USE_COLOR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(t: str) -> str:
    return _c("1", t)


def green(t: str) -> str:
    return _c("32", t)


def yellow(t: str) -> str:
    return _c("33", t)


def cyan(t: str) -> str:
    return _c("36", t)


def dim(t: str) -> str:
    return _c("2", t)


def red(t: str) -> str:
    return _c("31", t)


# ── Prompt helpers ────────────────────────────────────────────────────────────


def _prompt(msg: str, default: str = "") -> str:
    """Read a line from stdin, using default if empty."""
    hint = f" [{default}]" if default else ""
    try:
        val = input(f"{msg}{hint}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return val if val else default


def _prompt_secret(msg: str) -> str:
    """Read a password-style input (masked via getpass)."""
    import getpass
    try:
        return getpass.getpass(f"{msg}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def _choose(msg: str, options: list[str], default: int = 1) -> int:
    """Numbered menu; returns 0-based index."""
    for i, opt in enumerate(options, 1):
        print(f"  {cyan(str(i))}. {opt}")
    while True:
        raw = _prompt(msg, str(default))
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print(red(f"  請輸入 1–{len(options)} 之間的數字"))


def _yes_no(msg: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    raw = _prompt(f"{msg} [{hint}]").lower()
    if raw == "":
        return default
    return raw.startswith("y")


# ── Provider descriptions ──────────────────────────────────────────────────────

_PROVIDER_LABELS = {
    "tavily": "Tavily  (需要 API Key，AI 最佳化搜尋，推薦)",
    "duckduckgo": "DuckDuckGo  (無需 API Key，隱私優先)",
    "websearch": "WebSearch  (無需 API Key，多後端：Google / Bing / Brave / ...)",
}

_BACKEND_LABELS = {
    "duckduckgo": "DuckDuckGo",
    "google": "Google",
    "bing": "Bing",
    "brave": "Brave",
    "yandex": "Yandex",
    "yahoo": "Yahoo",
}


# ── Wizard ────────────────────────────────────────────────────────────────────


def _setup_tavily(existing_key: str | None) -> str | None:
    """Prompt for Tavily API Key. Returns stored value."""
    env_key = os.environ.get("TAVILY_API_KEY", "")
    if env_key:
        masked = env_key[:8] + "..." + env_key[-4:] if len(env_key) > 12 else "***"
        print(f"  偵測到環境變數 {cyan('TAVILY_API_KEY')}: {masked}")
        use_env = _yes_no("  使用環境變數引用（推薦）？", default=True)
        if use_env:
            print(f"  {green('✓')} 將以 {cyan('${TAVILY_API_KEY}')} 存入設定檔")
            return "${TAVILY_API_KEY}"
        else:
            print(f"  {yellow('!')} API key 將明文存入設定檔")
            return env_key
    else:
        if existing_key:
            masked = existing_key[:8] + "..." if len(existing_key) > 8 else "***"
            print(f"  已有設定的 API Key: {masked}")
            if _yes_no("  保留現有設定？", default=True):
                return existing_key
        print(f"  {yellow('!')} 未偵測到環境變數 TAVILY_API_KEY")
        print(f"  {dim('取得 API Key: https://app.tavily.com')}")
        raw_key = _prompt_secret("  請輸入 Tavily API Key")
        if not raw_key:
            print(red("  API Key 不可為空"))
            return existing_key
        print(f"  {yellow('!')} API key 將明文存入設定檔（建議改用環境變數 TAVILY_API_KEY）")
        return raw_key


def run_websearch_wizard() -> None:
    """Entry point for `derek-agent tools websearch`."""
    from ..core.config import WebSearchConfig, get_config

    print()
    print(bold("Derek Agent — 網路搜尋工具設定"))
    print("=" * 40)
    print()

    cfg = get_config()
    current = cfg.settings.web_search

    # ── 是否啟用搜尋 ─────────────────────────────────────────────────────────
    print(f"目前狀態：{'已設定 ' + cyan(current.provider) if current.provider else dim('未設定')}")
    print()

    # ── 選擇 Provider ─────────────────────────────────────────────────────────
    print("選擇搜尋工具提供者：")
    provider_list = list(SUPPORTED_PROVIDERS)
    labels = [_PROVIDER_LABELS[p] for p in provider_list]
    try:
        default_idx = provider_list.index(current.provider) + 1
    except ValueError:
        default_idx = 2  # duckduckgo
    idx = _choose("選擇", labels, default=default_idx)
    chosen_provider = provider_list[idx]
    print(f"  {green('✓')} 已選擇: {cyan(chosen_provider)}")
    print()

    # ── Provider 特定設定 ─────────────────────────────────────────────────────
    api_key = current.api_key
    backend = current.backend

    if chosen_provider == "tavily":
        api_key = _setup_tavily(current.api_key)
        backend = None

    elif chosen_provider == "duckduckgo":
        api_key = None
        backend = None
        print(f"  {green('✓')} DuckDuckGo 無需 API Key")

    elif chosen_provider == "websearch":
        api_key = None
        backend_list = list(WEBSEARCH_BACKENDS)
        backend_labels = [_BACKEND_LABELS[b] for b in backend_list]
        print("選擇搜尋後端：")
        try:
            default_backend_idx = backend_list.index(current.backend or "duckduckgo") + 1
        except ValueError:
            default_backend_idx = 1
        b_idx = _choose("選擇後端", backend_labels, default=default_backend_idx)
        backend = backend_list[b_idx]
        print(f"  {green('✓')} 後端: {cyan(backend)}")

    # ── 儲存設定 ─────────────────────────────────────────────────────────────
    new_search_config = WebSearchConfig(
        provider=chosen_provider,
        api_key=api_key,
        backend=backend,
    )

    settings = cfg.settings
    settings.web_search = new_search_config
    cfg._save_settings(settings)
    cfg._settings = settings

    print()
    print(f"  {green('✓')} 設定已儲存至 {cyan(str(cfg.config_file))}")

    # ── 建議如何啟用 ─────────────────────────────────────────────────────────
    print()
    print(bold("下一步：在 agents.yaml 中為 Agent 啟用搜尋功能"))
    print(dim("  範例："))
    print(f"""  {dim('agents:')}
  {dim('  - id: default')}
  {dim('    search:')}
  {dim('      enabled: true')}""")
    print()
    print(f"  {dim('或指定覆寫 provider：')}")
    print(f"""  {dim('    search:')}
  {dim('      enabled: true')}
  {dim('      provider: tavily')}""")

    # ── 提示快速啟用所有 Agent ────────────────────────────────────────────────
    print()
    if _yes_no("  是否將所有現有 Agent 的搜尋功能設為啟用？", default=False):
        _enable_all_agents(cfg, chosen_provider)

    print()


def _enable_all_agents(cfg, provider: str) -> None:
    """Set search.enabled=True for all agents."""
    from ..core.config import AgentSearchConfig

    try:
        agents = cfg.agents
        for agent in agents:
            agent.search = AgentSearchConfig(enabled=True)
            cfg.save_agent(agent)
        print(f"  {green('✓')} 已為 {cyan(str(len(agents)))} 個 Agent 啟用搜尋功能")
    except Exception as e:
        print(f"  {yellow('!')} 更新 agents.yaml 失敗: {e}")
        print(f"  {dim('請手動在 agents.yaml 中設定 search.enabled: true')}")
