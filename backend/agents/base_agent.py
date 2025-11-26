from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from groq import Groq, RateLimitError, APIError
from config import settings
from database import get_database
from datetime import datetime, timezone
import logging
import json
import time

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents following Parlant.io-like architecture
    
    Features:
    - Automatic retry logic with exponential backoff
    - Structured output validation
    - Context memory management with token limits
    - Fallback mechanisms for API failures
    - Rate limit handling
    """
    
    def __init__(self, name: str, model: str = "llama-3.3-70b-versatile"):
        self.name = name
        self.model = model
        self.fallback_model = "llama3-70b-8192"  # Fallback if primary model fails
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.context_history: List[Dict[str, Any]] = []
        self.max_context_messages = 10
        self.max_retries = 3
        self.rate_limit_retry_delay = 60  # seconds to wait on rate limit
    
    async def save_context(self, db=None):
        """Save agent context to database"""
        if db is None:
            db = get_database()
        
        context_doc = {
            "agent_name": self.name,
            "conversation_history": self.context_history,
            "metadata": {"model": self.model},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.agent_contexts.update_one(
            {"agent_name": self.name},
            {"$set": context_doc},
            upsert=True
        )
    
    async def load_context(self, db=None):
        """Load agent context from database"""
        if db is None:
            db = get_database()
        
        context_doc = await db.agent_contexts.find_one({"agent_name": self.name}, {"_id": 0})
        if context_doc:
            self.context_history = context_doc.get("conversation_history", [])
    
    def add_to_context(self, role: str, content: str):
        """Add message to context history with token management"""
        self.context_history.append({"role": role, "content": content})
        
        # Keep only last N messages to manage token limits
        if len(self.context_history) > self.max_context_messages:
            # Keep system message if exists, and last N messages
            system_msgs = [msg for msg in self.context_history if msg["role"] == "system"]
            other_msgs = [msg for msg in self.context_history if msg["role"] != "system"]
            self.context_history = system_msgs + other_msgs[-self.max_context_messages:]
    
    async def call_llm(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Optional[str] = None
    ) -> str:
        """Call LLM with enhanced retry logic and error handling
        
        Features:
        - Exponential backoff on failures
        - Rate limit handling
        - Model fallback
        - Structured output enforcement
        """
        import asyncio
        
        current_model = self.model
        
        for attempt in range(self.max_retries):
            try:
                # Build API call parameters
                api_params = {
                    "model": current_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                # Add response format if specified (for structured outputs)
                if response_format:
                    api_params["response_format"] = {"type": response_format}
                
                response = self.client.chat.completions.create(**api_params)
                content = response.choices[0].message.content
                
                # Log successful call
                logger.debug(f"LLM call successful (model: {current_model}, attempt: {attempt + 1})")
                return content
                
            except RateLimitError as e:
                logger.warning(f"Rate limit hit on attempt {attempt + 1}, waiting {self.rate_limit_retry_delay}s...")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.rate_limit_retry_delay)
                else:
                    raise Exception(f"Rate limit exceeded after {self.max_retries} retries")
                    
            except APIError as e:
                logger.error(f"API error (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                
                # Try fallback model on last attempt
                if attempt == self.max_retries - 1:
                    if current_model != self.fallback_model:
                        logger.info(f"Trying fallback model: {self.fallback_model}")
                        current_model = self.fallback_model
                        continue
                    else:
                        raise
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"LLM call failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        raise Exception("LLM call failed after all retries")
    
    async def call_llm_with_structured_output(
        self,
        messages: List[Dict[str, str]],
        output_schema: Dict[str, Any],
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Call LLM and enforce structured JSON output
        
        Args:
            messages: Conversation messages
            output_schema: Expected output structure description
            temperature: Model temperature
            
        Returns:
            Validated JSON output
        """
        # Add schema to system message
        schema_instruction = f"\n\nYou MUST respond with valid JSON matching this schema: {json.dumps(output_schema)}"
        
        enhanced_messages = messages.copy()
        if enhanced_messages and enhanced_messages[0]["role"] == "system":
            enhanced_messages[0]["content"] += schema_instruction
        else:
            enhanced_messages.insert(0, {"role": "system", "content": schema_instruction})
        
        # Call LLM
        response = await self.call_llm(enhanced_messages, temperature=temperature)
        
        # Parse and validate JSON
        try:
            # Extract JSON if wrapped in markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(response)
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM output as JSON: {e}")
            logger.error(f"Raw output: {response}")
            
            # Return safe default
            return {"error": "invalid_json", "raw_output": response}
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """Process input data - to be implemented by subclasses"""
        pass
    
    def clear_context(self):
        """Clear context history"""
        self.context_history = []
