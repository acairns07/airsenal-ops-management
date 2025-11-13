"""Prompt templates for OpenAI interactions."""
from typing import Dict, Any


class PromptTemplates:
    """Templates for various AI prompts."""

    SYSTEM_PROMPT = """You are an elite Fantasy Premier League (FPL) advisor with deep knowledge of football analytics, player performance, and game strategy.

Your role:
- Analyze statistical predictions (from AIrsenal ML) alongside real-time intelligence (news, injuries, sentiment, tactical insights)
- Identify conflicts between predictions and reality (e.g., predicted player is injured)
- Provide data-driven recommendations with clear reasoning
- Assess risk levels for each decision
- Prioritize recent, verified information over historical predictions
- Consider both short-term gains and long-term strategy

Guidelines:
- Be specific and actionable
- Provide confidence scores (0-1) for recommendations
- Flag high-risk moves clearly
- Consider budget constraints and chip availability
- Account for fixture difficulty and player form
- Think like a seasoned FPL manager, not just an algorithm

Output format: Valid JSON with structured recommendations, reasoning, confidence scores, and sources."""

    TRANSFER_ANALYSIS = """Analyze this FPL transfer situation and provide optimal recommendations:

CURRENT TEAM:
{current_team}

BUDGET: £{budget}m
CHIPS REMAINING: {chips}
CURRENT GAMEWEEK: {gameweek}

AIRSENAL ML PREDICTIONS (Statistical Analysis):
Top Predicted Players (Next 3 GWs):
{predicted_players}

Recommended Transfers:
{airsenal_transfers}

REAL-TIME INTELLIGENCE:
Breaking News:
{breaking_news}

Injuries & Availability:
{injuries}

Press Conference Insights:
{press_conferences}

Weather Conditions:
{weather}

SENTIMENT ANALYSIS:
Community Sentiment (r/FantasyPL):
{community_sentiment}

Player Buzz:
{player_sentiment}

FIXTURES (Next 3 Gameweeks):
{fixtures}

TASK:
Provide JSON response with:
{{
  "recommended_transfers": [
    {{
      "player_out": "Player Name",
      "player_out_id": 123,
      "player_in": "Player Name",
      "player_in_id": 456,
      "reasoning": "Clear explanation combining stats and intelligence",
      "confidence": 0.85,
      "risk_level": "low|medium|high",
      "sources": ["Source 1", "Source 2"],
      "priority": 1
    }}
  ],
  "avoid_transfers": [
    {{
      "player": "Player Name",
      "reason": "Why to avoid (injury, rotation, etc.)",
      "severity": "critical|high|medium|low"
    }}
  ],
  "overall_confidence": 0.8,
  "total_cost": 0.5,
  "summary": "Brief overview of transfer strategy"
}}

Prioritize safety and value. Flag conflicts between predictions and reality."""

    CAPTAINCY_ANALYSIS = """Analyze captaincy options for FPL:

CURRENT GAMEWEEK: {gameweek}

YOUR TEAM:
{team_players}

AIRSENAL PREDICTIONS:
{predicted_points}

REAL-TIME INTELLIGENCE:
Breaking News: {news}
Form & Confidence: {form}
Tactical Setup: {tactics}
Weather: {weather}

SENTIMENT:
{sentiment}

FIXTURES:
{fixtures}

Provide JSON response:
{{
  "recommended_captain": {{
    "player": "Player Name",
    "player_id": 123,
    "reasoning": "Why this player (form, fixture, prediction, news)",
    "expected_points": 12.5,
    "confidence": 0.92,
    "risk_factors": ["List any risks"]
  }},
  "alternatives": [
    {{
      "player": "Player Name",
      "player_id": 456,
      "reasoning": "Why this is a good backup option",
      "expected_points": 11.0,
      "confidence": 0.85
    }}
  ],
  "avoid": [
    {{
      "player": "Player Name",
      "reason": "Why to avoid captaining them"
    }}
  ]
}}"""

    WEEKLY_REPORT = """Generate a comprehensive weekly FPL intelligence report:

GAMEWEEK: {gameweek}
DEADLINE: {deadline}

YOUR TEAM HEALTH:
{team_status}

KEY INTELLIGENCE:
{intelligence_summary}

AIRSENAL ANALYSIS:
{airsenal_summary}

TOP OPPORTUNITIES:
{opportunities}

RISKS & ALERTS:
{risks}

COMMUNITY TRENDS:
{community_trends}

Provide JSON response:
{{
  "executive_summary": "2-3 sentence overview of the week",
  "key_actions": [
    {{
      "action": "Description",
      "priority": "critical|high|medium|low",
      "deadline": "Time-sensitive info"
    }}
  ],
  "player_spotlight": [
    {{
      "player": "Name",
      "status": "hot|rising|falling|avoid",
      "reasoning": "Why they're noteworthy"
    }}
  ],
  "tactical_insight": "Strategic advice for this gameweek",
  "chip_recommendation": {{
    "should_activate": true/false,
    "chip": "wildcard|free_hit|bench_boost|triple_captain",
    "reasoning": "Why now or why wait"
  }},
  "confidence_score": 0.8
}}"""

    RISK_ASSESSMENT = """Assess risks in this FPL team:

TEAM: {team}
GAMEWEEK: {gameweek}

INTELLIGENCE:
Injuries: {injuries}
Rotation Risks: {rotation}
Suspensions: {suspensions}
Form Concerns: {form}

Provide JSON response:
{{
  "critical_risks": [
    {{
      "player": "Name",
      "risk": "Description",
      "severity": "critical",
      "action_required": "What to do",
      "deadline": "When to act"
    }}
  ],
  "medium_risks": [...],
  "low_risks": [...],
  "overall_health_score": 0.75,
  "immediate_actions_needed": 2
}}"""

    @staticmethod
    def format_transfer_prompt(**kwargs) -> str:
        """Format transfer analysis prompt."""
        return PromptTemplates.TRANSFER_ANALYSIS.format(**kwargs)

    @staticmethod
    def format_captaincy_prompt(**kwargs) -> str:
        """Format captaincy analysis prompt."""
        return PromptTemplates.CAPTAINCY_ANALYSIS.format(**kwargs)

    @staticmethod
    def format_weekly_report_prompt(**kwargs) -> str:
        """Format weekly report prompt."""
        return PromptTemplates.WEEKLY_REPORT.format(**kwargs)

    @staticmethod
    def format_risk_assessment_prompt(**kwargs) -> str:
        """Format risk assessment prompt."""
        return PromptTemplates.RISK_ASSESSMENT.format(**kwargs)
