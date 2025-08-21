"""
Utility functions for Slack integration.

This module provides helper functions for processing Slack messages,
analyzing content, and extracting work-related information.
"""

import re
from typing import List, Set, Dict, Any
from datetime import datetime

from ..core.logging import get_logger


logger = get_logger(__name__)


def clean_message_text(text: str) -> str:
    """
    Clean Slack message text by removing formatting and mentions.
    
    Args:
        text: Raw Slack message text
        
    Returns:
        Cleaned message text
    """
    if not text:
        return ""
    
    # Remove user mentions (<@U123456>)
    text = re.sub(r'<@U[A-Z0-9]+>', '', text)
    
    # Remove channel mentions (<#C123456|channel-name>)
    text = re.sub(r'<#C[A-Z0-9]+\|([^>]+)>', r'#\1', text)
    
    # Remove URLs (<http://example.com|example.com>)
    text = re.sub(r'<(https?://[^>|]+)\|?[^>]*>', r'\1', text)
    
    # Remove special Slack formatting
    text = re.sub(r'<!here>', '@here', text)
    text = re.sub(r'<!channel>', '@channel', text)
    text = re.sub(r'<!everyone>', '@everyone', text)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    return text.strip()


def extract_mentions(text: str) -> Dict[str, List[str]]:
    """
    Extract mentions from Slack message text.
    
    Args:
        text: Slack message text
        
    Returns:
        Dictionary with 'users' and 'channels' lists
    """
    mentions = {
        'users': [],
        'channels': []
    }
    
    # Extract user mentions
    user_mentions = re.findall(r'<@(U[A-Z0-9]+)>', text)
    mentions['users'] = user_mentions
    
    # Extract channel mentions
    channel_mentions = re.findall(r'<#C[A-Z0-9]+\|([^>]+)>', text)
    mentions['channels'] = channel_mentions
    
    return mentions


def is_work_related_message(text: str) -> bool:
    """
    Analyze if a message is work-related based on content.
    
    Args:
        text: Cleaned message text
        
    Returns:
        True if message appears work-related
    """
    if not text or len(text.strip()) < 5:
        return False
    
    text_lower = text.lower()
    
    # Work-related keywords (positive indicators)
    work_keywords = {
        # Project and task management
        'project', 'task', 'deadline', 'milestone', 'sprint', 'epic', 'story',
        'issue', 'bug', 'feature', 'requirement', 'specification',
        
        # Development terms
        'code', 'repository', 'commit', 'merge', 'pull request', 'pr', 'branch',
        'deploy', 'deployment', 'release', 'version', 'build', 'test', 'testing',
        
        # Meeting and collaboration
        'meeting', 'discussion', 'decision', 'review', 'feedback', 'approval',
        'presentation', 'demo', 'standup', 'retrospective', 'planning',
        
        # Business terms
        'client', 'customer', 'user', 'stakeholder', 'business', 'requirement',
        'proposal', 'contract', 'budget', 'timeline', 'scope',
        
        # Documentation and process
        'document', 'documentation', 'specification', 'guideline', 'process',
        'procedure', 'workflow', 'architecture', 'design',
        
        # Status and progress
        'progress', 'status', 'update', 'complete', 'finished', 'done', 'todo',
        'working on', 'started', 'blocked', 'help needed'
    }
    
    # Exclude social/casual keywords
    exclude_keywords = {
        'lunch', 'coffee', 'weather', 'weekend', 'vacation', 'holiday',
        'birthday', 'congratulations', 'congrats', 'party', 'celebration',
        'music', 'movie', 'tv', 'game', 'sport', 'football', 'basketball',
        'joke', 'funny', 'lol', 'haha', 'emoji', 'meme'
    }
    
    # Check for work keywords
    work_score = 0
    for keyword in work_keywords:
        if keyword in text_lower:
            work_score += 1
    
    # Check for exclude keywords (penalty)
    exclude_score = 0
    for keyword in exclude_keywords:
        if keyword in text_lower:
            exclude_score += 2
    
    # Work-related patterns
    work_patterns = [
        r'\b(will|going to|plan to|need to|have to)\s+\w+',  # Action plans
        r'\b(completed|finished|done with|working on)\s+\w+',  # Status updates  
        r'\b(review|feedback|thoughts on)\s+\w+',  # Collaboration
        r'\b(issue|problem|bug)\s+with\s+\w+',  # Problem reporting
        r'\b(meeting|call|sync)\s+(today|tomorrow|this week)',  # Scheduling
        r'\b(deadline|due date|timeline)\s+',  # Time constraints
        r'[A-Z]+-\d+',  # Ticket numbers (JIRA-style)
        r'v\d+\.\d+',   # Version numbers
    ]
    
    pattern_matches = 0
    for pattern in work_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            pattern_matches += 1
    
    # Decision logic
    final_score = work_score + pattern_matches - exclude_score
    
    # Additional checks
    has_question = '?' in text
    has_code_block = '```' in text or '`' in text
    mentions_tools = any(tool in text_lower for tool in [
        'jira', 'github', 'confluence', 'slack', 'zoom', 'calendar',
        'trello', 'asana', 'monday', 'notion'
    ])
    
    if has_code_block or mentions_tools:
        final_score += 2
    
    if has_question and work_score > 0:
        final_score += 1
    
    # Message length bonus for substantive content
    if len(text) > 100:
        final_score += 1
    
    logger.debug(f"Work analysis - Score: {final_score}, Text: {text[:50]}...")
    
    return final_score >= 2


