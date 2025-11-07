"""AI recommendation engine combining predictions and intelligence."""
from typing import Dict, Any, List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from .openai_client import openai_client
from .prompt_templates import PromptTemplates
from .context_builder import ContextBuilder
from utils.logging import get_logger

logger = get_logger(__name__)


class RecommendationEngine:
    """Generate AI-powered FPL recommendations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize recommendation engine.

        Args:
            db: MongoDB database instance
        """
        self.db = db

    async def generate_transfer_recommendations(
        self,
        current_team: Dict[str, Any],
        budget: float,
        chips_remaining: List[str],
        gameweek: int,
        airsenal_predictions: Dict[str, Any],
        intelligence_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate AI-powered transfer recommendations.

        Args:
            current_team: Current team data
            budget: Available budget
            chips_remaining: List of available chips
            gameweek: Current gameweek
            airsenal_predictions: AIrsenal ML predictions
            intelligence_data: Real-time intelligence

        Returns:
            AI recommendations dict or None if error
        """
        if not openai_client.is_available():
            logger.error("OpenAI client not available")
            return None

        try:
            logger.info(f"Generating transfer recommendations for GW{gameweek}")

            # Build context
            context = ContextBuilder.build_transfer_context(
                current_team=current_team,
                budget=budget,
                chips_remaining=chips_remaining,
                gameweek=gameweek,
                airsenal_data=airsenal_predictions,
                intelligence_data=intelligence_data
            )

            # Format prompt
            user_prompt = PromptTemplates.format_transfer_prompt(**context)

            # Get AI analysis
            response = await openai_client.analyze_fpl_situation(
                system_prompt=PromptTemplates.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                expect_json=True
            )

            if not response:
                logger.error("No response from OpenAI")
                return None

            # Enrich response with metadata
            response['generated_at'] = datetime.now().isoformat()
            response['gameweek'] = gameweek
            response['model'] = openai_client.model
            response['intelligence_sources'] = self._get_sources_used(intelligence_data)

            # Save recommendation to database
            await self._save_recommendation(
                type='transfer',
                gameweek=gameweek,
                recommendation=response
            )

            logger.info(f"Generated {len(response.get('recommended_transfers', []))} transfer recommendations")
            return response

        except Exception as e:
            logger.error(f"Failed to generate transfer recommendations: {e}", exc_info=True)
            return None

    async def generate_captaincy_recommendation(
        self,
        team_players: List[Dict[str, Any]],
        gameweek: int,
        airsenal_predictions: Dict[str, Any],
        intelligence_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate AI-powered captaincy recommendation.

        Args:
            team_players: Current team players
            gameweek: Current gameweek
            airsenal_predictions: AIrsenal predictions
            intelligence_data: Real-time intelligence

        Returns:
            Captaincy recommendation or None
        """
        if not openai_client.is_available():
            return None

        try:
            logger.info(f"Generating captaincy recommendation for GW{gameweek}")

            # Build context
            context = ContextBuilder.build_captaincy_context(
                team_players=team_players,
                gameweek=gameweek,
                airsenal_predictions=airsenal_predictions,
                intelligence_data=intelligence_data
            )

            # Format prompt
            user_prompt = PromptTemplates.format_captaincy_prompt(**context)

            # Get AI analysis
            response = await openai_client.analyze_fpl_situation(
                system_prompt=PromptTemplates.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                expect_json=True
            )

            if not response:
                return None

            # Enrich response
            response['generated_at'] = datetime.now().isoformat()
            response['gameweek'] = gameweek
            response['model'] = openai_client.model

            # Save recommendation
            await self._save_recommendation(
                type='captaincy',
                gameweek=gameweek,
                recommendation=response
            )

            logger.info(f"Recommended captain: {response.get('recommended_captain', {}).get('player', 'Unknown')}")
            return response

        except Exception as e:
            logger.error(f"Failed to generate captaincy recommendation: {e}", exc_info=True)
            return None

    async def generate_comprehensive_analysis(
        self,
        current_team: Dict[str, Any],
        budget: float,
        chips_remaining: List[str],
        gameweek: int,
        airsenal_data: Dict[str, Any],
        intelligence_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analysis including transfers and captaincy.

        Args:
            current_team: Current team data
            budget: Available budget
            chips_remaining: List of chips
            gameweek: Current gameweek
            airsenal_data: AIrsenal predictions
            intelligence_data: Real-time intelligence

        Returns:
            Comprehensive analysis dict
        """
        logger.info(f"Generating comprehensive analysis for GW{gameweek}")

        analysis = {
            'gameweek': gameweek,
            'generated_at': datetime.now().isoformat(),
            'transfers': None,
            'captaincy': None,
            'risk_assessment': None,
            'overall_confidence': 0.0,
            'summary': ''
        }

        # Generate transfers
        team_players = current_team.get('players', [])
        transfers = await self.generate_transfer_recommendations(
            current_team=current_team,
            budget=budget,
            chips_remaining=chips_remaining,
            gameweek=gameweek,
            airsenal_predictions=airsenal_data,
            intelligence_data=intelligence_data
        )
        analysis['transfers'] = transfers

        # Generate captaincy
        captaincy = await self.generate_captaincy_recommendation(
            team_players=team_players,
            gameweek=gameweek,
            airsenal_predictions=airsenal_data,
            intelligence_data=intelligence_data
        )
        analysis['captaincy'] = captaincy

        # Calculate overall confidence
        confidences = []
        if transfers and 'overall_confidence' in transfers:
            confidences.append(transfers['overall_confidence'])
        if captaincy and 'recommended_captain' in captaincy:
            confidences.append(captaincy['recommended_captain'].get('confidence', 0))

        if confidences:
            analysis['overall_confidence'] = sum(confidences) / len(confidences)

        # Generate summary
        summary_parts = []
        if transfers:
            transfer_count = len(transfers.get('recommended_transfers', []))
            summary_parts.append(f"{transfer_count} transfer(s) recommended")
        if captaincy:
            captain_name = captaincy.get('recommended_captain', {}).get('player', 'Unknown')
            summary_parts.append(f"Captain: {captain_name}")

        analysis['summary'] = '. '.join(summary_parts) if summary_parts else 'No recommendations generated'

        return analysis

    async def get_recommendation_history(
        self,
        limit: int = 10,
        recommendation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recommendation history.

        Args:
            limit: Number of recommendations to return
            recommendation_type: Filter by type (transfer, captaincy, etc.)

        Returns:
            List of recommendations
        """
        try:
            query = {}
            if recommendation_type:
                query['type'] = recommendation_type

            recommendations = await self.db.ai_recommendations.find(
                query,
                {'_id': 0}
            ).sort('timestamp', -1).limit(limit).to_list(limit)

            return recommendations

        except Exception as e:
            logger.error(f"Failed to get recommendation history: {e}")
            return []

    async def _save_recommendation(
        self,
        type: str,
        gameweek: int,
        recommendation: Dict[str, Any]
    ) -> None:
        """Save recommendation to database."""
        try:
            doc = {
                'type': type,
                'gameweek': gameweek,
                'timestamp': datetime.now().isoformat(),
                'recommendation': recommendation,
                'model': openai_client.model,
                'user_accepted': None,
                'actual_outcome': None
            }

            await self.db.ai_recommendations.insert_one(doc)
            logger.debug(f"Saved {type} recommendation for GW{gameweek}")

        except Exception as e:
            logger.error(f"Failed to save recommendation: {e}")

    def _get_sources_used(self, intelligence_data: Dict[str, Any]) -> List[str]:
        """Extract list of intelligence sources used."""
        sources = []

        if intelligence_data.get('breaking_news'):
            sources.append('News Articles')
        if intelligence_data.get('top_reddit_topics'):
            sources.append('Reddit Community')
        if intelligence_data.get('injuries'):
            sources.append('Injury Reports')
        if intelligence_data.get('player_sentiment'):
            sources.append('Sentiment Analysis')

        return sources


# Global engine instance (will be initialized with db)
recommendation_engine: Optional[RecommendationEngine] = None


def init_recommendation_engine(db: AsyncIOMotorDatabase):
    """Initialize the global recommendation engine."""
    global recommendation_engine
    recommendation_engine = RecommendationEngine(db)
    logger.info("Recommendation engine initialized")
