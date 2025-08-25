"""
Gemini AI client for content processing.

This module provides a client for Gemini 2.5 AI model
for analyzing Slack messages and generating work journals.
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from ..core.logging import get_logger
from ..core.exceptions import AIProcessingError
from ..settings import GeminiSettings
from .schemas import AIRequest, AIResponse, AIModelType


logger = get_logger(__name__)


class GeminiClient:
    """
    Client for Gemini AI API.
    
    Handles communication with Gemini models for content analysis,
    journal generation, and work content extraction.
    """
    
    def __init__(self, settings: GeminiSettings) -> None:
        """
        Initialize Gemini client.
        
        Args:
            settings: Gemini AI configuration
        """
        self.settings = settings
        self.model = None
        self._initialized = False
        
        # Safety settings for work content
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        
        logger.info(f"Initialized Gemini client with model: {settings.model}")
    
    def initialize(self) -> None:
        """
        Initialize the Gemini client with API key.
        
        Raises:
            AIProcessingError: If initialization fails
        """
        try:
            if not self.settings.api_key:
                raise AIProcessingError(
                    "Gemini API key not provided",
                    model_name=self.settings.model
                )
            
            # Configure the API
            genai.configure(api_key=self.settings.api_key)
            
            # Initialize the model
            generation_config = genai.GenerationConfig(
                temperature=self.settings.temperature,
                top_p=0.95,
                top_k=40,
                max_output_tokens=self.settings.max_tokens,
                response_mime_type="text/plain"
            )
            
            self.model = genai.GenerativeModel(
                model_name=self.settings.model,
                generation_config=generation_config,
                safety_settings=self.safety_settings
            )
            
            self._initialized = True
            logger.info("Successfully initialized Gemini client")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise AIProcessingError(
                f"Gemini initialization failed: {str(e)}",
                model_name=self.settings.model
            )
    
    def _ensure_initialized(self) -> None:
        """Ensure client is initialized."""
        if not self._initialized:
            self.initialize()
    
    def analyze_messages(self, request: AIRequest) -> AIResponse:
        """
        Analyze messages. For daily summaries, we'll use a more direct approach
        to ensure correct tag classification.
        """
        # For daily summaries, use direct code processing instead of AI
        if request.task_type == "daily_summary":
            return self._analyze_messages_directly(request)
        else:
            return self._analyze_messages_with_ai(request)
    
    def _analyze_messages_directly(self, request: AIRequest) -> AIResponse:
        """
        Directly analyze messages without AI to ensure correct tag classification.
        """
        start_time = time.time()
        
        try:
            # Filter messages
            filtered_messages = self._filter_excluded_messages(request.messages)
            
            # Check if we should include user names
            include_user_names = request.context and request.context.get('include_user_names', False)
            
            # Generate summary directly
            summary_lines = []
            for msg in filtered_messages:
                text = msg.get('text', '')
                tag = self._get_tag_suggestion(text)
                
                # Get user display name - use the display name from Slack
                user_real_name = msg.get('user_real_name')
                user_name = msg.get('user_name') 
                user_id = msg.get('user', 'Unknown User')
                
                user_display_name = user_real_name or user_name or user_id
                
                # Extract project and description from text
                project, description = self._extract_project_info(text)
                
                # Format as MM/DD `tag` project - description</br>
                # Or MM/DD `user_name` `tag` project - description</br> if include_user_names
                from datetime import datetime
                now = datetime.now()
                date_str = now.strftime('%m/%d')
                
                if include_user_names:
                    summary_lines.append(f"{date_str} `{user_display_name}` `{tag}` {project} - {description}</br>")
                else:
                    summary_lines.append(f"{date_str} `{tag}` {project} - {description}</br>")
            
            raw_response = "\n".join(summary_lines)
            processing_time = time.time() - start_time
            
            return AIResponse(
                success=True,
                model_used=request.model_type,
                processing_time=processing_time,
                tokens_used=0,  # No AI tokens used
                raw_response=raw_response,
                confidence_score=1.0,  # High confidence since we're doing direct processing
                completeness_score=1.0,
                messages_processed=len(filtered_messages),
                work_items_extracted=len(summary_lines),
                projects_identified=1
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_message = f"Direct analysis failed: {str(e)}"
            logger.error(error_message)
            
            return AIResponse(
                success=False,
                error_message=error_message,
                model_used=request.model_type,
                processing_time=processing_time,
                tokens_used=0,
                messages_processed=len(request.messages),
                work_items_extracted=0,
                projects_identified=0
            )
    
    def _extract_project_info(self, text: str) -> tuple[str, str]:
        """Extract project name and description from Slack message text."""
        lines = text.strip().split('\n')
        if not lines:
            return "unknown", "no description"
        
        # First line usually contains project info
        first_line = lines[0].strip()
        
        # Remove backticks from develop
        project_line = first_line.replace('`develop`', '').strip()
        
        # Extract project name (first part before space or <)
        if '<' in project_line:
            parts = project_line.split('<')[0].strip()
        else:
            parts = project_line
        
        project = parts.strip()
        
        # Look for description in the rest of the text, avoiding URLs
        description = "工作項目"
        
        # Check for PR description or commit message
        if 'feat:' in text:
            desc_start = text.find('feat:') + 5
            desc_end = text.find('>', desc_start)
            if desc_end == -1:
                desc_end = len(text)
            description = text[desc_start:desc_end].strip()
        elif 'fix:' in text:
            desc_start = text.find('fix:') + 4
            desc_end = text.find('>', desc_start)
            if desc_end == -1:
                desc_end = len(text)
            description = text[desc_start:desc_end].strip()
        elif '提取要求' in text:
            # Look for PR description pattern like "提取要求 61899: 調整買屋廣告搜尋邏輯"
            for line in lines:
                if '提取要求' in line and ':' in line:
                    # Extract description after the colon
                    desc_part = line.split(':', 1)[-1].strip()
                    if desc_part and '<' in desc_part:
                        # Remove URL part
                        desc_part = desc_part.split('<')[0].strip()
                    if desc_part:
                        description = desc_part
                        break
        elif ':' in text:
            # Look for description after colon, but avoid URLs
            for line in lines:
                if ':' in line and not line.startswith('http') and not line.startswith('<http'):
                    # Extract description before any URL
                    desc_part = line.split(':', 1)[-1].strip()
                    if desc_part and '<' in desc_part:
                        # Remove URL part
                        desc_part = desc_part.split('<')[0].strip()
                    if desc_part:
                        description = desc_part
                        break
        
        # Clean up description - remove any remaining URL fragments
        import re
        # Remove URLs starting with < and ending with >
        description = re.sub(r'<[^>]*>', '', description).strip()
        # Remove standalone URLs
        description = re.sub(r'https?://[^\s]+', '', description).strip()
        # Remove file paths that look like URLs
        description = re.sub(r'//[^\s]*', '', description).strip()
        # Remove PR numbers with > suffix like "61899>"
        description = re.sub(r'\d+>', '', description).strip()
        # Remove any remaining > or < characters
        description = description.replace('>', '').replace('<', '').strip()
        # Clean up any remaining colons at the start
        description = description.lstrip(':').strip()
        
        return project or "unknown", description or "工作項目"

    def _analyze_messages_with_ai(self, request: AIRequest) -> AIResponse:
        """
        Analyze messages using Gemini AI.
        
        Args:
            request: AI processing request
            
        Returns:
            AI response with analysis results
            
        Raises:
            AIProcessingError: If analysis fails
        """
        self._ensure_initialized()
        
        start_time = time.time()
        
        try:
            # Prepare the prompt
            prompt = self._prepare_prompt(request)
            
            logger.debug(f"Sending request to Gemini (model: {request.model_type})")
            logger.debug(f"Prompt length: {len(prompt)} characters")
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=request.temperature,
                    max_output_tokens=request.max_tokens,
                    response_mime_type="application/json" if request.output_format == "json" else "text/plain"
                )
            )
            
            processing_time = time.time() - start_time
            
            # Extract response text
            if response.candidates:
                response_text = response.candidates[0].content.parts[0].text
            else:
                raise AIProcessingError(
                    "No response candidates generated",
                    model_name=request.model_type
                )
            
            # Parse JSON response if requested
            journal_structure = None
            if request.output_format == "json":
                try:
                    parsed_response = json.loads(response_text)
                    journal_structure = self._parse_journal_structure(parsed_response)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON response: {e}")
                    # Try to extract JSON from response
                    response_text = self._extract_json_from_text(response_text)
                    if response_text:
                        try:
                            parsed_response = json.loads(response_text)
                            journal_structure = self._parse_journal_structure(parsed_response)
                        except json.JSONDecodeError:
                            logger.error("Unable to parse JSON from response")
            
            # Calculate token usage (estimation)
            estimated_tokens = len(prompt.split()) + len(response_text.split())
            
            # Create response
            ai_response = AIResponse(
                success=True,
                model_used=request.model_type,
                processing_time=processing_time,
                tokens_used=estimated_tokens,
                journal_structure=journal_structure,
                raw_response=response_text,
                confidence_score=self._calculate_confidence_score(response_text),
                completeness_score=self._calculate_completeness_score(response_text, request),
                messages_processed=len(request.messages),
                work_items_extracted=len(journal_structure.projects[0].work_items) if journal_structure and journal_structure.projects else 0,
                projects_identified=len(journal_structure.projects) if journal_structure else 0
            )
            
            logger.info(f"Successfully processed {len(request.messages)} messages in {processing_time:.2f}s")
            return ai_response
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_message = f"Gemini analysis failed: {str(e)}"
            logger.error(error_message)
            
            return AIResponse(
                success=False,
                error_message=error_message,
                model_used=request.model_type,
                processing_time=processing_time,
                tokens_used=0,
                messages_processed=len(request.messages),
                work_items_extracted=0,
                projects_identified=0
            )
    
    def validate_response_quality(self, response_text: str) -> Dict[str, Any]:
        """
        Validate the quality of AI response.
        
        Args:
            response_text: Response text to validate
            
        Returns:
            Validation results
        """
        self._ensure_initialized()
        
        validation_prompt = f"""
