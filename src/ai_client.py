"""
Multi-Provider AI Client
Supports Anthropic Claude, OpenAI GPT, and Google Gemini
"""

import os
from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod
import logging

# AI Provider imports
import anthropic
import openai
import google.generativeai as genai

logger = logging.getLogger(__name__)

class AIClient(ABC):
    """Abstract base class for AI clients"""

    @abstractmethod
    def generate_text(self, prompt: str, max_tokens: int = 4000) -> str:
        """Generate text response from AI"""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        pass

class ClaudeClient(AIClient):
    """Anthropic Claude client"""

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate_text(self, prompt: str, max_tokens: int = 4000) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """Approximate token count for Claude"""
        # Claude typically uses ~4 characters per token
        return len(text) // 4

class OpenAIClient(AIClient):
    """OpenAI GPT client"""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def generate_text(self, prompt: str, max_tokens: int = 4000) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """Approximate token count for OpenAI"""
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))
        except:
            # Fallback approximation
            return len(text) // 4

class GeminiClient(AIClient):
    """Google Gemini client"""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def generate_text(self, prompt: str, max_tokens: int = 4000) -> str:
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """Approximate token count for Gemini"""
        # Gemini typically uses ~4 characters per token
        return len(text) // 4

class AIClientFactory:
    """Factory for creating AI clients"""

    @staticmethod
    def create_client(provider: str, api_key: str, model: Optional[str] = None) -> AIClient:
        """
        Create an AI client for the specified provider

        Args:
            provider: 'anthropic', 'openai', or 'gemini'
            api_key: API key for the provider
            model: Optional specific model name

        Returns:
            AIClient instance
        """
        provider = provider.lower()

        if provider == 'anthropic':
            return ClaudeClient(api_key, model or "claude-3-5-sonnet-20241022")
        elif provider == 'openai':
            return OpenAIClient(api_key, model or "gpt-4o")
        elif provider == 'gemini':
            return GeminiClient(api_key, model or "gemini-1.5-pro")
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")

    @staticmethod
    def get_available_providers() -> List[str]:
        """Get list of available AI providers"""
        return ['anthropic', 'openai', 'gemini']