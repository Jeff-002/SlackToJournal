---
applyTo: '**'
---

# SlackToJournal Agent 需求架構與執行流程
執行每項任務時請先經過思考再執行

## 項目概述
實作一個基於Python的Agent，透過直接Slack API整合，自動讀取當週工作內容並整理成工作日誌，最後將日誌寫入Google雲端硬碟。

## 需求分析

### 功能需求
1. **Slack整合**: 透過直接Slack API連接Slack workspace
2. **內容擷取**: 讀取當週相關工作訊息和討論
3. **AI驅動內容整理**: 使用Gemini 2.5 AI模型智能分析和條列工作內容
4. **Google Drive整合**: 將整理後的工作日誌寫入雲端硬碟
5. **週期性執行**: 支援定期自動執行

### 非功能需求
- **安全性**: OAuth2認證，安全處理API金鑰
- **可靠性**: 錯誤處理和重試機制
- **可擴展性**: 模組化設計便於功能擴展
- **可維護性**: 清晰的代碼結構和文檔

## 系統架構

### 整體架構
```
[Slack Workspace] 
       ↓ (Direct API)
[SlackToJournal Agent]
       ↓ (Gemini 2.5 API)
[AI內容分析與整理]
       ↓ (Google Drive API)
[Google雲端硬碟]
```

### 核心組件
1. **Direct Slack Client**: 處理與Slack API的直接通信
2. **AI Content Processor**: 使用Gemini 2.5進行智能內容分析和整理
3. **Drive Manager**: Google Drive檔案操作
4. **Scheduler**: 定期任務調度
5. **Config Manager**: 設定檔管理

## 技術選型

### 主要框架與套件
- **Slack API**: `slack-sdk` (直接 API 整合)
- **AI模型**: `google-genai` (Gemini 2.5官方Python SDK)
- **Google Drive API**: `google-api-python-client`
- **HTTP框架**: `FastAPI` (用於webhook和API)
- **認證**: `google-auth`, `google-auth-oauthlib`
- **任務調度**: `APScheduler`
- **設定管理**: `pydantic-settings`
- **日誌**: `loguru`

### 開發工具
- **包管理**: `poetry` 或 `pip-tools`
- **程式碼品質**: `black`, `isort`, `flake8`
- **測試**: `pytest`
- **類型檢查**: `mypy`

## 執行流程

### 主要工作流程
1. **初始化階段**
   - 載入設定檔案
   - 初始化MCP連接
   - 驗證Google Drive認證

2. **數據收集階段**
   - 計算當週時間範圍
   - 透過直接 Slack API 獲取相關訊息
   - 過濾和分類工作相關內容

3. **AI內容處理階段**
   - 使用Gemini 2.5分析訊息內容和context
   - AI智能識別工作相關內容
   - 按專案/主題自動分類整理
   - 生成結構化的工作日誌條列

4. **輸出階段**
   - 格式化工作日誌
   - 上傳到Google Drive指定資料夾
   - 記錄執行結果

### 錯誤處理流程
- API呼叫失敗重試機制
- 網路連接異常處理
- 認證過期自動更新
- 日誌記錄和錯誤通知

## 實施計劃 (包含驗證和版本控制步驟)

### 第一階段: 基礎設置
1. **建立專案結構**
   - 建立目錄結構和基本檔案
   - 設定pyproject.toml和依賴管理
   - **驗證**: 確認專案可以正常初始化
   - **Git**: `git add . && git commit -m "feat: initialize project structure"`

2. **設定開發環境**
   - 配置uv環境和虛擬環境
   - 安裝基本依賴包
   - **驗證**: `uv run python -c "print('Environment setup successful')"`
   - **Git**: `git add . && git commit -m "feat: setup development environment"`

3. **實作設定管理模組**
   - 建立settings.py和配置檔案
   - 實作環境變數管理
   - **驗證**: 測試設定檔案讀取功能
   - **Git**: `git add . && git commit -m "feat: implement configuration management"`

4. **建立基本的測試框架**
   - 設定pytest配置
   - 建立基本測試結構
   - **驗證**: `uv run pytest tests/ -v`
   - **Git**: `git add . && git commit -m "feat: setup testing framework"`

