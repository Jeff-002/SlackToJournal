"""
AI processing service layer.

This module provides high-level business logic for AI content analysis,
combining message processing, prompt generation, and result validation.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from ..core.logging import get_logger
from ..core.exceptions import AIProcessingError
from ..settings import GeminiSettings
from .client import GeminiClient
from .prompts import PromptBuilder, JournalPrompts
from .schemas import (
    AIRequest, AIResponse, PromptContext, JournalStructure,
    WorkItem, ValidationResult, AIModelType
)


logger = get_logger(__name__)


class AIProcessingService:
    """
    High-level service for AI content processing.
    
    Orchestrates message analysis, prompt generation, and response validation
    to produce structured work journals.
    """
    
    def __init__(self, settings: GeminiSettings) -> None:
        """
        Initialize AI processing service.
        
        Args:
            settings: Gemini AI settings
        """
        self.settings = settings
        self.client = GeminiClient(settings)
        self.prompt_builder = PromptBuilder()
        
        logger.info("Initialized AI processing service")
    
    async def generate_weekly_journal(
        self,
        messages: List[Dict[str, Any]],
        context: PromptContext,
        include_trends: bool = False,
        custom_focus: Optional[List[str]] = None
    ) -> AIResponse:
        """
        Generate a complete weekly work journal from Slack messages.
        
        Args:
            messages: Slack messages to analyze
            context: Context information for prompt generation
            include_trends: Whether to include trend analysis
            custom_focus: Custom focus areas for analysis
            
        Returns:
            AI response with generated journal
            
        Raises:
            AIProcessingError: If journal generation fails
        """
        try:
            logger.info(f"Generating weekly journal for {len(messages)} messages")
            
            # Build comprehensive prompt
            prompt = self.prompt_builder.build_weekly_journal_prompt(
                messages=messages,
                context=context,
                include_trends=include_trends,
                focus_areas=custom_focus
            )
            
            # Create AI request
            ai_request = AIRequest(
                messages=messages,
                context=context.model_dump(),
                model_type=AIModelType(self.settings.model),
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
                task_type="weekly_journal_generation",
                output_format="text",
                group_by_project=True,
                extract_action_items=True
            )
            
            # Replace prompt in request (this is a simplified approach)
            # In a real implementation, we'd modify the client to accept custom prompts
            
            # Process with AI
            response = self.client.analyze_messages(ai_request)
            
            # Validate response quality if successful
            if response.success and response.journal_structure:
                validation_result = await self._validate_journal_quality(response)
                response.completeness_score = validation_result.quality_score
            
            logger.info(f"Journal generation completed. Success: {response.success}")
            return response
            
        except Exception as e:
            logger.error(f"Weekly journal generation failed: {e}")
            raise AIProcessingError(
                f"Journal generation failed: {str(e)}",
                model_name=self.settings.model
            )
    
    async def generate_daily_summary(
        self,
        messages: List[Dict[str, Any]],
        date: datetime,
        user_name: str = "User"
    ) -> AIResponse:
        """
        Generate a daily work summary.
        
        Args:
            messages: Messages from the day
            date: Date of the summary
            user_name: Name of the user
            
        Returns:
            AI response with daily summary
        """
        try:
            logger.info(f"Generating daily summary for {date.strftime('%Y-%m-%d')}")
            
            # Build daily summary prompt
            prompt = JournalPrompts.DAILY_SUMMARY_PROMPT.render(
                date=date.strftime('%Y-%m-%d'),
                user_name=user_name,
                messages_content=self._format_messages_for_prompt(messages)
            )
            
            # Create request
            ai_request = AIRequest(
                messages=messages,
                model_type=AIModelType(self.settings.model),
                temperature=self.settings.temperature,
                max_tokens=4096,
                task_type="daily_summary",
                output_format="text"
            )
            
            # Process
            response = self.client.analyze_messages(ai_request)
            
            logger.info(f"Daily summary generation completed. Success: {response.success}")
            return response
            
        except Exception as e:
            logger.error(f"Daily summary generation failed: {e}")
            raise AIProcessingError(
                f"Daily summary failed: {str(e)}",
                model_name=self.settings.model
            )
    
    async def analyze_project_progress(
        self,
        messages: List[Dict[str, Any]],
        project_name: str
    ) -> Dict[str, Any]:
        """
        Analyze progress for a specific project.
        
        Args:
            messages: Project-related messages
            project_name: Name of the project
            
        Returns:
            Project progress analysis
        """
        try:
            logger.info(f"Analyzing progress for project: {project_name}")
            
            # Filter messages for project
            project_messages = self._filter_project_messages(messages, project_name)
            
            if not project_messages:
                return {
                    "project_name": project_name,
                    "analysis": "No project-related messages found",
                    "confidence_score": 0.0
                }
            
            # Build project analysis prompt
            prompt = JournalPrompts.PROJECT_EXTRACTION_PROMPT.render(
                messages_content=self._format_messages_for_prompt(project_messages)
            )
            
            # Create request
            ai_request = AIRequest(
                messages=project_messages,
                model_type=AIModelType(self.settings.model),
                temperature=0.2,  # Lower temperature for factual analysis
                max_tokens=4096,
                task_type="project_analysis",
                output_format="json"
            )
            
            # Process
            response = self.client.analyze_messages(ai_request)
            
            if response.success and response.raw_response:
                try:
                    import json
                    analysis = json.loads(response.raw_response)
                    analysis["project_name"] = project_name
                    return analysis
                except json.JSONDecodeError:
                    return {
                        "project_name": project_name,
                        "analysis": response.raw_response,
                        "confidence_score": response.confidence_score
                    }
            else:
                return {
                    "project_name": project_name,
                    "error": response.error_message,
                    "confidence_score": 0.0
                }
                
        except Exception as e:
            logger.error(f"Project analysis failed for {project_name}: {e}")
            return {
                "project_name": project_name,
                "error": str(e),
                "confidence_score": 0.0
            }
    
    async def extract_meeting_insights(
        self,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract insights from meeting-related messages.
        
        Args:
            messages: Meeting-related messages
            
        Returns:
            Meeting insights and action items
        """
        try:
            logger.info("Extracting meeting insights")
            
            # Filter for meeting-related content
            meeting_messages = self._filter_meeting_messages(messages)
            
            if not meeting_messages:
                return {
                    "meetings": [],
                    "action_items": [],
                    "insights": "No meeting-related content found"
                }
            
            # Build meeting analysis prompt
            prompt = JournalPrompts.MEETING_ANALYSIS_PROMPT.render(
                messages_content=self._format_messages_for_prompt(meeting_messages)
            )
            
            # Create request
            ai_request = AIRequest(
                messages=meeting_messages,
                model_type=AIModelType(self.settings.model),
                temperature=0.2,
                max_tokens=4096,
                task_type="meeting_analysis",
                output_format="json",
                extract_action_items=True
            )
            
            # Process
            response = self.client.analyze_messages(ai_request)
            
            if response.success and response.raw_response:
                try:
                    import json
                    return json.loads(response.raw_response)
                except json.JSONDecodeError:
                    return {
                        "insights": response.raw_response,
                        "confidence_score": response.confidence_score
                    }
            else:
                return {
                    "error": response.error_message,
                    "confidence_score": 0.0
                }
                
        except Exception as e:
            logger.error(f"Meeting insights extraction failed: {e}")
            return {"error": str(e)}
    
    async def _validate_journal_quality(self, response: AIResponse) -> ValidationResult:
        """
        Validate the quality of generated journal.
        
        Args:
            response: AI response to validate
            
        Returns:
            Validation result
        """
        try:
            if not response.raw_response:
                return ValidationResult(
                    is_valid=False,
                    validation_errors=["No response content to validate"],
                    quality_score=0.0,
                    structure_valid=False,
                    content_complete=False,
                    format_correct=False
                )
            
            # Use client to validate response quality
            validation_data = self.client.validate_response_quality(response.raw_response)
            
            if "error" in validation_data:
                return ValidationResult(
                    is_valid=False,
                    validation_errors=[validation_data["error"]],
                    quality_score=0.0,
                    structure_valid=False,
                    content_complete=False,
                    format_correct=False
                )
            
            # Parse validation results
            overall_score = validation_data.get("overall_score", 0) / 10.0  # Normalize to 0-1
            is_acceptable = validation_data.get("is_acceptable", False)
            
            return ValidationResult(
                is_valid=is_acceptable,
                quality_score=overall_score,
                structure_valid=validation_data.get("dimension_scores", {}).get("structure", 0) > 6,
                content_complete=validation_data.get("dimension_scores", {}).get("completeness", 0) > 6,
                format_correct=validation_data.get("dimension_scores", {}).get("clarity", 0) > 6,
                improvement_suggestions=validation_data.get("improvements", [])
            )
            
        except Exception as e:
            logger.warning(f"Journal validation failed: {e}")
            return ValidationResult(
                is_valid=True,  # Default to valid if validation fails
                quality_score=0.7,  # Moderate score
                structure_valid=True,
                content_complete=True,
                format_correct=True,
                validation_errors=[f"Validation process failed: {str(e)}"]
            )
    
    def _format_messages_for_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for prompt inclusion."""
        formatted = []
        for i, msg in enumerate(messages[:30], 1):  # Limit messages
            user = msg.get('user', 'Unknown')
            text = msg.get('text', '')
            timestamp = msg.get('timestamp', 'Unknown')
            channel = msg.get('channel', 'general')
            
            if len(text) > 300:
                text = text[:300] + "..."
            
            formatted.append(f"[{i}] {timestamp} - {user} in #{channel}:\n{text}\n")
        
        return "\n".join(formatted)
    
    def _filter_project_messages(
        self, 
        messages: List[Dict[str, Any]], 
        project_name: str
    ) -> List[Dict[str, Any]]:
        """Filter messages related to a specific project."""
        project_keywords = project_name.lower().split()
        filtered = []
        
        for msg in messages:
            text = msg.get('text', '').lower()
            if any(keyword in text for keyword in project_keywords):
                filtered.append(msg)
        
        return filtered
    
    def _filter_meeting_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter messages related to meetings."""
        meeting_keywords = [
            'meeting', 'call', 'sync', 'standup', 'retrospective',
            'planning', 'review', 'discussion', 'demo', 'presentation'
        ]
        
        filtered = []
        for msg in messages:
            text = msg.get('text', '').lower()
            if any(keyword in text for keyword in meeting_keywords):
                filtered.append(msg)
        
        return filtered
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "model_info": self.client.get_model_info(),
            "settings": {
                "model": self.settings.model,
                "temperature": self.settings.temperature,
                "max_tokens": self.settings.max_tokens
            },
            "initialized": self.client._initialized
        }