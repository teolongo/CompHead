"""Authenticated HTTP client for the Al Dente mock APIs."""

from __future__ import annotations

import httpx

from services.config import Settings, get_settings


class MockApiError(Exception):
    """Raised when a mock API request fails."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


class MockApiClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.MOCK_API_BASE_URL.rstrip("/")
        self._token = settings.MOCK_API_TOKEN
        self._client = httpx.Client(timeout=30.0)

    def get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self._base_url}{path if path.startswith('/') else f'/{path}'}"
        response = self._client.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        if response.status_code >= 400:
            text = response.text
            if response.status_code == 401 and "access_denied" in text:
                raise MockApiError(
                    response.status_code,
                    f"Mock API access denied (401 access_denied): {text}",
                )
            raise MockApiError(
                response.status_code,
                f"Mock API error {response.status_code}: {text}",
            )
        return response.json()

    def close(self) -> None:
        self._client.close()


def get_client() -> MockApiClient:
    return MockApiClient(get_settings())
