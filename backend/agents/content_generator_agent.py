from agents.base_agent import BaseAgent
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ContentGeneratorAgent(BaseAgent):
    """Generates content templates for opportunities"""
    
    def __init__(self):
        super().__init__(name="ContentGeneratorAgent", model="llama-3.3-70b-versatile")
    
    async def process(self, opportunity_data: Dict[str, Any]) -> str:
        """Generate content template based on opportunity"""
        opp_type = opportunity_data.get("type", "")
        content = opportunity_data.get("content", "")
        suggested_action = opportunity_data.get("suggested_action", "")
        
        # Different prompts based on opportunity type
        if opp_type == "question":
            system_prompt = """You are a helpful B2B SaaS expert. Generate a high-quality answer to the question below.

Include:
1. Direct answer to the question
2. Practical tips
3. Natural mention of email verification/lead generation tools (without being too salesy)
4. Call-to-action at the end

Keep it conversational and helpful. Maximum 300 words."""
        
        elif opp_type == "trending_keyword":
            system_prompt = """Generate a blog post outline for the trending keyword below.

Include:
1. Catchy title
2. Introduction hook
3. 5-7 main sections with subheadings
4. Key points to cover in each section
5. SEO keywords to include
6. Call-to-action

Format as a structured outline."""
        
        elif opp_type == "competitor_mention":
            system_prompt = """Generate a comparison/alternative content template.

Include:
1. Fair comparison points
2. Unique differentiators
3. Use cases where our tool excels
4. Pricing comparison points
5. Migration guide mention

Keep it factual and helpful, not negative."""
        
        else:
            system_prompt = """Generate actionable content based on the opportunity described below.
Make it practical, helpful, and include a natural call-to-action."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Action: {suggested_action}\n\nContext:\n{content[:500]}"}
        ]
        
        try:
            response = await self.call_llm(messages, temperature=0.7)
            
            self.add_to_context("user", suggested_action)
            self.add_to_context("assistant", response[:200])
            
            return response
        except Exception as e:
            logger.error(f"Content generation error: {e}")
            return "Content template generation failed. Manual creation required."
