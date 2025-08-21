# Slack 設定指南

本指南將協助你設定 Slack 整合，讓 SlackToJournal 能夠讀取你的 Slack 訊息。

## 🚀 快速設定 (推薦)

### 🛠️ 自動設定腳本

我已經創建了自動設定腳本來簡化流程：

```bash
# 運行交互式設定腳本
uv run python scripts/setup_slack.py
```

這個腳本會：
- 指導你創建 Slack App
- 測試你的 Bot Token  
- 自動更新 .env 檔案
- 驗證整合是否正常工作

## 📝 手動設定步驟

### 選項 1: 使用 Slack Bot Token (最簡單)

1. **建立 Slack App**:
   - 前往 https://api.slack.com/apps
   - 點選 "Create New App" → "From scratch"
   - 輸入 App 名稱 (例如: "WorkJournal Bot")
   - 選擇你的 Workspace

2. **設定 Bot Token**:
   - 在左側選單選擇 "OAuth & Permissions"
   - 在 "Scopes" 區域，新增以下 Bot Token Scopes:
     ```
     channels:history    - 讀取公開頻道訊息
     channels:read       - 查看公開頻道資訊
     users:read          - 讀取使用者資訊
     search:read         - 搜尋訊息 (選用，需付費方案)
     ```
   
3. **安裝 App 到 Workspace**:
   - 點選頁面上方的 "Install to Workspace"
   - 授權應用程式權限
   - 複製 "Bot User OAuth Token" (以 `xoxb-` 開頭)

4. **邀請 Bot 到頻道**:
   ```
   在你想要分析的 Slack 頻道中輸入:
   /invite @WorkJournal Bot
   ```

5. **設定環境變數**:
   在 `.env` 檔案中設定:
   ```env
   # 使用 Slack Bot Token 而非 MCP
   SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   SLACK_WORKSPACE_ID=your-team-id
   
   # 如果你想用 MCP，設定這個 (可選)
   SLACK_MCP_SERVER_URL=http://localhost:3000
   ```

## 🔧 選項 2: MCP Server 設定 (進階)

如果你想使用 Model Context Protocol (MCP)：

### 安裝 Slack MCP Server

```bash
# 方法 1: 使用 npm (需要 Node.js)
npm install -g @slack/mcp-server

# 方法 2: 使用 Python 實作
pip install slack-mcp-python
```

### 設定 MCP Server

1. **建立 MCP 配置檔案** (`slack-mcp-config.json`):
```json
{
  "slack": {
    "bot_token": "xoxb-your-bot-token",
    "app_token": "xapp-your-app-token",  
    "signing_secret": "your-signing-secret"
  },
  "server": {
    "host": "localhost",
    "port": 3000
  }
}
```

2. **啟動 MCP Server**:
```bash
# 使用配置檔案啟動
slack-mcp-server --config slack-mcp-config.json

# 或者直接指定參數
slack-mcp-server --bot-token xoxb-xxx --port 3000
```

3. **設定環境變數**:
```env
SLACK_MCP_SERVER_URL=http://localhost:3000
SLACK_WORKSPACE_ID=your-team-id
```

## 📋 獲取 Workspace ID

有幾種方式獲取你的 Slack Workspace ID：

### 方法 1: 從 Slack App 設定
- 在你的 Slack App 設定頁面
- 查看 "Basic Information" 
- 找到 "Team ID" 或使用 Bot Token 測試時返回的 `team_id`

### 方法 2: 使用 Web API 測試
```bash
curl -H "Authorization: Bearer xoxb-your-bot-token" \
     https://slack.com/api/auth.test
```

返回的 JSON 中會包含 `team_id`。

### 方法 3: 使用內建測試指令
```bash
# 設定好 Bot Token 後執行
uv run python -m src.main test --test-slack
```

## ✅ 驗證設定

設定完成後，執行以下指令驗證：

```bash
# 檢查系統狀態
uv run python -m src.main status

# 測試 Slack 連接
uv run python -m src.main test --test-slack

# 生成測試日誌
uv run python -m src.main weekly
```

## ❓ 常見問題

### Q: Bot Token 無法使用？
A: 確保你的 token 以 `xoxb-` 開頭，並且已經安裝 App 到 workspace。

### Q: 無法讀取頻道訊息？
A: 確保 bot 已被邀請到相關頻道，使用 `/invite @your-bot-name`。

### Q: MCP Server 連不上？
A: 檢查 server 是否運行在正確的 port，防火牆是否阻擋連接。

### Q: 沒有權限搜尋訊息？
A: 搜尋功能需要付費的 Slack 方案，或者使用頻道遍歷的方式。

## 🔄 從 MCP 切換到直接 API

如果你之前設定了 MCP 但想改用直接 API：

1. 在 `.env` 中註解掉 MCP 設定：
   ```env
   # SLACK_MCP_SERVER_URL=http://localhost:3000
   ```

2. 新增 Bot Token：
   ```env
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_WORKSPACE_ID=your-team-id
   ```

3. 重新測試：
   ```bash
   uv run python -m src.main test --test-slack
   ```

SlackToJournal 會自動偵測可用的整合方式並選擇最適合的方法。