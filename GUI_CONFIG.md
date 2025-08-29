# GUI 配置說明

## 當前狀態

GUI 目前使用**模擬模式**運行，這意味著：
- ✅ GUI 介面完全可用
- ✅ 所有操作都會顯示模擬結果
- ⚠️ 不會執行真實的 Slack 數據處理

## 切換到真實模式

當您的系統完全配置好後（包括 Slack API、Gemini AI、Google Drive 等），可以切換到真實模式：

### 步驟 1：確保所有服務正常
```bash
# 檢查系統狀態
uv run -m src.main status

# 測試所有組件
uv run -m src.main test --test-all
```

### 步驟 2：修改 GUI 配置
編輯 `src/gui/app.py` 檔案，找到以下行：
```python
cli_wrapper = get_cli_wrapper(use_mock=True)
```

將 `use_mock=True` 改為 `use_mock=False`：
```python
cli_wrapper = get_cli_wrapper(use_mock=False)
```

### 步驟 3：重新啟動 GUI
```bash
uv run python gui.py
```

## 故障排除

如果切換到真實模式後遇到錯誤：

1. **檢查環境變數**：確保 `.env` 文件包含所有必要的 API 金鑰
2. **檢查憑證檔案**：確保 Google 憑證檔案存在於 `configs/credentials/`
3. **檢查網路連線**：確保可以存取 Slack API 和 Gemini API
4. **回到模擬模式**：將 `use_mock=False` 改回 `use_mock=True`

## 模擬模式功能

模擬模式提供以下功能：
- 完整的 GUI 操作體驗
- 模擬的處理時間和進度條
- 成功和錯誤狀態的展示
- 所有表單驗證和使用者互動

這讓您可以：
- 測試 GUI 的所有功能
- 訓練使用者如何操作
- 驗證介面設計和使用流程