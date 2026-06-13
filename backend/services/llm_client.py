"""OpenAI-compatible LLM client factory."""

from __future__ import annotations

from openai import OpenAI

from services.config import get_settings


def get_llm_client() -> OpenAI:
    """Return an OpenAI SDK client configured from environment.

    Regolo model ids are case-sensitive. Use a model that supports tool calling.
    """
    settings = get_settings()
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)


def get_model() -> str:
    return get_settings().MODEL
