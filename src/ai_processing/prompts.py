"""
AI prompt templates for journal generation.

This module provides structured prompt templates for different
types of content analysis and journal generation tasks.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from string import Template

from ..core.logging import get_logger
from .schemas import PromptContext


logger = get_logger(__name__)


class PromptTemplate:
    """Base class for AI prompt templates."""
    
    def __init__(self, template_string: str, required_variables: List[str] = None):
        """
        Initialize prompt template.
        
        Args:
            template_string: Template string with variables
            required_variables: List of required variable names
        """
        self.template = Template(template_string)
        self.required_variables = required_variables or []
    
    def render(self, **kwargs) -> str:
        """
        Render template with provided variables.
        
        Args:
            **kwargs: Template variables
            
        Returns:
            Rendered prompt string
            
        Raises:
            KeyError: If required variables are missing
        """
        # Check for required variables
        missing_vars = set(self.required_variables) - set(kwargs.keys())
        if missing_vars:
            raise KeyError(f"Missing required variables: {missing_vars}")
        
        try:
            return self.template.substitute(**kwargs)
        except KeyError as e:
            logger.error(f"Template variable missing: {e}")
            raise


class JournalPrompts:
    """Collection of journal-specific prompts."""
    
    WORK_ANALYSIS_PROMPT = PromptTemplate("""
你是一個專業的工作日誌分析師，專門從 Slack 對話中提取簡潔的工作內容摘要。

**重要**: 請仔細檢查輸入的訊息內容。如果沒有提供真實的 Slack 訊息，或訊息為空、無效，請回報沒有內容可分析。

**任務**: 分析以下 Slack 訊息，提取工作相關內容並以簡潔條列方式呈現。

**時間範圍**: $period_start 到 $period_end
**分析對象**: $user_name

**輸入訊息**:
$messages_content

**分析要求**:
1. 只提取實際存在的工作活動和任務討論
2. 忽略閒聊、打招呼等非工作內容
3. 每個條目格式：MM/DD [狀態標籤] 簡潔工作描述
4. 基於真實對話內容，絕對不要編造

**狀態標籤規則** (請嚴格按照以下順序檢查):
1. **優先檢查上線關鍵字**: 如果訊息包含以下任一關鍵字，必須添加 `上線` 標籤：
   - `develop` (包括 develop 分支)
   - `dev` 
   - `master`
   - `部署`
   - `上線`
   - `deploy`
   - `production`
2. **其次檢查測試關鍵字**: 如果訊息包含以下關鍵字，添加 `交測` 標籤：
   - `測試`
   - `測試機`
   - `test`
   - `testing`
   - `training`
   - `qa`
3. **最後才使用**: 其他工作相關訊息添加 `分支合併` 標籤

**重要**: 請特別注意 `develop` 關鍵字，這代表開發分支部署，必須使用 `上線` 標籤！

**輸出格式**: 請以以下格式回應，每行一個工作項目，每行結尾加上</br>：

**🔥 重要格式規則**：

**如果訊息中有 [使用者名稱: XXX] 資訊，請使用此格式**：
MM/DD `使用者名稱` `狀態標籤` 工作項目描述</br>

**如果訊息中沒有 [使用者名稱: XXX] 資訊，請使用此格式（不要包含任何使用者 ID 或名稱）**：
MM/DD `狀態標籤` 工作項目描述</br>

**絕對不要在輸出中使用**：
- 使用者 ID（如 U04GEUT18QN）
- 訊息格式中的使用者欄位
- 除非有明確的 [使用者名稱: XXX] 指示

**範例格式**:
08/25 `Jeffery` `上線` ws.buycase - 調整買屋廣告搜尋邏輯 (PR 61899)</br>
08/25 `Alice` `交測` ws.buycase - 修復購屋搜尋過濾問題</br>
08/25 `Bob` `分支合併` feature/user-profile - 完成用戶資料頁面開發</br>

**沒有使用者名稱時**：
08/25 `上線` ws.buycase - 調整買屋廣告搜尋邏輯 (PR 61899)</br>
08/25 `交測` ws.buycase - 修復購屋搜尋過濾問題</br>
08/25 `分支合併` feature/user-profile - 完成用戶資料頁面開發</br>

**重要**: 
- 不要使用 ``` ``` 包圍整個輸出內容
- 每行工作項目結尾必須加上</br>標籤
- 狀態標籤使用 ` ` 而不是 ** **

**如果沒有有效訊息內容，請回報**: 
```
本週期沒有發現工作相關內容
```
""")
    
    DAILY_SUMMARY_PROMPT = PromptTemplate("""
你是一個專業的工作日誌分析師，專門從 Slack 對話中提取簡潔的每日工作內容摘要。

**重要**: 請仔細檢查輸入的訊息內容。如果沒有提供真實的 Slack 訊息，或訊息為空、無效，請回報沒有內容可分析。

