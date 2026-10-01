"""
http_adapter.py — generic authenticated REST client for custom CRM/logistics
APIs whose shape isn't known in advance. Configure CUSTOM_API_BASE_URL and
CUSTOM_API_KEY in .env, then call get()/post() with the endpoint's relative
path. When DRY_RUN is true (the default), post() logs the payload instead of
sending it — reads (get) always execute live since they have no side effects.

Public functions:
  - get(path, params=None) -> dict
  - post(path, payload) -> dict
"""

import requests

from config import settings


def _base_url() -> str:
    if not settings.custom_api_base_url:
        raise EnvironmentError(
            "[http_adapter] CUSTOM_API_BASE_URL is not set in .env."
        )
    return settings.custom_api_base_url.rstrip("/")


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if settings.custom_api_key:
        headers["Authorization"] = f"Bearer {settings.custom_api_key}"
    return headers


def get(path: str, params: dict = None) -> dict:
    """GET a JSON resource from the configured custom API."""
    url = f"{_base_url()}/{path.lstrip('/')}"
    resp = requests.get(url, headers=_headers(), params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def post(path: str, payload: dict) -> dict:
    """
    POST a JSON payload to the configured custom API, unless DRY_RUN is
    enabled (default), in which case the payload is logged and not sent.
    """
    if settings.dry_run:
        print(f"[http_adapter] DRY_RUN — would POST to '{path}': {payload}")
        return {"dry_run": True, "path": path, "payload": payload}

    url = f"{_base_url()}/{path.lstrip('/')}"
    resp = requests.post(url, headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()
