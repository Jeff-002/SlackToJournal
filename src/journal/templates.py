"""
Journal templates and formatters.

This module provides templates for different journal formats
and utilities for formatting structured content.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from string import Template
import json

from ..core.logging import get_logger
from .schemas import JournalFormat, TemplateConfig, JournalMetadata


logger = get_logger(__name__)


class MarkdownFormatter:
    """Formatter for Markdown output."""
    
    @staticmethod
    def format_header(metadata: JournalMetadata, level: int = 1) -> str:
        """Format journal header."""
        header_prefix = "#" * level
        date_range = f"{metadata.period_start.strftime('%m/%d')} - {metadata.period_end.strftime('%m/%d')}"
        
        return f"""# 工作日誌_{metadata.period_start.strftime('%Y%m%d')}_{metadata.period_end.strftime('%Y%m%d')}

**期間**: {date_range}  
**生成**: {metadata.generated_at.strftime('%Y-%m-%d %H:%M')}  

"""
    
    @staticmethod
    def format_simple_work_list(work_items: List[Dict[str, Any]], summary: Dict[str, Any], has_content: bool = None) -> str:
        """Format simple work items list."""
        # Check if there's actually content
        if has_content is False or not work_items:
            return "本期間沒有檢測到工作相關的 Slack 討論內容。\n"
        
        # Group by category
        categories = {}
        for item in work_items:
            category = item.get('category', '其他')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        content = []
        
        # Add main focus summary if available
        if summary and summary.get('main_focus'):
            content.append(f"**本週重點**: {summary['main_focus']}\n")
        
        # Add work items by category
        category_order = ['開發', '會議', '討論', '決策', '任務', '問題', '計劃', '其他']
        
        for category in category_order:
            if category in categories:
                items = categories[category]
                content.append(f"## {category}")
                for item in items:
                    content_text = item.get('content', '未知工作項目')
                    participants = item.get('participants', [])
                    if participants:
                        participant_str = f" ({', '.join(participants[:2])}" + ("等" if len(participants) > 2 else "") + ")"
                    else:
                        participant_str = ""
                    content.append(f"- {content_text}{participant_str}")
                content.append("")
        
        return "\n".join(content)
    
    @staticmethod
    def format_summary(summary: str) -> str:
        """Format executive summary."""
        return f"""
## 📋 執行摘要

{summary}

---
"""
    
    @staticmethod
    def format_highlights(highlights: List[str]) -> str:
        """Format key highlights."""
        if not highlights:
            return ""
        
        highlights_md = "\n".join(f"- ✨ {highlight}" for highlight in highlights)
        return f"""
## 🌟 本週重點

{highlights_md}

