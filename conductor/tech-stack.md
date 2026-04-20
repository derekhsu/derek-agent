# Tech Stack

## Languages
- Python 3.14+

## Frameworks and Libraries
- Agno：agent runtime 與能力整合基礎，包含內建的 Rich logging 系統。
- Textual：終端介面與互動元件。
- Pydantic：資料模型與設定驗證。
- PyYAML：YAML 設定檔解析。
- OpenAI / Anthropic Python SDK：模型供應商整合。
- MCP Python package：MCP client 支援。
- Rich (via Agno)：彩色終端日誌輸出與格式化。

## Data Stores
- SQLite：本地對話與應用資料儲存。

## Tooling
- `uv`：依賴安裝與環境同步。
- `pytest`：測試執行。
- 專案入口：`python main.py` 或 `derek-agent` console script。

## Constraints and Decisions
- 目前專案以本機執行為前提，不依賴外部資料庫。
- 使用 YAML 作為設定來源，降低 agent 與 MCP 配置成本。
- TUI 與核心邏輯分層，便於日後擴充命令列或其他介面。
- 目前測試覆蓋偏低，後續工作需優先補強核心模組的可驗證性。
