from scrapers.base_scraper import BaseScraper
from typing import List, Dict, Any
import httpx
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CompetitorScraper(BaseScraper):
    """Monitors competitor websites for updates, blog posts, and product changes"""
    
    def __init__(self, channel_id: str, competitors: List[str]):
        super().__init__(channel_id, "Competitor Monitor")
        self.competitors = competitors
    
    async def scrape(self) -> List[Dict[str, Any]]:
        signals = []
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for competitor in self.competitors:
                try:
                    # Try to find blog/news pages
                    blog_urls = [
                        f"https://{competitor}/blog",
                        f"https://blog.{competitor}",
                        f"https://{competitor}/news",
                        f"https://{competitor}/updates",
                        f"https://{competitor}/changelog"
                    ]
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    for blog_url in blog_urls:
                        try:
                            response = await client.get(blog_url, headers=headers, timeout=15.0)
                            if response.status_code == 200:
                                soup = BeautifulSoup(response.text, 'html.parser')
                                
                                # Find article titles and links
                                articles = []
                                
                                # Common patterns for blog posts
                                for tag in ['article', 'div']:
                                    articles.extend(soup.find_all(tag, class_=lambda x: x and any(
                                        keyword in str(x).lower() for keyword in ['post', 'article', 'entry', 'blog']
                                    ))[:5])
                                
                                for article in articles[:3]:  # Limit to 3 per competitor
                                    try:
                                        title_elem = article.find(['h1', 'h2', 'h3', 'a'])
                                        if title_elem:
                                            title = title_elem.get_text(strip=True)
                                            
                                            # Get link
                                            link_elem = article.find('a', href=True)
                                            link = link_elem['href'] if link_elem else blog_url
                                            if link.startswith('/'):
                                                link = f"https://{competitor}{link}"
                                            
                                            # Get snippet
                                            snippet_elem = article.find(['p', 'div'], class_=lambda x: x and 'excerpt' in str(x).lower())
                                            if not snippet_elem:
                                                snippet_elem = article.find('p')
                                            snippet = snippet_elem.get_text(strip=True)[:300] if snippet_elem else ''
                                            
                                            if title:
                                                content = f"Competitor Update: {competitor}\n\n{title}\n\n{snippet}"
                                                
                                                signal = self.create_signal(
                                                    content=content,
                                                    link=link,
                                                    meta={
                                                        "competitor": competitor,
                                                        "platform": "competitor_blog",
                                                        "title": title
                                                    }
                                                )
                                                signals.append(signal)
                                    except Exception as e:
                                        logger.debug(f"Error parsing article: {e}")
                                
                                # If we found articles, no need to try other URLs
                                if articles:
                                    break
                                    
                        except httpx.HTTPError:
                            continue
                    
                    # Also search for recent mentions
                    search_query = f"{competitor} new feature OR update OR launch"
                    google_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}&num=5&tbs=qdr:w"
                    
                    try:
                        response = await client.get(google_url, headers=headers)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            results = soup.find_all('div', class_='g')
                            
                            for result in results[:3]:
                                try:
                                    title_elem = result.find('h3')
                                    link_elem = result.find('a')
                                    snippet_elem = result.find('div', class_='VwiC3b')
                                    
                                    if title_elem and link_elem:
                                        title = title_elem.get_text()
                                        link = link_elem.get('href', '')
                                        snippet = snippet_elem.get_text() if snippet_elem else ''
                                        
                                        content = f"Competitor Mention: {competitor}\n\n{title}\n\n{snippet}"
                                        
                                        signal = self.create_signal(
                                            content=content,
                                            link=link,
                                            meta={
                                                "competitor": competitor,
                                                "platform": "competitor_mention"
                                            }
                                        )
                                        signals.append(signal)
                                except Exception as e:
                                    logger.debug(f"Error parsing search result: {e}")
                    except Exception as e:
                        logger.debug(f"Error searching for competitor mentions: {e}")
                    
                    import asyncio
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Competitor scraping error for '{competitor}': {e}")
        
        return signals
