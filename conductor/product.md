# Derek Agent Runner

基於 Agno Framework 的本地 Agent Runner，提供終端介面的多 Agent 對話、MCP 連線與技能載入能力，讓使用者能以設定檔方式管理代理人與執行環境。

# Product Overview

## Target Users
- 需要在本機終端中使用 AI agent 的開發者。
- 想透過 YAML 設定管理多個 agent、skills 與 MCP servers 的進階使用者。
- 偏好本地儲存對話歷史，不希望依賴外部資料庫的個人或小型團隊。

## Goals
- 提供穩定、可切換多 agent 的 TUI 對話體驗。
- 讓 skills、MCP servers 與 agent 設定可以透過檔案直接維護。
- 以本地 SQLite 保留對話資料，降低部署成本與操作門檻。

## Key Features
- 基於 Agno 的 agent 執行與管理。
- Textual TUI 介面與互動式聊天畫面。
- MCP client 管理與外部 server 整合。
- Skills 註冊與 agent 能力配置。
- SQLite 對話儲存與歷史保留。

## Non-Goals
- 雲端多租戶服務與後端 SaaS 平台。
- 複雜的網頁管理後台。
- 企業級身分驗證、權限模型與集中式資料庫管理。

## Success Metrics
- 預設 agent 啟動與基本對話流程可穩定執行。
- 主要核心模組具備可重複執行的自動化測試。
- 新增或調整 agent 設定時，不需要修改核心程式碼。
