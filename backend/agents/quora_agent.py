from agents.base_agent import BaseAgent
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class QuoraAgent(BaseAgent):
    """Specialized agent for Quora platform analysis"""
    
    def __init__(self):
        super().__init__(name="QuoraAgent", model="llama-3.3-70b-versatile")
        self.system_prompt = """You are a Quora traffic opportunity specialist for a B2B SaaS company.

Analyze Quora questions and identify opportunities. Quora users expect:
- Detailed, well-researched answers
- Expert credibility
- Practical examples
- Less promotional content

Return ONLY valid JSON with:
- is_relevant: boolean
- opportunity_type: string (question, content_gap)
- relevance_score: number 1-10
- traffic_potential: number 1-10 (Quora has high SEO value)
- competition_level: number 1-5 (number of existing answers)
- user_intent_score: number 1-10
- key_topics: array of strings
- suggested_action: string
- reasoning: string
- quora_specific_tips: string (answer length, tone, credibility markers)
"""
    
    async def process(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        content = signal_data.get("content", "")
        meta = signal_data.get("meta", {})
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Question:\n{content}"}
        ]
        
        try:
            response = await self.call_llm(messages, temperature=0.3)
            response = response.strip().strip("```json").strip("```").strip()
            result = json.loads(response)
            result["platform"] = "quora"
            
            self.add_to_context("user", content[:200])
            self.add_to_context("assistant", json.dumps(result))
            
            return result
        except Exception as e:
            logger.error(f"Quora agent error: {e}")
            return self._default_response()
    
    def _default_response(self) -> Dict[str, Any]:
        return {
            "is_relevant": False,
            "opportunity_type": "question",
            "relevance_score": 1,
            "traffic_potential": 1,
            "competition_level": 5,
            "user_intent_score": 1,
            "key_topics": [],
            "suggested_action": "Skip",
            "reasoning": "Failed to classify",
            "platform": "quora"
        }
