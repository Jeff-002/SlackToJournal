"""
Slack service using direct API integration.

This provides an alternative to MCP-based integration using
Slack Web API directly for easier setup.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re

from ..core.logging import get_logger
from ..core.exceptions import SlackIntegrationError, ValidationError
from ..settings import SlackSettings
from .direct_client import DirectSlackClient
from .schemas import SlackMessage, MessageFilter
from .utils import is_work_related_message, clean_message_text


logger = get_logger(__name__)


class DirectSlackService:
    """
    Slack service using direct Web API integration.
    
    Alternative to MCP-based service that provides the same functionality
    but with simpler setup using Slack bot tokens.
    """
    
    def __init__(self, bot_token: str, user_token: Optional[str] = None, settings: Optional[SlackSettings] = None) -> None:
        """
        Initialize Direct Slack service.
        
        Args:
            bot_token: Slack bot token (xoxb-)
            user_token: Optional user token (xoxp-)
            settings: Slack settings including target channels and exclude keywords
        """
        self.client = DirectSlackClient(bot_token, user_token)
        self.settings = settings
        self.target_channels = settings.target_channels if settings else None
        if self.target_channels:
            logger.info(f"Initialized Direct Slack service with target channels: {', '.join(self.target_channels)}")
        else:
            logger.info("Initialized Direct Slack service with auto-detect channels")
            
        if self.settings and self.settings.exclude_keywords:
            logger.info(f"Excluding messages with keywords: {', '.join(self.settings.exclude_keywords)}")
    
    async def get_weekly_work_messages(
        self,
        target_date: Optional[datetime] = None,
        work_channels: Optional[List[str]] = None,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> List[SlackMessage]:
        """
        Get work-related messages from the current or specified week.
        
        Args:
            target_date: Target date for week calculation (defaults to now)
            work_channels: List of channel IDs to search (defaults to all accessible channels)
            user_email: Filter messages by specific user email (if provided)
            user_name: Filter messages by specific user name (if provided)
            
        Returns:
            List of work-related messages from the week
        """
        if target_date is None:
            target_date = datetime.now()
        
        # Calculate work week boundaries (Monday to Friday only)
        week_start = target_date - timedelta(days=target_date.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        # Only include Monday to Friday (4 days after Monday)
        week_end = week_start + timedelta(days=4, hours=23, minutes=59, seconds=59)
        
        logger.info(f"Retrieving work messages for week: {week_start.date()} to {week_end.date()}")
        
        # Authenticate
        await self.client.authenticate()
        
        # Get channels if not specified
        if work_channels is None:
            work_channels = await self._get_work_channels()
        
        # Create message filter
        message_filter = MessageFilter(
            channels=work_channels,
            start_date=week_start,
            end_date=week_end,
            include_bots=False,
            include_threads=True,
            min_length=5,
            user_emails=[user_email] if user_email else None,
            user_names=[user_name] if user_name else None
        )
        
        # Retrieve messages from all channels
        all_messages = []
        for channel_id in work_channels:
            try:
                channel_messages = await self.client.get_messages(
                    channel_id=channel_id,
                    message_filter=message_filter,
                    limit=200  # Reasonable limit per channel
                )
                all_messages.extend(channel_messages)
            except Exception as e:
                logger.warning(f"Failed to get messages from channel {channel_id}: {e}")
                continue
        
        # Filter for work-related content
        work_messages = self._filter_work_messages(all_messages)
        
        logger.info(f"Retrieved {len(work_messages)} work-related messages")
        return work_messages
    
    async def get_channel_work_summary(
        self,
        channel_id: str,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Get work summary for a specific channel.
        
        Args:
            channel_id: Channel ID to analyze
            days_back: Number of days to look back
            
        Returns:
            Dictionary containing channel work summary
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        await self.client.authenticate()
        
        # Get channel info
        channels = await self.client.get_channels()
        channel_info = next((c for c in channels if c.id == channel_id), None)
        
        if not channel_info:
            raise ValidationError(f"Channel {channel_id} not found")
        
        # Get messages
        message_filter = MessageFilter(
            start_date=start_date,
            end_date=end_date,
            include_bots=False
        )
        
        messages = await self.client.get_messages(
            channel_id=channel_id,
            message_filter=message_filter,
            limit=500
        )
        
        # Analyze messages
        work_messages = self._filter_work_messages(messages)
        
        summary = {
            "channel": {
                "id": channel_info.id,
                "name": channel_info.name,
                "type": channel_info.type
            },
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days_back
            },
            "statistics": {
                "total_messages": len(messages),
                "work_messages": len(work_messages),
                "unique_users": len(set(msg.user for msg in work_messages if msg.user)),
                "threads": len([msg for msg in work_messages if msg.thread_ts])
            },
            "messages": [self._message_to_dict(msg) for msg in work_messages]
        }
        
        logger.info(f"Generated work summary for channel {channel_info.name}")
        return summary
    
    async def search_work_content(
        self,
        keywords: List[str],
        days_back: int = 30
    ) -> List[SlackMessage]:
        """
        Search for work-related content by keywords.
        
        Args:
            keywords: List of keywords to search for
            days_back: Number of days to search back
            
        Returns:
            List of matching work-related messages
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        message_filter = MessageFilter(
            start_date=start_date,
            end_date=end_date,
            keywords=keywords,
            include_bots=False,
            min_length=10
        )
        
        await self.client.authenticate()
        
        all_matches = []
        for keyword in keywords:
            try:
                matches = await self.client.search_messages(
                    query=keyword,
                    message_filter=message_filter
                )
                all_matches.extend(matches)
            except Exception as e:
                logger.warning(f"Search failed for keyword '{keyword}': {e}")
                continue
        
        # Remove duplicates and filter for work content
        unique_messages = {msg.ts: msg for msg in all_matches}.values()
        work_messages = self._filter_work_messages(list(unique_messages))
        
        logger.info(f"Found {len(work_messages)} work-related messages for keywords: {keywords}")
        return work_messages
    
    async def _get_work_channels(self) -> List[str]:
        """Get list of work-related channel IDs."""
        channels = await self.client.get_channels(include_private=True)
        
        # If specific target channels are configured, use them
        if self.target_channels:
            work_channels = []
            for channel in channels:
                if channel.name in self.target_channels:
                    work_channels.append(channel.id)
                    logger.info(f"✅ Found target channel: {channel.name} ({channel.id})")
            
            # Check if all target channels were found
            found_names = [ch.name for ch in channels if ch.id in work_channels]
            missing_channels = set(self.target_channels) - set(found_names)
            if missing_channels:
                logger.warning(f"⚠️ Target channels not found: {', '.join(missing_channels)}")
            
            logger.info(f"Using {len(work_channels)} specified target channels")
            return work_channels
        
        # If no target channels specified, use auto-detection
        # Filter for work-related channels (exclude social/random channels)
        exclude_patterns = [
            r'^(general|random|social|lunch|coffee|music|games?)$',
            r'^(announce|announcement)s?$',
            r'^(water.?cooler|chat|casual)$',
            r'^(社交|閒聊|聊天|音樂|遊戲)$'  # Chinese social channel names
        ]
        
        work_channels = []
        for channel in channels:
            if channel.is_archived:
                continue
            
            # Check if channel name suggests it's work-related
            is_excluded = any(
                re.match(pattern, channel.name, re.IGNORECASE)
                for pattern in exclude_patterns
            )
            
            if not is_excluded:
                work_channels.append(channel.id)
                logger.info(f"✅ Auto-detected work channel: {channel.name} ({channel.id})")
            else:
                logger.info(f"❌ Excluded channel: {channel.name}")
        
        logger.info(f"Auto-detected {len(work_channels)} work-related channels")
        return work_channels
    
    def _filter_work_messages(self, messages: List[SlackMessage]) -> List[SlackMessage]:
        """Filter messages to include only work-related content."""
        work_messages = []
        
        for message in messages:
            if self._is_work_related_message(message):
                work_messages.append(message)
        
        # Sort by timestamp
        work_messages.sort(key=lambda m: float(m.ts))
        
        logger.debug(f"Filtered {len(work_messages)} work messages from {len(messages)} total")
        return work_messages
    
    def _is_work_related_message(self, message: SlackMessage) -> bool:
        """Determine if a message is work-related."""
        # Skip bot messages unless they're from work tools
        if message.is_from_bot:
            work_bots = ['github', 'jira', 'confluence', 'calendar', 'zoom']
            if not any(bot in (message.username or '').lower() for bot in work_bots):
                return False
        
        # Clean and analyze message text
        text = clean_message_text(message.text)
        
        # Skip very short messages
        if len(text) < 5:
            return False
        
        # Skip messages containing excluded keywords (HIGHEST PRIORITY - overrides all other analysis)
        # Get exclude keywords from multiple sources
        exclude_keywords = []
        
        # From settings
        if hasattr(self, 'settings') and self.settings and self.settings.exclude_keywords:
            exclude_keywords.extend(self.settings.exclude_keywords)
        
        # From environment variable SLACK_EXCLUDE_KEYWORDS
        import os
        env_exclude = os.getenv('SLACK_EXCLUDE_KEYWORDS', '')
        if env_exclude.strip():
            env_keywords = [kw.strip().lower() for kw in env_exclude.split(',') if kw.strip()]
            exclude_keywords.extend(env_keywords)
        
        # Apply exclusion filter (absolute - overrides all work-related analysis)
        if exclude_keywords:
            text_lower = text.lower()
            for keyword in exclude_keywords:
                if keyword in text_lower:
                    logger.info(f"EXCLUDED: Message contains blocked keyword '{keyword}': {text[:80]}...")
                    return False
        
        # Use utility function for detailed analysis
        return is_work_related_message(text)
    
    def _message_to_dict(self, message: SlackMessage) -> Dict[str, Any]:
        """Convert SlackMessage to dictionary for JSON serialization."""
        return {
            'ts': message.ts,
            'user': message.user,
            'text': message.text,
            'channel': message.channel,
            'datetime': message.datetime.isoformat() if hasattr(message, 'datetime') else None,
            'is_thread_reply': message.is_thread_reply,
            'reply_count': message.reply_count
        }
    
    async def get_workspace_info(self) -> Dict[str, Any]:
        """Get workspace information."""
        await self.client.authenticate()
        return self.client.get_workspace_info()