---
"""
    
    @staticmethod
    def format_projects(projects: List[Dict[str, Any]]) -> str:
        """Format project breakdown."""
        if not projects:
            return ""
        
        content = ["## 📁 專案進展\n"]
        
        for project in projects:
            project_name = project.get('project_name', '未知專案')
            work_items = project.get('work_items', [])
            achievements = project.get('key_achievements', [])
            challenges = project.get('challenges', [])
            next_steps = project.get('next_steps', [])
            
            content.append(f"### 🚀 {project_name}\n")
            
            # Work items
            if work_items:
                content.append("#### 工作項目\n")
                for item in work_items:
                    status_emoji = {
                        'completed': '✅',
                        'in_progress': '🔄', 
                        'planned': '📋',
                        'blocked': '🚫',
                        'cancelled': '❌'
                    }.get(item.get('status', 'planned'), '📋')
                    
                    priority_emoji = {
                        'high': '🔴',
                        'medium': '🟡',
                        'low': '🟢'
                    }.get(item.get('priority', 'medium'), '🟡')
                    
                    title = item.get('title', '未知任務')
                    description = item.get('description', '')
                    
                    content.append(f"- {status_emoji} {priority_emoji} **{title}**")
                    if description:
                        content.append(f"  - {description}")
                content.append("")
            
            # Achievements
            if achievements:
                content.append("#### ✨ 主要成就\n")
                content.extend(f"- {achievement}" for achievement in achievements)
                content.append("")
            
            # Challenges
            if challenges:
                content.append("#### ⚠️ 遇到的挑戰\n")
                content.extend(f"- {challenge}" for challenge in challenges)
                content.append("")
            
            # Next steps
            if next_steps:
                content.append("#### 📋 下一步計劃\n")
                content.extend(f"- {step}" for step in next_steps)
                content.append("")
            
            content.append("---\n")
        
        return "\n".join(content)
    
    @staticmethod
    def format_categories(work_by_category: Dict[str, List[Dict[str, Any]]]) -> str:
        """Format work by categories."""
        if not work_by_category:
            return ""
        
        category_names = {
            'development': '💻 開發工作',
            'project_management': '📊 專案管理',
            'meeting': '🤝 會議討論',
            'decision': '🎯 決策制定',
            'documentation': '📝 文件撰寫',
            'support': '🛠️ 技術支援',
            'collaboration': '👥 協作交流',
            'planning': '📅 規劃安排',
            'review': '🔍 審查評估',
            'general': '📋 一般工作'
        }
        
        content = ["## 📊 工作分類分析\n"]
        
        for category, items in work_by_category.items():
            if not items:
                continue
                
            category_title = category_names.get(category, f"📋 {category}")
            content.append(f"### {category_title}\n")
            
            for item in items:
                title = item.get('title', '未知項目')
                status = item.get('status', 'unknown')
                status_emoji = {
                    'completed': '✅',
                    'in_progress': '🔄',
                    'planned': '📋',
                    'blocked': '🚫',
                    'cancelled': '❌'
                }.get(status, '📋')
                
                content.append(f"- {status_emoji} {title}")
            
            content.append("")
        
        content.append("---\n")
        return "\n".join(content)
    
    @staticmethod
    def format_action_items(action_items: List[Dict[str, Any]]) -> str:
        """Format action items."""
        if not action_items:
            return ""
        
        content = ["## 📝 待辦事項\n"]
        
        # Group by priority
        high_priority = [item for item in action_items if item.get('priority') == 'high']
        medium_priority = [item for item in action_items if item.get('priority') == 'medium']
        low_priority = [item for item in action_items if item.get('priority') == 'low']
        
        for priority_group, title, emoji in [
            (high_priority, "高優先級", "🔴"),
            (medium_priority, "中優先級", "🟡"),
            (low_priority, "低優先級", "🟢")
        ]:
            if priority_group:
                content.append(f"### {emoji} {title}\n")
                for item in priority_group:
                    title = item.get('title', '未知事項')
                    description = item.get('description', '')
                    content.append(f"- **{title}**")
                    if description:
                        content.append(f"  - {description}")
                content.append("")
        
        content.append("---\n")
        return "\n".join(content)
    
    @staticmethod
    def format_metrics(metrics: Dict[str, Any]) -> str:
        """Format metrics section."""
        if not metrics:
            return ""
        
        content = ["## 📈 工作指標\n"]
        
        # Create metrics table
        content.append("| 指標 | 數值 |")
        content.append("|------|------|")
        
        metric_labels = {
            'total_messages_analyzed': '分析訊息數',
            'projects_involved': '參與專案數',
            'meetings_attended': '參與會議數',
            'decisions_made': '制定決策數',
            'work_items_completed': '完成工作項目',
            'work_items_in_progress': '進行中項目'
        }
        
        for key, value in metrics.items():
            label = metric_labels.get(key, key.replace('_', ' ').title())
            content.append(f"| {label} | {value} |")
        
        content.append("\n---\n")
        return "\n".join(content)
    
    @staticmethod
    def format_learnings_and_challenges(learnings: List[str], challenges: List[str]) -> str:
        """Format learnings and challenges."""
        content = []
        
        if learnings:
            content.append("## 💡 學習與洞察\n")
            content.extend(f"- {learning}" for learning in learnings)
            content.append("")
        
        if challenges:
            content.append("## ⚠️ 挑戰與問題\n")
            content.extend(f"- {challenge}" for challenge in challenges)
            content.append("")
        
        if content:
            content.append("---\n")
        
        return "\n".join(content)
    
    @staticmethod
    def format_footer(metadata: JournalMetadata) -> str:
        """Format journal footer."""
        return f"""
---

**📊 統計資訊**
- 分析訊息數: {metadata.total_messages}
- 識別工作項目: {metadata.work_items_count}
- 涉及專案數: {metadata.projects_count}
- 整體信心分數: {metadata.confidence_score:.1%}

