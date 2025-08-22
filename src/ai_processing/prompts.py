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
3. 每個條目格式：MM/DD 簡潔工作描述
4. 基於真實對話內容，絕對不要編造

**輸出格式**: 請以以下格式回應，每行一個工作項目：

```
MM/DD 工作項目描述
MM/DD 工作項目描述
MM/DD 工作項目描述
```

**範例格式**:
```
8/21 實作Slack讀取工作內容
8/21 修改S2列表Bug上測試機
8/22 實作Slack工作日誌總結專案
```

**如果沒有有效訊息內容，請回報**: 
```
本週期沒有發現工作相關內容
```
""")
    
    DAILY_SUMMARY_PROMPT = PromptTemplate("""
你是一個專業的工作日誌分析師，專門從 Slack 對話中提取簡潔的每日工作內容摘要。

**重要**: 請仔細檢查輸入的訊息內容。如果沒有提供真實的 Slack 訊息，或訊息為空、無效，請回報沒有內容可分析。

**任務**: 分析以下 Slack 訊息，提取工作相關內容並以簡潔條列方式呈現。

**日期**: $date
**分析對象**: $user_name

**輸入訊息**:
$messages_content

**分析要求**:
1. 只提取實際存在的工作活動和任務討論
2. 忽略閒聊、打招呼等非工作內容
3. 每個條目格式：MM/DD 簡潔工作描述
4. 基於真實對話內容，絕對不要編造

**輸出格式**: 請以以下格式回應，每行一個工作項目：

```
MM/DD 工作項目描述
MM/DD 工作項目描述
MM/DD 工作項目描述
```

**範例格式**:
```
8/22 實作Slack工作日誌總結專案
8/22 修復日誌生成驗證問題
8/22 測試每日摘要功能
```

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