"""Reddit scraper for r/FantasyPL intelligence gathering."""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import praw
from utils.logging import get_logger

logger = get_logger(__name__)


class RedditScraper:
    """Scrape r/FantasyPL for community insights."""

    def __init__(self):
        """Initialize Reddit client."""
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.user_agent = os.getenv('REDDIT_USER_AGENT', 'AIrsenalOps/1.0')

        if not self.client_id or not self.client_secret:
            logger.warning("Reddit credentials not set - Reddit features will not work")
            self.reddit = None
        else:
            try:
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent
                )
                logger.info("Reddit client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit client: {e}")
                self.reddit = None

    def is_available(self) -> bool:
        """Check if Reddit client is available."""
        return self.reddit is not None

    async def get_hot_topics(
        self,
        subreddit: str = 'FantasyPL',
        limit: int = 25,
        time_filter: str = 'day'
    ) -> List[Dict[str, Any]]:
        """
        Get hot topics from r/FantasyPL.

        Args:
            subreddit: Subreddit name
            limit: Number of posts to fetch
            time_filter: Time filter (hour, day, week, month)

        Returns:
            List of topic dicts
        """
        if not self.is_available():
            logger.warning("Reddit client not available")
            return []

        try:
            logger.debug(f"Fetching hot topics from r/{subreddit}")

            subreddit_obj = self.reddit.subreddit(subreddit)
            topics = []

            for submission in subreddit_obj.hot(limit=limit):
                # Skip stickied posts
                if submission.stickied:
                    continue

                # Calculate age
                created_utc = datetime.fromtimestamp(submission.created_utc)
                age_hours = (datetime.now() - created_utc).total_seconds() / 3600

                # Filter by time
                if time_filter == 'hour' and age_hours > 1:
                    continue
                elif time_filter == 'day' and age_hours > 24:
                    continue
                elif time_filter == 'week' and age_hours > 168:
                    continue

                topic = {
                    'title': submission.title,
                    'score': submission.score,
                    'url': f"https://reddit.com{submission.permalink}",
                    'author': str(submission.author),
                    'created': created_utc.isoformat(),
                    'num_comments': submission.num_comments,
                    'upvote_ratio': submission.upvote_ratio,
                    'flair': submission.link_flair_text,
                    'content': submission.selftext[:500] if submission.selftext else None
                }

                topics.append(topic)

            logger.info(f"Fetched {len(topics)} topics from r/{subreddit}")
            return topics

        except Exception as e:
            logger.error(f"Failed to fetch Reddit topics: {e}", exc_info=True)
            return []

    async def search_player_mentions(
        self,
        player_name: str,
        subreddit: str = 'FantasyPL',
        limit: int = 10,
        time_filter: str = 'week'
    ) -> List[Dict[str, Any]]:
        """
        Search for mentions of a specific player.

        Args:
            player_name: Player name to search
            subreddit: Subreddit to search
            limit: Number of results
            time_filter: Time filter

        Returns:
            List of mentions
        """
        if not self.is_available():
            return []

        try:
            logger.debug(f"Searching for '{player_name}' in r/{subreddit}")

            subreddit_obj = self.reddit.subreddit(subreddit)
            mentions = []

            for submission in subreddit_obj.search(
                query=player_name,
                time_filter=time_filter,
                limit=limit
            ):
                created_utc = datetime.fromtimestamp(submission.created_utc)

                mention = {
                    'title': submission.title,
                    'score': submission.score,
                    'url': f"https://reddit.com{submission.permalink}",
                    'created': created_utc.isoformat(),
                    'context': submission.selftext[:300] if submission.selftext else None
                }

                mentions.append(mention)

            logger.info(f"Found {len(mentions)} mentions of '{player_name}'")
            return mentions

        except Exception as e:
            logger.error(f"Failed to search player mentions: {e}", exc_info=True)
            return []

    async def get_community_sentiment(
        self,
        gameweek: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze community sentiment from recent posts.

        Args:
            gameweek: Optional gameweek to focus on

        Returns:
            Sentiment analysis dict
        """
        if not self.is_available():
            return {
                'overall_mood': 'unknown',
                'top_players_mentioned': [],
                'hot_topics': [],
                'consensus': {}
            }

        try:
            topics = await self.get_hot_topics(limit=50, time_filter='day')

            # Extract player mentions (simple keyword extraction)
            player_mentions = {}
            differential_mentions = []
            avoid_mentions = []

            for topic in topics:
                title_lower = topic['title'].lower()
                content_lower = (topic.get('content') or '').lower()
                combined_text = f"{title_lower} {content_lower}"

                # Look for differential keywords
                if 'differential' in combined_text or 'punt' in combined_text:
                    differential_mentions.append(topic)

                # Look for avoid keywords
                if 'avoid' in combined_text or 'sell' in combined_text or 'transfer out' in combined_text:
                    avoid_mentions.append(topic)

            sentiment = {
                'overall_mood': 'neutral',  # Would need sentiment analysis
                'top_topics': topics[:10],
                'differential_discussions': differential_mentions[:5],
                'avoid_discussions': avoid_mentions[:5],
                'total_posts_analyzed': len(topics),
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"Analyzed community sentiment from {len(topics)} posts")
            return sentiment

        except Exception as e:
            logger.error(f"Failed to analyze community sentiment: {e}", exc_info=True)
            return {'error': str(e)}

    async def get_gameweek_thread_insights(
        self,
        gameweek: int
    ) -> Dict[str, Any]:
        """
        Extract insights from gameweek rant/discussion threads.

        Args:
            gameweek: Gameweek number

        Returns:
            Insights dict
        """
        if not self.is_available():
            return {}

        try:
            # Search for gameweek threads
            search_terms = [
                f"GW{gameweek} rant",
                f"Gameweek {gameweek} rant",
                f"GW{gameweek} discussion"
            ]

            for term in search_terms:
                results = await self.search_player_mentions(
                    player_name=term,
                    limit=5,
                    time_filter='week'
                )

                if results:
                    logger.info(f"Found GW{gameweek} thread with {results[0]['score']} upvotes")
                    return {
                        'thread_found': True,
                        'thread_url': results[0]['url'],
                        'score': results[0]['score'],
                        'title': results[0]['title']
                    }

            return {'thread_found': False}

        except Exception as e:
            logger.error(f"Failed to find gameweek thread: {e}", exc_info=True)
            return {'error': str(e)}


# Global scraper instance
reddit_scraper = RedditScraper()
