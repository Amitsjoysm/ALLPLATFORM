from agents.base_agent import BaseAgent
from agents.classifier_agent import ClassifierAgent
from agents.content_generator_agent import ContentGeneratorAgent
from typing import Dict, Any, List
import logging
import asyncio

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Orchestrates multiple specialized agents and manages workflow"""
    
    def __init__(self):
        super().__init__(name="OrchestratorAgent", model="llama-3.3-70b-versatile")
        self.classifier = ClassifierAgent()
        self.content_generator = ContentGeneratorAgent()
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        
        # Platform-specific agents - lazy initialization
        self._platform_agents = {}
    
    async def assign_task(self, task_id: str, task_type: str, task_data: Dict[str, Any]):
        """Assign task to appropriate agent"""
        self.active_tasks[task_id] = {
            "type": task_type,
            "status": "assigned",
            "data": task_data,
            "result": None
        }
        
        logger.info(f"Task {task_id} assigned: {task_type}")
    
    async def check_task_completion(self, task_id: str) -> Dict[str, Any]:
        """Check if task is completed"""
        return self.active_tasks.get(task_id, {"status": "not_found"})
    
    async def process_signal_pipeline(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete pipeline: classify signal -> generate content -> return opportunity"""
        try:
            # Step 1: Classify signal
            logger.info(f"Orchestrator: Classifying signal {signal_data.get('id', 'unknown')}")
            classification = await self.classifier.process(signal_data)
            
            # Check if relevant
            if not classification.get("is_relevant", False):
                logger.info(f"Signal not relevant, skipping")
                return {"status": "skipped", "reason": "not_relevant"}
            
            # Step 2: Calculate opportunity score
            score = self.calculate_score(classification)
            
            # Step 3: Generate content if score is high enough
            content_template = None
            if score >= 50:  # Only generate content for high-value opportunities
                logger.info(f"Generating content for high-value opportunity (score: {score})")
                opportunity_data = {
                    "type": classification["opportunity_type"],
                    "content": signal_data.get("content", ""),
                    "suggested_action": classification["suggested_action"]
                }
                content_template = await self.content_generator.process(opportunity_data)
            
            # Compile opportunity
            opportunity = {
                "raw_signal_id": signal_data.get("id"),
                "channel_id": signal_data.get("channel_id"),
                "score": score,
                "type": classification["opportunity_type"],
                "difficulty": 6 - classification.get("competition_level", 3),  # Inverse of competition
                "relevance": classification["relevance_score"],
                "traffic_potential": classification["traffic_potential"],
                "competition": classification["competition_level"],
                "user_intent": classification["user_intent_score"],
                "suggested_action": classification["suggested_action"],
                "content_template": content_template,
                "meta": {
                    "key_topics": classification.get("key_topics", []),
                    "reasoning": classification.get("reasoning", "")
                }
            }
            
            logger.info(f"Orchestrator: Opportunity created with score {score}")
            return {"status": "success", "opportunity": opportunity}
            
        except Exception as e:
            logger.error(f"Orchestrator pipeline error: {e}")
            return {"status": "error", "error": str(e)}
    
    def calculate_score(self, classification: Dict[str, Any]) -> float:
        """Calculate opportunity score using the formula"""
        relevance = classification.get("relevance_score", 1)
        traffic_potential = classification.get("traffic_potential", 1)
        competition = classification.get("competition_level", 3)
        user_intent = classification.get("user_intent_score", 1)
        
        # Formula: Relevance + Traffic Potential + (6 - Competition) + User Intent + (6 - Difficulty)
        # Difficulty is derived from competition
        difficulty = 6 - competition
        
        score = relevance + traffic_potential + (6 - competition) + user_intent + difficulty
        
        # Normalize to 0-100 scale (max possible is 55)
        normalized_score = (score / 55) * 100
        
        return round(normalized_score, 2)
    
    async def batch_process_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple signals in parallel with token management"""
        # Process in batches to avoid overwhelming the API
        batch_size = 5
        results = []
        
        for i in range(0, len(signals), batch_size):
            batch = signals[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} signals)")
            
            # Process batch in parallel
            tasks = [self.process_signal_pipeline(signal) for signal in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results and exceptions
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch processing error: {result}")
                    results.append({"status": "error", "error": str(result)})
                else:
                    results.append(result)
            
            # Small delay between batches to respect rate limits
            if i + batch_size < len(signals):
                await asyncio.sleep(1)
        
        return results
    
    async def process(self, input_data: Any) -> Any:
        """Main process method for orchestrator"""
        if isinstance(input_data, list):
            return await self.batch_process_signals(input_data)
        else:
            return await self.process_signal_pipeline(input_data)
