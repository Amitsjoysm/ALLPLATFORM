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
    
    async def scrape_with_key(self, api_key: str, key_id: str, keyword: str) -> List[Dict[str, Any]]:
        """Scrape LinkedIn posts using a specific API key"""
        signals = []
        
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
                            author = post.get("author", {})
                            author_name = author.get("name", "Unknown") if isinstance(author, dict) else str(author)
                            
                            # Combine title and content
                            content = f"LinkedIn Post by {author_name}\n\n{post_text[:500]}"
                            
                            signal = self.create_signal(
                                content=content,
                                link=post_url,
                                meta={
                                    "keyword": keyword,
                                    "platform": "linkedin_rapidapi",
                                    "author": author_name,
                                    "source": "rapidapi"
                                }
                            )
                            signals.append(signal)
                        except Exception as e:
                            logger.debug(f"Error parsing LinkedIn post: {e}")
                    
                elif response.status_code == 429:
                    logger.warning(f"Rate limit hit for API key {key_id}")
                    # Could mark this key as temporarily unavailable
                else:
                    logger.error(f"LinkedIn RapidAPI returned status {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error scraping LinkedIn with RapidAPI for keyword '{keyword}': {e}")
        
        return signals
    
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
            
            signals = await self.scrape_with_key(
                current_key["api_key"],
                current_key["id"],
                keyword
            )
            all_signals.extend(signals)
            
            # Rate limiting - wait between requests
            await asyncio.sleep(2)
        
        logger.info(f"LinkedIn RapidAPI scraper found {len(all_signals)} signals")
        return all_signals
