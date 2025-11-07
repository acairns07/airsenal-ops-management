"""AI module for OpenAI integration and recommendation generation."""
from .openai_client import openai_client, OpenAIClient
from .prompt_templates import PromptTemplates
from .recommendation_engine import RecommendationEngine, recommendation_engine
from .context_builder import ContextBuilder

__all__ = [
    'openai_client',
    'OpenAIClient',
    'PromptTemplates',
    'RecommendationEngine',
    'recommendation_engine',
    'ContextBuilder'
]
