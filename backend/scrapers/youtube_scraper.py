from scrapers.base_scraper import BaseScraper
from typing import List, Dict, Any
import httpx
import logging
from bs4 import BeautifulSoup
import json
import re

logger = logging.getLogger(__name__)


class YouTubeScraper(BaseScraper):
    """Scrapes YouTube for new videos and discussions"""
    
    def __init__(self, channel_id: str, keywords: List[str]):
        super().__init__(channel_id, "YouTube")
        self.keywords = keywords
    
    async def scrape(self) -> List[Dict[str, Any]]:
        signals = []
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for keyword in self.keywords:
                try:
                    # YouTube search URL
                    search_url = f"https://www.youtube.com/results?search_query={keyword.replace(' ', '+')}&sp=CAISAhAB"
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    response = await client.get(search_url, headers=headers)
                    if response.status_code == 200:
                        # Extract video data from page
                        content = response.text
                        
                        # Find ytInitialData JSON
                        match = re.search(r'var ytInitialData = ({.*?});', content)
                        if match:
                            try:
                                data = json.loads(match.group(1))
                                
                                # Navigate through the complex YouTube data structure
                                contents = (data.get('contents', {})
                                           .get('twoColumnSearchResultsRenderer', {})
                                           .get('primaryContents', {})
                                           .get('sectionListRenderer', {})
                                           .get('contents', []))
                                
                                for section in contents:
                                    items = section.get('itemSectionRenderer', {}).get('contents', [])
                                    
                                    for item in items[:10]:
                                        video = item.get('videoRenderer', {})
                                        if video:
                                            video_id = video.get('videoId', '')
                                            title = video.get('title', {}).get('runs', [{}])[0].get('text', '')
                                            
                                            # Get description/snippet
                                            description_snippets = video.get('detailedMetadataSnippets', [{}])
                                            description = ''
                                            if description_snippets:
                                                snippet_runs = description_snippets[0].get('snippetText', {}).get('runs', [])
                                                description = ' '.join([r.get('text', '') for r in snippet_runs])
                                            
                                            if not description:
                                                description = video.get('descriptionSnippet', {}).get('runs', [{}])[0].get('text', '')
                                            
                                            views = video.get('viewCountText', {}).get('simpleText', '0 views')
                                            
                                            if title:
                                                content_text = f"{title}\n\n{description}\n\nViews: {views}"
                                                link = f"https://www.youtube.com/watch?v={video_id}"
                                                
                                                signal = self.create_signal(
                                                    content=content_text,
                                                    link=link,
                                                    meta={
                                                        "keyword": keyword,
                                                        "platform": "youtube",
                                                        "video_id": video_id,
                                                        "views": views
                                                    }
                                                )
                                                signals.append(signal)
                            except Exception as e:
                                logger.debug(f"Error parsing YouTube JSON: {e}")
                    
                    import asyncio
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"YouTube scraping error for keyword '{keyword}': {e}")
        
        return signals