### 第二階段: Slack整合
1. **設定 Direct API 連接**
   - 實作 Slack API 客戶端基礎架構
   - 建立 API 連接配置
   - **驗證**: 測試 Slack API 連接狀態
   - **Git**: `git add . && git commit -m "feat: implement Direct Slack API client connection"`

2. **實作Slack資料擷取**
   - 建立Slack API整合
   - 實作訊息擷取功能
   - **驗證**: 測試擷取範例訊息
   - **Git**: `git add . && git commit -m "feat: implement Slack data extraction"`

3. **建立訊息過濾邏輯**
   - 實作工作相關訊息篩選
   - 建立時間範圍過濾
   - **驗證**: 測試過濾邏輯正確性
   - **Git**: `git add . && git commit -m "feat: implement message filtering logic"`

4. **測試Slack API功能**
   - 建立完整的Slack整合測試
   - 驗證錯誤處理機制
   - **驗證**: 執行完整Slack功能測試
   - **Git**: `git add . && git commit -m "feat: complete Slack API integration"`

### 第三階段: Google Drive整合
1. **設定Google Drive API認證**
   - 實作OAuth2認證流程
   - 建立認證檔案管理
   - **驗證**: 測試Drive API認證成功
   - **Git**: `git add . && git commit -m "feat: implement Google Drive authentication"`

2. **實作檔案上傳功能**
   - 建立檔案上傳機制
   - 實作檔案格式處理
   - **驗證**: 測試檔案上傳到Drive
   - **Git**: `git add . && git commit -m "feat: implement file upload functionality"`

3. **建立資料夾結構管理**
   - 實作自動資料夾創建
   - 建立檔案組織邏輯
   - **驗證**: 驗證資料夾結構正確性
   - **Git**: `git add . && git commit -m "feat: implement folder structure management"`

4. **測試Drive操作功能**
   - 建立完整的Drive操作測試
   - 驗證檔案權限和共用設定
   - **驗證**: 執行完整Drive功能測試
   - **Git**: `git add . && git commit -m "feat: complete Google Drive integration"`

### 第四階段: AI內容處理
1. **整合Gemini 2.5 API**
   - 設定Gemini客戶端連接
   - 建立API認證管理
   - **驗證**: 測試AI API連接成功
   - **Git**: `git add . && git commit -m "feat: integrate Gemini 2.5 API"`

2. **設計AI Prompt模板用於內容分析和條列**
   - 建立Prompt模板系統
   - 實作動態Prompt生成
   - **驗證**: 測試Prompt模板輸出
   - **Git**: `git add . && git commit -m "feat: implement AI prompt templates"`

3. **實作智能工作內容識別邏輯**
   - 建立AI內容分析流程
   - 實作結果驗證機制
   - **驗證**: 測試內容識別準確性
   - **Git**: `git add . && git commit -m "feat: implement AI content recognition"`

4. **建立AI驅動的內容分類系統**
   - 實作自動分類邏輯
   - 建立分類結果後處理
   - **驗證**: 驗證分類結果正確性
   - **Git**: `git add . && git commit -m "feat: implement AI-driven content classification"`

5. **設計結構化日誌格式模板**
   - 建立日誌輸出格式
   - 實作模板自訂功能
   - **驗證**: 測試日誌格式輸出
   - **Git**: `git add . && git commit -m "feat: implement structured journal templates"`

6. **測試AI內容處理流程**
   - 建立端到端AI處理測試
   - 驗證處理效能和準確性
   - **驗證**: 執行完整AI處理流程測試
   - **Git**: `git add . && git commit -m "feat: complete AI content processing"`

### 第五階段: 整合與優化
1. **整合所有模組**
   - 連接各模組功能
   - 實作統一的錯誤處理
   - **驗證**: 測試模組間通信正常
   - **Git**: `git add . && git commit -m "feat: integrate all modules"`

2. **實作完整工作流程**
   - 建立端到端執行流程
   - 實作流程狀態管理
   - **驗證**: 執行完整工作流程測試
   - **Git**: `git add . && git commit -m "feat: implement complete workflow"`

