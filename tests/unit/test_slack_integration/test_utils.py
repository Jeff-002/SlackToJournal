"""
Tests for Slack integration utilities.
"""

import pytest
from src.slack_integration.utils import (
    clean_message_text,
    extract_mentions,
    is_work_related_message,
    extract_action_items,
    categorize_message,
    get_message_urgency
)


class TestCleanMessageText:
    """Test message text cleaning."""
    
    def test_remove_user_mentions(self):
        """Test removing user mentions."""
        text = "Hey <@U12345> how are you?"
        cleaned = clean_message_text(text)
        assert cleaned == "Hey  how are you?"
    
    def test_remove_channel_mentions(self):
        """Test removing channel mentions."""
        text = "Posted in <#C12345|general>"
        cleaned = clean_message_text(text)
        assert cleaned == "Posted in #general"
    
    def test_remove_urls(self):
        """Test removing URLs."""
        text = "Check this out: <https://example.com|example.com>"
        cleaned = clean_message_text(text)
        assert cleaned == "Check this out: https://example.com"
    
    def test_clean_special_mentions(self):
        """Test cleaning special mentions."""
        text = "<!here> everyone, <!channel> meeting in 5"
        cleaned = clean_message_text(text)
        assert cleaned == "@here everyone, @channel meeting in 5"


class TestExtractMentions:
    """Test mention extraction."""
    
    def test_extract_user_mentions(self):
        """Test extracting user mentions."""
        text = "Hello <@U12345> and <@U67890>!"
        mentions = extract_mentions(text)
        assert mentions['users'] == ['U12345', 'U67890']
        assert mentions['channels'] == []
    
    def test_extract_channel_mentions(self):
        """Test extracting channel mentions."""
        text = "Posted in <#C12345|general> and <#C67890|dev-team>"
        mentions = extract_mentions(text)
        assert mentions['users'] == []
        assert mentions['channels'] == ['general', 'dev-team']


class TestIsWorkRelatedMessage:
    """Test work-related message detection."""
    
    def test_work_related_development(self):
        """Test development-related messages."""
        messages = [
            "Fixed the bug in the authentication module",
            "Pull request ready for review",
            "Deployed version 2.1 to staging",
            "Unit tests are failing on CI"
        ]
        
        for msg in messages:
            assert is_work_related_message(msg), f"Should detect work content: {msg}"
    
    def test_work_related_project_management(self):
        """Test project management messages."""
        messages = [
            "Sprint planning meeting tomorrow at 9am",
            "Milestone deadline is next Friday",
            "Task XYZ-123 is completed",
            "Project status update: we're on track"
        ]
        
        for msg in messages:
            assert is_work_related_message(msg), f"Should detect work content: {msg}"
    
    def test_non_work_related_social(self):
        """Test non-work social messages."""
        messages = [
            "Happy birthday! 🎉",
            "Anyone want to grab lunch?",
            "Great weather today!",
            "Did you watch the game last night?",
            "lol that's funny 😂"
        ]
        
        for msg in messages:
            assert not is_work_related_message(msg), f"Should not detect work content: {msg}"
    
    def test_short_messages_excluded(self):
        """Test that very short messages are excluded."""
        short_messages = ["ok", "yes", "no", "thanks", "👍"]
        
        for msg in short_messages:
            assert not is_work_related_message(msg)
    
    def test_code_blocks_included(self):
        """Test that messages with code are included."""
        code_messages = [
            "Here's the fix: ```python\ndef func():\n    return True```",
            "Try this command: `git status`"
        ]
        
        for msg in code_messages:
            assert is_work_related_message(msg)


class TestExtractActionItems:
    """Test action item extraction."""
    
    def test_extract_need_to_items(self):
        """Test extracting 'need to' action items."""
        text = "We need to fix the database issue and need to update the docs"
        items = extract_action_items(text)
        assert any("fix the database issue" in item for item in items)
        assert any("update the docs" in item for item in items)
    
    def test_extract_todo_items(self):
        """Test extracting TODO items."""
        text = "TODO: update the configuration file"
        items = extract_action_items(text)
        assert any("update the configuration" in item for item in items)
    
    def test_extract_bullet_points(self):
        """Test extracting bullet point actions."""
        text = "Action items:\n- Review the PR\n- Test the new feature\n• Update documentation"
        items = extract_action_items(text)
        assert len(items) >= 2
        assert any("Review the PR" in item for item in items)


class TestCategorizeMessage:
    """Test message categorization."""
    
    def test_development_category(self):
        """Test development message categorization."""
        text = "Fixed the bug in the payment processing code"
        category = categorize_message(text)
        assert category == "development"
    
    def test_meeting_category(self):
        """Test meeting message categorization."""
        text = "Team meeting scheduled for tomorrow at 2pm"
        category = categorize_message(text)
        assert category == "meeting"
    
    def test_project_management_category(self):
        """Test project management categorization."""
        text = "Sprint milestone achieved, moving to next phase"
        category = categorize_message(text)
        assert category == "project_management"
    
    def test_general_category(self):
        """Test general category for uncategorized messages."""
        text = "Random message without specific work keywords"
        category = categorize_message(text)
        assert category == "general"


class TestGetMessageUrgency:
    """Test message urgency detection."""
    
    def test_high_urgency(self):
        """Test high urgency detection."""
        messages = [
            "URGENT: Production system is down",
            "Need this ASAP for client meeting",
            "Critical bug blocking deployment"
        ]
        
        for msg in messages:
            assert get_message_urgency(msg) == "high"
    
    def test_medium_urgency(self):
        """Test medium urgency detection."""
        messages = [
            "Important: Please review by end of week",
            "Priority task for this sprint",
            "Deadline is Friday"
        ]
        
        for msg in messages:
            assert get_message_urgency(msg) == "medium"
    
    def test_low_urgency(self):
        """Test low urgency detection."""
        messages = [
            "General update on project status",
            "Sharing some interesting findings",
            "FYI - new documentation available"
        ]
        
        for msg in messages:
            assert get_message_urgency(msg) == "low"