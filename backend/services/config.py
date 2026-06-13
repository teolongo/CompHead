"""Environment-backed settings for the company brain backend."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    LLM_BASE_URL: str
    LLM_API_KEY: str
    MODEL: str
    MOCK_API_BASE_URL: str
    MOCK_API_TOKEN: str
    PUBLIC_BASE_URL: str


def get_settings() -> Settings:
    return Settings(
        LLM_BASE_URL=os.environ.get("LLM_BASE_URL", "https://api.regolo.ai/v1").strip(),
        LLM_API_KEY=_require("LLM_API_KEY"),
        MODEL=_require("MODEL"),
        MOCK_API_BASE_URL=os.environ.get(
            "MOCK_API_BASE_URL", "https://aldente.yellowtest.it"
        ).strip(),
        MOCK_API_TOKEN=_require("MOCK_API_TOKEN"),
        PUBLIC_BASE_URL=os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").strip(),
    )