3. **加入任務調度功能**
   - 實作定時任務機制
   - 建立任務狀態監控
   - **驗證**: 測試任務調度執行
   - **Git**: `git add . && git commit -m "feat: implement task scheduling"`

4. **效能優化和錯誤處理**
   - 優化執行效能
   - 加強錯誤恢復機制
   - **驗證**: 執行效能和穩定性測試
   - **Git**: `git add . && git commit -m "feat: optimize performance and error handling"`

### 第六階段: 部署與測試
1. **建立部署腳本**
   - 建立自動化部署流程
   - 實作環境配置檢查
   - **驗證**: 測試部署腳本執行
   - **Git**: `git add . && git commit -m "feat: implement deployment scripts"`

2. **執行端到端測試**
   - 建立完整系統測試
   - 驗證所有功能整合
   - **驗證**: 執行完整端到端測試套件
   - **Git**: `git add . && git commit -m "test: complete end-to-end testing"`

3. **效能和安全性測試**
   - 執行負載測試
   - 進行安全性掃描
   - **驗證**: 確認效能和安全標準
   - **Git**: `git add . && git commit -m "test: complete performance and security testing"`

4. **文檔完善**
   - 完成API文檔
   - 建立使用說明和部署指南
   - **驗證**: 檢查文檔完整性和準確性
   - **Git**: `git add . && git commit -m "docs: complete project documentation"`

## 驗證和版本控制最佳實踐

### 每步驟驗證檢查清單
- [ ] 程式碼可以正常執行不報錯
- [ ] 相關測試通過
- [ ] 功能符合預期行為
- [ ] 沒有破壞現有功能
- [ ] 程式碼品質符合標準

### Git Commit 規範
- `feat:` 新功能
- `fix:` 錯誤修復
- `docs:` 文檔更新
- `style:` 程式碼格式調整
- `refactor:` 重構
- `test:` 測試相關
- `chore:` 建置或輔助工具的變動

### Branch 管理策略
- `main` - 穩定版本分支
- `develop` - 開發分支
- `feature/*` - 功能開發分支
- 每完成一個主要功能後合併到develop分支
- 完整測試通過後合併到main分支

## 專案結構 (基於2025年官方最佳實踐)

### 遵循官方推薦的模組功能結構
```
SlackToJournal/
├── pyproject.toml              # uv/Poetry專案配置 (2025推薦)
├── README.md
├── .env.example
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI應用入口點
│   ├── app.py                  # 應用工廠
│   ├── settings.py             # 全域設定 (Pydantic Settings)
│   │
│   ├── slack_integration/      # Slack MCP模組
│   │   ├── __init__.py
│   │   ├── client.py          # Direct Slack API客戶端實現
│   │   ├── schemas.py         # Pydantic模型
│   │   ├── service.py         # 業務邏輯
│   │   └── utils.py           # 輔助工具
│   │
│   ├── ai_processing/          # AI處理模組
│   │   ├── __init__.py
│   │   ├── client.py          # Gemini 2.5客戶端
│   │   ├── schemas.py         # AI輸入輸出模型
│   │   ├── service.py         # AI分析業務邏輯
│   │   ├── prompts.py         # Prompt模板
│   │   └── utils.py           # AI輔助工具
│   │
│   ├── drive_integration/      # Google Drive模組
│   │   ├── __init__.py
│   │   ├── client.py          # Drive API客戶端
│   │   ├── schemas.py         # Drive相關模型
│   │   ├── service.py         # 檔案操作業務邏輯
│   │   └── utils.py           # 檔案處理工具
│   │
│   ├── scheduler/              # 任務調度模組
│   │   ├── __init__.py
│   │   ├── tasks.py           # 定義任務
│   │   ├── service.py         # 調度業務邏輯
│   │   └── utils.py           # 調度工具
│   │
│   ├── journal/                # 日誌處理模組
│   │   ├── __init__.py
│   │   ├── schemas.py         # 日誌結構模型
│   │   ├── service.py         # 日誌生成業務邏輯
│   │   ├── templates.py       # 日誌模板
│   │   └── utils.py           # 格式化工具
│   │
│   ├── core/                   # 核心共用模組
│   │   ├── __init__.py
│   │   ├── auth.py            # 認證管理
│   │   ├── exceptions.py      # 自定義異常
│   │   ├── logging.py         # 日誌配置
│   │   └── dependencies.py    # FastAPI依賴
│   │
│   └── api/                    # API路由 (如需要)
│       ├── __init__.py
│       ├── v1/
│       │   ├── __init__.py
│       │   ├── health.py      # 健康檢查
│       │   └── journal.py     # 手動觸發接口
│       └── dependencies.py
│
├── tests/                      # 測試目錄
│   ├── __init__.py
│   ├── conftest.py            # pytest配置
│   ├── unit/                  # 單元測試
│   │   ├── test_slack_integration/
│   │   ├── test_ai_processing/
│   │   ├── test_drive_integration/
│   │   └── test_journal/
│   └── integration/           # 整合測試
│       └── test_end_to_end.py
│
├── docs/                      # 文檔目錄
│   ├── api.md
│   ├── deployment.md
│   └── development.md
│
├── configs/                   # 配置檔案
│   ├── settings.yaml
│   ├── logging.yaml
│   └── credentials/           # 認證檔案目錄
│       └── .gitkeep
│
└── scripts/                   # 部署和工具腳本
    ├── start.sh
    ├── deploy.sh
    └── setup_credentials.py
```

