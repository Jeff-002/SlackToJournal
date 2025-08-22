# SlackToJournal

AI驅動的自動化工具，讀取Slack工作區內容並使用直接Slack API整合和Gemini 2.0 Flash AI生成結構化工作日誌。

## 功能特色

- 🚀 **Slack整合**：直接Slack API整合，具備自動加入頻道功能
- 🤖 **AI智能內容分析**：使用Gemini 2.0 Flash進行智能工作內容提取
- 📁 **Google Drive整合**：自動上傳日誌到Google Drive（可選）
- 📅 **每日和週報**：生成每日摘要和週報
- 🔧 **模組化架構**：乾淨、易維護的Python程式碼
- 🔐 **SSL支援**：處理企業SSL環境

## 快速開始

### 前置條件

1. **Slack Bot Token**：建立Slack應用程式並取得具備以下權限的bot token：
   - `channels:history` - 讀取頻道訊息
   - `channels:read` - 列出頻道
   - `channels:join` - 自動加入頻道
   - `users:read` - 取得使用者資訊

2. **Gemini API Key**：從[Google AI Studio](https://makersuite.google.com/app/apikey)取得

3. **Google Drive憑證**（可選）：用於自動上傳到Google Drive

### 安裝與設定

1. **安裝依賴**：
   ```bash
   uv sync
   ```

2. **設定環境變數**：
   在專案根目錄建立`.env`檔案：
   ```env
   # Slack 整合
   SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   SLACK_USER_TOKEN=xoxp-your-user-token-here  # 可選
   SLACK_WORKSPACE_ID=your-workspace-id

   # AI 處理
   GEMINI_API_KEY=your-gemini-api-key

   # Google Drive（可選）
   # GOOGLE_DRIVE_CREDENTIALS_FILE=configs/credentials/google_credentials.json
   # GOOGLE_DRIVE_FOLDER_ID=your-drive-folder-id

   # 應用程式設定
   DEBUG=false
   LOG_LEVEL=INFO
   ```

3. **執行設定命令**：
   ```bash
   python -m src.main setup
   ```

4. **測試設定**：
   ```bash
   python -m src.main status
   python -m src.main test --test-all
   ```

### 使用方法

**生成每日摘要**：
```bash
python -m src.main daily                    # 預設上傳到Google Drive
python -m src.main daily --no-upload        # 僅本地儲存
```

**生成週報**：
```bash
python -m src.main weekly --no-upload       # 僅本地儲存
python -m src.main weekly                   # 上傳到Google Drive
```

**檢查系統狀態**：
```bash
python -m src.main status
```

**查看最近的日誌**：
```bash
python -m src.main recent --days 30
```

## 系統架構

- `src/slack_integration/` - 直接Slack API客戶端，具備自動加入頻道功能
- `src/ai_processing/` - Gemini 2.0 Flash AI內容分析和日誌生成
- `src/drive_integration/` - Google Drive認證和檔案操作
- `src/journal/` - 日誌格式化、範本和匯出管理
- `src/core/` - 共用工具、日誌記錄和設定

## 疑難排解

### SSL憑證問題
如果在企業環境中遇到SSL憑證錯誤：

1. **僅供測試使用**，可以停用SSL驗證：
   ```python
   import ssl
   ssl._create_default_https_context = ssl._create_unverified_context
   ```

2. **正式環境**，請正確設定企業憑證。

### 頻道存取問題
當bot遇到"not_in_channel"錯誤時會自動嘗試加入頻道。請確保你的bot token具有`channels:join`權限。

### Windows Unicode顯示問題
使用PowerShell或Windows Terminal以正確顯示表情符號：
```powershell
$env:PYTHONIOENCODING="utf-8"; python -m src.main daily
```

## 開發

```bash
# 執行測試
pytest

# 程式碼格式化
black src tests
isort src tests

# 型別檢查
mypy src
```

## 設定

詳細設定選項請參考`configs/settings.yaml`，環境變數請參考`.env`檔案。