def extract_action_items(text: str) -> List[str]:
    """
    Extract action items from message text.
    
    Args:
        text: Message text to analyze
        
    Returns:
        List of potential action items
    """
    action_items = []
    text_lower = text.lower()
    
    # Action patterns
    action_patterns = [
        r'\b(need to|have to|must|should|will)\s+([^.!?]+)',
        r'\b(todo|to-do|action item):\s*([^.!?]+)',
        r'\b(please|can you|could you)\s+([^.!?]+)',
        r'[-•]\s*([^.!?\n]+)',  # Bullet points
    ]
    
    for pattern in action_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                action_item = match[-1].strip()
            else:
                action_item = match.strip()
            
            if len(action_item) > 10 and action_item not in action_items:
                action_items.append(action_item)
    
    return action_items


def categorize_message(text: str) -> str:
    """
    Categorize message by its primary work-related topic.
    
    Args:
        text: Message text to categorize
        
    Returns:
        Category string
    """
    text_lower = text.lower()
    
    categories = {
        'development': [
            'code', 'programming', 'development', 'coding', 'repository', 'commit',
            'merge', 'pull request', 'branch', 'build', 'deploy', 'test', 'bug'
        ],
        'project_management': [
            'project', 'milestone', 'deadline', 'timeline', 'sprint', 'epic',
            'task', 'story', 'planning', 'status', 'progress'
        ],
        'meeting': [
            'meeting', 'call', 'discussion', 'sync', 'standup', 'retrospective',
            'review', 'presentation', 'demo'
        ],
        'decision': [
            'decision', 'approval', 'feedback', 'review', 'thoughts', 'opinion',
            'recommendation', 'proposal'
        ],
        'documentation': [
            'document', 'documentation', 'spec', 'specification', 'guideline',
            'process', 'procedure', 'architecture', 'design'
        ],
        'support': [
            'help', 'support', 'issue', 'problem', 'error', 'blocked', 'stuck',
            'question', 'assistance'
        ]
    }
    
    category_scores = {}
    for category, keywords in categories.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if score > 0:
            category_scores[category] = score
    
    if not category_scores:
        return 'general'
    
    # Return category with highest score
    return max(category_scores.items(), key=lambda x: x[1])[0]


def extract_date_mentions(text: str) -> List[str]:
    """
    Extract date and time mentions from text.
    
    Args:
        text: Text to analyze
        
    Returns:
        List of date/time strings found
    """
    date_patterns = [
        r'\b(today|tomorrow|yesterday)\b',
        r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        r'\b(this|next|last)\s+(week|month|quarter|year)\b',
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # Date formats
        r'\b\d{1,2}:\d{2}\s*(am|pm)?\b',       # Time formats
        r'\b(morning|afternoon|evening|night)\b',
        r'\b(eod|end of day|by friday|by monday)\b'
    ]
    
    dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        dates.extend(matches)
    
    return list(set(dates))  # Remove duplicates


def get_message_urgency(text: str) -> str:
    """
    Determine message urgency level.
    
    Args:
        text: Message text to analyze
        
    Returns:
        Urgency level: 'high', 'medium', 'low'
    """
    text_lower = text.lower()
    
    high_urgency_indicators = [
        'urgent', 'asap', 'immediately', 'critical', 'emergency',
        'deadline today', 'due today', 'overdue', 'blocking'
    ]
    
    medium_urgency_indicators = [
        'important', 'priority', 'soon', 'this week', 'by friday',
        'deadline', 'due date', 'need feedback'
    ]
    
    if any(indicator in text_lower for indicator in high_urgency_indicators):
        return 'high'
    elif any(indicator in text_lower for indicator in medium_urgency_indicators):
        return 'medium'
    else:
        return 'low'