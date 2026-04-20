# Derek Agent Runner

基於 Agno Framework 的 Agent Runner，具有 TUI (Terminal User Interface) 介面、MCP Client 支援、多 Agent 切換能力，以及網路搜尋功能。

## 功能特色

- **核心引擎**：基於 Agno Framework，支援 Tools 和 MCP Servers
- **多 Agent 支援**：可切換不同 Agent 配置
- **網路搜尋**：支援 Tavily、DuckDuckGo、WebSearch（含多後端）
- **MCP Client**：連接外部 MCP Servers（如 filesystem, github 等）
- **TUI 介面**：現代化的終端介面（使用 Textual）
- **本地儲存**：使用 SQLite 儲存對話歷史，無需外部資料庫
- **設定檔優先**：所有設定使用 YAML 檔案管理
- **整合 Logging**：使用 Agno 內建的 Rich 彩色日誌系統，與 Agent 輸出風格統一

## 專案結構

```
derek-agent/
├── src/
│   ├── core/               # 核心引擎（與介面分離）
│   │   ├── config.py         # 設定管理
│   │   ├── skill_registry.py # Skill 註冊中心
│   │   ├── mcp_client.py     # MCP Client 管理
│   │   ├── agent_manager.py  # Agent 管理
│   │   └── agent_runner.py   # 執行引擎
│   ├── tools/            # 核心工具（固定功能）
│   │   └── web_search.py     # 網路搜尋工具工廠
│   ├── storage/          # 本地儲存
│   │   ├── base.py           # 儲存介面
│   │   └── sqlite.py         # SQLite 實作
│   ├── interface/        # TUI 介面層
│   │   ├── app.py            # 主應用
│   │   ├── screens/          # 畫面
│   │   └── widgets/          # 元件
│   ├── cli/              # CLI 互動式設定精靈
│   │   ├── models_cmd.py     # derek-agent models
│   │   └── tools_cmd.py      # derek-agent tools
│   └── skills/           # 可擴充 Skills
├── .derek-agent/         # 本地設定目錄（gitignored）
│   ├── settings.yaml       # 全域設定
│   ├── agents.yaml         # Agent 定義
│   └── data/               # SQLite DB
└── main.py               # 入口點
```

## 安裝

```bash
uv sync
```

## 設定目錄

| 情境 | 路徑 |
|------|------|
| 開發（預設） | `repo/.derek-agent/`（透過 `script/server` 或 `DEREK_AGENT_CONFIG_DIR`） |
| 正式安裝 | `~/.derek-agent/` |
| 自訂 | `DEREK_AGENT_CONFIG_DIR=/your/path` |

## 使用方式

### 啟動 TUI（開發）

```bash
./script/server
# 或
DEREK_AGENT_CONFIG_DIR=.derek-agent uv run python main.py
```

### 設定模型 Provider

```bash
uv run python main.py models
```

### 設定網路搜尋工具

```bash
uv run python main.py tools websearch
```

### 快捷鍵

| 快捷鍵 | 功能 |
|--------|------|
| `q` | 退出程式 |
| `a` | 切換 Agent |
| `n` | 開始新對話 |
| `h` | 顯示對話歷史 |
| `?` | 顯示幫助 |
| `Enter` | 發送訊息 |
| `Shift+Enter` | 輸入多行文字 |

## 設定檔

### agents.yaml

```yaml
agents:
  - id: default
    name: 通用助手
    model: openai:gpt-4o
    system_prompt: "你是一個有用的 AI 助手。請用繁體中文回答。"
    description: "適合各種日常任務的通用助手"
    skills: []
    mcp_servers: []
    search:
      enabled: true          # 啟用網路搜尋（使用全域設定的 provider）

  - id: coder
    name: 程式助手
    model: anthropic:claude-3-5-sonnet
    system_prompt: "你是專業的程式開發助手。請用繁體中文回答。"
    skills: []
    mcp_servers:
      - name: filesystem
        command: "npx -y @modelcontextprotocol/server-filesystem /path"
    search:
      enabled: true
      provider: tavily        # 覆寫全域設定，指定特定 provider
```

### settings.yaml

```yaml
default_agent: default
storage:
  type: sqlite
  path: /path/to/.derek-agent/data/derek-agent.db
ui:
  theme: dark
  language: zh-TW
web_search:
  provider: duckduckgo        # tavily | duckduckgo | websearch
  api_key: null               # Tavily 需要填入或使用 ${TAVILY_API_KEY}
  backend: null               # websearch provider 的後端選項
logging:
  level: info                 # debug | info | warning | error
  console:
    enabled: true             # 啟用 console 輸出
    color: true               # Rich 彩色輸出
  file:
    enabled: false            # 啟用檔案記錄
    path: ~/.derek-agent/logs/derek-agent.log  # 預設路徑
    max_bytes: 10485760       # 10MB rotation 大小
    backup_count: 5           # 保留備份數量
```

### 支援的搜尋 Provider

| Provider | API Key | 說明 |
|----------|---------|------|
| `duckduckgo` | 不需要 | 隱私優先，預設選項 |
| `tavily` | 需要 | AI 最佳化搜尋，準確度高 |
| `websearch` | 不需要 | 多後端（google/bing/brave/yandex/yahoo） |

## 支援的模型格式

- `openai:gpt-4o` — OpenAI GPT-4o
- `openai:gpt-4o-mini` — OpenAI GPT-4o Mini
- `anthropic:claude-3-5-sonnet` — Anthropic Claude 3.5 Sonnet
- `minimax:MiniMax-M2.7` — Minimax M2.7

## 開發計劃

- [x] 專案結構與設定載入
- [x] 核心引擎 (AgentManager, MCPClient, SkillRegistry)
- [x] 儲存層 (SQLite)
- [x] TUI 介面
- [x] 網路搜尋工具（Tavily / DuckDuckGo / WebSearch）
- [x] 互動式 CLI 設定精靈（models / tools）
- [ ] 對話歷史畫面
- [ ] 設定編輯畫面
- [ ] 測試覆蓋

## 授權

MIT