Please evaluate the quality of this work journal:

{response_text}

Rate each dimension from 0-10 and provide feedback:
1. Completeness - covers all important work
2. Accuracy - information is correct
3. Structure - well-organized content
4. Clarity - easy to understand
5. Usefulness - valuable for review

Respond in JSON format:
```json
{{
  "overall_score": number,
  "dimension_scores": {{
    "completeness": number,
    "accuracy": number,
    "structure": number,
    "clarity": number,
    "usefulness": number
  }},
  "strengths": ["strength1", "strength2"],
  "improvements": ["suggestion1", "suggestion2"],
  "is_acceptable": boolean
}}
```
"""
        
        try:
            response = self.model.generate_content(
                validation_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            
            if response.candidates:
                validation_text = response.candidates[0].content.parts[0].text
                return json.loads(validation_text)
            else:
                return {"error": "No validation response generated"}
                
        except Exception as e:
            logger.error(f"Response validation failed: {e}")
            return {"error": str(e)}
    
    def _prepare_prompt(self, request: AIRequest) -> str:
        """
        Prepare prompt from request data.
        
        Args:
            request: AI request
            
        Returns:
            Formatted prompt string
        """
        # Use the new simplified prompt from prompts.py
        from .prompts import JournalPrompts
        from datetime import datetime, timedelta
        
        # Filter out messages containing excluded keywords before sending to AI
        filtered_messages = self._filter_excluded_messages(request.messages)
        
        messages_text = ""
        for i, msg in enumerate(filtered_messages[:50], 1):
            user = msg.get('user', 'Unknown')
            text = msg.get('text', '')
            channel = msg.get('channel', 'general')
            timestamp = msg.get('timestamp', 'Unknown time')
            
            # Pre-analyze message for tag suggestion
            tag_hint = self._get_tag_suggestion(text)
            
            messages_text += f"[{i}] {timestamp} - {user} in #{channel}:\n{text}\n[建議標籤: {tag_hint}]\n\n"
        
        now = datetime.now()
        
        # Add exclusion instruction to prompt
        exclusion_note = self._get_exclusion_note()
        
        # Use different prompts based on task type
        if request.task_type == "daily_summary":
            # Use daily summary prompt
            base_prompt = JournalPrompts.DAILY_SUMMARY_PROMPT.render(
                date=now.strftime('%Y-%m-%d'),
                user_name="Team Member",
                messages_content=messages_text
            )
            prompt = base_prompt + exclusion_note
        else:
            # Use work analysis prompt for weekly and other tasks
            week_start = now - timedelta(days=7)
            base_prompt = JournalPrompts.WORK_ANALYSIS_PROMPT.render(
                period_start=week_start.strftime('%Y-%m-%d'),
                period_end=now.strftime('%Y-%m-%d'),
                user_name="Team Member",
                messages_content=messages_text
            )
            prompt = base_prompt + exclusion_note
        
        return prompt
    
    def _filter_excluded_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out messages containing excluded keywords.
        
        This provides a final safety net to ensure excluded content doesn't reach AI processing.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Filtered list of messages
        """
        # Get exclude keywords from multiple sources
        exclude_keywords = []
        
        # From settings (if available)
        try:
            from ..settings import get_settings
            settings = get_settings()
            if settings.slack.exclude_keywords:
                exclude_keywords.extend(settings.slack.exclude_keywords)
        except Exception:
            pass
        
        # From environment variable
        import os
        env_exclude = os.getenv('SLACK_EXCLUDE_KEYWORDS', '')
        if env_exclude.strip():
            env_keywords = [kw.strip().lower() for kw in env_exclude.split(',') if kw.strip()]
            exclude_keywords.extend(env_keywords)
        
        if not exclude_keywords:
            return messages
        
        # Filter messages
        filtered_messages = []
        excluded_count = 0
        
        for msg in messages:
            text = msg.get('text', '').lower()
            should_exclude = False
            
            for keyword in exclude_keywords:
                if keyword in text:
                    should_exclude = True
                    excluded_count += 1
                    logger.info(f"AI FILTER: Excluding message with keyword '{keyword}': {msg.get('text', '')[:80]}...")
                    break
            
            if not should_exclude:
                filtered_messages.append(msg)
        
        if excluded_count > 0:
            logger.info(f"AI processing excluded {excluded_count} messages containing blocked keywords")
        
        return filtered_messages
    
    def _get_exclusion_note(self) -> str:
        """
        Generate exclusion note for AI prompt based on configured exclude keywords.
        
        Returns:
            Exclusion instruction string to add to prompts
        """
        # Get exclude keywords from multiple sources
        exclude_keywords = []
        
        # From settings (if available)
        try:
            from ..settings import get_settings
            settings = get_settings()
            if settings.slack.exclude_keywords:
                exclude_keywords.extend(settings.slack.exclude_keywords)
        except Exception:
            pass
        
        # From environment variable
        import os
        env_exclude = os.getenv('SLACK_EXCLUDE_KEYWORDS', '')
        if env_exclude.strip():
            env_keywords = [kw.strip().lower() for kw in env_exclude.split(',') if kw.strip()]
            exclude_keywords.extend(env_keywords)
        
        if not exclude_keywords:
            return ""
        
        keywords_list = "、".join(f"'{kw}'" for kw in exclude_keywords)
        
        return f"""

**重要排除規則**: 
- 絕對不要在工作日誌中包含任何含有以下關鍵字的內容：{keywords_list}
- 即使這些內容看起來與工作相關，也必須完全排除
- 這是最高優先級規則，覆蓋所有其他分析判斷
"""
    
    def _parse_journal_structure(self, parsed_response: Dict[str, Any]) -> Optional[Any]:
        """
        Parse response into JournalStructure.
        
        Args:
            parsed_response: Parsed JSON response
            
        Returns:
            JournalStructure object or None
        """
        try:
            # Import here to avoid circular imports
            from .schemas import JournalStructure
            return JournalStructure(**parsed_response)
        except Exception as e:
            logger.error(f"Failed to parse journal structure: {e}")
            return None
    
    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Extract JSON from text that might contain other content.
        
        Args:
            text: Text that might contain JSON
            
        Returns:
            Extracted JSON string or None
        """
        # Look for JSON blocks
        import re
        
        # Try to find JSON between ```json and ```
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Try to find JSON between { and }
        brace_match = re.search(r'\{.*\}', text, re.DOTALL)
        if brace_match:
            return brace_match.group(0)
        
        return None
    
    def _calculate_confidence_score(self, response_text: str) -> float:
        """
        Calculate confidence score based on response characteristics.
        
        Args:
            response_text: AI response text
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.5  # Base score
        
        # Higher score for structured content
        if '"confidence_score"' in response_text:
            score += 0.2
        
        # Higher score for longer, detailed responses
        if len(response_text) > 1000:
            score += 0.1
        
        # Higher score for JSON format
        if response_text.strip().startswith('{'):
            score += 0.1
        
        # Lower score for error indicators
        if any(word in response_text.lower() for word in ['error', 'sorry', 'cannot', 'unable']):
            score -= 0.3
        
        return max(0.0, min(1.0, score))
    
    def _calculate_completeness_score(self, response_text: str, request: AIRequest) -> float:
        """
        Calculate completeness score based on expected content.
        
        Args:
            response_text: AI response text
            request: Original request
            
        Returns:
            Completeness score between 0.0 and 1.0
        """
        score = 0.0
        expected_sections = ['projects', 'work_items', 'summary', 'achievements']
        
        for section in expected_sections:
            if section in response_text.lower():
                score += 0.25
        
        # Bonus for having structured data
        if 'confidence_score' in response_text:
            score += 0.1
        
        return min(1.0, score)
    
    def _get_user_display_name(self, user_id: str) -> str:
        """
        Convert Slack user ID to display name.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            Display name for the user
        """
        # Cache for user info to avoid repeated API calls
        if not hasattr(self, '_user_cache'):
            self._user_cache = {}
        
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        
        # This method should no longer be needed since we get real names from Slack API
        # But keeping as fallback for any missing users
        
        # Check if we have a mapping for this user
        if user_id in user_mappings:
            display_name = user_mappings[user_id]
        else:
            # Try to get a more readable name from the user ID
            # If it starts with U and is 11 characters, it's likely a Slack user ID
            if user_id.startswith('U') and len(user_id) == 11:
                display_name = f"User_{user_id[-4:]}"  # Show last 4 characters
            else:
                display_name = user_id
        
        # Cache the result
        self._user_cache[user_id] = display_name
        return display_name

    def _get_tag_suggestion(self, text: str) -> str:
        """
        Pre-analyze message text to suggest appropriate tag.
        
        Args:
            text: Message text
            
        Returns:
            Suggested tag
        """
        text_lower = text.lower()
        
        # Check for deployment/production keywords (highest priority)
        deploy_keywords = ['develop', 'dev', 'master', '部署', '上線', 'deploy', 'production', 'prod']
        if any(keyword in text_lower for keyword in deploy_keywords):
            return '上線'
        
        # Check for testing keywords
        test_keywords = ['測試', '測試機', 'test', 'testing', 'training', 'qa', 'staging']
        if any(keyword in text_lower for keyword in test_keywords):
            return '交測'
        
        # Default
        return '分支合併'

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Model information dictionary
        """
        return {
            "model_name": self.settings.model,
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
            "initialized": self._initialized,
            "api_key_configured": bool(self.settings.api_key)
        }