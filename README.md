# SlackToJournal

AI驅動的Slack工作日誌自動生成工具，使用Gemini AI分析Slack對話並生成結構化週報。

## 快速開始

### 1. 安裝與設定

**一鍵自動安裝** (推薦使用)：

**執行 Batch 批次檔** (適用於 Windows CMD)
```cmd
install.bat
```

### 2. 依賴安裝選項

根據不同需求選擇適合的依賴安裝：

- **生產環境** (僅核心功能)：
  ```bash
  uv sync
  ```

- **輕量級開發** (快速開發，不包含型別檢查)：
  ```bash
  uv sync --group dev-lite
  ```

- **完整開發環境** (包含所有開發工具)：
  ```bash
  uv sync --group dev
  ```

> 💡 **提示**：如果 mypy 安裝較慢，建議使用 `dev-lite` 組進行日常開發，僅在需要完整型別檢查時使用 `dev` 組。

## 使用方法

**生成每日摘要**：
```bash
uv run -m src.main daily --no-upload        # 僅本地儲存
uv run -m src.main daily -e user@company.com # 特定使用者email
uv run -m src.main daily -n "張三"          # 特定使用者名稱
```

**生成週報**：
```bash
uv run -m src.main weekly --no-upload       # 僅本地儲存
uv run -m src.main weekly -e user@company.com # 特定使用者email
uv run -m src.main weekly -n "團隊"         # 特定使用者名稱
```

## API金鑰取得

### Slack Bot Token
1. 前往 [Slack API](https://api.slack.com/apps) 建立應用程式
2. 在 OAuth & Permissions 中添加以下權限：
   - `channels:history` `channels:read` `channels:join`
   - `groups:history` `groups:read` 
   - `users:read`
3. 安裝到工作區並複製Bot User OAuth Token

### Gemini API Key
前往 [Google AI Studio](https://makersuite.google.com/app/apikey) 取得API金鑰

## 疑難排解

如遇問題，執行系統診斷：
```bash
uv run -m src.main status
```

詳細文檔請參考 `SLACK_SETUP.md`