**任務**: 分析以下 Slack 訊息，提取工作相關內容並以簡潔條列方式呈現。

**🚨 極其重要**: 每條訊息後面都有 [建議標籤: xxx] 提示，你**必須**使用該建議標籤！不要自己判斷，直接使用建議的標籤！

**日期**: $date
**分析對象**: $user_name

**輸入訊息**:
$messages_content

**分析要求**:
1. 只提取實際存在的工作活動和任務討論
2. 忽略閒聊、打招呼等非工作內容
3. 每個條目格式：MM/DD [狀態標籤] 簡潔工作描述
4. 基於真實對話內容，絕對不要編造

**狀態標籤規則** (請嚴格按照以下順序檢查):
1. **優先檢查上線關鍵字**: 如果訊息包含以下任一關鍵字，必須添加 `上線` 標籤：
   - `develop` (包括 develop 分支)
   - `dev` 
   - `master`
   - `部署`
   - `上線`
   - `deploy`
   - `production`
2. **其次檢查測試關鍵字**: 如果訊息包含以下關鍵字，添加 `交測` 標籤：
   - `測試`
   - `測試機`
   - `test`
   - `testing`
   - `training`
   - `qa`
3. **最後才使用**: 其他工作相關訊息添加 `分支合併` 標籤

**重要**: 請特別注意 `develop` 關鍵字，這代表開發分支部署，必須使用 `上線` 標籤！

**輸出格式**: 請以以下格式回應，每行一個工作項目，每行結尾加上</br>：

MM/DD `狀態標籤` 工作項目描述</br>
MM/DD `狀態標籤` 工作項目描述</br>
MM/DD `狀態標籤` 工作項目描述</br>

**範例格式**:
08/25 `上線` ws.buycase - 部署買屋搜尋功能到生產環境</br>
08/25 `交測` feature/search - 測試機驗證搜尋邏輯</br>
08/25 `分支合併` hotfix/user-bug - 修復用戶登入問題</br>

**關鍵詞判斷範例**:
- 如果訊息含有 "`develop` ws.buycase" → 必須使用 `上線` (因為包含 develop)
- 如果訊息含有 "`master` web.007" → 必須使用 `上線` (因為包含 master)  
- 如果訊息含有 "test server 測試" → 使用 `交測` (因為包含 test)
- 如果訊息只有 "fix bug" → 使用 `分支合併` (沒有上線或測試關鍵字)

**操作步驟**:
1. 閱讀每條訊息和其後的 [建議標籤: xxx] 
2. **直接使用建議的標籤**，不要更改！
3. 格式化輸出：MM/DD `建議的標籤` 工作描述</br>

**重要指示**: 
- 🔥 **必須使用 [建議標籤: xxx] 中的標籤，不可改變！**
- 不要使用 ``` ``` 包圍整個輸出內容
- 每行工作項目結尾必須加上</br>標籤
- 狀態標籤使用 ` ` 格式

**如果沒有有效訊息內容，請回報**: 
```
今日沒有發現工作相關內容
```
""")
    
    PROJECT_EXTRACTION_PROMPT = PromptTemplate("""
從以下 Slack 訊息中識別和提取專案相關資訊。

**任務**: 識別所有提及的專案、功能開發、或重大工作計劃

**訊息內容**:
$messages_content

**輸出要求**:
- 專案名稱和描述
- 涉及的團隊成員
- 專案狀態和進展
- 關鍵里程碑
- 技術細節和決策

以結構化JSON格式回應。
""")
    
    MEETING_ANALYSIS_PROMPT = PromptTemplate("""
分析會議相關的 Slack 討論，提取會議要點。

**會議相關訊息**:
$messages_content

**分析重點**:
1. **會議主題和目的**
2. **主要討論點**
3. **做出的決定**
4. **行動項目** (Action Items)
5. **參與者**
6. **後續會議或跟進**

請以結構化方式整理這些資訊。
""")
    
    TREND_ANALYSIS_PROMPT = PromptTemplate("""
基於歷史工作日誌數據，分析工作模式和趨勢。

**歷史數據**:
$historical_data

**分析維度**:
1. **工作量變化趨勢**
2. **專案投入時間分配**
3. **協作模式變化**
4. **挑戰和問題類型**
5. **技能發展軌跡**
6. **生產力指標**

**時間範圍**: $period_start 到 $period_end

