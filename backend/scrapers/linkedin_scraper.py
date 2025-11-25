from scrapers.base_scraper import BaseScraper
from typing import List, Dict, Any
import httpx
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """Scrapes LinkedIn posts and discussions"""
    
    def __init__(self, channel_id: str, keywords: List[str]):
        super().__init__(channel_id, "LinkedIn")
        self.keywords = keywords
    
    async def scrape(self) -> List[Dict[str, Any]]:
        signals = []
        
        # Note: LinkedIn requires authentication for direct scraping
        # Using Google search as workaround
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for keyword in self.keywords:
                try:
                    search_query = f"site:linkedin.com/posts {keyword}"
                    google_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}&num=10"
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    response = await client.get(google_url, headers=headers)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        results = soup.find_all('div', class_='g')
                        
                        for result in results[:8]:
                            try:
                                title_elem = result.find('h3')
                                link_elem = result.find('a')
                                snippet_elem = result.find('div', class_='VwiC3b')
                                
                                if title_elem and link_elem:
                                    title = title_elem.get_text()
                                    link = link_elem.get('href', '')
                                    snippet = snippet_elem.get_text() if snippet_elem else ''
                                    
                                    content = f"{title}\n\n{snippet}"
                                    
                                    signal = self.create_signal(
                                        content=content,
                                        link=link,
                                        meta={
                                            "keyword": keyword,
                                            "platform": "linkedin"
                                        }
                                    )
                                    signals.append(signal)
                            except Exception as e:
                                logger.debug(f"Error parsing LinkedIn result: {e}")
                    
                    import asyncio
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"LinkedIn scraping error for keyword '{keyword}': {e}")
        
        return signals