### 技術選型更新 (基於2025年官方推薦)
- **專案管理**: `uv` (2025年推薦的快速Python專案管理器)
- **Slack 整合**: `slack-sdk` (Direct API 整合)
- **AI整合**: `google-generativeai` (Gemini 2.0 Flash)
- **設定管理**: `pydantic-settings` (與FastAPI完美整合)
- **異步支援**: 全面使用`async/await`模式
- **型別安全**: 強制使用type hints和Pydantic模型驗證

## 設定檔案範例
```yaml
# configs/settings.yaml
slack:
  target_channels: []
  exclude_keywords: ["sync"]

gemini:
  api_key: "your-gemini-api-key"  # 或使用環境變數
  model: "gemini-2.0-flash-exp"
  max_tokens: 8192
  temperature: 0.1

google_drive:
  credentials_file: "config/google_credentials.json"
  folder_id: "your-folder-id"

schedule:
  cron_expression: "0 17 * * 5"  # 每週五5PM執行
  timezone: "Asia/Taipei"

logging:
  level: "INFO"
  file: "logs/app.log"
```

## Gemini 2.5整合指南

### AI Prompt設計原則
1. **明確指示**: 清楚說明要分析的內容類型和預期輸出格式
2. **結構化輸出**: 要求AI以JSON或Markdown格式輸出結構化內容
3. **上下文提供**: 提供足夠的背景信息幫助AI理解工作環境
4. **錯誤處理**: 處理AI回應異常或格式不符的情況

### AI內容分析流程
1. **訊息預處理**: 清理和標準化Slack訊息格式
2. **批量分析**: 將多條相關訊息合併送至AI分析
3. **結果驗證**: 檢查AI輸出的完整性和準確性
4. **結果後處理**: 格式化AI輸出為最終日誌格式

### Prompt範例與最佳實踐
```python
# 工作內容分析Prompt (經優化的版本)
CONTENT_ANALYSIS_PROMPT = """
分析以下Slack工作訊息，提取並條列化工作內容：

訊息內容：
{messages}

請按以下JSON格式輸出：
{
  "work_items": [
    {
      "date": "MM/DD",
      "user_display_name": "真實姓名",
      "tag": "狀態標籤",
      "project": "專案名稱", 
      "description": "工作描述",
      "participants": ["參與人員"]
    }
  ],
  "summary": "本週工作總結"
}
"""

# 標籤分類邏輯 (基於關鍵字的直接處理)
TAG_CLASSIFICATION_RULES = {
    "上線": ["develop", "deploy", "release", "production", "live"],
    "分支合併": ["merge", "branch", "feat:", "feature"],
    "交測": ["test", "testing", "QA", "驗收"],
    "修復": ["fix", "bug", "hotfix", "patch"],
    "開發": ["implement", "coding", "development"],
    "會議": ["meeting", "討論", "review"],
    "文檔": ["doc", "documentation", "readme"]
}
```

