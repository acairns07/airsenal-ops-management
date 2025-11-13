"""Sentiment analysis for text content."""
from typing import Dict, Any, List
import re
from utils.logging import get_logger

logger = get_logger(__name__)


class SentimentAnalyzer:
    """Analyze sentiment of text content."""

    def __init__(self):
        """Initialize sentiment analyzer."""
        # Simple keyword-based sentiment (can be enhanced with ML models)
        self.positive_keywords = [
            'great', 'excellent', 'amazing', 'brilliant', 'superb', 'fantastic',
            'good', 'best', 'strong', 'hot', 'form', 'essential', 'must-have',
            'haul', 'points', 'captain', 'in-form', 'returns', 'differential'
        ]

        self.negative_keywords = [
            'bad', 'poor', 'terrible', 'awful', 'avoid', 'sell', 'drop',
            'injured', 'injury', 'suspended', 'doubt', 'rotation', 'risk',
            'blank', 'benched', 'dropped', 'out', 'flagged', 'concern'
        ]

        logger.info("Sentiment analyzer initialized (keyword-based)")

    def analyze_text(self, text: str) -> float:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze

        Returns:
            Sentiment score (-1 to 1, where -1 is very negative, 1 is very positive)
        """
        if not text:
            return 0.0

        text_lower = text.lower()

        # Count positive and negative keywords
        positive_count = sum(1 for keyword in self.positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in self.negative_keywords if keyword in text_lower)

        # Simple scoring
        total = positive_count + negative_count
        if total == 0:
            return 0.0

        score = (positive_count - negative_count) / total

        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, score))

    def analyze_reddit_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze sentiment of a Reddit post.

        Args:
            post: Reddit post dict with 'title' and optional 'content'

        Returns:
            Sentiment analysis result
        """
        title = post.get('title', '')
        content = post.get('content', '')
        combined_text = f"{title} {content}"

        sentiment_score = self.analyze_text(combined_text)

        # Adjust based on engagement
        score = post.get('score', 0)
        upvote_ratio = post.get('upvote_ratio', 0.5)

        # Higher engagement with positive sentiment = stronger signal
        if sentiment_score > 0 and score > 100:
            sentiment_score = min(1.0, sentiment_score * 1.2)
        elif sentiment_score < 0 and score > 100:
            sentiment_score = max(-1.0, sentiment_score * 1.2)

        return {
            'sentiment_score': sentiment_score,
            'sentiment_label': self._get_label(sentiment_score),
            'confidence': abs(sentiment_score),
            'engagement_score': score,
            'upvote_ratio': upvote_ratio
        }

    def analyze_news_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze sentiment of a news article.

        Args:
            article: Article dict with 'title' and 'description'

        Returns:
            Sentiment analysis result
        """
        title = article.get('title', '')
        description = article.get('description', '')
        combined_text = f"{title} {description}"

        sentiment_score = self.analyze_text(combined_text)

        return {
            'sentiment_score': sentiment_score,
            'sentiment_label': self._get_label(sentiment_score),
            'confidence': abs(sentiment_score),
            'source': article.get('source', 'Unknown')
        }

    def aggregate_player_sentiment(
        self,
        reddit_posts: List[Dict[str, Any]],
        news_articles: List[Dict[str, Any]],
        player_name: str
    ) -> Dict[str, Any]:
        """
        Aggregate sentiment for a specific player from multiple sources.

        Args:
            reddit_posts: List of Reddit posts mentioning player
            news_articles: List of news articles about player
            player_name: Player name

        Returns:
            Aggregated sentiment analysis
        """
        reddit_sentiments = [
            self.analyze_reddit_post(post)['sentiment_score']
            for post in reddit_posts
        ]

        news_sentiments = [
            self.analyze_news_article(article)['sentiment_score']
            for article in news_articles
        ]

        all_sentiments = reddit_sentiments + news_sentiments

        if not all_sentiments:
            return {
                'player': player_name,
                'overall_sentiment': 0.0,
                'sentiment_label': 'Neutral',
                'confidence': 0.0,
                'volume': 'none',
                'sources_count': 0
            }

        avg_sentiment = sum(all_sentiments) / len(all_sentiments)
        volume = 'very high' if len(all_sentiments) > 20 else \
                 'high' if len(all_sentiments) > 10 else \
                 'medium' if len(all_sentiments) > 5 else \
                 'low'

        return {
            'player': player_name,
            'overall_sentiment': avg_sentiment,
            'sentiment_label': self._get_label(avg_sentiment),
            'confidence': abs(avg_sentiment),
            'volume': volume,
            'sources_count': len(all_sentiments),
            'reddit_mentions': len(reddit_posts),
            'news_mentions': len(news_articles)
        }

    def extract_player_mentions(self, text: str) -> List[str]:
        """
        Extract potential player names from text (simple pattern matching).

        Args:
            text: Text to analyze

        Returns:
            List of potential player names
        """
        # This is a very simple implementation
        # In production, would use Named Entity Recognition (NER)
        words = re.findall(r'\b[A-Z][a-z]+\b', text)

        # Filter out common non-name words
        common_words = {'The', 'This', 'That', 'When', 'Where', 'Why', 'How', 'Premier', 'League', 'Fantasy'}
        potential_names = [word for word in words if word not in common_words]

        return potential_names

    def _get_label(self, score: float) -> str:
        """Get sentiment label from score."""
        if score < -0.5:
            return 'Very Negative'
        elif score < -0.2:
            return 'Negative'
        elif score < 0.2:
            return 'Neutral'
        elif score < 0.5:
            return 'Positive'
        else:
            return 'Very Positive'


# Global analyzer instance
sentiment_analyzer = SentimentAnalyzer()
