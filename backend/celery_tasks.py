from celery_app import celery_app
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from scrapers import (
    RedditScraper, HackerNewsScraper, ProductHuntScraper, GoogleTrendsScraper, 
    ExaResearchScraper, QuoraScraper, TwitterScraper, LinkedInScraper, 
    YouTubeScraper, CompetitorScraper, FacebookScraper
)
from agents import OrchestratorAgent
from models import RawSignal, Opportunity, OpportunityStatus, Recommendation
import logging
import asyncio
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


def get_async_db():
    """Get database connection for Celery tasks"""
    client = AsyncIOMotorClient(settings.MONGO_URL)
    return client[settings.DB_NAME]


async def async_run_hourly_scan():
    """Async implementation of hourly scan"""
    db = get_async_db()
    
    try:
        logger.info("=== Starting hourly traffic scan ===")
        
        # Initialize scrapers
        channel_configs = await db.channels.find({"is_active": True}, {"_id": 0}).to_list(100)
        
        # If no channels configured, create defaults
        if not channel_configs:
            logger.info("Creating default channel configurations")
            default_channels = [
                {"id": str(uuid.uuid4()), "name": "Reddit", "type": "reddit", "config": {"keywords": settings.REDDIT_KEYWORDS}, "is_active": True},
                {"id": str(uuid.uuid4()), "name": "HackerNews", "type": "hacker_news", "config": {"keywords": settings.REDDIT_KEYWORDS[:3]}, "is_active": True},
                {"id": str(uuid.uuid4()), "name": "ProductHunt", "type": "product_hunt", "config": {}, "is_active": True},
                {"id": str(uuid.uuid4()), "name": "GoogleTrends", "type": "google_trends", "config": {"topics": ["email verification", "b2b leads"]}, "is_active": True},
                {"id": str(uuid.uuid4()), "name": "ExaResearch", "type": "exa", "config": {"topics": ["email verification tools", "B2B lead generation 2025"]}, "is_active": True},
                {"id": str(uuid.uuid4()), "name": "Quora", "type": "quora", "config": {"keywords": settings.QUORA_KEYWORDS}, "is_active": True},
                {"id": str(uuid.uuid4()), "name": "Twitter", "type": "twitter", "config": {"keywords": settings.REDDIT_KEYWORDS[:5]}, "is_active": True},
                {"id": str(uuid.uuid4()), "name": "LinkedIn", "type": "linkedin", "config": {"keywords": settings.REDDIT_KEYWORDS[:4]}, "is_active": True},
                {"id": str(uuid.uuid4()), "name": "YouTube", "type": "youtube", "config": {"keywords": settings.REDDIT_KEYWORDS[:3]}, "is_active": True},
                {"id": str(uuid.uuid4()), "name": "Competitor Monitor", "type": "competitor", "config": {"competitors": settings.COMPETITORS}, "is_active": True},
                {"id": str(uuid.uuid4()), "name": "Facebook", "type": "facebook", "config": {"keywords": settings.REDDIT_KEYWORDS[:4]}, "is_active": True},
            ]
            await db.channels.insert_many(default_channels)
            channel_configs = default_channels
        
        # Run scrapers
        all_signals = []
        for channel in channel_configs:
            try:
                channel_type = channel["type"]
                channel_id = channel["id"]
                config = channel.get("config", {})
                
                scraper = None
                if channel_type == "reddit":
                    scraper = RedditScraper(channel_id, config.get("keywords", settings.REDDIT_KEYWORDS))
                elif channel_type == "hacker_news":
                    scraper = HackerNewsScraper(channel_id, config.get("keywords", settings.REDDIT_KEYWORDS[:3]))
                elif channel_type == "product_hunt":
                    scraper = ProductHuntScraper(channel_id)
                elif channel_type == "google_trends":
                    scraper = GoogleTrendsScraper(channel_id, config.get("topics", ["email verification"]))
                elif channel_type == "exa":
                    scraper = ExaResearchScraper(channel_id, config.get("topics", ["email verification"]))
                elif channel_type == "quora":
                    scraper = QuoraScraper(channel_id, config.get("keywords", settings.QUORA_KEYWORDS))
                elif channel_type == "twitter":
                    scraper = TwitterScraper(channel_id, config.get("keywords", settings.REDDIT_KEYWORDS[:5]))
                elif channel_type == "linkedin":
                    scraper = LinkedInScraper(channel_id, config.get("keywords", settings.REDDIT_KEYWORDS[:4]))
                elif channel_type == "youtube":
                    scraper = YouTubeScraper(channel_id, config.get("keywords", settings.REDDIT_KEYWORDS[:3]))
                elif channel_type == "competitor":
                    scraper = CompetitorScraper(channel_id, config.get("competitors", settings.COMPETITORS))
                elif channel_type == "facebook":
                    scraper = FacebookScraper(channel_id, config.get("keywords", settings.REDDIT_KEYWORDS[:4]))
                
                if scraper:
                    signals = await scraper.run()
                    all_signals.extend(signals)
                    
            except Exception as e:
                logger.error(f"Scraper error for channel {channel.get('name')}: {e}")
        
        logger.info(f"Total signals collected: {len(all_signals)}")
        
        # Store raw signals
        if all_signals:
            # Add IDs to signals
            for signal in all_signals:
                signal["id"] = str(uuid.uuid4())
            
            await db.raw_signals.insert_many(all_signals)
            logger.info(f"Stored {len(all_signals)} raw signals")
        
        # Process signals with Orchestrator
        orchestrator = OrchestratorAgent()
        results = await orchestrator.batch_process_signals(all_signals)
        
        # Store opportunities
        opportunities = []
        for result in results:
            if result.get("status") == "success" and result.get("opportunity"):
                opp = result["opportunity"]
                opp["id"] = str(uuid.uuid4())
                opp["created_at"] = datetime.now(timezone.utc).isoformat()
                opp["status"] = OpportunityStatus.PENDING.value
                opportunities.append(opp)
        
        if opportunities:
            await db.opportunities.insert_many(opportunities)
            logger.info(f"Created {len(opportunities)} opportunities")
        
        # Create recommendations for users
        await create_user_recommendations(db, opportunities)
        
        logger.info("=== Hourly traffic scan completed ===")
        
    except Exception as e:
        logger.error(f"Hourly scan error: {e}", exc_info=True)
    finally:
        # Close database connection
        db.client.close()


