"""News aggregator for FPL and Premier League news."""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from newsapi import NewsApiClient
import httpx
from bs4 import BeautifulSoup
from utils.logging import get_logger

logger = get_logger(__name__)


class NewsAggregator:
    """Aggregate news from multiple sources."""

    def __init__(self):
        """Initialize news aggregator."""
        self.news_api_key = os.getenv('NEWS_API_KEY')

        if self.news_api_key:
            try:
                self.news_api = NewsApiClient(api_key=self.news_api_key)
                logger.info("NewsAPI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize NewsAPI: {e}")
                self.news_api = None
        else:
            logger.warning("NEWS_API_KEY not set - NewsAPI features will not work")
            self.news_api = None

    def is_available(self) -> bool:
        """Check if news API is available."""
        return self.news_api is not None

    async def get_fpl_news(
        self,
        query: str = 'fantasy premier league',
        hours_ago: int = 24,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get FPL-related news from NewsAPI.

        Args:
            query: Search query
            hours_ago: How many hours back to search
            limit: Maximum number of articles

        Returns:
            List of news articles
        """
        if not self.is_available():
            logger.warning("NewsAPI not available")
            return []

        try:
            from_date = (datetime.now() - timedelta(hours=hours_ago)).isoformat()

            logger.debug(f"Fetching news for '{query}' from last {hours_ago} hours")

            response = self.news_api.get_everything(
                q=query,
                from_param=from_date,
                language='en',
                sort_by='relevancy',
                page_size=limit
            )

            articles = []
            for article in response.get('articles', []):
                articles.append({
                    'title': article.get('title'),
                    'description': article.get('description'),
                    'url': article.get('url'),
                    'source': article.get('source', {}).get('name'),
                    'published_at': article.get('publishedAt'),
                    'author': article.get('author')
                })

            logger.info(f"Fetched {len(articles)} news articles")
            return articles

        except Exception as e:
            logger.error(f"Failed to fetch news: {e}", exc_info=True)
            return []

    async def get_player_news(
        self,
        player_name: str,
        hours_ago: int = 48
    ) -> List[Dict[str, Any]]:
        """
        Get news about a specific player.

        Args:
            player_name: Player name
            hours_ago: How many hours back to search

        Returns:
            List of relevant articles
        """
        query = f"{player_name} premier league"
        return await self.get_fpl_news(query=query, hours_ago=hours_ago, limit=10)

    async def get_team_news(
        self,
        team_name: str,
        hours_ago: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get news about a specific team.

        Args:
            team_name: Team name
            hours_ago: How many hours back to search

        Returns:
            List of relevant articles
        """
        query = f"{team_name} premier league"
        return await self.get_fpl_news(query=query, hours_ago=hours_ago, limit=10)

    async def scrape_official_fpl_news(self) -> List[Dict[str, Any]]:
        """
        Scrape news from official FPL site.

        Returns:
            List of news items
        """
        try:
            url = "https://fantasy.premierleague.com/news"
            logger.debug(f"Scraping FPL news from {url}")

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []

            # This is a placeholder - actual scraping would need to inspect the HTML structure
            # For now, return empty list
            logger.warning("FPL news scraping not yet implemented - requires HTML inspection")

            return articles

        except Exception as e:
            logger.error(f"Failed to scrape FPL news: {e}", exc_info=True)
            return []

    async def get_injury_news(
        self,
        hours_ago: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get injury-related news.

        Args:
            hours_ago: How many hours back to search

        Returns:
            List of injury news
        """
        queries = [
            'premier league injury',
            'premier league suspended',
            'premier league fitness'
        ]

        all_news = []
        for query in queries:
            news = await self.get_fpl_news(query=query, hours_ago=hours_ago, limit=5)
            all_news.extend(news)

        # Deduplicate by URL
        seen_urls = set()
        unique_news = []
        for item in all_news:
            if item['url'] not in seen_urls:
                seen_urls.add(item['url'])
                unique_news.append(item)

        logger.info(f"Fetched {len(unique_news)} injury news articles")
        return unique_news

    async def aggregate_breaking_news(
        self,
        hours_ago: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Aggregate breaking news from multiple sources.

        Args:
            hours_ago: How many hours back to check

        Returns:
            List of breaking news items
        """
        categories = [
            ('fantasy premier league', 'FPL'),
            ('premier league injury', 'Injury'),
            ('premier league transfer', 'Transfer'),
            ('premier league team news', 'Team News')
        ]

        all_news = []
        for query, category in categories:
            news = await self.get_fpl_news(query=query, hours_ago=hours_ago, limit=5)
            for item in news:
                item['category'] = category
            all_news.extend(news)

        # Sort by recency
        all_news.sort(key=lambda x: x['published_at'], reverse=True)

        logger.info(f"Aggregated {len(all_news)} breaking news items")
        return all_news[:20]


# Global aggregator instance
news_aggregator = NewsAggregator()
