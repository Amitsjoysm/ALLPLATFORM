from scrapers.base_scraper import BaseScraper
from typing import List, Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)


class HackerNewsScraper(BaseScraper):
    """Scrapes Hacker News using official API"""
    
    def __init__(self, channel_id: str, keywords: List[str]):
        super().__init__(channel_id, "HackerNews")
        self.keywords = keywords
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.algolia_url = "https://hn.algolia.com/api/v1"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        signals = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for keyword in self.keywords:
                try:
                    # Use Algolia API for search
                    url = f"{self.algolia_url}/search"
                    params = {
                        "query": keyword,
                        "tags": "story",
                        "numericFilters": "created_at_i>" + str(int((datetime.now(timezone.utc).timestamp() - 86400)))  # Last 24 hours
                    }
                    
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        hits = data.get("hits", [])
                        
                        for hit in hits[:20]:  # Limit to 20 per keyword
                            title = hit.get("title", "")
                            url_link = hit.get("url", "")
                            story_text = hit.get("story_text", "")
                            points = hit.get("points", 0)
                            
                            content = f"{title}\n\n{story_text}"
                            
                            signal = self.create_signal(
                                content=content,
                                link=url_link or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                                meta={
                                    "keyword": keyword,
                                    "points": points,
                                    "num_comments": hit.get("num_comments", 0)
                                }
                            )
                            signals.append(signal)
                    
                    import asyncio
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"HackerNews scraping error for keyword '{keyword}': {e}")
        
        return signals


from datetime import datetime, timezone
