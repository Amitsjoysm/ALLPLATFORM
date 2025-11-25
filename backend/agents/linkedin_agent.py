from agents.base_agent import BaseAgent
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class LinkedInAgent(BaseAgent):
    """Specialized agent for LinkedIn platform analysis"""
    
    def __init__(self):
        super().__init__(name="LinkedInAgent", model="llama-3.3-70b-versatile")
        self.system_prompt = """You are a LinkedIn traffic opportunity specialist for a B2B SaaS company.

Analyze LinkedIn posts and identify B2B opportunities. LinkedIn is ideal for:
- Professional thought leadership
- B2B decision makers
- Long-form content
- Case studies and success stories

Return ONLY valid JSON with:
- is_relevant: boolean
- opportunity_type: string (question, content_gap, trending_keyword)
- relevance_score: number 1-10
- traffic_potential: number 1-10 (B2B audience reach)
- competition_level: number 1-5
- user_intent_score: number 1-10
- key_topics: array of strings
- suggested_action: string (comment, post, article)
- reasoning: string
- linkedin_specific_tips: string (professional tone, hashtags, tagging)
"""
    
    async def process(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        content = signal_data.get("content", "")
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"LinkedIn Post:\n{content}"}
        ]
        
        try:
            response = await self.call_llm(messages, temperature=0.3)
            response = response.strip().strip("```json").strip("```").strip()
            result = json.loads(response)
            result["platform"] = "linkedin"
            
            self.add_to_context("user", content[:200])
            self.add_to_context("assistant", json.dumps(result))
            
            return result
        except Exception as e:
            logger.error(f"LinkedIn agent error: {e}")
            return self._default_response()
    
    def _default_response(self) -> Dict[str, Any]:
        return {
            "is_relevant": False,
            "opportunity_type": "forum_discussion",
            "relevance_score": 1,
            "traffic_potential": 1,
            "competition_level": 5,
            "user_intent_score": 1,
            "key_topics": [],
            "suggested_action": "Skip",
            "reasoning": "Failed to classify",
            "platform": "linkedin"
        }
