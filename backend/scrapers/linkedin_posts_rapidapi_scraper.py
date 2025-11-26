from scrapers.base_scraper import BaseScraper
from typing import List, Dict, Any, Optional
import httpx
import logging
from database import get_database
import asyncio

logger = logging.getLogger(__name__)


class LinkedInPostsRapidAPIScraper(BaseScraper):
    """Scrapes LinkedIn posts using RapidAPI"""
    
    def __init__(self, channel_id: str, keywords: List[str]):
        super().__init__(channel_id, "LinkedIn Posts (RapidAPI)")
        self.keywords = keywords
        self.api_url = "https://linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com/posts/search"
        self.comments_api_url = "https://linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com/post/comments"
        self.api_host = "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
    
    async def get_active_api_keys(self) -> List[Dict[str, Any]]:
        """Fetch active RapidAPI keys from database"""
        try:
            db = get_database()
            keys = await db.rapidapi_keys.find(
                {"is_active": True},
                {"_id": 0}
            ).sort("usage_count", 1).to_list(None)  # Sort by usage count (least used first)
            
            return keys
        except Exception as e:
            logger.error(f"Error fetching RapidAPI keys: {e}")
            return []
    
    async def update_key_usage(self, key_id: str):
        """Update usage statistics for an API key"""
        try:
            from datetime import datetime, timezone
            db = get_database()
            await db.rapidapi_keys.update_one(
                {"id": key_id},
                {
                    "$inc": {"usage_count": 1},
                    "$set": {"last_used": datetime.now(timezone.utc).isoformat()}
                }
            )
        except Exception as e:
            logger.error(f"Error updating key usage: {e}")
    
    async def fetch_post_comments(self, post_url: str, api_key: str, max_comments: int = 20) -> List[Dict[str, Any]]:
        """Fetch comments for a specific post"""
        try:
            headers = {
                "x-rapidapi-key": api_key,
                "x-rapidapi-host": self.api_host
            }
            
            params = {
                "post_url": post_url,
                "sort_order": "Most relevant"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.comments_api_url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    comments_data = data.get("data", []) if isinstance(data, dict) else []
                    
                    comments = []
                    for comment in comments_data[:max_comments]:
                        try:
                            comments.append({
                                "text": comment.get("text", "") or comment.get("comment", ""),
                                "author": {
                                    "name": comment.get("author", {}).get("name", "Unknown"),
                                    "url": comment.get("author", {}).get("profile_url", "") or comment.get("author", {}).get("url", ""),
                                    "headline": comment.get("author", {}).get("headline", "")
                                },
                                "timestamp": comment.get("created_at", "") or comment.get("timestamp", "")
                            })
                        except Exception as e:
                            logger.debug(f"Error parsing comment: {e}")
                    
                    return comments
                    
        except Exception as e:
            logger.debug(f"Error fetching comments for post {post_urn}: {e}")
        
        return []
    
    async def scrape_with_key(self, api_key: str, key_id: str, keyword: str, fetch_comments: bool = True) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Scrape LinkedIn posts using a specific API key
        
        Returns:
            Tuple of (signals, posts_with_comments)
        """
        signals = []
        posts_with_comments = []
        
        try:
            headers = {
                "x-rapidapi-key": api_key,
                "x-rapidapi-host": self.api_host
            }
            
            params = {
                "keyword": keyword,
                "page_number": "1",
                "sort_type": "date_posted",
                "date_filter": "past-24h"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.api_url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Update key usage
                    await self.update_key_usage(key_id)
                    
                    # Parse the response - adjust based on actual API response structure
                    posts = data.get("data", []) if isinstance(data, dict) else []
                    
                    for post in posts[:10]:  # Limit to 10 posts per keyword
                        try:
                            # Extract post data - adjust field names based on actual API response
                            post_text = post.get("text", "") or post.get("content", "")
                            post_url = post.get("url", "") or post.get("link", "")
                            post_urn = post.get("urn", "") or post.get("post_id", "")
                            author = post.get("author", {})
                            author_name = author.get("name", "Unknown") if isinstance(author, dict) else str(author)
                            author_url = author.get("profile_url", "") or author.get("url", "") if isinstance(author, dict) else ""
                            author_headline = author.get("headline", "") if isinstance(author, dict) else ""
                            
                            # Combine title and content
                            content = f"LinkedIn Post by {author_name}\n\n{post_text[:500]}"
                            
                            signal = self.create_signal(
                                content=content,
                                link=post_url,
                                meta={
                                    "keyword": keyword,
                                    "platform": "linkedin_rapidapi",
                                    "author": author_name,
                                    "source": "rapidapi",
                                    "post_urn": post_urn
                                }
                            )
                            signals.append(signal)
                            
                            # Fetch comments for lead identification
                            comments = []
                            if fetch_comments and post_url:
                                comments = await self.fetch_post_comments(post_url, api_key)
                                await asyncio.sleep(1)  # Rate limiting
                            
                            # Store post with comments for lead identification
                            posts_with_comments.append({
                                "post": {
                                    "title": post_text[:100] if post_text else "",
                                    "content": post_text,
                                    "url": post_url,
                                    "urn": post_urn,
                                    "author": {
                                        "name": author_name,
                                        "url": author_url,
                                        "headline": author_headline
                                    },
                                    "keyword": keyword
                                },
                                "comments": comments
                            })
                            
                        except Exception as e:
                            logger.debug(f"Error parsing LinkedIn post: {e}")
                    
                elif response.status_code == 429:
                    logger.warning(f"Rate limit hit for API key {key_id}")
                    # Could mark this key as temporarily unavailable
                else:
                    logger.error(f"LinkedIn RapidAPI returned status {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error scraping LinkedIn with RapidAPI for keyword '{keyword}': {e}")
        
        return signals, posts_with_comments
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """Main scrape method that uses API key pool"""
        all_signals = []
        
        # Get active API keys
        api_keys = await self.get_active_api_keys()
        
        if not api_keys:
            logger.warning("No active RapidAPI keys found for LinkedIn scraping")
            return []
        
        logger.info(f"Found {len(api_keys)} active RapidAPI keys")
        
        # Use keys in rotation
        key_index = 0
        
        for keyword in self.keywords:
            if not api_keys:
                logger.warning("No API keys available")
                break
            
            # Get next key in rotation
            current_key = api_keys[key_index % len(api_keys)]
            key_index += 1
            
            signals, _ = await self.scrape_with_key(
                current_key["api_key"],
                current_key["id"],
                keyword,
                fetch_comments=False  # Don't fetch comments in regular scrape
            )
            all_signals.extend(signals)
            
            # Rate limiting - wait between requests
            await asyncio.sleep(2)
        
        logger.info(f"LinkedIn RapidAPI scraper found {len(all_signals)} signals")
        return all_signals
    
    async def scrape_with_comments(self) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Scrape LinkedIn posts WITH comments for lead identification
        
        Returns:
            Tuple of (signals, posts_with_comments)
        """
        all_signals = []
        all_posts_with_comments = []
        
        # Get active API keys
        api_keys = await self.get_active_api_keys()
        
        if not api_keys:
            logger.warning("No active RapidAPI keys found for LinkedIn scraping")
            return [], []
        
        logger.info(f"Found {len(api_keys)} active RapidAPI keys for lead scraping")
        
        # Use keys in rotation
        key_index = 0
        
        for keyword in self.keywords:
            if not api_keys:
                logger.warning("No API keys available")
                break
            
            # Get next key in rotation
            current_key = api_keys[key_index % len(api_keys)]
            key_index += 1
            
            signals, posts_with_comments = await self.scrape_with_key(
                current_key["api_key"],
                current_key["id"],
                keyword,
                fetch_comments=True  # Fetch comments for lead identification
            )
            all_signals.extend(signals)
            all_posts_with_comments.extend(posts_with_comments)
            
            # Rate limiting - wait between requests
            await asyncio.sleep(2)
        
        logger.info(f"LinkedIn RapidAPI scraper found {len(all_signals)} signals and {len(all_posts_with_comments)} posts with comments")
        return all_signals, all_posts_with_comments
