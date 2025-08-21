"""
Pydantic schemas for Slack integration.

This module defines data models for Slack API responses and internal
data structures used throughout the Slack integration.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class MessageType(str, Enum):
    """Slack message types."""
    MESSAGE = "message"
    THREAD_REPLY = "thread_reply"
    FILE_SHARE = "file_share"
    APP_MENTION = "app_mention"


class ChannelType(str, Enum):
    """Slack channel types."""
    PUBLIC = "public_channel"
    PRIVATE = "private_channel"
    IM = "im"
    MPIM = "mpim"


class SlackUser(BaseModel):
    """Slack user information."""
    
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(description="Slack user ID")
    name: str = Field(description="User display name")
    real_name: Optional[str] = Field(default=None, description="User's real name")
    email: Optional[str] = Field(default=None, description="User's email address")
    is_bot: bool = Field(default=False, description="Whether user is a bot")
    team_id: str = Field(description="Slack team/workspace ID")


class SlackChannel(BaseModel):
    """Slack channel information."""
    
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(description="Slack channel ID")
    name: str = Field(description="Channel name")
    type: ChannelType = Field(description="Channel type")
    is_private: bool = Field(default=False, description="Whether channel is private")
    is_archived: bool = Field(default=False, description="Whether channel is archived")
    topic: Optional[str] = Field(default=None, description="Channel topic")
    purpose: Optional[str] = Field(default=None, description="Channel purpose")
    member_count: Optional[int] = Field(default=None, description="Number of members")


class SlackMessage(BaseModel):
    """Slack message data model."""
    
    model_config = ConfigDict(extra="ignore")
    
    ts: str = Field(description="Message timestamp (unique ID)")
    user: Optional[str] = Field(default=None, description="User ID who sent the message")
    text: str = Field(description="Message text content")
    channel: str = Field(description="Channel ID where message was sent")
    type: MessageType = Field(default=MessageType.MESSAGE, description="Message type")
    subtype: Optional[str] = Field(default=None, description="Message subtype")
    
    # Thread information
    thread_ts: Optional[str] = Field(default=None, description="Parent thread timestamp")
    reply_count: Optional[int] = Field(default=0, description="Number of replies")
    
    # Additional metadata
    bot_id: Optional[str] = Field(default=None, description="Bot ID if from bot")
    username: Optional[str] = Field(default=None, description="Bot username")
    permalink: Optional[str] = Field(default=None, description="Permanent link to message")
    
    # Attachments and files
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="Message attachments")
    files: List[Dict[str, Any]] = Field(default_factory=list, description="File uploads")
    
    # Reactions and interactions
    reactions: List[Dict[str, Any]] = Field(default_factory=list, description="Message reactions")
    
    @property
    def datetime(self) -> datetime:
        """Convert timestamp to datetime object."""
        return datetime.fromtimestamp(float(self.ts))
    
    @property
    def is_thread_reply(self) -> bool:
        """Check if message is a thread reply."""
        return self.thread_ts is not None and self.thread_ts != self.ts
    
    @property
    def is_from_bot(self) -> bool:
        """Check if message is from a bot."""
        return self.bot_id is not None or self.username is not None


class MessageFilter(BaseModel):
    """Filter criteria for message retrieval."""
    
    model_config = ConfigDict(extra="allow")
    
    channels: Optional[List[str]] = Field(default=None, description="Channel IDs to include")
    users: Optional[List[str]] = Field(default=None, description="User IDs to include")
    start_date: Optional[datetime] = Field(default=None, description="Start date for messages")
    end_date: Optional[datetime] = Field(default=None, description="End date for messages")
    
    include_bots: bool = Field(default=False, description="Include bot messages")
    include_threads: bool = Field(default=True, description="Include thread replies")
    include_files: bool = Field(default=True, description="Include file shares")
    
    keywords: Optional[List[str]] = Field(default=None, description="Keywords to search for")
    exclude_keywords: Optional[List[str]] = Field(default=None, description="Keywords to exclude")
    
    min_length: Optional[int] = Field(default=None, description="Minimum message length")
    max_messages: Optional[int] = Field(default=1000, description="Maximum messages to retrieve")


class SlackWorkspace(BaseModel):
    """Slack workspace information."""
    
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(description="Workspace ID")
    name: str = Field(description="Workspace name")
    domain: str = Field(description="Workspace domain")
    icon: Optional[Dict[str, str]] = Field(default=None, description="Workspace icon URLs")
    
    # User and channel counts
    user_count: Optional[int] = Field(default=None, description="Number of users")
    channel_count: Optional[int] = Field(default=None, description="Number of channels")


class MCPResponse(BaseModel):
    """Generic MCP server response."""
    
    model_config = ConfigDict(extra="allow")
    
    success: bool = Field(description="Whether the request was successful")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class SlackAPIError(BaseModel):
    """Slack API error response."""
    
    ok: bool = Field(default=False, description="Always false for errors")
    error: str = Field(description="Error type")
    warning: Optional[str] = Field(default=None, description="Warning message")
    response_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Response metadata")