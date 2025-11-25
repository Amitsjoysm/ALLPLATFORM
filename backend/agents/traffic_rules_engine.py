from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TrafficRulesEngine:
    """
    Implements business logic rules for converting opportunities into actionable recommendations.
    
    Rules:
    1. Question → generate answer + CTA
    2. Rising keyword → suggest landing page/blog/video
    3. Competitor mention → suggest comparison page
    4. Complaints → suggest targeted campaign
    5. Website traffic (future) → suggest reach-out
    """
    
    def __init__(self):
        self.rules = {
            "question": self._rule_question,
            "trending_keyword": self._rule_trending_keyword,
            "competitor_mention": self._rule_competitor_mention,
            "complaint": self._rule_complaint,
            "forum_discussion": self._rule_forum_discussion,
            "content_gap": self._rule_content_gap
        }
    
    def apply_rules(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Apply business logic rules to enhance opportunity"""
        opp_type = opportunity.get("type", "forum_discussion")
        
        rule_func = self.rules.get(opp_type, self._rule_default)
        enhanced = rule_func(opportunity)
        
        return enhanced
    
    def _rule_question(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rule 1: Question → generate answer + CTA + link
        """
        platform = opp.get("meta", {}).get("platform", "")
        
        # Enhance suggested action
        if not opp.get("suggested_action"):
            opp["suggested_action"] = f"Answer this question on {platform}"
        
        # Add action template
        opp["action_template"] = {
            "type": "question_answer",
            "steps": [
                "1. Read the question thoroughly",
                "2. Provide a detailed, helpful answer (300-500 words)",
                "3. Include practical examples",
                "4. Add subtle CTA mentioning your tool",
                "5. Link to relevant resource on your website"
            ],
            "tone": self._get_platform_tone(platform),
            "cta_examples": [
                "If you need help with email verification, check out [your tool]",
                "We built [tool] specifically to solve this problem",
                "Feel free to try our free plan at [link]"
            ]
        }
        
        # Set priority based on user intent
        if opp.get("user_intent", 1) >= 8:
            opp["priority"] = "high"
        elif opp.get("user_intent", 1) >= 5:
            opp["priority"] = "medium"
        else:
            opp["priority"] = "low"
        
        return opp
    
    def _rule_trending_keyword(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rule 2: Rising keyword → suggest landing page/blog/video/tweet
        """
        keyword = opp.get("meta", {}).get("keyword", "")
        traffic_potential = opp.get("traffic_potential", 5)
        
        # Suggest multiple content types
        content_suggestions = []
        
        if traffic_potential >= 8:
            content_suggestions = [
                "Create dedicated landing page",
                "Write comprehensive blog post (2000+ words)",
                "Create YouTube tutorial video",
                "Launch Twitter/LinkedIn thread"
            ]
        elif traffic_potential >= 5:
            content_suggestions = [
                "Write blog post (1000-1500 words)",
                "Create Twitter thread",
                "Post on LinkedIn"
            ]
        else:
            content_suggestions = [
                "Write short blog post (500-800 words)",
                "Create social media post"
            ]
        
        opp["action_template"] = {
            "type": "content_creation",
            "keyword": keyword,
            "content_suggestions": content_suggestions,
            "seo_focus": True,
            "steps": [
                f"1. Research '{keyword}' - analyze top 10 Google results",
                "2. Identify content gaps",
                "3. Create comprehensive content",
                "4. Optimize for SEO",
                "5. Publish and promote on social media"
            ]
        }
        
        opp["priority"] = "high" if traffic_potential >= 7 else "medium"
        
        return opp
    
    def _rule_competitor_mention(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rule 3: Competitor mention → suggest comparison/alternative page
        """
        competitor = opp.get("meta", {}).get("competitor_name", "")
        
        opp["action_template"] = {
            "type": "competitor_response",
            "competitor": competitor,
            "content_suggestions": [
                f"Create '{competitor} alternative' landing page",
                f"Write 'vs {competitor}' comparison blog",
                f"Create migration guide from {competitor}",
                "Update pricing comparison page"
            ],
            "steps": [
                f"1. Analyze {competitor}'s recent update/mention",
                "2. Identify differentiation points",
                "3. Create comparison content (factual, not negative)",
                "4. Highlight unique value propositions",
                "5. Add customer success stories",
                "6. Include pricing comparison if relevant"
            ],
            "tone": "professional, factual, helpful",
            "avoid": ["Being negative", "False claims", "Direct attacks"]
        }
        
        # High priority if competitor is gaining traction
        if opp.get("meta", {}).get("urgency") == "high":
            opp["priority"] = "high"
        else:
            opp["priority"] = "medium"
        
        return opp
    
    def _rule_complaint(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rule 4: Complaints → suggest targeted campaign/outreach
        """
        platform = opp.get("meta", {}).get("platform", "")
        
        opp["action_template"] = {
            "type": "complaint_response",
            "content_suggestions": [
                "Respond empathetically to complaint",
                "Create targeted landing page addressing pain point",
                "Launch email campaign to similar users",
                "Create comparison content highlighting solution"
            ],
            "steps": [
                "1. Understand the specific complaint/pain point",
                "2. Craft empathetic response",
                "3. Position your solution as alternative (not attacking competitor)",
                "4. Offer free trial or demo",
                "5. Follow up with targeted content"
            ],
            "tone": "empathetic, solution-focused, helpful",
            "response_timing": "Within 24 hours for maximum impact"
        }
        
        opp["priority"] = "high"  # Complaints are time-sensitive
        
        return opp
    
    def _rule_forum_discussion(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general forum discussions"""
        opp["action_template"] = {
            "type": "forum_engagement",
            "steps": [
                "1. Read the full discussion thread",
                "2. Provide valuable insights",
                "3. Share relevant experience",
                "4. Subtly mention your tool if relevant",
                "5. Build relationships, not just pitch"
            ]
        }
        
        opp["priority"] = "medium"
        
        return opp
    
    def _rule_content_gap(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """Handle content gap opportunities"""
        opp["action_template"] = {
            "type": "content_creation",
            "content_suggestions": [
                "Create blog post",
                "Create tutorial video",
                "Create guide/documentation"
            ],
            "steps": [
                "1. Validate the content gap",
                "2. Research what exists",
                "3. Create comprehensive content",
                "4. Optimize for SEO",
                "5. Promote across channels"
            ]
        }
        
        opp["priority"] = "medium"
        
        return opp
    
    def _rule_default(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """Default rule for unknown types"""
        opp["action_template"] = {
            "type": "general",
            "steps": [
                "1. Analyze the opportunity",
                "2. Determine best response strategy",
                "3. Create relevant content",
                "4. Engage with the community"
            ]
        }
        
        opp["priority"] = "low"
        
        return opp
    
    def _get_platform_tone(self, platform: str) -> str:
        """Get appropriate tone for each platform"""
        tones = {
            "reddit": "casual, conversational, community-focused",
            "quora": "professional, detailed, expert",
            "twitter": "concise, engaging, conversational",
            "linkedin": "professional, thoughtful, business-focused",
            "youtube": "friendly, educational, engaging",
            "facebook": "conversational, community-focused"
        }
        
        return tones.get(platform.lower(), "professional, helpful")
