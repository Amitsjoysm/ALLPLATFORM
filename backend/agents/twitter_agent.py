from agents.base_agent import BaseAgent
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class TwitterAgent(BaseAgent):
    """Specialized agent for Twitter/X platform analysis"""
    
    def __init__(self):
        super().__init__(name="TwitterAgent", model="llama-3.3-70b-versatile")
        self.system_prompt = """You are a Twitter/X traffic opportunity specialist for a B2B SaaS company.

Analyze tweets and identify opportunities. Twitter is best for:
- Quick, engaging responses
- Building relationships with founders
- Trending topics and viral moments
- Thread opportunities

Return ONLY valid JSON with:
- is_relevant: boolean
- opportunity_type: string (trending_keyword, competitor_mention, forum_discussion)
- relevance_score: number 1-10
- traffic_potential: number 1-10 (viral potential)
- competition_level: number 1-5
- user_intent_score: number 1-10
- key_topics: array of strings
- suggested_action: string (tweet reply, thread, quote tweet)
- reasoning: string
- twitter_specific_tips: string (hashtags, mentions, thread structure)
"""
    
    async def process(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        content = signal_data.get("content", "")
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Tweet:\n{content}"}
        ]
        
        try:
            response = await self.call_llm(messages, temperature=0.3)
            response = response.strip().strip("```json").strip("```").strip()
            result = json.loads(response)
            result["platform"] = "twitter"
            
            self.add_to_context("user", content[:200])
            self.add_to_context("assistant", json.dumps(result))
            
            return result
        except Exception as e:
            logger.error(f"Twitter agent error: {e}")
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
            "platform": "twitter"
        }
