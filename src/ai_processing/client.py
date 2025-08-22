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
        
        messages_text = ""
        for i, msg in enumerate(request.messages[:50], 1):
            user = msg.get('user', 'Unknown')
            text = msg.get('text', '')
            channel = msg.get('channel', 'general')
            timestamp = msg.get('timestamp', 'Unknown time')
            
            messages_text += f"[{i}] {timestamp} - {user} in #{channel}:\n{text}\n\n"
        
        now = datetime.now()
        
        # Use different prompts based on task type
        if request.task_type == "daily_summary":
            # Use daily summary prompt
            prompt = JournalPrompts.DAILY_SUMMARY_PROMPT.render(
                date=now.strftime('%Y-%m-%d'),
                user_name="Team Member",
                messages_content=messages_text
            )
        else:
            # Use work analysis prompt for weekly and other tasks
            week_start = now - timedelta(days=7)
            prompt = JournalPrompts.WORK_ANALYSIS_PROMPT.render(
                period_start=week_start.strftime('%Y-%m-%d'),
                period_end=now.strftime('%Y-%m-%d'),
                user_name="Team Member",
                messages_content=messages_text
            )
        
        return prompt
    
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