提供洞察和建議。
""")


class PromptBuilder:
    """Dynamic prompt builder for complex scenarios."""
    
    def __init__(self):
        """Initialize prompt builder."""
        self.base_templates = JournalPrompts()
        
    def build_weekly_journal_prompt(
        self,
        messages: List[Dict[str, Any]],
        context: PromptContext,
        include_trends: bool = False,
        focus_areas: Optional[List[str]] = None
    ) -> str:
        """
        Build comprehensive weekly journal prompt.
        
        Args:
            messages: Slack messages to analyze
            context: Context information
            include_trends: Whether to include trend analysis
            focus_areas: Specific areas to focus on
            
        Returns:
            Complete prompt string
        """
        # Format messages for prompt
        formatted_messages = self._format_messages_for_prompt(messages)
        
        # Prepare template variables
        template_vars = {
            "period_start": context.period_start.strftime("%Y-%m-%d"),
            "period_end": context.period_end.strftime("%Y-%m-%d"),
            "user_name": context.user_name or "Unknown User",
            "role": context.role or "Team Member",
            "team": context.team or "Development Team",
            "messages_content": formatted_messages
        }
        
        # Add focus areas if specified
        if focus_areas:
            focus_instruction = f"\n**特別關注**: {', '.join(focus_areas)}"
            template_vars["focus_areas"] = focus_instruction
        else:
            template_vars["focus_areas"] = ""
        
        # Render main prompt
        prompt = self.base_templates.WORK_ANALYSIS_PROMPT.render(**template_vars)
        
        # Add trend analysis if requested
        if include_trends and context.previous_journal:
            trend_section = self._build_trend_section(context.previous_journal)
            prompt += f"\n\n**趨勢分析**:\n{trend_section}"
        
        return prompt
    
    def build_custom_analysis_prompt(
        self,
        messages: List[Dict[str, Any]],
        analysis_type: str,
        custom_instructions: str,
        context: Optional[PromptContext] = None
    ) -> str:
        """
        Build custom analysis prompt.
        
        Args:
            messages: Messages to analyze
            analysis_type: Type of analysis
            custom_instructions: Custom analysis instructions
            context: Optional context
            
        Returns:
            Custom prompt string
        """
        formatted_messages = self._format_messages_for_prompt(messages)
        
        base_prompt = f"""
**自定義分析任務**: {analysis_type}

**特殊指示**:
{custom_instructions}

**訊息內容**:
{formatted_messages}

**輸出要求**:
- 結構化JSON格式
- 包含信心分數
- 提供分析依據
- 使用繁體中文回應
"""
        
        if context:
            context_info = f"""
**背景資訊**:
- 時間範圍: {context.period_start.strftime('%Y-%m-%d')} 到 {context.period_end.strftime('%Y-%m-%d')}
- 分析對象: {context.user_name or 'Unknown'}
- 團隊: {context.team or 'Unknown'}
"""
            base_prompt = context_info + base_prompt
        
        return base_prompt
    
    def _format_messages_for_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format messages for inclusion in prompt.
        
        Args:
            messages: Raw message data
            
        Returns:
            Formatted message string
        """
        formatted_lines = []
        
        for i, msg in enumerate(messages[:50], 1):  # Limit to 50 messages
            timestamp = msg.get('timestamp', 'Unknown time')
            user = msg.get('user', 'Unknown user')
            channel = msg.get('channel', 'Unknown channel')
            text = msg.get('text', '')
            
            # Clean and truncate long messages
            if len(text) > 500:
                text = text[:500] + "..."
            
            formatted_lines.append(
                f"[{i}] {timestamp} - {user} in #{channel}:\n{text}\n"
            )
        
        if len(messages) > 50:
            formatted_lines.append(f"\n... (省略其餘 {len(messages) - 50} 條訊息)")
        
        return "\n".join(formatted_lines)
    
    def _build_trend_section(self, previous_journal: str) -> str:
        """Build trend analysis section from previous journal."""
        return f"""
基於以下先前的工作日誌，請分析工作模式變化：

{previous_journal[:1000]}...

請比較本週與上週的：
1. 工作重點變化
2. 協作模式差異
3. 挑戰類型演變
4. 專案進展對比
"""
    
    def get_validation_prompt(self, ai_response: str) -> str:
        """
        Generate prompt for validating AI response quality.
        
        Args:
            ai_response: AI-generated response to validate
            
        Returns:
            Validation prompt
        """
        return f"""
請評估以下AI生成的工作日誌品質：

{ai_response}

**評估標準**:
1. **完整性** (0-10): 是否涵蓋所有重要工作內容
2. **準確性** (0-10): 資訊是否準確無誤
3. **結構性** (0-10): 組織是否清晰合理
4. **可讀性** (0-10): 語言是否流暢易懂
5. **實用性** (0-10): 是否對工作回顧有實際價值

**輸出格式**:
```json
{
  "overall_score": 總分,
  "dimension_scores": {
    "completeness": 完整性分數,
    "accuracy": 準確性分數,
    "structure": 結構性分數,
    "readability": 可讀性分數,
    "usefulness": 實用性分數
  },
  "strengths": ["優點1", "優點2"],
  "improvements": ["改進建議1", "改進建議2"],
  "is_acceptable": true/false
}
```
"""