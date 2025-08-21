"""
Slack integration adapter.

This module provides a unified interface that can use either
MCP-based integration or direct Slack API integration.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..core.logging import get_logger
from ..settings import SlackSettings
from .schemas import SlackMessage
from .service import SlackService
from .direct_service import DirectSlackService


logger = get_logger(__name__)


class SlackAdapter:
    """
    Unified Slack integration adapter.
    
    Automatically chooses between MCP and direct API integration
    based on available configuration.
    """
    
    def __init__(self, settings: SlackSettings) -> None:
        """
        Initialize Slack adapter.
        
        Args:
            settings: Slack integration settings
        """
        self.settings = settings
        self.service = None
        
        # Check if we have bot token for direct integration
        bot_token = os.getenv('SLACK_BOT_TOKEN')
        user_token = os.getenv('SLACK_USER_TOKEN')  # Optional
        
        if bot_token:
            logger.info("Using direct Slack API integration")
            self.service = DirectSlackService(bot_token, user_token)
            self.integration_type = "direct"
        else:
            logger.info("Using MCP-based Slack integration")
            self.service = SlackService(settings)
            self.integration_type = "mcp"
    
    async def get_weekly_work_messages(
        self,
        target_date: Optional[datetime] = None,
        work_channels: Optional[List[str]] = None
    ) -> List[SlackMessage]:
        """Get weekly work messages using available integration."""
        return await self.service.get_weekly_work_messages(target_date, work_channels)
    
    async def get_channel_work_summary(
        self,
        channel_id: str,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """Get channel work summary using available integration."""
        return await self.service.get_channel_work_summary(channel_id, days_back)
    
    async def search_work_content(
        self,
        keywords: List[str],
        days_back: int = 30
    ) -> List[SlackMessage]:
        """Search work content using available integration."""
        return await self.service.search_work_content(keywords, days_back)
    
    def get_integration_info(self) -> Dict[str, Any]:
        """Get information about the current integration."""
        info = {
            "type": self.integration_type,
            "ready": self.service is not None
        }
        
        if self.integration_type == "direct":
            info["bot_token_configured"] = bool(os.getenv('SLACK_BOT_TOKEN'))
            info["user_token_configured"] = bool(os.getenv('SLACK_USER_TOKEN'))
        else:
            info["mcp_server_url"] = self.settings.mcp_server_url
            info["workspace_id"] = self.settings.workspace_id
        
        return info