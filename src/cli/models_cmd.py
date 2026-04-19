"""Interactive `derek-agent models` setup wizard."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ..core.providers import (
    MINIMAX_DEFAULT_BASE_URL,
    MINIMAX_MODELS,
    DefaultsConfig,
    ModelInfo,
    ProviderConfig,
    ProvidersConfig,
    get_providers_file,
    load_providers,
    save_providers,
)

# ── ANSI helpers ─────────────────────────────────────────────────────────────

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


# ── Provider wizards ──────────────────────────────────────────────────────────


def _setup_minimax(existing: ProviderConfig | None) -> ProviderConfig:
    """Interactive wizard for Minimax provider."""
    print()
    print(bold("【Minimax 設定】"))
    print()

    # ── API Key ──────────────────────────────────────────────────────────────
    env_key = os.environ.get("MINIMAX_API_KEY", "")
    if env_key:
        masked = env_key[:8] + "..." + env_key[-4:] if len(env_key) > 12 else "***"
        print(f"  偵測到環境變數 {cyan('MINIMAX_API_KEY')}: {masked}")
        use_env = _yes_no("  使用環境變數引用（推薦）？", default=True)
        if use_env:
            api_key_stored = "${MINIMAX_API_KEY}"
            print(f"  {green('✓')} 將以 {cyan('${MINIMAX_API_KEY}')} 存入設定檔")
        else:
            api_key_stored = env_key
            print(f"  {yellow('!')} API key 將明文存入設定檔")
    else:
        print(f"  {yellow('!')} 未偵測到環境變數 MINIMAX_API_KEY")
        raw_key = _prompt_secret("  請輸入 API Key")
        if not raw_key:
            print(red("  API Key 不可為空，略過 Minimax 設定"))
            return existing or ProviderConfig()
        api_key_stored = raw_key
        print(f"  {yellow('!')} API key 將明文存入設定檔（建議改用環境變數 MINIMAX_API_KEY）")

    # ── Base URL ─────────────────────────────────────────────────────────────
    print()
    print(f"  API Base URL（預設: {dim(MINIMAX_DEFAULT_BASE_URL)}）")
    print(f"  {dim('中國節點: https://api.minimaxi.com/anthropic')}")
    custom_url = _prompt("  輸入 URL 或直接按 Enter 使用預設", default="")
    base_url = custom_url if custom_url else MINIMAX_DEFAULT_BASE_URL
    print(f"  {green('✓')} Base URL: {cyan(base_url)}")

    # ── Default model ─────────────────────────────────────────────────────────
    print()
    print("  可用模型：")
    model_labels = [
        f"{m.name}  {dim(f'{m.context_window//1000}k context')}{'  [reasoning]' if m.reasoning else ''}"
        for m in MINIMAX_MODELS
    ]
    idx = _choose("  選擇預設模型", model_labels, default=1)
    chosen_model = MINIMAX_MODELS[idx]
    print(f"  {green('✓')} 預設模型: {cyan(chosen_model.name)}")

    return ProviderConfig(
        api_key=api_key_stored,
        base_url=base_url,
        api_protocol="anthropic",
        models=[m for m in MINIMAX_MODELS],
    ), chosen_model


# ── Agents.yaml sync ─────────────────────────────────────────────────────────


def _sync_agents_model(model_ref: str) -> None:
    """Update every agent in agents.yaml to use model_ref."""
    import sys

    from ..core.config import get_config

    try:
        cfg = get_config()
        agents = cfg.agents
        for agent in agents:
            agent.model = model_ref
        for agent in agents:
            cfg.save_agent(agent)
        print(f"  {green('✓')} 已更新 {cyan(str(len(agents)))} 個 Agent 使用 {cyan(model_ref)}")
    except Exception as e:
        print(f"  {yellow('!')} 更新 agents.yaml 失敗: {e}")
        print(f"  {dim('請手動修改 agents.yaml 的 model 欄位')}")


# ── Main entry ────────────────────────────────────────────────────────────────

PROVIDERS = [
    ("Minimax", "minimax", _setup_minimax),
]


def run_models_wizard() -> None:
    """Entry point for `derek-agent models`."""
    print()
    print(bold("Derek Agent — 模型設定精靈"))
    print("=" * 40)
    print()

    current = load_providers()
    providers_file = get_providers_file()

    print("請選擇要設定的 Provider：")
    labels = [name for name, _, _ in PROVIDERS]
    idx = _choose("選擇", labels, default=1)

    _, provider_key, wizard_fn = PROVIDERS[idx]

    existing = current.providers.get(provider_key)
    result = wizard_fn(existing)

    if isinstance(result, tuple):
        prov_config, chosen_model = result
    else:
        prov_config = result
        chosen_model = prov_config.models[0] if prov_config.models else None

    # Update config
    current.providers[provider_key] = prov_config
    if chosen_model:
        current.defaults = DefaultsConfig(
            provider=provider_key,
            model=chosen_model.id,
        )

    save_providers(current)

    print()
    print(f"  {green('✓')} 設定已儲存至 {cyan(str(providers_file))}")

    model_ref = f"{provider_key}:{chosen_model.id}" if chosen_model else f"{provider_key}:default"

    # ── Offer to sync agents.yaml ─────────────────────────────────────────────
    print()
    if _yes_no(f"  是否將所有 Agent 的模型切換為 {cyan(model_ref)}？", default=True):
        _sync_agents_model(model_ref)
    else:
        print()
        print(dim("  手動在 agents.yaml 中設定："))
        print(f"    model: \"{cyan(model_ref)}\"")

    print()
