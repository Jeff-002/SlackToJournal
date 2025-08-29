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

### 圖形化介面（推薦）

**啟動 GUI 介面**：
```bash
uv run python gui.py
```

GUI 將在瀏覽器中開啟（預設端口 8080），提供直觀的操作介面。

> 📝 **注意**：GUI 預設使用**模擬模式**運行，這讓您可以測試所有界面功能而無需配置所有服務。當所有服務配置完成後，請參閱 `GUI_CONFIG.md` 瞭解如何切換到真實模式。

- **週報生成**：選擇日期、用戶篩選、團隊名稱等參數，一鍵生成週報
- **日報摘要**：設定日期和用戶篩選，快速產生每日工作摘要
- **系統狀態**：檢查 Slack、AI、Google Drive 等服務連線狀態
- **初始設定**：執行系統初始化和配置檢查
- **測試組件**：測試各項系統組件的功能

#### GUI 操作說明

1. **首次使用**：
   - 執行 `uv run python gui.py` 啟動 GUI
   - 瀏覽器會自動開啟到 `http://localhost:8080`
   - 建議先使用「初始設定」檢查系統配置

2. **週報生成操作**：
   - 點選左側選單「週報生成」
   - 選擇週起始日期（預設為本週）
   - 可選填特定使用者 Email 或名稱進行篩選
   - 設定團隊名稱（預設為 "Development Team"）
   - 勾選是否上傳至 Google Drive
   - 點選「生成週報」按鈕開始處理

3. **日報摘要操作**：
   - 點選左側選單「日報摘要」
   - 選擇摘要日期（預設為今日）
   - 可選填使用者篩選條件
   - 設定是否跳過上傳
   - 點選「生成日報摘要」按鈕

4. **系統維護**：
   - 「系統狀態」：檢查各服務連線狀況
   - 「初始設定」：執行系統初始化
   - 「測試組件」：測試 Slack、AI、Drive 等組件

### 命令列介面

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

### GUI 相關問題

**GUI 無法啟動**：
```bash
# 檢查 NiceGUI 是否正確安裝
uv sync --native-tls

# 驗證 GUI 功能
uv run python validate_gui.py
```

**瀏覽器無法開啟 GUI**：
- 檢查防火牆設定是否阻擋端口 8080
- 手動開啟瀏覽器並前往 `http://localhost:8080`
- 嘗試使用不同端口（修改 `src/gui/app.py` 中的 port 設定）

**功能執行錯誤**：
- GUI 使用相同的 CLI 功能，請確保 CLI 命令正常運作
- 檢查 .env 文件中的 API 金鑰設定
- 使用「系統狀態」功能檢查各組件連線

### CLI 相關問題

如遇命令列問題，執行系統診斷：
```bash
uv run -m src.main status
```

詳細文檔請參考 `SLACK_SETUP.md`