async def create_user_recommendations(db, opportunities: list):
    """Create personalized recommendations for users based on their plan"""
    try:
        # Get all active users
        users = await db.users.find({"is_active": True}, {"_id": 0}).to_list(1000)
        
        for user in users:
            user_id = user["id"]
            plan = user.get("plan", "free")
            
            # Filter opportunities based on plan
            if plan == "free":
                # Free users get top 5 opportunities per day
                user_opportunities = sorted(opportunities, key=lambda x: x["score"], reverse=True)[:5]
            else:
                # Pro users get top 20
                user_opportunities = sorted(opportunities, key=lambda x: x["score"], reverse=True)[:20]
            
            # Create recommendations
            recommendations = []
            for opp in user_opportunities:
                rec = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "opportunity_id": opp["id"],
                    "action_text": opp["suggested_action"],
                    "content_template": opp.get("content_template"),
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "completed_at": None
                }
                recommendations.append(rec)
            
            if recommendations:
                # Remove old pending recommendations (older than 7 days)
                seven_days_ago = datetime.now(timezone.utc).timestamp() - (7 * 24 * 60 * 60)
                await db.recommendations.delete_many({
                    "user_id": user_id,
                    "status": "pending",
                    "created_at": {"$lt": datetime.fromtimestamp(seven_days_ago, tz=timezone.utc).isoformat()}
                })
                
                # Insert new recommendations
                await db.recommendations.insert_many(recommendations)
                logger.info(f"Created {len(recommendations)} recommendations for user {user_id}")
    
    except Exception as e:
        logger.error(f"Error creating recommendations: {e}")


@celery_app.task(name="celery_tasks.run_hourly_scan")
def run_hourly_scan():
    """Celery task wrapper for async hourly scan"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(async_run_hourly_scan())
    finally:
        loop.close()
    return {"status": "completed"}
