from agents.base_agent import BaseAgent
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class ClassifierAgent(BaseAgent):
    """Classifies raw signals and extracts relevant information"""
    
    def __init__(self):
        super().__init__(name="ClassifierAgent", model="llama-3.3-70b-versatile")
        self.system_prompt = """You are a traffic opportunity classifier for a B2B SaaS company (email verification, lead generation tools).

Analyze the given content and classify it. Return ONLY a valid JSON object with these fields:
- is_relevant: boolean (true if related to email verification, B2B tools, CRM, sales, marketing, lead gen)
- opportunity_type: string (one of: question, trending_keyword, competitor_mention, complaint, forum_discussion, content_gap)
- relevance_score: number 1-10 (how relevant to our business)
- traffic_potential: number 1-10 (how much traffic this could bring)
- competition_level: number 1-5 (how competitive this space is)
- user_intent_score: number 1-10 (how strong is user's intent)
- key_topics: array of strings (main topics mentioned)
- suggested_action: string (what action to take)
- reasoning: string (brief explanation)

Return ONLY valid JSON, no additional text."""
    
    async def process(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Classify a raw signal"""
        content = signal_data.get("content", "")
        channel = signal_data.get("channel", "")
        
        # Prepare messages
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Channel: {channel}\n\nContent:\n{content}"}
        ]
        
        try:
            response = await self.call_llm(messages, temperature=0.3)
            
            # Parse JSON response
            # Clean response - remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            result = json.loads(response)
            
            self.add_to_context("user", content[:200])
            self.add_to_context("assistant", json.dumps(result))
            
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Return default classification
            return {
                "is_relevant": False,
                "opportunity_type": "forum_discussion",
                "relevance_score": 1,
                "traffic_potential": 1,
                "competition_level": 5,
                "user_intent_score": 1,
                "key_topics": [],
                "suggested_action": "Skip - could not classify",
                "reasoning": "Failed to parse classification"
            }
        except Exception as e:
            logger.error(f"Classification error: {e}")
            raise
