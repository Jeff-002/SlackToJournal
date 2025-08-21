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
你是一個專業的工作日誌分析師，專門分析 Slack 對話並提取工作相關內容。

**任務**: 分析以下 Slack 訊息，識別並結構化工作相關內容。

**時間範圍**: $period_start 到 $period_end
**分析對象**: $user_name ($role)
**團隊**: $team

**輸入訊息**:
$messages_content

**分析要求**:
1. 識別所有工作相關的活動和任務
2. 按專案分組相關工作內容
3. 提取關鍵成就、挑戰和學習
4. 識別需要後續行動的項目
5. 分析工作模式和趨勢

**輸出格式**: 請以以下JSON格式回應：

```json
{
  "period": "$period_start 到 $period_end",
  "executive_summary": "整週工作的高層次摘要",
  "key_highlights": ["重點成就1", "重點成就2"],
  "projects": [
    {
      "project_name": "專案名稱",
      "work_items": [
        {
          "title": "工作項目標題",
          "description": "詳細描述",
          "category": "development|project_management|meeting|decision|documentation|support|collaboration|planning|review|general",
          "priority": "high|medium|low",
          "status": "completed|in_progress|planned|blocked|cancelled",
          "participants": ["參與者1", "參與者2"],
          "confidence_score": 0.9
        }
      ],
      "key_achievements": ["成就1", "成就2"],
      "challenges": ["挑戰1", "挑戰2"],
      "next_steps": ["下一步1", "下一步2"]
    }
  ],
  "action_items": [
    {
      "title": "需要跟進的事項",
      "description": "詳細說明",
      "category": "相關分類",
      "priority": "優先級",
      "status": "planned",
      "confidence_score": 0.8
    }
  ],
  "learnings": ["學習點1", "學習點2"],
  "challenges": ["遇到的挑戰1", "遇到的挑戰2"],
  "metrics": {
    "total_messages_analyzed": 數字,
    "projects_involved": 數字,
    "meetings_attended": 數字,
    "decisions_made": 數字
  }
}
```

**重要指示**:
- 只分析工作相關內容，排除社交閒聊
- 使用繁體中文回應
- 為每個工作項目提供信心分數 (0.0-1.0)
- 合併相關的討論主題
- 注重實際產出和成果
""")
    
    DAILY_SUMMARY_PROMPT = PromptTemplate("""
分析以下單日的工作訊息，生成每日工作摘要。

**日期**: $date
**使用者**: $user_name

**訊息內容**:
$messages_content

**請提供以下結構化分析**:
1. **今日重點工作** (3-5個關鍵活動)
2. **完成的任務** (具體完成項目)
3. **進行中的工作** (尚未完成但有進展)
4. **遇到的挑戰** (問題和阻礙)
5. **明日計劃** (從討論中推斷的下一步)
6. **重要決定** (做出的決策)
7. **協作互動** (與他人的重要協作)

以JSON格式回應，包含信心分數。
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