"""API routes for AI-powered recommendations."""
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from auth import get_current_user
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_db():
    """Dependency to get database instance."""
    from database import db
    return db


def get_recommendation_engine():
    """Dependency to get recommendation engine."""
    from ai.recommendation_engine import recommendation_engine
    if not recommendation_engine:
        raise HTTPException(status_code=500, detail="Recommendation engine not initialized")
    return recommendation_engine


def get_intelligence_service():
    """Dependency to get intelligence service."""
    from intelligence.intelligence_service import intelligence_service
    if not intelligence_service:
        raise HTTPException(status_code=500, detail="Intelligence service not initialized")
    return intelligence_service


class RecommendationRequest(BaseModel):
    """Request for AI recommendations."""
    gameweek: int
    include_transfers: bool = True
    include_captaincy: bool = True
    focus_players: Optional[List[str]] = None


@router.post("/analyze")
async def generate_ai_analysis(
    request: RecommendationRequest,
    current_user: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    engine = Depends(get_recommendation_engine),
    intel_service = Depends(get_intelligence_service)
):
    """
    Generate comprehensive AI analysis with recommendations.

    Args:
        request: Analysis request parameters
        current_user: Authenticated user
        db: Database instance
        engine: Recommendation engine
        intel_service: Intelligence service

    Returns:
        Comprehensive AI analysis
    """
    try:
        logger.info(
            f"Generating AI analysis for GW{request.gameweek}",
            extra={'user_email': current_user}
        )

        # Get current team from FPL API
        team_id_doc = await db.secrets.find_one({"key": "FPL_TEAM_ID"})
        if not team_id_doc:
            raise HTTPException(status_code=404, detail="FPL team ID not configured")

        # For now, use mock team data - in production would fetch from FPL API
        current_team = {
            'team_id': team_id_doc.get('value'),
            'players': [],  # Would be populated from FPL API
            'budget': 0.5
        }

        # Get AIrsenal predictions (latest job)
        airsenal_prediction = await db.jobs.find_one(
            {"command": "predict", "status": "completed", "output": {"$exists": True}},
            sort=[("completed_at", -1)]
        )

        airsenal_optimization = await db.jobs.find_one(
            {"command": "optimize", "status": "completed", "output": {"$exists": True}},
            sort=[("completed_at", -1)]
        )

        airsenal_data = {
            'top_predicted_players': airsenal_prediction.get('output', {}).get('players', []) if airsenal_prediction else [],
            'recommended_transfers': airsenal_optimization.get('output', {}).get('transfers', []) if airsenal_optimization else []
        }

        # Gather intelligence
        intelligence_data = await intel_service.gather_comprehensive_intelligence(
            gameweek=request.gameweek,
            focus_players=request.focus_players
        )

        # Generate analysis
        analysis = await engine.generate_comprehensive_analysis(
            current_team=current_team,
            budget=current_team['budget'],
            chips_remaining=['wildcard', 'free_hit'],  # Would come from user data
            gameweek=request.gameweek,
            airsenal_data=airsenal_data,
            intelligence_data=intelligence_data
        )

        logger.info(f"AI analysis completed", extra={'user_email': current_user})
        return analysis

    except Exception as e:
        logger.error(f"Failed to generate AI analysis: {e}", extra={'user_email': current_user}, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate analysis: {str(e)}")


@router.get("/history")
async def get_recommendation_history(
    limit: int = 10,
    type: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    engine = Depends(get_recommendation_engine)
):
    """
    Get AI recommendation history.

    Args:
        limit: Number of recommendations to return
        type: Filter by type (transfer, captaincy, etc.)
        current_user: Authenticated user
        engine: Recommendation engine

    Returns:
        List of past recommendations
    """
    try:
        history = await engine.get_recommendation_history(
            limit=limit,
            recommendation_type=type
        )

        return history

    except Exception as e:
        logger.error(f"Failed to get recommendation history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/player/{player_name}")
async def get_player_intelligence(
    player_name: str,
    current_user: str = Depends(get_current_user),
    intel_service = Depends(get_intelligence_service)
):
    """
    Get intelligence report for a specific player.

    Args:
        player_name: Player name
        current_user: Authenticated user
        intel_service: Intelligence service

    Returns:
        Player intelligence report
    """
    try:
        logger.info(f"Getting intelligence for player: {player_name}", extra={'user_email': current_user})

        intelligence = await intel_service.get_player_intelligence(player_name)

        return intelligence

    except Exception as e:
        logger.error(f"Failed to get player intelligence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intelligence/feed")
async def get_intelligence_feed(
    hours: int = 24,
    current_user: str = Depends(get_current_user),
    intel_service = Depends(get_intelligence_service)
):
    """
    Get recent intelligence feed.

    Args:
        hours: Hours of data to retrieve
        current_user: Authenticated user
        intel_service: Intelligence service

    Returns:
        Intelligence feed
    """
    try:
        # Gather recent intelligence
        intelligence = await intel_service.gather_comprehensive_intelligence(
            gameweek=None,
            focus_players=None
        )

        # Filter to requested time window
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=hours)

        feed = {
            'breaking_news': intelligence.get('breaking_news', []),
            'top_reddit_topics': intelligence.get('top_reddit_topics', []),
            'injuries': intelligence.get('injuries', []),
            'community_sentiment': intelligence.get('community_sentiment', {}),
            'timestamp': intelligence.get('timestamp')
        }

        return feed

    except Exception as e:
        logger.error(f"Failed to get intelligence feed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
