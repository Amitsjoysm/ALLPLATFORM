from agents.base_agent import BaseAgent
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class CompetitorAgent(BaseAgent):
    """Specialized agent for competitor monitoring and analysis"""
    
    def __init__(self):
        super().__init__(name="CompetitorAgent", model="llama-3.3-70b-versatile")
        self.system_prompt = """You are a competitor intelligence specialist for a B2B SaaS company.

Analyze competitor updates, launches, and mentions. Look for:
- New features we should respond to
- Pricing changes
- User complaints about competitors
- Market positioning shifts
- Content gaps we can fill

Return ONLY valid JSON with:
- is_relevant: boolean
- opportunity_type: string (competitor_mention, complaint, content_gap)
- relevance_score: number 1-10
- traffic_potential: number 1-10
- competition_level: number 1-5
- user_intent_score: number 1-10
- key_topics: array of strings
- suggested_action: string (comparison content, alternative page, response strategy)
- reasoning: string
- competitor_insights: string (what they're doing, how to respond)
- urgency: string (low, medium, high)
"""
    
    async def process(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        content = signal_data.get("content", "")
        meta = signal_data.get("meta", {})
        competitor = meta.get("competitor", "")
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Competitor: {competitor}\n\nUpdate:\n{content}"}
        ]
        
        try:
            response = await self.call_llm(messages, temperature=0.3)
            response = response.strip().strip("```json").strip("```").strip()
            result = json.loads(response)
            result["platform"] = "competitor"
            result["competitor_name"] = competitor
            
            self.add_to_context("user", content[:200])
            self.add_to_context("assistant", json.dumps(result))
            
            return result
        except Exception as e:
            logger.error(f"Competitor agent error: {e}")
            return self._default_response()
    
    def _default_response(self) -> Dict[str, Any]:
        return {
            "is_relevant": False,
            "opportunity_type": "competitor_mention",
            "relevance_score": 1,
            "traffic_potential": 1,
            "competition_level": 5,
            "user_intent_score": 1,
            "key_topics": [],
            "suggested_action": "Monitor",
            "reasoning": "Failed to classify",
            "platform": "competitor",
            "urgency": "low"
        }
