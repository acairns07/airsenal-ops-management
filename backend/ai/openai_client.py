"""OpenAI API client wrapper."""
import os
from typing import Dict, Any, Optional, List
from openai import OpenAI, AsyncOpenAI
from utils.logging import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    """Wrapper for OpenAI API with error handling and logging."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set - AI features will not work")
            self.client = None
            self.async_client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
            self.async_client = AsyncOpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized")

        self.model = os.getenv('AI_MODEL', 'gpt-4o-mini')
        self.temperature = float(os.getenv('AI_TEMPERATURE', '0.7'))

    def is_available(self) -> bool:
        """Check if OpenAI client is available."""
        return self.client is not None

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Send chat completion request to OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature (defaults to configured temp)
            max_tokens: Maximum tokens in response
            response_format: Optional response format (e.g., {"type": "json_object"})

        Returns:
            Response text or None if error
        """
        if not self.is_available():
            logger.error("OpenAI client not available - check API key")
            return None

        try:
            model = model or self.model
            temperature = temperature if temperature is not None else self.temperature

            logger.debug(
                f"Sending chat completion request",
                extra={
                    'model': model,
                    'temperature': temperature,
                    'message_count': len(messages)
                }
            )

            kwargs = {
                'model': model,
                'messages': messages,
                'temperature': temperature
            }

            if max_tokens:
                kwargs['max_tokens'] = max_tokens
            if response_format:
                kwargs['response_format'] = response_format

            response = await self.async_client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content
            usage = response.usage

            logger.info(
                f"Chat completion successful",
                extra={
                    'model': model,
                    'prompt_tokens': usage.prompt_tokens,
                    'completion_tokens': usage.completion_tokens,
                    'total_tokens': usage.total_tokens
                }
            )

            return content

        except Exception as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            return None

    async def structured_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send chat completion request expecting JSON response.

        Args:
            messages: List of message dicts
            model: Model to use
            temperature: Sampling temperature

        Returns:
            Parsed JSON response or None if error
        """
        import json

        response_text = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"}
        )

        if not response_text:
            return None

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            return None

    async def analyze_fpl_situation(
        self,
        system_prompt: str,
        user_prompt: str,
        expect_json: bool = True
    ) -> Optional[Any]:
        """
        Analyze FPL situation with OpenAI.

        Args:
            system_prompt: System message defining AI role
            user_prompt: User message with situation details
            expect_json: Whether to expect JSON response

        Returns:
            AI response (dict if expect_json, str otherwise)
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        if expect_json:
            return await self.structured_completion(messages)
        else:
            return await self.chat_completion(messages)


# Global client instance
openai_client = OpenAIClient()
