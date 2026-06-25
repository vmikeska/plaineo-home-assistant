"""Plaineo API client used by the Home Assistant conversation agent."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import REQUEST_TIMEOUT_SECONDS


class PlaineoApiError(Exception):
    """Base Plaineo API error."""


class CannotConnect(PlaineoApiError):
    """Raised when Home Assistant cannot reach Plaineo."""


class InvalidAuth(PlaineoApiError):
    """Raised when the Plaineo API key is rejected."""


@dataclass(slots=True)
class PlaineoConversationResult:
    """Conversation response returned by Plaineo."""

    speech: str
    continue_conversation: bool
    conversation_id: str | None
    raw: dict[str, Any]


class PlaineoApiClient:
    """Small HTTP client for the Plaineo Nabu connector."""

    def __init__(self, session: ClientSession, api_url: str, api_key: str) -> None:
        self._session = session
        self._api_url = api_url.rstrip("/")
        self._api_key = api_key

    async def async_validate(self) -> None:
        """Validate the configured URL and API key."""
        await self._request("GET", "/api/nabu/status")

    async def async_conversation(
        self,
        *,
        text: str,
        language: str,
        conversation_id: str | None,
        home_assistant_instance_id: str | None,
        device_id: str | None,
        satellite_id: str | None,
    ) -> PlaineoConversationResult:
        """Send an already-transcribed utterance to Plaineo."""
        data = await self._request(
            "POST",
            "/api/nabu/conversation",
            json={
                "text": text,
                "language": language,
                "conversationId": conversation_id,
                "homeAssistantInstanceId": home_assistant_instance_id,
                "deviceId": device_id,
                "satelliteId": satellite_id,
            },
        )

        speech = str(data.get("speech") or "Plaineo did not return a spoken response.")
        return PlaineoConversationResult(
            speech=speech,
            continue_conversation=bool(data.get("continueConversation")),
            conversation_id=data.get("conversationId"),
            raw=data,
        )

    async def async_exchange_home_assistant_code(
        self,
        *,
        code: str,
        redirect_uri: str,
    ) -> str:
        """Exchange a one-time Home Assistant auth code for a Plaineo API key."""
        data = await self._request(
            "POST",
            "/oauth/home-assistant/token",
            json={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        access_token = data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise CannotConnect("Plaineo did not return an access token")
        return access_token

    async def async_revoke_home_assistant_token(self) -> None:
        """Revoke the configured Home Assistant token in Plaineo."""
        url = self._build_url("/oauth/home-assistant/revoke")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                response = await self._session.request(
                    "POST",
                    url,
                    headers=headers,
                    json={"token": self._api_key},
                )
                async with response:
                    response.raise_for_status()
        except (asyncio.TimeoutError, ClientResponseError, ClientError) as err:
            raise CannotConnect(f"Could not revoke Plaineo token at {url}") from err

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = self._build_url(path)
        headers = {
            "Accept": "application/json",
        }
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        if method.upper() != "GET":
            headers["Content-Type"] = "application/json"

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                response = await self._session.request(method, url, headers=headers, **kwargs)
                async with response:
                    if response.status in (401, 403):
                        raise InvalidAuth("Plaineo API key was rejected")
                    response.raise_for_status()
                    payload = await response.json(content_type=None)
        except InvalidAuth:
            raise
        except (asyncio.TimeoutError, ClientResponseError, ClientError) as err:
            raise CannotConnect(f"Could not reach Plaineo at {url}") from err

        if not isinstance(payload, dict):
            raise CannotConnect("Plaineo returned an unexpected response")

        return payload

    def _build_url(self, path: str) -> str:
        if self._api_url.endswith("/api") and path.startswith("/api/"):
            return f"{self._api_url}{path[4:]}"
        return f"{self._api_url}{path}"
