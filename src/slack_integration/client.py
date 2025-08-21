"""
MCP client for Slack integration.

This module provides the MCP (Model Context Protocol) client for
communicating with Slack workspaces through an MCP server.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..core.logging import get_logger
from ..core.exceptions import SlackIntegrationError, AuthenticationError
from ..settings import SlackSettings
from .schemas import (
    SlackMessage, SlackChannel, SlackWorkspace, MessageFilter,
    MCPResponse, SlackAPIError
)


logger = get_logger(__name__)


class SlackMCPClient:
    """
    MCP client for Slack workspace integration.
    
    This client communicates with a Slack MCP server to retrieve
    workspace data, channels, messages, and user information.
    """
    
    def __init__(self, settings: SlackSettings) -> None:
        """
        Initialize the Slack MCP client.
        
        Args:
            settings: Slack integration settings
        """
        self.settings = settings
        self.session: Optional[ClientSession] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self._connected = False
        
        logger.info(f"Initialized Slack MCP client for server: {settings.mcp_server_url}")
    
    async def __aenter__(self) -> "SlackMCPClient":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> None:
        """
        Connect to the MCP server.
        
        Raises:
            SlackIntegrationError: If connection fails
        """
        try:
            logger.info("Connecting to Slack MCP server...")
            
            # Initialize HTTP client for direct API calls
            self.http_client = httpx.AsyncClient(timeout=30.0)
            
            # For now, we'll use HTTP client to communicate with MCP server
            # In a full implementation, this would use the official MCP protocol
            
            # Test connection
            await self._test_connection()
            
            self._connected = True
            logger.info("Successfully connected to Slack MCP server")
            
        except Exception as e:
            logger.error(f"Failed to connect to Slack MCP server: {e}")
            raise SlackIntegrationError(
                f"MCP server connection failed: {str(e)}",
                response_code=None
            )
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self.http_client:
            await self.http_client.aclose()
        
        self._connected = False
        logger.info("Disconnected from Slack MCP server")
    
    async def _test_connection(self) -> None:
        """Test the connection to MCP server."""
        try:
            response = await self.http_client.get(
                f"{self.settings.mcp_server_url}/health"
            )
            response.raise_for_status()
            logger.debug("MCP server health check passed")
        except httpx.RequestError as e:
            raise SlackIntegrationError(f"MCP server unreachable: {e}")
        except httpx.HTTPStatusError as e:
            raise SlackIntegrationError(f"MCP server error: {e.response.status_code}")
    
    async def get_workspace_info(self) -> SlackWorkspace:
        """
        Get workspace information.
        
        Returns:
            SlackWorkspace: Workspace information
            
        Raises:
            SlackIntegrationError: If the request fails
        """
        if not self._connected:
            raise SlackIntegrationError("Client not connected to MCP server")
        
        try:
            response = await self._make_request("GET", "/workspace/info")
            return SlackWorkspace(**response.data)
        except Exception as e:
            logger.error(f"Failed to get workspace info: {e}")
            raise SlackIntegrationError(f"Workspace info request failed: {str(e)}")
    
    async def get_channels(self, include_private: bool = False) -> List[SlackChannel]:
        """
        Get list of channels in the workspace.
        
        Args:
            include_private: Whether to include private channels
            
        Returns:
            List of SlackChannel objects
            
        Raises:
            SlackIntegrationError: If the request fails
        """
        if not self._connected:
            raise SlackIntegrationError("Client not connected to MCP server")
        
        try:
            params = {"include_private": include_private}
            response = await self._make_request("GET", "/channels", params=params)
            
            channels = []
            for channel_data in response.data.get("channels", []):
                channels.append(SlackChannel(**channel_data))
            
            logger.info(f"Retrieved {len(channels)} channels")
            return channels
            
        except Exception as e:
            logger.error(f"Failed to get channels: {e}")
            raise SlackIntegrationError(f"Channels request failed: {str(e)}")
    
    async def get_messages(
        self, 
        channel_id: str,
        message_filter: Optional[MessageFilter] = None,
        limit: int = 100
    ) -> List[SlackMessage]:
        """
        Get messages from a specific channel.
        
        Args:
            channel_id: Channel ID to get messages from
            message_filter: Optional filter criteria
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of SlackMessage objects
            
        Raises:
            SlackIntegrationError: If the request fails
        """
        if not self._connected:
            raise SlackIntegrationError("Client not connected to MCP server")
        
        try:
            params = {
                "channel": channel_id,
                "limit": limit
            }
            
            if message_filter:
                if message_filter.start_date:
                    params["oldest"] = message_filter.start_date.timestamp()
                if message_filter.end_date:
                    params["latest"] = message_filter.end_date.timestamp()
                if message_filter.include_bots is False:
                    params["exclude_bots"] = True
            
            response = await self._make_request("GET", "/messages", params=params)
            
            messages = []
            for msg_data in response.data.get("messages", []):
                # Add channel ID to message data
                msg_data["channel"] = channel_id
                messages.append(SlackMessage(**msg_data))
            
            logger.info(f"Retrieved {len(messages)} messages from channel {channel_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get messages from {channel_id}: {e}")
            raise SlackIntegrationError(f"Messages request failed: {str(e)}")
    
    async def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
        limit: int = 100
    ) -> List[SlackMessage]:
        """
        Get replies to a thread.
        
        Args:
            channel_id: Channel ID where thread exists
            thread_ts: Thread timestamp
            limit: Maximum number of replies to retrieve
            
        Returns:
            List of SlackMessage objects
            
        Raises:
            SlackIntegrationError: If the request fails
        """
        if not self._connected:
            raise SlackIntegrationError("Client not connected to MCP server")
        
        try:
            params = {
                "channel": channel_id,
                "ts": thread_ts,
                "limit": limit
            }
            
            response = await self._make_request("GET", "/thread/replies", params=params)
            
            replies = []
            for reply_data in response.data.get("messages", []):
                reply_data["channel"] = channel_id
                replies.append(SlackMessage(**reply_data))
            
            logger.info(f"Retrieved {len(replies)} thread replies")
            return replies
            
        except Exception as e:
            logger.error(f"Failed to get thread replies: {e}")
            raise SlackIntegrationError(f"Thread replies request failed: {str(e)}")
    
    async def search_messages(
        self,
        query: str,
        message_filter: Optional[MessageFilter] = None
    ) -> List[SlackMessage]:
        """
        Search messages across the workspace.
        
        Args:
            query: Search query string
            message_filter: Optional filter criteria
            
        Returns:
            List of SlackMessage objects
            
        Raises:
            SlackIntegrationError: If the request fails
        """
        if not self._connected:
            raise SlackIntegrationError("Client not connected to MCP server")
        
        try:
            params = {"query": query}
            
            if message_filter:
                if message_filter.channels:
                    params["channels"] = ",".join(message_filter.channels)
                if message_filter.start_date:
                    params["after"] = message_filter.start_date.isoformat()
                if message_filter.end_date:
                    params["before"] = message_filter.end_date.isoformat()
            
            response = await self._make_request("GET", "/search/messages", params=params)
            
            messages = []
            for match in response.data.get("matches", []):
                messages.append(SlackMessage(**match))
            
            logger.info(f"Found {len(messages)} messages matching query: {query}")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to search messages: {e}")
            raise SlackIntegrationError(f"Message search failed: {str(e)}")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """
        Make an HTTP request to the MCP server.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            
        Returns:
            MCPResponse object
            
        Raises:
            SlackIntegrationError: If the request fails
        """
        if not self.http_client:
            raise SlackIntegrationError("HTTP client not initialized")
        
        url = f"{self.settings.mcp_server_url}{endpoint}"
        
        try:
            logger.debug(f"Making {method} request to {url}")
            
            if method.upper() == "GET":
                response = await self.http_client.get(url, params=params)
            elif method.upper() == "POST":
                response = await self.http_client.post(url, params=params, json=data)
            else:
                raise SlackIntegrationError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            json_data = response.json()
            
            # Handle Slack API error format
            if "ok" in json_data and not json_data["ok"]:
                error_data = SlackAPIError(**json_data)
                raise SlackIntegrationError(
                    f"Slack API error: {error_data.error}",
                    slack_error=error_data.error,
                    response_code=response.status_code
                )
            
            return MCPResponse(
                success=True,
                data=json_data,
                timestamp=datetime.now()
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise SlackIntegrationError(
                f"MCP server HTTP error: {e.response.status_code}",
                response_code=e.response.status_code
            )
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise SlackIntegrationError(f"MCP server request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise SlackIntegrationError(f"Unexpected error: {str(e)}")