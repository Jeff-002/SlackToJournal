"""
Direct Slack Web API client as alternative to MCP.

This provides a more straightforward integration with Slack
using the official Slack SDK instead of MCP protocol.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..core.logging import get_logger
from ..core.exceptions import SlackIntegrationError, AuthenticationError
from ..settings import SlackSettings
from .schemas import SlackMessage, SlackChannel, MessageFilter, SlackUser


logger = get_logger(__name__)


class DirectSlackClient:
    """
    Direct Slack Web API client.
    
    Alternative to MCP client that uses Slack Web API directly
    for simpler setup and more reliable operation.
    """
    
    def __init__(self, bot_token: str, user_token: Optional[str] = None) -> None:
        """
        Initialize Direct Slack client.
        
        Args:
            bot_token: Slack bot token (starts with xoxb-)
            user_token: Optional user token for additional permissions (starts with xoxp-)
        """
        self.bot_token = bot_token
        self.user_token = user_token
        
        # Initialize clients
        self.bot_client = WebClient(token=bot_token)
        self.user_client = WebClient(token=user_token) if user_token else None
        
        self._authenticated = False
        self.workspace_info = None
        
        logger.info("Initialized Direct Slack client")
    
    async def authenticate(self) -> None:
        """Test authentication and get workspace info."""
        try:
            # Test bot token
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.bot_client.auth_test
            )
            
            if not response["ok"]:
                raise AuthenticationError(
                    f"Bot token authentication failed: {response.get('error', 'Unknown error')}",
                    service="Slack",
                    auth_type="Bot Token"
                )
            
            self.workspace_info = {
                'team_id': response['team_id'],
                'team': response['team'],
                'user_id': response['user_id'],
                'user': response['user']
            }
            
            # Test user token if provided
            if self.user_client:
                user_response = await asyncio.get_event_loop().run_in_executor(
                    None, self.user_client.auth_test
                )
                if not user_response["ok"]:
                    logger.warning(f"User token authentication failed: {user_response.get('error')}")
                    self.user_client = None
            
            self._authenticated = True
            logger.info(f"Successfully authenticated with Slack workspace: {self.workspace_info['team']}")
            
        except SlackApiError as e:
            logger.error(f"Slack API authentication failed: {e}")
            raise AuthenticationError(
                f"Slack authentication failed: {e}",
                service="Slack",
                auth_type="Web API"
            )
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise SlackIntegrationError(f"Authentication failed: {str(e)}")
    
    async def get_channels(self, include_private: bool = True) -> List[SlackChannel]:
        """Get list of channels."""
        if not self._authenticated:
            await self.authenticate()
        
        try:
            # Get public channels
            channels = []
            cursor = None
            
            while True:
                # Try with all types first, fall back if permissions are missing
                channel_types = "public_channel"
                if include_private:
                    # Start with basic private channels
                    channel_types = "public_channel,private_channel"
                
                response = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: self.bot_client.conversations_list(
                        exclude_archived=True,
                        types=channel_types,
                        cursor=cursor,
                        limit=200
                    )
                )
                
                if not response["ok"]:
                    error_msg = response.get('error', 'unknown_error')
                    if error_msg == 'missing_scope':
                        missing_scope = response.get('needed', 'unknown')
                        logger.warning(f"Missing scope '{missing_scope}', falling back to public channels only")
                        if include_private and channel_types != "public_channel":
                            # Retry with public channels only
                            logger.info("Retrying with public channels only due to insufficient permissions")
                            response = await asyncio.get_event_loop().run_in_executor(
                                None, 
                                lambda: self.bot_client.conversations_list(
                                    exclude_archived=True,
                                    types="public_channel",
                                    cursor=cursor,
                                    limit=200
                                )
                            )
                            if not response["ok"]:
                                raise SlackIntegrationError(f"Failed to get channels: {response.get('error')}")
                        else:
                            raise SlackIntegrationError(f"Failed to get channels: {response.get('error')}")
                    else:
                        raise SlackIntegrationError(f"Failed to get channels: {error_msg}")
                
                for channel_data in response["channels"]:
                    # Determine channel type
                    if channel_data.get("is_im", False):
                        channel_type = "im"
                    elif channel_data.get("is_mpim", False):
                        channel_type = "mpim"
                    elif channel_data.get("is_private", False):
                        channel_type = "private_channel"
                    else:
                        channel_type = "public_channel"
                        
                    channel = SlackChannel(
                        id=channel_data["id"],
                        name=channel_data.get("name", f"Direct Message ({channel_data['id']})"),
                        type=channel_type,
                        is_private=channel_data.get("is_private", False) or channel_data.get("is_im", False) or channel_data.get("is_mpim", False),
                        is_archived=channel_data.get("is_archived", False),
                        topic=channel_data.get("topic", {}).get("value"),
                        purpose=channel_data.get("purpose", {}).get("value"),
                        member_count=channel_data.get("num_members")
                    )
                    channels.append(channel)
                
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
            
            logger.info(f"Retrieved {len(channels)} channels")
            return channels
            
        except SlackApiError as e:
            logger.error(f"Failed to get channels: {e}")
            raise SlackIntegrationError(f"Channels request failed: {e}")
    
    async def join_channel(self, channel_id: str) -> bool:
        """Join a channel if not already a member."""
        if not self._authenticated:
            await self.authenticate()
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.bot_client.conversations_join(channel=channel_id)
            )
            
            if response["ok"]:
                logger.info(f"Successfully joined channel {channel_id}")
                return True
            else:
                logger.warning(f"Failed to join channel {channel_id}: {response.get('error')}")
                return False
                
        except SlackApiError as e:
            logger.warning(f"Could not join channel {channel_id}: {e}")
            return False
    
    async def get_messages(
        self,
        channel_id: str,
        message_filter: Optional[MessageFilter] = None,
        limit: int = 100
    ) -> List[SlackMessage]:
        """Get messages from a channel."""
        if not self._authenticated:
            await self.authenticate()
        
        # Convert user emails and names to user IDs if provided
        target_user_ids = set()
        if message_filter:
            if message_filter.users:
                target_user_ids.update(message_filter.users)
            
            if message_filter.user_emails:
                logger.info(f"Looking up user IDs for emails: {message_filter.user_emails}")
                found_user_ids = await self.find_users_by_email(message_filter.user_emails)
                target_user_ids.update(found_user_ids)
                logger.info(f"Found {len(found_user_ids)} matching users by email")
            
            if message_filter.user_names:
                logger.info(f"Looking up user IDs for names: {message_filter.user_names}")
                found_user_ids = await self.find_users_by_name(message_filter.user_names)
                target_user_ids.update(found_user_ids)
                logger.info(f"Found {len(found_user_ids)} matching users by name")
        
        try:
            messages = []
            cursor = None
            collected = 0
            
            # Set time boundaries
            oldest = None
            latest = None
            
            if message_filter:
                if message_filter.start_date:
                    oldest = message_filter.start_date.timestamp()
                if message_filter.end_date:
                    latest = message_filter.end_date.timestamp()
            
            while collected < limit:
                try:
                    response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.bot_client.conversations_history(
                            channel=channel_id,
                            cursor=cursor,
                            limit=min(200, limit - collected),
                            oldest=oldest,
                            latest=latest
                        )
                    )
                except SlackApiError as e:
                    if "not_in_channel" in str(e):
                        logger.info(f"Bot not in channel {channel_id}, attempting to join...")
                        # Try to join the channel
                        joined = await self.join_channel(channel_id)
                        if joined:
                            # Retry getting messages after joining
                            try:
                                response = await asyncio.get_event_loop().run_in_executor(
                                    None,
                                    lambda: self.bot_client.conversations_history(
                                        channel=channel_id,
                                        cursor=cursor,
                                        limit=min(200, limit - collected),
                                        oldest=oldest,
                                        latest=latest
                                    )
                                )
                            except SlackApiError as retry_e:
                                logger.error(f"Still failed to get messages after joining {channel_id}: {retry_e}")
                                break
                        else:
                            logger.warning(f"Could not join channel {channel_id}, skipping")
                            break
                    else:
                        raise e
                
                if not response["ok"]:
                    raise SlackIntegrationError(f"Failed to get messages: {response.get('error')}")
                
                for msg_data in response["messages"]:
                    # Skip bot messages if requested
                    if message_filter and not message_filter.include_bots:
                        if msg_data.get("bot_id") or msg_data.get("subtype") == "bot_message":
                            continue
                    
                    # Filter by user if specified
                    if target_user_ids:
                        message_user = msg_data.get("user")
                        if not message_user or message_user not in target_user_ids:
                            continue
                    
                    # Skip very short messages
                    text = msg_data.get("text", "")
                    if message_filter and message_filter.min_length:
                        if len(text) < message_filter.min_length:
                            continue
                    
                    # Get user info for display name
                    user_id = msg_data.get("user")
                    user_name = None
                    user_real_name = None
                    
                    if user_id:
                        try:
                            user_info = await self.get_user_info(user_id)
                            if user_info:
                                # Use display_name as the primary choice for user identification
                                user_name = user_info.name
                                user_real_name = user_info.display_name or user_info.real_name
                        except Exception as e:
                            logger.warning(f"Failed to get user info for {user_id}: {e}")
                    
                    message = SlackMessage(
                        ts=msg_data["ts"],
                        user=user_id,
                        user_name=user_name,
                        user_real_name=user_real_name,
                        text=text,
                        channel=channel_id,
                        thread_ts=msg_data.get("thread_ts"),
                        reply_count=msg_data.get("reply_count", 0),
                        bot_id=msg_data.get("bot_id"),
                        username=msg_data.get("username"),
                        attachments=msg_data.get("attachments", []),
                        files=msg_data.get("files", []),
                        reactions=msg_data.get("reactions", [])
                    )
                    messages.append(message)
                    collected += 1
                    
                    # Fetch thread replies if this message has replies and thread inclusion is enabled
                    reply_count = msg_data.get("reply_count", 0)
                    has_thread_ts = msg_data.get("thread_ts")
                    
                    # Log message details for debugging
                    logger.info(f"Message {msg_data['ts']}: reply_count={reply_count}, thread_ts={has_thread_ts}, include_threads={message_filter.include_threads if message_filter else False}")
                    
                    if (message_filter and message_filter.include_threads and 
                        reply_count > 0 and 
                        (not has_thread_ts or has_thread_ts == msg_data["ts"])):  # Parent messages or root thread messages
                        
                        logger.info(f"Fetching {reply_count} thread replies for message {msg_data['ts']}")
                        thread_replies = await self.get_thread_replies(channel_id, msg_data["ts"], message_filter, target_user_ids)
                        messages.extend(thread_replies)
                        collected += len(thread_replies)
                    
                    if collected >= limit:
                        break
                
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
            
            logger.info(f"Retrieved {len(messages)} messages from channel {channel_id}")
            return messages
            
        except SlackApiError as e:
            logger.error(f"Failed to get messages from {channel_id}: {e}")
            raise SlackIntegrationError(f"Messages request failed: {e}")
    
    async def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
        message_filter: Optional[MessageFilter] = None,
        target_user_ids: Optional[set] = None
    ) -> List[SlackMessage]:
        """Get replies for a specific thread."""
        if not self._authenticated:
            await self.authenticate()
        
        try:
            messages = []
            cursor = None
            
            while True:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.bot_client.conversations_replies(
                        channel=channel_id,
                        ts=thread_ts,
                        cursor=cursor,
                        limit=200
                    )
                )
                
                if not response["ok"]:
                    logger.warning(f"Failed to get thread replies for {thread_ts}: {response.get('error')}")
                    break
                
                # Skip the first message if it's the parent (it has the same ts as thread_ts)
                reply_messages = response["messages"][1:] if response["messages"] and response["messages"][0]["ts"] == thread_ts else response["messages"]
                
                for reply_data in reply_messages:
                    # Skip bot messages if requested
                    if message_filter and not message_filter.include_bots:
                        if reply_data.get("bot_id") or reply_data.get("subtype") == "bot_message":
                            continue
                    
                    # Filter by user if specified
                    if target_user_ids:
                        reply_user = reply_data.get("user")
                        if not reply_user or reply_user not in target_user_ids:
                            continue
                    
                    # Skip very short messages
                    text = reply_data.get("text", "")
                    if message_filter and message_filter.min_length:
                        if len(text) < message_filter.min_length:
                            continue
                    
                    # Get user info for display name
                    user_id = reply_data.get("user")
                    user_name = None
                    user_real_name = None
                    
                    if user_id:
                        try:
                            user_info = await self.get_user_info(user_id)
                            if user_info:
                                user_name = user_info.name
                                user_real_name = user_info.display_name or user_info.real_name
                        except Exception as e:
                            logger.warning(f"Failed to get user info for {user_id}: {e}")
                    
                    reply_message = SlackMessage(
                        ts=reply_data["ts"],
                        user=user_id,
                        user_name=user_name,
                        user_real_name=user_real_name,
                        text=text,
                        channel=channel_id,
                        thread_ts=reply_data.get("thread_ts"),
                        reply_count=0,  # Reply messages don't have their own replies
                        bot_id=reply_data.get("bot_id"),
                        username=reply_data.get("username"),
                        attachments=reply_data.get("attachments", []),
                        files=reply_data.get("files", []),
                        reactions=reply_data.get("reactions", [])
                    )
                    messages.append(reply_message)
                
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
            
            if messages:
                logger.info(f"Retrieved {len(messages)} thread replies for {thread_ts}")
            
            return messages
            
        except SlackApiError as e:
            logger.error(f"Failed to get thread replies for {thread_ts}: {e}")
            # Don't raise exception here, just return empty list to continue processing other messages
            return []
    
    async def get_user_info(self, user_id: str) -> Optional[SlackUser]:
        """Get user information."""
        if not self._authenticated:
            await self.authenticate()
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.bot_client.users_info(user=user_id)
            )
            
            if not response["ok"]:
                logger.warning(f"Failed to get user info for {user_id}: {response.get('error')}")
                return None
            
            user_data = response["user"]
            profile = user_data.get("profile", {})
            
            
            return SlackUser(
                id=user_data["id"],
                name=user_data.get("name", "Unknown"),
                real_name=user_data.get("real_name"),
                display_name=profile.get("display_name"),
                display_name_normalized=profile.get("display_name_normalized"),
                first_name=profile.get("first_name"),
                last_name=profile.get("last_name"),
                email=profile.get("email"),
                is_bot=user_data.get("is_bot", False),
                team_id=user_data.get("team_id", "")
            )
            
        except SlackApiError as e:
            logger.warning(f"Failed to get user info: {e}")
            return None
    
    async def find_users_by_name(self, user_names: List[str]) -> List[str]:
        """Find user IDs by their display names or real names."""
        if not self._authenticated:
            await self.authenticate()
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.bot_client.users_list()
            )
            
            if not response["ok"]:
                logger.warning(f"Failed to get users list: {response.get('error')}")
                return []
            
            matched_user_ids = []
            
            # Normalize target names for case-insensitive matching
            target_names = [name.lower().strip() for name in user_names]
            
            for user_data in response["members"]:
                if user_data.get("is_bot", False) or user_data.get("deleted", False):
                    continue
                
                # Check display name, real name, and username
                user_display_name = user_data.get("name", "").lower()
                user_real_name = user_data.get("real_name", "").lower()
                user_profile_name = user_data.get("profile", {}).get("display_name", "").lower()
                
                # Match against any of the user identifiers
                for target_name in target_names:
                    if (target_name in user_display_name or 
                        target_name in user_real_name or 
                        target_name in user_profile_name or
                        user_display_name == target_name or
                        user_real_name == target_name or
                        user_profile_name == target_name):
                        matched_user_ids.append(user_data["id"])
                        user_name = user_data.get("real_name") or user_data.get("name", "Unknown")
                        logger.info(f"Found user: {user_name} ({user_data['id']}) for name '{target_name}'")
                        break
            
            return matched_user_ids
            
        except SlackApiError as e:
            logger.warning(f"Failed to search users: {e}")
            return []

    async def find_users_by_email(self, user_emails: List[str]) -> List[str]:
        """Find user IDs by their email addresses."""
        if not self._authenticated:
            await self.authenticate()
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.bot_client.users_list()
            )
            
            if not response["ok"]:
                logger.warning(f"Failed to get users list: {response.get('error')}")
                return []
            
            matched_user_ids = []
            
            # Normalize target emails for case-insensitive matching
            target_emails = [email.lower().strip() for email in user_emails]
            
            for user_data in response["members"]:
                if user_data.get("is_bot", False) or user_data.get("deleted", False):
                    continue
                
                # Check email in profile
                user_email = user_data.get("profile", {}).get("email", "").lower()
                
                if user_email and user_email in target_emails:
                    matched_user_ids.append(user_data["id"])
                    user_name = user_data.get("real_name") or user_data.get("name", "Unknown")
                    logger.info(f"Found user: {user_name} ({user_data['id']}) for email '{user_email}'")
            
            return matched_user_ids
            
        except SlackApiError as e:
            logger.warning(f"Failed to search users: {e}")
            return []
    
    async def search_messages(
        self,
        query: str,
        message_filter: Optional[MessageFilter] = None
    ) -> List[SlackMessage]:
        """Search messages across workspace."""
        if not self._authenticated:
            await self.authenticate()
        
        # Note: search.messages requires a paid Slack plan
        try:
            # Build search query
            search_query = query
            
            if message_filter:
                if message_filter.channels:
                    channel_query = " OR ".join(f"in:#{ch}" for ch in message_filter.channels)
                    search_query += f" AND ({channel_query})"
                
                if message_filter.start_date:
                    search_query += f" after:{message_filter.start_date.strftime('%Y-%m-%d')}"
                
                if message_filter.end_date:
                    search_query += f" before:{message_filter.end_date.strftime('%Y-%m-%d')}"
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.bot_client.search_messages(
                    query=search_query,
                    count=message_filter.max_messages if message_filter else 100
                )
            )
            
            if not response["ok"]:
                # Search might not be available, fall back to channel-by-channel search
                logger.warning(f"Search API not available: {response.get('error')}")
                return await self._fallback_search(query, message_filter)
            
            messages = []
            for match in response.get("messages", {}).get("matches", []):
                message = SlackMessage(
                    ts=match["ts"],
                    user=match.get("user"),
                    text=match.get("text", ""),
                    channel=match.get("channel", {}).get("id", ""),
                    thread_ts=match.get("thread_ts"),
                    permalink=match.get("permalink")
                )
                messages.append(message)
            
            logger.info(f"Found {len(messages)} messages matching query: {query}")
            return messages
            
        except SlackApiError as e:
            logger.warning(f"Search failed, using fallback: {e}")
            return await self._fallback_search(query, message_filter)
    
    async def _fallback_search(
        self,
        query: str,
        message_filter: Optional[MessageFilter] = None
    ) -> List[SlackMessage]:
        """Fallback search by checking channels manually."""
        try:
            # Get channels to search
            channels = await self.get_channels()
            
            # Filter channels if specified
            if message_filter and message_filter.channels:
                channels = [ch for ch in channels if ch.id in message_filter.channels]
            
            all_messages = []
            query_lower = query.lower()
            
            for channel in channels[:10]:  # Limit to first 10 channels
                try:
                    messages = await self.get_messages(
                        channel_id=channel.id,
                        message_filter=message_filter,
                        limit=50
                    )
                    
                    # Filter messages containing query
                    matching_messages = [
                        msg for msg in messages
                        if query_lower in msg.text.lower()
                    ]
                    
                    all_messages.extend(matching_messages)
                    
                except Exception as e:
                    logger.warning(f"Failed to search channel {channel.name}: {e}")
                    continue
            
            logger.info(f"Fallback search found {len(all_messages)} messages")
            return all_messages
            
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []
    
    def get_workspace_info(self) -> Dict[str, Any]:
        """Get workspace information."""
        return self.workspace_info or {}