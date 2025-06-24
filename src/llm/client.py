from openai import AsyncOpenAI
from src.config import get_settings
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Global LLM client instance
_llm_client: Optional[AsyncOpenAI] = None


def get_llm_client() -> AsyncOpenAI:
    """Get or create the LLM client instance"""
    global _llm_client
    
    if _llm_client is None:
        settings = get_settings()
        _llm_client = AsyncOpenAI(
            api_key=settings.google_api_key,
            base_url=settings.google_openai_base_url
        )
        logger.info("Initialized Gemini LLM client")
    
    return _llm_client


async def generate_completion(
    messages: list[Dict[str, str]],
    model: str = "gemini-2.5-flash",
    temperature: float = 0.1,
    max_tokens: int = 2048,
    response_format: Optional[Dict[str, Any]] = None
) -> str:
    """Generate a completion using the LLM"""
    client = get_llm_client()
    
    try:
        # Note: Gemini doesn't support response_format parameter yet
        # We'll handle JSON parsing in the prompt
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        logger.info(f"Calling LLM with model={model}, temperature={temperature}")
        response = await client.chat.completions.create(**kwargs)
        
        if not response.choices:
            raise ValueError("No response from LLM")
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")
        
        logger.info(f"LLM response received, length={len(content)}")
        return content
        
    except Exception as e:
        logger.error(f"LLM generation failed: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise


def reset_llm_client():
    """Reset the LLM client (useful for testing)"""
    global _llm_client
    _llm_client = None