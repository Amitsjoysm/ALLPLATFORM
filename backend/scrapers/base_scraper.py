from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self, channel_id: str, channel_name: str):
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.signals: List[Dict[str, Any]] = []
    
    @abstractmethod
    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape data from the channel - to be implemented by subclasses"""
        pass
    
    def create_signal(self, content: str, link: str = None, meta: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a standardized signal object"""
        return {
            "channel_id": self.channel_id,
            "content": content,
            "link": link,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "meta": meta or {},
            "processed": False
        }
    
    async def run(self) -> List[Dict[str, Any]]:
        """Run the scraper and return signals"""
        try:
            logger.info(f"Starting scraper: {self.channel_name}")
            signals = await self.scrape()
            logger.info(f"Scraper {self.channel_name} found {len(signals)} signals")
            return signals
        except Exception as e:
            logger.error(f"Scraper {self.channel_name} failed: {str(e)}")
            return []
