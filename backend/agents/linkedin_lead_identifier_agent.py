from agents.base_agent import BaseAgent
from typing import Dict, Any, List, Optional
import logging
import json
import re

logger = logging.getLogger(__name__)


class LinkedInLeadIdentifierAgent(BaseAgent):
    """
    Specialized agent for identifying potential leads from LinkedIn post comments.
    Analyzes comments to find people who might need the user's product/service.
    """
    
    def __init__(self):
        super().__init__(
            name="LinkedInLeadIdentifierAgent",
            model="llama-3.3-70b-versatile"
        )
        
        self.system_prompt = """You are a B2B lead qualification expert specialized in analyzing LinkedIn posts and comments to identify potential customers.

Your task is to analyze either:
1. POST AUTHORS - Determine if the person posting has a need/problem that the product solves
2. COMMENTERS - Determine if the commenter is expressing interest/need

For each person, provide:
1. lead_qualified: boolean - Is this a qualified lead?
2. quality_score: number (0-100) - How likely are they to be interested?
3. need_identified: string - What specific need/problem did you identify?
4. reason_qualified: string - Why is this person a qualified lead?
5. suggested_approach: string - How should they be approached?
6. confidence: string - "high", "medium", or "low"
7. lead_source: string - "post_author" or "commenter"

QUALIFICATION CRITERIA:
✅ Expressing a problem/need that the product solves
✅ Asking questions about solutions in this space
✅ Showing interest in similar products/services
✅ Demonstrating authority/decision-making power (job title, company)
✅ Budget indicators ("looking to buy", "need a solution", "willing to pay")
✅ Urgency signals ("ASAP", "urgent", "need quickly")
✅ Intent signals ("recommendations?", "which tool?", "best option?")
✅ Pain point mentions (complaints, frustrations, challenges)
✅ Research behavior (comparing options, asking for advice)

DISQUALIFICATION SIGNS:
❌ Generic comments ("Great post!", "Thanks for sharing")
❌ Spam or promotional comments
❌ Comments from competitors
❌ Clearly irrelevant to the product
❌ Students or job seekers (unless target customer)

Respond in JSON format only."""
    
    async def analyze_comment(
        self, 
        comment_data: Dict[str, Any], 
        post_context: Dict[str, Any],
        user_keywords: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a single comment to determine if it's a qualified lead
        
        Args:
            comment_data: Comment text, author info, etc.
            post_context: Context about the post
            user_keywords: Keywords related to user's product
        
        Returns:
            Lead analysis result or None if not qualified
        """
        try:
            comment_text = comment_data.get("text", "")
            author_name = comment_data.get("author", {}).get("name", "Unknown")
            author_url = comment_data.get("author", {}).get("url", "")
            
            if not comment_text or len(comment_text) < 20:  # Skip very short comments
                return None
            
            # Build analysis prompt
            user_prompt = f"""
PRODUCT/SERVICE KEYWORDS: {', '.join(user_keywords)}

POST CONTEXT:
Title: {post_context.get('title', 'N/A')}
Content: {post_context.get('content', '')[:300]}...

COMMENT TO ANALYZE:
Author: {author_name}
Comment: {comment_text}

Analyze this comment and determine if this person is a potential lead based on the product keywords.
Provide a detailed JSON response with lead qualification analysis.
"""
            
            # Call LLM for analysis
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self._call_llm_with_retry(messages)
            
            if not response:
                return None
            
            # Parse JSON response
            result = self._extract_json(response)
            
            if result and result.get("lead_qualified", False):
                # Add original comment data
                result["comment_text"] = comment_text
                result["author_name"] = author_name
                result["linkedin_url"] = author_url or self._extract_linkedin_url(comment_text)
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing comment: {e}")
            return None
    
    async def analyze_post_comments(
        self,
        post_data: Dict[str, Any],
        comments: List[Dict[str, Any]],
        user_keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Analyze all comments on a post to identify leads
        
        Args:
            post_data: Post information
            comments: List of comments on the post
            user_keywords: User's product keywords
        
        Returns:
            List of qualified leads
        """
        qualified_leads = []
        
        if not comments:
            return qualified_leads
        
        logger.info(f"Analyzing {len(comments)} comments for potential leads")
        
        post_context = {
            "title": post_data.get("title", ""),
            "content": post_data.get("content", ""),
            "url": post_data.get("url", "")
        }
        
        for comment in comments:
            try:
                lead_analysis = await self.analyze_comment(
                    comment,
                    post_context,
                    user_keywords
                )
                
                if lead_analysis:
                    # Add post context to lead
                    lead_analysis["post_url"] = post_context["url"]
                    lead_analysis["post_content"] = post_context["content"][:500]
                    qualified_leads.append(lead_analysis)
                    
            except Exception as e:
                logger.error(f"Error processing comment: {e}")
                continue
        
        logger.info(f"Found {len(qualified_leads)} qualified leads from {len(comments)} comments")
        return qualified_leads
    
    async def batch_analyze_posts(
        self,
        posts_with_comments: List[Dict[str, Any]],
        user_keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple posts and their comments
        
        Args:
            posts_with_comments: List of posts, each containing comments
            user_keywords: User's product keywords
        
        Returns:
            List of all qualified leads
        """
        all_leads = []
        
        for post in posts_with_comments:
            post_data = post.get("post", {})
            comments = post.get("comments", [])
            
            leads = await self.analyze_post_comments(
                post_data,
                comments,
                user_keywords
            )
            
            all_leads.extend(leads)
        
        return all_leads
    
    def _extract_linkedin_url(self, text: str) -> Optional[str]:
        """Extract LinkedIn profile URL from text"""
        # Common LinkedIn URL patterns
        patterns = [
            r'linkedin\.com/in/[\w-]+',
            r'linkedin\.com/company/[\w-]+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return f"https://{match.group(0)}"
        
        return None
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response"""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            # If no JSON found, try parsing the whole response
            return json.loads(text)
        except Exception as e:
            logger.error(f"Error extracting JSON: {e}")
            return None
    
    def calculate_quality_score(self, score: float) -> str:
        """Convert numeric score to quality category"""
        if score >= 80:
            return "hot"
        elif score >= 60:
            return "warm"
        elif score >= 40:
            return "cold"
        else:
            return "unqualified"
