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
    
    async def analyze_post_author(
        self,
        post_data: Dict[str, Any],
        product_profile: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze post author to determine if they're a potential lead
        
        Args:
            post_data: Post content and author info
            product_profile: User's product profile for context
        
        Returns:
            Lead analysis result or None if not qualified
        """
        try:
            post_content = post_data.get("content", "")
            author = post_data.get("author", {})
            author_name = author.get("name", "Unknown")
            author_url = author.get("url", "")
            author_headline = author.get("headline", "")
            
            if not post_content or len(post_content) < 50:
                return None
            
            # Build product context
            product_name = product_profile.get("product_name", "our product")
            product_desc = product_profile.get("product_description", "")
            target_customer = product_profile.get("target_customer_profile", "")
            problems_solved = product_profile.get("key_problems_solved", [])
            buying_signals = product_profile.get("buying_signals", [])
            
            # Build analysis prompt
            user_prompt = f"""
PRODUCT INFORMATION:
Name: {product_name}
Description: {product_desc}
Target Customers: {target_customer}
Problems Solved: {', '.join(problems_solved)}
Buying Signals: {', '.join(buying_signals)}

POST AUTHOR TO ANALYZE:
Name: {author_name}
Headline: {author_headline}
Post Content: {post_content}

Task: Analyze if this post author is expressing a need/problem that {product_name} solves.
Consider: Are they asking for solutions? Complaining about a problem? Looking for recommendations?

Provide JSON response with lead qualification analysis. Set lead_source to "post_author".
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
                # Add original data
                result["comment_text"] = post_content  # Store post as "comment_text" for consistency
                result["author_name"] = author_name
                result["linkedin_url"] = author_url or self._extract_linkedin_url(post_content)
                result["author_headline"] = author_headline
                result["lead_source"] = "post_author"
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing post author: {e}")
            return None
    
    async def analyze_comment(
        self, 
        comment_data: Dict[str, Any], 
        post_context: Dict[str, Any],
        product_profile: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a single comment to determine if it's a qualified lead
        
        Args:
            comment_data: Comment text, author info, etc.
            post_context: Context about the post
            product_profile: User's product profile for context
        
        Returns:
            Lead analysis result or None if not qualified
        """
        try:
            comment_text = comment_data.get("text", "")
            author = comment_data.get("author", {})
            author_name = author.get("name", "Unknown")
            author_url = author.get("url", "")
            author_headline = author.get("headline", "")
            
            if not comment_text or len(comment_text) < 20:  # Skip very short comments
                return None
            
            # Build product context
            product_name = product_profile.get("product_name", "our product")
            product_desc = product_profile.get("product_description", "")
            target_customer = product_profile.get("target_customer_profile", "")
            problems_solved = product_profile.get("key_problems_solved", [])
            buying_signals = product_profile.get("buying_signals", [])
            
            # Build analysis prompt
            user_prompt = f"""
PRODUCT INFORMATION:
Name: {product_name}
Description: {product_desc}
Target Customers: {target_customer}
Problems Solved: {', '.join(problems_solved)}
Buying Signals: {', '.join(buying_signals)}

POST CONTEXT:
Title: {post_context.get('title', 'N/A')}
Content: {post_context.get('content', '')[:300]}...

COMMENT TO ANALYZE:
Author: {author_name}
Headline: {author_headline}
Comment: {comment_text}

Task: Analyze if this commenter is expressing interest/need that {product_name} addresses.
Provide JSON response with lead qualification analysis. Set lead_source to "commenter".
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
                result["author_headline"] = author_headline
                result["lead_source"] = "commenter"
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing comment: {e}")
            return None
    
    async def analyze_post_and_comments(
        self,
        post_data: Dict[str, Any],
        comments: List[Dict[str, Any]],
        product_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze post author AND comments to identify leads
        
        Args:
            post_data: Post information including author
            comments: List of comments on the post
            product_profile: User's product profile
        
        Returns:
            List of qualified leads (from both post author and comments)
        """
        qualified_leads = []
        
        post_url = post_data.get("url", "")
        post_content = post_data.get("content", "")
        
        # 1. Analyze post author as potential lead
        try:
            author_lead = await self.analyze_post_author(post_data, product_profile)
            if author_lead:
                author_lead["post_url"] = post_url
                author_lead["post_content"] = post_content[:500]
                qualified_leads.append(author_lead)
                logger.info(f"Qualified lead from post author: {author_lead.get('author_name')}")
        except Exception as e:
            logger.error(f"Error analyzing post author: {e}")
        
        # 2. Analyze comments for leads
        if not comments:
            return qualified_leads
        
        logger.info(f"Analyzing {len(comments)} comments for potential leads")
        
        post_context = {
            "title": post_data.get("title", ""),
            "content": post_content,
            "url": post_url
        }
        
        for comment in comments:
            try:
                lead_analysis = await self.analyze_comment(
                    comment,
                    post_context,
                    product_profile
                )
                
                if lead_analysis:
                    # Add post context to lead
                    lead_analysis["post_url"] = post_url
                    lead_analysis["post_content"] = post_content[:500]
                    qualified_leads.append(lead_analysis)
                    
            except Exception as e:
                logger.error(f"Error processing comment: {e}")
                continue
        
        logger.info(f"Found {len(qualified_leads)} qualified leads from post and comments")
        return qualified_leads
    
    async def batch_analyze_posts(
        self,
        posts_with_comments: List[Dict[str, Any]],
        product_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple posts and their comments for leads
        
        Args:
            posts_with_comments: List of posts, each containing comments
            product_profile: User's product profile
        
        Returns:
            List of all qualified leads (from both post authors and commenters)
        """
        all_leads = []
        
        for post in posts_with_comments:
            post_data = post.get("post", {})
            comments = post.get("comments", [])
            
            leads = await self.analyze_post_and_comments(
                post_data,
                comments,
                product_profile
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
