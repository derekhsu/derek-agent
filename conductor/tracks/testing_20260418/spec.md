# Track Specification

## Overview
- 建立一條以測試補強為主的初始 track，優先覆蓋 core runtime、設定載入與 TUI 啟動相關的高風險模組。

## Background
- 專案目前已有基本結構與單一 `tests/test_imports.py`，但 README 明確指出測試覆蓋仍待補強。
- 由於此專案整合 agent、MCP、TUI 與本地儲存，多數回歸風險集中在啟動流程與模組邊界。

## Functional Requirements
- 為設定載入、agent 管理或 runner 的核心路徑新增可重複執行的單元測試。
- 為 TUI 啟動或主要畫面組裝新增至少一組不依賴外部網路的測試。
- 釐清測試執行指令，讓開發者可穩定執行基本測試與 coverage。

## Non-Functional Requirements
- 測試必須可於本機非互動模式執行。
- 測試應避免依賴真實模型 API 或外部 MCP server。
- 新增測試應維持合理執行時間，適合日常開發迴圈。

## Acceptance Criteria
- 至少一個核心模組測試檔與一個介面相關測試檔被建立或補強。
- `pytest` 可在專案根目錄成功執行。
- coverage 指令與期望範圍已記錄在 workflow 與 plan 中。

## Out of Scope
- 完整重構 TUI 架構。
- 新增新的 provider 或 MCP server 功能。
- 大幅調整產品功能或設定格式。

## Dependencies
- 現有 `pytest` 測試基礎。
- `src/core/`、`src/interface/` 既有模組設計。