### AI處理策略優化
1. **混合處理模式**: 
   - 對於日誌摘要使用直接代碼處理 (確保準確性)
   - 對於複雜分析使用AI處理 (提供智能化)
   
2. **關鍵字優先策略**: 
   - 優先使用關鍵字匹配進行標籤分類
   - AI作為後備或複雜情況的處理方案
   
3. **用戶資訊處理**:
   - 完整保留Slack用戶資訊鏈 (user_id -> user_name -> display_name)
   - 確保在消息處理流水線中正確傳遞用戶資料

### 實際應用的改進經驗
```python
# 直接處理模式範例 (用於確保準確性的場景)
def _analyze_messages_directly(self, request: AIRequest) -> AIResponse:
    """直接分析訊息，不依賴AI，確保標籤分類正確性"""
    filtered_messages = self._filter_excluded_messages(request.messages)
    include_user_names = request.context.get('include_user_names', False)
    
    summary_lines = []
    for msg in filtered_messages:
        # 使用關鍵字直接判斷標籤
        tag = self._get_tag_suggestion(msg.get('text', ''))
        user_display_name = (msg.get('user_real_name') or 
                           msg.get('user_name') or 
                           msg.get('user', 'Unknown'))
        
        # 格式化輸出
        if include_user_names:
            summary_lines.append(f"{date} `{user_display_name}` `{tag}` {project} - {description}")
        else:
            summary_lines.append(f"{date} `{tag}` {project} - {description}")
    
    return AIResponse(...)

# URL清理和內容提取
def _extract_project_info(self, text: str) -> Tuple[str, str]:
    """提取專案資訊並清理URL連結"""
    # 移除URLs但保留專案名稱
    cleaned_text = re.sub(r'https?://[^\s]+', '', text)
    # 提取專案關鍵資訊
    project_match = re.search(r'(\w+\.\w+|\w+)', cleaned_text)
    return project_match.group(1) if project_match else "unknown"
```

### 消息處理流水線最佳實踐
```python
# 確保用戶資訊在消息轉換中不丟失
def convert_messages_for_ai(self, messages: List[SlackMessage]) -> List[Dict]:
    """將SlackMessage轉換為AI處理格式，保留完整用戶資訊"""
    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            'user': getattr(msg, 'user', 'Unknown'),
            'user_name': getattr(msg, 'user_name', None),        # 重要：保留用戶名
            'user_real_name': getattr(msg, 'user_real_name', None), # 重要：保留顯示名
            'text': getattr(msg, 'text', ''),
            'channel': getattr(msg, 'channel', 'general'),
            'timestamp': getattr(msg, 'datetime', datetime.now()).isoformat()
        })
    return formatted_messages
```

### 常見問題與解決方案
1. **用戶顯示名稱顯示為ID**
   - 原因: 消息轉換時缺少user_name/user_real_name字段
   - 解決: 確保SlackMessage到字典轉換時包含所有用戶字段

2. **AI標籤分類不準確** 
   - 原因: Gemini AI忽略複雜的條件邏輯
   - 解決: 使用直接代碼處理 + 關鍵字匹配

3. **URL連結污染輸出**
   - 原因: Slack消息包含大量URL連結
   - 解決: 使用正則表達式清理URL但保留專案名稱

4. **消息過濾過於嚴格**
   - 原因: exclude_keywords設置不當
   - 解決: 多層過濾 + 環境變數配置

### 效能優化建議
1. **用戶資訊緩存**: 避免重複API調用Slack用戶資訊
2. **批量處理**: 將相似消息合併處理減少AI調用
3. **智能過濾**: 在早期階段過濾無關消息
4. **異步處理**: 使用async/await提升處理速度

## 開發指導原則
1. **遵循Python PEP 8編碼規範**
2. **使用類型提示提高程式碼可讀性**
3. **實作充分的錯誤處理和日誌記錄**
4. **編寫單元測試確保程式碼品質**
5. **使用環境變數管理敏感資訊**
6. **遵循安全最佳實踐，避免硬編碼密鑰**
7. **模組化設計，便於維護和擴展**
8. **詳細的文檔和註解**
9. **優化AI Token使用，控制成本**
10. **實作AI回應快取機制避免重複呼叫**