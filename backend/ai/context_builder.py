"""Build context for AI analysis from various data sources."""
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.logging import get_logger

logger = get_logger(__name__)


class ContextBuilder:
    """Build rich context for AI analysis."""

    @staticmethod
    def format_player_list(players: List[Dict[str, Any]], limit: int = 10) -> str:
        """Format player list for prompt."""
        if not players:
            return "No players available"

        lines = []
        for i, player in enumerate(players[:limit], 1):
            name = player.get('player', player.get('name', 'Unknown'))
            points = player.get('expected_points', player.get('points', 0))
            position = player.get('position', '')
            team = player.get('team', '')

            line = f"{i}. {name}"
            if position:
                line += f" ({position})"
            if team:
                line += f" - {team}"
            line += f" - {points:.1f} pts"

            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def format_team(team_data: Dict[str, Any]) -> str:
        """Format team data for prompt."""
        if not team_data or 'players' not in team_data:
            return "No team data available"

        players = team_data['players']
        lines = []

        # Group by position
        by_position = {}
        for player in players:
            pos = player.get('position', 'Unknown')
            if pos not in by_position:
                by_position[pos] = []
            by_position[pos].append(player)

        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            if pos in by_position:
                lines.append(f"\n{pos}:")
                for player in by_position[pos]:
                    name = player.get('name', 'Unknown')
                    is_captain = player.get('is_captain', False)
                    is_vice = player.get('is_vice_captain', False)
                    multiplier = player.get('multiplier', 1)

                    line = f"  - {name}"
                    if is_captain:
                        line += " (C)"
                    elif is_vice:
                        line += " (VC)"
                    elif multiplier == 0:
                        line += " (Bench)"

                    lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def format_news_items(news: List[Dict[str, Any]], limit: int = 10) -> str:
        """Format news items for prompt."""
        if not news:
            return "No recent news"

        lines = []
        for item in news[:limit]:
            headline = item.get('headline', item.get('title', ''))
            source = item.get('source', 'Unknown')
            sentiment = item.get('sentiment', 0)

            sentiment_emoji = "🔴" if sentiment < -0.3 else "🟡" if sentiment < 0.3 else "🟢"

            lines.append(f"{sentiment_emoji} [{source}] {headline}")

        return "\n".join(lines)

    @staticmethod
    def format_injuries(injuries: List[Dict[str, Any]]) -> str:
        """Format injury data for prompt."""
        if not injuries:
            return "No injury concerns"

        lines = []
        for injury in injuries:
            player = injury.get('player', 'Unknown')
            status = injury.get('status', 'Unknown')
            severity = injury.get('severity', 'Unknown')
            return_date = injury.get('return_date', 'TBD')

            line = f"⚠️ {player}: {status}"
            if severity:
                line += f" ({severity})"
            if return_date and return_date != 'TBD':
                line += f" - Return: {return_date}"

            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def format_sentiment(sentiment_data: Dict[str, Any]) -> str:
        """Format sentiment data for prompt."""
        if not sentiment_data:
            return "No sentiment data available"

        lines = []

        if 'player_sentiment' in sentiment_data:
            lines.append("Player Sentiment:")
            for player, data in list(sentiment_data['player_sentiment'].items())[:10]:
                score = data.get('score', 0)
                volume = data.get('volume', 'low')

                sentiment_text = "Very Negative" if score < -0.5 else \
                                "Negative" if score < -0.2 else \
                                "Neutral" if score < 0.2 else \
                                "Positive" if score < 0.5 else \
                                "Very Positive"

                lines.append(f"  {player}: {sentiment_text} (Volume: {volume})")

        if 'community_consensus' in sentiment_data:
            consensus = sentiment_data['community_consensus']
            if 'top_differentials' in consensus:
                lines.append(f"\nTop Differentials: {', '.join(consensus['top_differentials'][:5])}")
            if 'avoid_players' in consensus:
                lines.append(f"Players to Avoid: {', '.join(consensus['avoid_players'][:5])}")

        return "\n".join(lines) if lines else "No sentiment analysis available"

    @staticmethod
    def format_fixtures(fixtures: List[Dict[str, Any]], limit: int = 5) -> str:
        """Format fixture data for prompt."""
        if not fixtures:
            return "No fixture data available"

        lines = []
        for fixture in fixtures[:limit]:
            home = fixture.get('home_team', 'TBD')
            away = fixture.get('away_team', 'TBD')
            difficulty_home = fixture.get('difficulty_home', 0)
            difficulty_away = fixture.get('difficulty_away', 0)
            gameweek = fixture.get('gameweek', '')

            line = f"GW{gameweek}: {home} (Diff: {difficulty_home}) vs {away} (Diff: {difficulty_away})"
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def build_transfer_context(
        current_team: Dict[str, Any],
        budget: float,
        chips_remaining: List[str],
        gameweek: int,
        airsenal_data: Dict[str, Any],
        intelligence_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Build context for transfer recommendations."""
        return {
            'current_team': ContextBuilder.format_team(current_team),
            'budget': f"{budget:.1f}",
            'chips': ', '.join(chips_remaining) if chips_remaining else 'None',
            'gameweek': str(gameweek),
            'predicted_players': ContextBuilder.format_player_list(
                airsenal_data.get('top_predicted_players', [])
            ),
            'airsenal_transfers': ContextBuilder.format_player_list(
                airsenal_data.get('recommended_transfers', [])
            ),
            'breaking_news': ContextBuilder.format_news_items(
                intelligence_data.get('breaking_news', [])
            ),
            'injuries': ContextBuilder.format_injuries(
                intelligence_data.get('injuries', [])
            ),
            'press_conferences': intelligence_data.get('press_conference_summary', 'No recent press conferences'),
            'weather': intelligence_data.get('weather_summary', 'No weather alerts'),
            'community_sentiment': intelligence_data.get('community_summary', 'No community data'),
            'player_sentiment': ContextBuilder.format_sentiment(
                intelligence_data.get('sentiment', {})
            ),
            'fixtures': ContextBuilder.format_fixtures(
                intelligence_data.get('fixtures', [])
            )
        }

    @staticmethod
    def build_captaincy_context(
        team_players: List[Dict[str, Any]],
        gameweek: int,
        airsenal_predictions: Dict[str, Any],
        intelligence_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Build context for captaincy recommendations."""
        return {
            'gameweek': str(gameweek),
            'team_players': ContextBuilder.format_player_list(team_players),
            'predicted_points': ContextBuilder.format_player_list(
                airsenal_predictions.get('predictions', [])
            ),
            'news': ContextBuilder.format_news_items(
                intelligence_data.get('news', [])
            ),
            'form': intelligence_data.get('form_summary', 'No form data'),
            'tactics': intelligence_data.get('tactical_summary', 'No tactical info'),
            'weather': intelligence_data.get('weather_summary', 'No weather alerts'),
            'sentiment': ContextBuilder.format_sentiment(
                intelligence_data.get('sentiment', {})
            ),
            'fixtures': ContextBuilder.format_fixtures(
                intelligence_data.get('fixtures', [])
            )
        }
