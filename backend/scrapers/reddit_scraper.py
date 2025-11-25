from scrapers.base_scraper import BaseScraper
from typing import List, Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)


class RedditScraper(BaseScraper):
    """Scrapes Reddit using public API"""
    
    def __init__(self, channel_id: str, keywords: List[str]):
        super().__init__(channel_id, "Reddit")
        self.keywords = keywords
        self.base_url = "https://www.reddit.com"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        signals = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for keyword in self.keywords:
                try:
                    # Use Reddit's JSON API
                    url = f"{self.base_url}/search.json"
                    params = {
                        "q": keyword,
                        "sort": "new",
                        "limit": 25,
                        "t": "day"  # Last 24 hours
                    }
                    
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        posts = data.get("data", {}).get("children", [])
                        
                        for post in posts:
                            post_data = post.get("data", {})
                            title = post_data.get("title", "")
                            selftext = post_data.get("selftext", "")
                            url_link = f"{self.base_url}{post_data.get('permalink', '')}"
                            upvotes = post_data.get("ups", 0)
                            
                            content = f"{title}\n\n{selftext}"
                            
                            signal = self.create_signal(
                                content=content,
                                link=url_link,
                                meta={
                                    "keyword": keyword,
                                    "upvotes": upvotes,
                                    "subreddit": post_data.get("subreddit", "")
                                }
                            )
                            signals.append(signal)
                    
                    # Rate limiting
                    import asyncio
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Reddit scraping error for keyword '{keyword}': {e}")
        
        return signals
