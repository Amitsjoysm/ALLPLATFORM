from agents.base_agent import BaseAgent
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class YouTubeAgent(BaseAgent):
    """Specialized agent for YouTube platform analysis"""
    
    def __init__(self):
        super().__init__(name="YouTubeAgent", model="llama-3.3-70b-versatile")
        self.system_prompt = """You are a YouTube traffic opportunity specialist for a B2B SaaS company.

Analyze YouTube videos and identify content opportunities:
- Comment opportunities on relevant videos
- Video topic gaps to create content
- Collaboration opportunities
- Tutorial needs

Return ONLY valid JSON with:
- is_relevant: boolean
- opportunity_type: string (content_gap, trending_keyword)
- relevance_score: number 1-10
- traffic_potential: number 1-10 (video views + SEO)
- competition_level: number 1-5
- user_intent_score: number 1-10
- key_topics: array of strings
- suggested_action: string (comment, create video, tutorial)
- reasoning: string
- youtube_specific_tips: string (comment strategy, video ideas, SEO keywords)
"""
    
    async def process(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        content = signal_data.get("content", "")
        meta = signal_data.get("meta", {})
        views = meta.get("views", "")
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Video Details:\n{content}\n\nViews: {views}"}
        ]
        
        try:
            response = await self.call_llm(messages, temperature=0.3)
            response = response.strip().strip("```json").strip("```").strip()
            result = json.loads(response)
            result["platform"] = "youtube"
            
            self.add_to_context("user", content[:200])
            self.add_to_context("assistant", json.dumps(result))
            
            return result
        except Exception as e:
            logger.error(f"YouTube agent error: {e}")
            return self._default_response()
    
    def _default_response(self) -> Dict[str, Any]:
        return {
            "is_relevant": False,
            "opportunity_type": "content_gap",
            "relevance_score": 1,
            "traffic_potential": 1,
            "competition_level": 5,
            "user_intent_score": 1,
            "key_topics": [],
            "suggested_action": "Skip",
            "reasoning": "Failed to classify",
            "platform": "youtube"
        }
