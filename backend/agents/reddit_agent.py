from agents.base_agent import BaseAgent
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class RedditAgent(BaseAgent):
    """Specialized agent for Reddit platform analysis"""
    
    def __init__(self):
        super().__init__(name="RedditAgent", model="llama-3.3-70b-versatile")
        self.system_prompt = """You are a Reddit traffic opportunity specialist for a B2B SaaS company.

Analyze Reddit posts/questions and identify actionable opportunities. Consider:
- Subreddit context and audience
- Upvotes and engagement potential
- Question quality and specificity
- Timing for response
- Karma farming vs genuine questions

Return ONLY valid JSON with:
- is_relevant: boolean
- opportunity_type: string (question, forum_discussion, competitor_mention, complaint)
- relevance_score: number 1-10
- traffic_potential: number 1-10 (consider subreddit size)
- competition_level: number 1-5 (how many answers already)
- user_intent_score: number 1-10
- key_topics: array of strings
- suggested_action: string (specific action with subreddit context)
- reasoning: string
- reddit_specific_tips: string (subreddit rules, tone, timing)
"""
    
    async def process(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Reddit signal with platform-specific context"""
        content = signal_data.get("content", "")
        meta = signal_data.get("meta", {})
        subreddit = meta.get("subreddit", "")
        upvotes = meta.get("upvotes", 0)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Subreddit: {subreddit}\nUpvotes: {upvotes}\n\nPost:\n{content}"}
        ]
        
        try:
            response = await self.call_llm(messages, temperature=0.3)
            
            # Parse JSON
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            result = json.loads(response)
            
            # Add platform-specific metadata
            result["platform"] = "reddit"
            result["subreddit"] = subreddit
            
            self.add_to_context("user", content[:200])
            self.add_to_context("assistant", json.dumps(result))
            
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Reddit agent response: {e}")
            return self._default_response()
        except Exception as e:
            logger.error(f"Reddit agent error: {e}")
            raise
    
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
            "platform": "reddit"
        }
