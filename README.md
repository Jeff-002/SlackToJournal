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
   - `channels:history` - 讀取公開頻道訊息
   - `channels:read` - 列出公開頻道
   - `channels:join` - 自動加入頻道
   - `groups:history` - 讀取私人頻道訊息 ⚠️ **重要**
   - `groups:read` - 列出私人頻道 ⚠️ **重要**
   - `mpim:history` - 讀取多人私訊群組訊息
   - `mpim:read` - 列出多人私訊群組 ⚠️ **重要**
   - `im:history` - 讀取私人訊息
   - `im:read` - 列出私人訊息
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
   
   # 訊息過濾
   SLACK_EXCLUDE_KEYWORDS=sync,test,debug  # 排除關鍵字（逗號分隔）

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
python -m src.main daily                              # 所有使用者，預設上傳到Google Drive
python -m src.main daily --no-upload                  # 所有使用者，僅本地儲存
python -m src.main daily -e user@company.com          # 特定使用者email
python -m src.main daily -n "張三"                    # 特定使用者名稱
python -m src.main daily -n "張三" -e user@company.com # 指定使用者名稱和email
```

**生成週報**：
```bash
python -m src.main weekly --no-upload                 # 所有使用者，僅本地儲存
python -m src.main weekly                             # 所有使用者，上傳到Google Drive
python -m src.main weekly -e user@company.com         # 特定使用者email的週報
python -m src.main weekly -n "團隊"                   # 特定使用者名稱的週報
python -m src.main weekly -n "團隊" -e user@company.com # 指定使用者名稱和email
```

**檢查系統狀態**：
```bash
python -m src.main status
```

**查看最近的日誌**：
```bash
python -m src.main recent --days 30
```

### 使用者過濾參數說明

**`-e, --user-email`**：根據使用者email過濾訊息
- 格式：`user@company.com`
- 完全匹配使用者的Slack註冊email

**`-n, --user-name`**：根據使用者名稱過濾訊息
- 格式：支援顯示名稱、真實姓名或使用者名稱
- 不區分大小寫匹配
- 支援中英文及Unicode字元
- 範例：`"張三"`、`"Han_張麗華"`、`"John Smith"`

**組合使用**：可同時使用 `-e` 和 `-n` 參數進行更精確的過濾
```

## 系統架構

- `src/slack_integration/` - 直接Slack API客戶端，具備自動加入頻道功能
- `src/ai_processing/` - Gemini 2.0 Flash AI內容分析和日誌生成
- `src/drive_integration/` - Google Drive認證和檔案操作
- `src/journal/` - 日誌格式化、範本和匯出管理
- `src/core/` - 共用工具、日誌記錄和設定

## 疑難排解

### 私人頻道訊息讀取問題

如果bot無法讀取私人頻道訊息：

1. **檢查Bot權限**：確保在Slack App設定中已啟用以下OAuth Scopes：
   ```
   groups:history, groups:read, mpim:history, mpim:read, im:history, im:read
   ```
   
   **常見錯誤**：
   - `missing_scope: mpim:read` - 需要添加多人私訊群組列表權限
   - `missing_scope: groups:read` - 需要添加私人頻道列表權限
   - `missing_scope: im:read` - 需要添加私人訊息列表權限

2. **重新安裝App**：修改權限後需要重新安裝到工作區：
   - 前往 Slack App 設定頁面
   - 點選 "Install to Workspace" 重新安裝
   - 重新授權新的權限

3. **確認Bot已加入私人頻道**：
   - 在私人頻道中輸入 `/invite @你的bot名稱`
   - 或者在頻道設定中手動添加bot

4. **測試權限**：
   ```bash
   python -m src.main status
   ```

5. **查看詳細日誌**：
   ```bash
   # 啟用DEBUG模式
   export LOG_LEVEL=DEBUG
   python -m src.main daily
   ```

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
