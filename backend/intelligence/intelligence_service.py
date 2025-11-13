"""Intelligence service that coordinates all intelligence gathering."""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from .reddit_scraper import reddit_scraper
from .news_aggregator import news_aggregator
from .sentiment_analyzer import sentiment_analyzer
from utils.logging import get_logger

logger = get_logger(__name__)


class IntelligenceService:
    """Coordinate intelligence gathering from multiple sources."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize intelligence service.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.cache_hours = int(os.getenv('INTELLIGENCE_CACHE_HOURS', '1'))

    async def gather_comprehensive_intelligence(
        self,
        gameweek: Optional[int] = None,
        focus_players: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Gather comprehensive intelligence from all sources.

        Args:
            gameweek: Current gameweek
            focus_players: List of player names to focus on

        Returns:
            Comprehensive intelligence dict
        """
        logger.info(f"Gathering comprehensive intelligence for GW{gameweek}")

        # Check cache first
        cached = await self._get_cached_intelligence(gameweek)
        if cached:
            logger.info("Using cached intelligence data")
            return cached

        intelligence = {
            'gameweek': gameweek,
            'timestamp': datetime.now().isoformat(),
            'breaking_news': [],
            'injuries': [],
            'press_conferences': [],
            'community_sentiment': {},
            'player_sentiment': {},
            'top_reddit_topics': [],
            'weather': {},
            'fixtures': []
        }

        # Gather news
        try:
            breaking_news = await news_aggregator.aggregate_breaking_news(hours_ago=12)
            intelligence['breaking_news'] = breaking_news[:10]

            injury_news = await news_aggregator.get_injury_news(hours_ago=48)
            intelligence['injuries'] = injury_news[:5]

            logger.info(f"Gathered {len(breaking_news)} breaking news items and {len(injury_news)} injury reports")
        except Exception as e:
            logger.error(f"Failed to gather news: {e}", exc_info=True)

        # Gather Reddit intelligence
        try:
            community_sentiment = await reddit_scraper.get_community_sentiment(gameweek)
            intelligence['community_sentiment'] = community_sentiment

            hot_topics = await reddit_scraper.get_hot_topics(limit=20, time_filter='day')
            intelligence['top_reddit_topics'] = hot_topics[:10]

            logger.info(f"Gathered Reddit intelligence: {len(hot_topics)} hot topics")
        except Exception as e:
            logger.error(f"Failed to gather Reddit data: {e}", exc_info=True)

        # Analyze sentiment for focus players
        if focus_players:
            try:
                for player_name in focus_players[:10]:  # Limit to 10 players
                    player_sentiment = await self._analyze_player_sentiment(player_name)
                    if player_sentiment:
                        intelligence['player_sentiment'][player_name] = player_sentiment

                logger.info(f"Analyzed sentiment for {len(intelligence['player_sentiment'])} players")
            except Exception as e:
                logger.error(f"Failed to analyze player sentiment: {e}", exc_info=True)

        # Cache the results
        await self._cache_intelligence(intelligence)

        return intelligence

    async def get_player_intelligence(
        self,
        player_name: str
    ) -> Dict[str, Any]:
        """
        Get intelligence for a specific player.

        Args:
            player_name: Player name

        Returns:
            Player intelligence dict
        """
        logger.info(f"Gathering intelligence for player: {player_name}")

        intelligence = {
            'player': player_name,
            'timestamp': datetime.now().isoformat(),
            'news': [],
            'reddit_mentions': [],
            'sentiment': {},
            'alerts': []
        }

        # Get news about player
        try:
            news = await news_aggregator.get_player_news(player_name, hours_ago=48)
            intelligence['news'] = news[:5]
        except Exception as e:
            logger.error(f"Failed to get player news: {e}")

        # Get Reddit mentions
        try:
            reddit_mentions = await reddit_scraper.search_player_mentions(player_name, time_filter='week', limit=10)
            intelligence['reddit_mentions'] = reddit_mentions
        except Exception as e:
            logger.error(f"Failed to get Reddit mentions: {e}")

        # Analyze sentiment
        try:
            sentiment = await self._analyze_player_sentiment(player_name)
            intelligence['sentiment'] = sentiment
        except Exception as e:
            logger.error(f"Failed to analyze sentiment: {e}")

        # Identify alerts (injuries, suspensions, etc.)
        alerts = self._extract_player_alerts(intelligence['news'], player_name)
        intelligence['alerts'] = alerts

        return intelligence

    async def _analyze_player_sentiment(
        self,
        player_name: str
    ) -> Dict[str, Any]:
        """Analyze sentiment for a player from all sources."""
        # Get Reddit posts
        reddit_posts = await reddit_scraper.search_player_mentions(player_name, time_filter='week', limit=10)

        # Get news articles
        news_articles = await news_aggregator.get_player_news(player_name, hours_ago=72)

        # Aggregate sentiment
        sentiment = sentiment_analyzer.aggregate_player_sentiment(
            reddit_posts=reddit_posts,
            news_articles=news_articles,
            player_name=player_name
        )

        return sentiment

    def _extract_player_alerts(
        self,
        news_articles: List[Dict[str, Any]],
        player_name: str
    ) -> List[Dict[str, Any]]:
        """Extract alerts from news articles."""
        alerts = []

        alert_keywords = {
            'critical': ['injured', 'out for', 'ruled out', 'suspended', 'ban'],
            'high': ['doubt', 'questionable', 'assessment', 'scan', 'fitness test'],
            'medium': ['rotation', 'rested', 'managed', 'minutes']
        }

        for article in news_articles:
            text = f"{article.get('title', '')} {article.get('description', '')}".lower()

            for severity, keywords in alert_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        alerts.append({
                            'player': player_name,
                            'severity': severity,
                            'alert': keyword.replace('_', ' ').title(),
                            'source': article.get('source', 'Unknown'),
                            'url': article.get('url'),
                            'timestamp': article.get('published_at')
                        })
                        break

        return alerts

    async def _get_cached_intelligence(
        self,
        gameweek: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        """Get cached intelligence if available and recent."""
        try:
            cache_cutoff = datetime.now() - timedelta(hours=self.cache_hours)

            query = {
                'type': 'comprehensive_intelligence',
                'gameweek': gameweek,
                'timestamp': {'$gte': cache_cutoff.isoformat()}
            }

            cached = await self.db.intelligence_cache.find_one(
                query,
                sort=[('timestamp', -1)]
            )

            if cached:
                cached.pop('_id', None)
                cached.pop('type', None)
                return cached

        except Exception as e:
            logger.error(f"Failed to get cached intelligence: {e}")

        return None

    async def _cache_intelligence(
        self,
        intelligence: Dict[str, Any]
    ) -> None:
        """Cache intelligence data."""
        try:
            doc = {
                'type': 'comprehensive_intelligence',
                'gameweek': intelligence.get('gameweek'),
                'timestamp': intelligence['timestamp'],
                **intelligence
            }

            await self.db.intelligence_cache.insert_one(doc)
            logger.debug("Intelligence data cached")

        except Exception as e:
            logger.error(f"Failed to cache intelligence: {e}")


# Global service instance (will be initialized with db)
intelligence_service: Optional[IntelligenceService] = None


def init_intelligence_service(db: AsyncIOMotorDatabase):
    """Initialize the global intelligence service."""
    global intelligence_service
    import os
    intelligence_service = IntelligenceService(db)
    logger.info("Intelligence service initialized")
