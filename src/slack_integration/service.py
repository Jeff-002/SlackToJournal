"""
Slack service layer for business logic.

This module provides high-level business logic for Slack integration,
including message filtering, data processing, and work content extraction.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
import re

from ..core.logging import get_logger
from ..core.exceptions import SlackIntegrationError, ValidationError
from ..settings import SlackSettings
from .client import SlackMCPClient
from .schemas import (
    SlackMessage, SlackChannel, MessageFilter, 
    ChannelType, MessageType
)
from .utils import is_work_related_message, extract_mentions, clean_message_text


logger = get_logger(__name__)


class SlackService:
    """
    High-level service for Slack workspace operations.
    
    This service provides business logic for extracting work-related
    content from Slack workspaces through the MCP client.
    """
    
    def __init__(self, settings: SlackSettings) -> None:
        """
        Initialize the Slack service.
        
        Args:
            settings: Slack integration settings
        """
        self.settings = settings
        self.client = SlackMCPClient(settings)
        
        logger.info("Initialized Slack service")
    
    async def get_weekly_work_messages(
        self,
        target_date: Optional[datetime] = None,
        work_channels: Optional[List[str]] = None
    ) -> List[SlackMessage]:
        """
        Get work-related messages from the current or specified week.
        
        Args:
            target_date: Target date for week calculation (defaults to now)
            work_channels: List of channel IDs to search (defaults to all public channels)
            
        Returns:
            List of work-related messages from the week
            
        Raises:
            SlackIntegrationError: If data retrieval fails
        """
        if target_date is None:
            target_date = datetime.now()
        
        # Calculate week boundaries (Monday to Sunday)
        week_start = target_date - timedelta(days=target_date.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        logger.info(f"Retrieving work messages for week: {week_start.date()} to {week_end.date()}")
        
        async with self.client:
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
                min_length=10
            )
            
            # Retrieve messages from all channels
            all_messages = []
            for channel_id in work_channels:
                try:
                    channel_messages = await self.client.get_messages(
                        channel_id=channel_id,
                        message_filter=message_filter,
                        limit=500
                    )
                    all_messages.extend(channel_messages)
                except Exception as e:
                    logger.warning(f"Failed to get messages from channel {channel_id}: {e}")
                    continue
            
            # Filter for work-related content
            work_messages = self._filter_work_messages(all_messages)
            
            # Get thread replies for work messages
            enhanced_messages = await self._enhance_with_threads(work_messages)
            
            logger.info(f"Retrieved {len(enhanced_messages)} work-related messages")
            return enhanced_messages
    
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
        
        async with self.client:
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
                limit=1000
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
                "messages": work_messages
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
        
        async with self.client:
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
        """
        Get list of work-related channel IDs.
        
        Returns:
            List of channel IDs that are likely work-related
        """
        channels = await self.client.get_channels(include_private=False)
        
        # Filter for work-related channels (exclude social/random channels)
        exclude_patterns = [
            r'^(general|random|social|lunch|coffee|music|games?)$',
            r'^(announce|announcement)s?$',
            r'^(water.?cooler|chat|casual)$'
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
        
        logger.info(f"Identified {len(work_channels)} work-related channels")
        return work_channels
    
    def _filter_work_messages(self, messages: List[SlackMessage]) -> List[SlackMessage]:
        """
        Filter messages to include only work-related content.
        
        Args:
            messages: List of all messages
            
        Returns:
            List of work-related messages
        """
        work_messages = []
        
        for message in messages:
            if self._is_work_related_message(message):
                work_messages.append(message)
        
        # Sort by timestamp
        work_messages.sort(key=lambda m: m.ts)
        
        logger.debug(f"Filtered {len(work_messages)} work messages from {len(messages)} total")
        return work_messages
    
    def _is_work_related_message(self, message: SlackMessage) -> bool:
        """
        Determine if a message is work-related.
        
        Args:
            message: SlackMessage to analyze
            
        Returns:
            True if message appears to be work-related
        """
        # Skip bot messages unless they're from work tools
        if message.is_from_bot:
            work_bots = ['github', 'jira', 'confluence', 'calendar', 'zoom']
            if not any(bot in (message.username or '').lower() for bot in work_bots):
                return False
        
        # Clean and analyze message text
        text = clean_message_text(message.text)
        
        # Skip very short messages
        if len(text) < 10:
            return False
        
        # Use utility function for detailed analysis
        return is_work_related_message(text)
    
    async def _enhance_with_threads(self, messages: List[SlackMessage]) -> List[SlackMessage]:
        """
        Enhance messages with their thread replies.
        
        Args:
            messages: List of messages to enhance
            
        Returns:
            List of messages with thread replies included
        """
        enhanced_messages = []
        processed_threads: Set[str] = set()
        
        for message in messages:
            enhanced_messages.append(message)
            
            # Get thread replies if this is a parent message
            if (message.reply_count and message.reply_count > 0 
                and message.ts not in processed_threads):
                try:
                    replies = await self.client.get_thread_replies(
                        channel_id=message.channel,
                        thread_ts=message.ts,
                        limit=50
                    )
                    
                    # Filter work-related replies
                    work_replies = self._filter_work_messages(replies)
                    enhanced_messages.extend(work_replies)
                    processed_threads.add(message.ts)
                    
                except Exception as e:
                    logger.warning(f"Failed to get thread replies for {message.ts}: {e}")
        
        return enhanced_messages