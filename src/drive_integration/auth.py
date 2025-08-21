"""
Google Drive authentication module.

This module handles OAuth2 authentication flow for Google Drive API
access, including credential management and token refresh.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..core.logging import get_logger
from ..core.exceptions import AuthenticationError, DriveIntegrationError
from ..settings import GoogleDriveSettings


logger = get_logger(__name__)


class DriveAuthenticator:
    """
    Google Drive OAuth2 authentication handler.
    
    Manages the OAuth2 flow, token storage, and credential refresh
    for accessing Google Drive API.
    """
    
    # Google Drive API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.metadata'
    ]
    
    def __init__(self, settings: GoogleDriveSettings) -> None:
        """
        Initialize the Drive authenticator.
        
        Args:
            settings: Google Drive settings containing credentials path
        """
        self.settings = settings
        self.credentials: Optional[Credentials] = None
        self.token_file = self.settings.credentials_file.parent / "token.json"
        
        logger.info(f"Initialized Drive authenticator with credentials: {settings.credentials_file}")
    
    def authenticate(self, force_reauth: bool = False) -> Credentials:
        """
        Authenticate and return valid credentials.
        
        Args:
            force_reauth: Force re-authentication even if valid tokens exist
            
        Returns:
            Valid Google OAuth2 credentials
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            if not force_reauth:
                # Try to load existing token
                self.credentials = self._load_existing_token()
            
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    logger.info("Refreshing expired credentials...")
                    self._refresh_credentials()
                else:
                    logger.info("Starting OAuth2 flow...")
                    self._perform_oauth_flow()
                
                # Save the credentials for next time
                self._save_token()
            
            logger.info("Authentication successful")
            return self.credentials
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise AuthenticationError(
                f"Google Drive authentication failed: {str(e)}",
                service="Google Drive",
                auth_type="OAuth2"
            )
    
    def _load_existing_token(self) -> Optional[Credentials]:
        """
        Load existing token from file.
        
        Returns:
            Credentials if valid token file exists, None otherwise
        """
        if not self.token_file.exists():
            logger.debug("No existing token file found")
            return None
        
        try:
            with open(self.token_file, 'r') as token:
                credentials = Credentials.from_authorized_user_info(
                    json.load(token), self.SCOPES
                )
            
            logger.debug("Loaded existing credentials from token file")
            return credentials
            
        except Exception as e:
            logger.warning(f"Failed to load existing token: {e}")
            return None
    
    def _refresh_credentials(self) -> None:
        """
        Refresh expired credentials.
        
        Raises:
            AuthenticationError: If refresh fails
        """
        try:
            self.credentials.refresh(Request())
            logger.info("Credentials refreshed successfully")
            
        except Exception as e:
            logger.error(f"Failed to refresh credentials: {e}")
            raise AuthenticationError(
                f"Failed to refresh Google Drive credentials: {str(e)}",
                service="Google Drive",
                auth_type="OAuth2 Refresh"
            )
    
    def _perform_oauth_flow(self) -> None:
        """
        Perform the OAuth2 authorization flow.
        
        Raises:
            AuthenticationError: If OAuth flow fails
        """
        if not self.settings.credentials_file.exists():
            raise AuthenticationError(
                f"Credentials file not found: {self.settings.credentials_file}",
                service="Google Drive",
                auth_type="OAuth2"
            )
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.settings.credentials_file), self.SCOPES
            )
            
            # Use local server for OAuth flow
            self.credentials = flow.run_local_server(
                port=0,
                prompt='consent',
                authorization_prompt_message='Please visit this URL to authorize the application: {url}',
                success_message='Authorization successful. You can close this window.'
            )
            
            logger.info("OAuth2 flow completed successfully")
            
        except Exception as e:
            logger.error(f"OAuth2 flow failed: {e}")
            raise AuthenticationError(
                f"OAuth2 flow failed: {str(e)}",
                service="Google Drive",
                auth_type="OAuth2"
            )
    
    def _save_token(self) -> None:
        """
        Save credentials to token file for future use.
        
        Raises:
            AuthenticationError: If saving fails
        """
        try:
            # Ensure token directory exists
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.token_file, 'w') as token:
                token.write(self.credentials.to_json())
            
            logger.debug(f"Credentials saved to {self.token_file}")
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            raise AuthenticationError(
                f"Failed to save credentials: {str(e)}",
                service="Google Drive",
                auth_type="Token Storage"
            )
    
    def test_authentication(self) -> Dict[str, Any]:
        """
        Test authentication by making a simple API call.
        
        Returns:
            Dictionary with test results
            
        Raises:
            AuthenticationError: If test fails
        """
        try:
            credentials = self.authenticate()
            
            # Build service and make a test call
            service = build('drive', 'v3', credentials=credentials)
            about = service.about().get(fields="user,storageQuota").execute()
            
            result = {
                "success": True,
                "user_email": about.get('user', {}).get('emailAddress'),
                "user_name": about.get('user', {}).get('displayName'),
                "storage_limit": about.get('storageQuota', {}).get('limit'),
                "storage_usage": about.get('storageQuota', {}).get('usage')
            }
            
            logger.info(f"Authentication test successful for user: {result['user_email']}")
            return result
            
        except HttpError as e:
            logger.error(f"API test failed: {e}")
            raise AuthenticationError(
                f"Google Drive API test failed: {e}",
                service="Google Drive",
                auth_type="API Test"
            )
        except Exception as e:
            logger.error(f"Authentication test failed: {e}")
            raise AuthenticationError(
                f"Authentication test failed: {str(e)}",
                service="Google Drive",
                auth_type="Test"
            )
    
    def revoke_credentials(self) -> None:
        """
        Revoke current credentials and remove token file.
        
        This forces a fresh authentication on next use.
        """
        try:
            if self.credentials and self.credentials.valid:
                # Revoke the token
                self.credentials.revoke(Request())
                logger.info("Credentials revoked successfully")
            
            # Remove token file
            if self.token_file.exists():
                self.token_file.unlink()
                logger.info("Token file removed")
            
            self.credentials = None
            
        except Exception as e:
            logger.warning(f"Failed to revoke credentials: {e}")
            # Still remove the token file
            if self.token_file.exists():
                self.token_file.unlink()
            self.credentials = None
    
    def get_authorization_url(self) -> str:
        """
        Get authorization URL for manual OAuth flow.
        
        Returns:
            Authorization URL string
            
        Raises:
            AuthenticationError: If URL generation fails
        """
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.settings.credentials_file), self.SCOPES
            )
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            
            logger.info("Generated authorization URL")
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            raise AuthenticationError(
                f"Failed to generate authorization URL: {str(e)}",
                service="Google Drive",
                auth_type="OAuth2"
            )
    
    @property
    def is_authenticated(self) -> bool:
        """Check if currently authenticated with valid credentials."""
        return (self.credentials is not None 
                and self.credentials.valid 
                and not self.credentials.expired)
    
    @property
    def user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information if authenticated."""
        if not self.is_authenticated:
            return None
        
        try:
            service = build('drive', 'v3', credentials=self.credentials)
            about = service.about().get(fields="user").execute()
            return about.get('user', {})
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None