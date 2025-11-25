from scrapers.base_scraper import BaseScraper
from typing import List, Dict, Any
import logging
from exa_py import Exa
from config import settings

logger = logging.getLogger(__name__)


class ExaResearchScraper(BaseScraper):
    """Uses Exa.ai for intelligent web research and content discovery"""
    
    def __init__(self, channel_id: str, topics: List[str]):
        super().__init__(channel_id, "ExaResearch")
        self.topics = topics
        self.exa = Exa(api_key=settings.EXA_API_KEY)
    
    async def scrape(self) -> List[Dict[str, Any]]:
        signals = []
        
        for topic in self.topics:
            try:
                # Use Exa for semantic search
                results = self.exa.search_and_contents(
                    topic,
                    type="neural",
                    use_autoprompt=True,
                    num_results=10,
                    text=True
                )
                
                for result in results.results:
                    content = f"{result.title}\n\n{result.text[:500] if result.text else ''}"
                    
                    signal = self.create_signal(
                        content=content,
                        link=result.url,
                        meta={
                            "topic": topic,
                            "score": result.score if hasattr(result, 'score') else 0,
                            "published_date": result.published_date if hasattr(result, 'published_date') else None
                        }
                    )
                    signals.append(signal)
                
                logger.info(f"Exa research found {len(results.results)} results for '{topic}'")
                
                # Rate limiting
                import asyncio
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Exa research error for topic '{topic}': {e}")
        
        return signals