*本日誌由 SlackToJournal 自動生成 v{metadata.generator_version}*  
*生成時間: {metadata.generated_at.strftime('%Y-%m-%d %H:%M:%S')}*
"""


class HTMLFormatter:
    """Formatter for HTML output."""
    
    @staticmethod
    def format_journal(content: str, metadata: JournalMetadata) -> str:
        """Format complete journal as HTML."""
        # Convert Markdown to HTML (simplified)
        html_content = MarkdownFormatter._markdown_to_html(content)
        
        return f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{metadata.title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3 {{ color: #2c3e50; }}
        .metadata {{ 
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .highlight {{ color: #e74c3c; }}
        table {{ 
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        th, td {{ 
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{ background-color: #f2f2f2; }}
        .emoji {{ font-size: 1.2em; }}
    </style>
</head>
<body>
    <div class="metadata">
        <strong>期間:</strong> {metadata.period_start.strftime('%Y-%m-%d')} 到 {metadata.period_end.strftime('%Y-%m-%d')}<br>
        <strong>作者:</strong> {metadata.author_name}<br>
        <strong>團隊:</strong> {metadata.team or 'N/A'}<br>
        <strong>生成時間:</strong> {metadata.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
    </div>
    
    {html_content}
    
    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.9em; color: #666;">
        本日誌由 SlackToJournal 自動生成 v{metadata.generator_version}
    </footer>
</body>
</html>
"""
    
    @staticmethod
    def _markdown_to_html(markdown: str) -> str:
        """Simple Markdown to HTML conversion."""
        # This is a simplified conversion - in production, use a proper Markdown library
        html = markdown
        
        # Headers
        html = html.replace('### ', '<h3>').replace('\n', '</h3>\n', 1) if '### ' in html else html
        html = html.replace('## ', '<h2>').replace('\n', '</h2>\n', 1) if '## ' in html else html
        html = html.replace('# ', '<h1>').replace('\n', '</h1>\n', 1) if '# ' in html else html
        
        # Bold
        import re
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        
        # Lists
        lines = html.split('\n')
        in_list = False
        result_lines = []
        
        for line in lines:
            if line.strip().startswith('- '):
                if not in_list:
                    result_lines.append('<ul>')
                    in_list = True
                result_lines.append(f'<li>{line[2:].strip()}</li>')
            else:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                result_lines.append(line)
        
        if in_list:
            result_lines.append('</ul>')
        
        return '\n'.join(result_lines)


class JournalTemplates:
    """Collection of journal templates."""
    
    WEEKLY_MARKDOWN_TEMPLATE = Template("""
$header

$summary

$highlights

$projects

$categories

$action_items

$metrics

$learnings_challenges

$footer
""")
    
    DAILY_MARKDOWN_TEMPLATE = Template("""
# 📅 每日工作總結 - $date

$summary

## 🎯 今日重點工作
$key_work

## ✅ 完成項目
$completed_items

## 🔄 進行中工作
$in_progress_items

## ⚠️ 遇到挑戰
$challenges

## 📋 明日計劃
$tomorrow_plans

$footer
""")
    
    SIMPLE_WORK_LOG_TEMPLATE = Template("""$header$work_items
---
*共 $total_items 項工作內容*
""")

    @classmethod
    def render_simple_work_log(
        cls,
        journal_data: Dict[str, Any],
        metadata: JournalMetadata
    ) -> str:
        """Render simple work log template."""
        formatter = MarkdownFormatter()
        
        work_items = journal_data.get('work_items', [])
        summary = journal_data.get('summary', {})
        has_content = journal_data.get('has_content', True)
        
        header = formatter.format_header(metadata)
        work_list = formatter.format_simple_work_list(work_items, summary, has_content)
        total_items = summary.get('total_items', len(work_items))
        
        return cls.SIMPLE_WORK_LOG_TEMPLATE.substitute(
            header=header,
            work_items=work_list,
            total_items=total_items
        )
    
    @classmethod
    def render_weekly_journal(
        cls,
        journal_data: Dict[str, Any],
        metadata: JournalMetadata,
        config: TemplateConfig
    ) -> str:
        """Render weekly journal using template."""
        formatter = MarkdownFormatter()
        
        # Build sections based on config
        sections = {}
        
        sections['header'] = formatter.format_header(metadata) if config.include_summary else ""
        sections['summary'] = formatter.format_summary(journal_data.get('executive_summary', '')) if config.include_summary else ""
        sections['highlights'] = formatter.format_highlights(journal_data.get('key_highlights', [])) if config.include_highlights else ""
        sections['projects'] = formatter.format_projects(journal_data.get('projects', [])) if config.include_projects else ""
        sections['categories'] = formatter.format_categories(journal_data.get('work_by_category', {})) if config.include_categories else ""
        sections['action_items'] = formatter.format_action_items(journal_data.get('action_items', [])) if config.include_action_items else ""
        sections['metrics'] = formatter.format_metrics(journal_data.get('metrics', {})) if config.include_metrics else ""
        
        learnings = journal_data.get('learnings', [])
        challenges = journal_data.get('challenges', [])
        sections['learnings_challenges'] = formatter.format_learnings_and_challenges(learnings, challenges) if (config.include_learnings or config.include_challenges) else ""
        
        sections['footer'] = formatter.format_footer(metadata)
        
        # Render template
        return cls.WEEKLY_MARKDOWN_TEMPLATE.substitute(**sections)
    
    @classmethod
    def get_default_config(cls, format_type: JournalFormat = JournalFormat.MARKDOWN) -> TemplateConfig:
        """Get default template configuration."""
        return TemplateConfig(
            name="default_weekly",
            description="Default weekly journal template",
            format_type=format_type,
            include_summary=True,
            include_highlights=True,
            include_projects=True,
            include_categories=True,
            include_timeline=False,
            include_metrics=True,
            include_action_items=True,
            include_learnings=True,
            include_challenges=True,
            use_emoji=True,
            table_of_contents=False,
            syntax_highlighting=True
        )