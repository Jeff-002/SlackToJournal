"""Slack integration module using Model Context Protocol (MCP)."""

from .client import SlackMCPClient
from .service import SlackService
from .schemas import SlackMessage, SlackChannel, MessageFilter

__all__ = [
    "SlackMCPClient",
    "SlackService", 
    "SlackMessage",
    "SlackChannel",
    "MessageFilter"
]