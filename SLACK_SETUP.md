# Slack 設定指南

本指南將協助你設定 Slack 整合，讓 SlackToJournal 能夠使用直接 API 方式讀取你的 Slack 訊息。

## 🚀 設定步驟

### 使用 Slack Bot Token (直接 API)

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
   SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   SLACK_USER_TOKEN=xoxp-your-user-token-here  # 可選
   SLACK_TARGET_CHANNELS=頻道1,頻道2  # 指定目標頻道（可選）
   SLACK_EXCLUDE_KEYWORDS=sync,test  # 排除關鍵字（可選）
   ```

## 📋 頻道過濾設定

你可以透過以下方式過濾要分析的頻道和訊息：

### 指定目標頻道
在 `.env` 檔案中設定:
```env
# 只分析特定頻道（使用頻道名稱，不是 ID）
SLACK_TARGET_CHANNELS=開發討論,產品規劃,技術分享
```

### 排除特定關鍵字
```env
# 排除包含這些關鍵字的訊息
SLACK_EXCLUDE_KEYWORDS=sync,test,debug,lunch
```

如果不設定 `SLACK_TARGET_CHANNELS`，系統會自動偵測所有工作相關頻道（排除 general、random 等社交頻道）。


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


### Q: 沒有權限搜尋訊息？
A: 搜尋功能需要付費的 Slack 方案，或者使用頻道遍歷的方式。

## 📊 自動設定腳本

我們提供了自動設定腳本來簡化設定流程：

```bash
# 運行交互式設定腳本
uv run python scripts/setup_slack.py
```

這個腳本會：
- 指導你創建 Slack App
- 測試你的 Bot Token  
- 自動更新 .env 檔案
- 驗證整合是否正常工作

SlackToJournal 使用直接 Slack API 整合方式，設定簡單且可靠。