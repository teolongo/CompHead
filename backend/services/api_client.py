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
        self._client = httpx.Client(timeout=10.0)

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

    def get_all_pages(
        self,
        path: str,
        params: dict | None = None,
        limit: int = 200,
        data_key: str = "data",
    ) -> list[dict]:
        """Page through a list endpoint, following ``pagination.total``.

        Requests pages of ``limit`` rows (capped at the API max of 200),
        advancing ``offset`` by the number of rows collected so far, until the
        collected rows reach ``pagination.total`` or a page returns no rows.
        The caller's ``params`` dict is never mutated.
        """
        page_limit = min(max(int(limit), 1), 200)
        base_params = dict(params or {})
        collected: list[dict] = []
        offset = 0

        while True:
            page_params = dict(base_params)
            page_params["limit"] = page_limit
            page_params["offset"] = offset
            payload = self.get(path, params=page_params)
            rows = payload.get(data_key) or []
            collected.extend(rows)

            if not rows:
                break
            total = (payload.get("pagination") or {}).get("total")
            if total is None or len(collected) >= int(total):
                break
            offset = len(collected)

        return collected

    def close(self) -> None:
        self._client.close()


def get_client() -> MockApiClient:
    return MockApiClient(get_settings())
