"""Tests for the Plaineo Home Assistant API client."""

from __future__ import annotations

import asyncio

import pytest

from custom_components.plaineo.api import CannotConnect, InvalidAuth, PlaineoApiClient


class FakeResponse:
    def __init__(self, *, status: int = 200, payload=None, raise_error: Exception | None = None):
        self.status = status
        self.payload = {} if payload is None else payload
        self.raise_error = raise_error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        if self.raise_error:
            raise self.raise_error

    async def json(self, *, content_type=None):
        return self.payload


class FakeSession:
    def __init__(self, *responses: FakeResponse):
        self.responses = list(responses)
        self.requests = []

    async def request(self, method, url, **kwargs):
        self.requests.append({"method": method, "url": url, **kwargs})
        if self.responses:
            return self.responses.pop(0)
        return FakeResponse()


def run(coro):
    return asyncio.run(coro)


def test_validate_sends_status_request_with_api_key():
    session = FakeSession(FakeResponse(payload={"ok": True}))
    client = PlaineoApiClient(session, "https://api.plaineo.com", "secret")

    run(client.async_validate())

    assert session.requests == [
        {
            "method": "GET",
            "url": "https://api.plaineo.com/api/nabu/status",
            "headers": {"Accept": "application/json", "X-API-Key": "secret"},
        }
    ]


def test_api_url_ending_in_api_does_not_duplicate_api_path():
    session = FakeSession(FakeResponse(payload={"ok": True}))
    client = PlaineoApiClient(session, "https://api.plaineo.com/api", "secret")

    run(client.async_validate())

    assert session.requests[0]["url"] == "https://api.plaineo.com/api/nabu/status"


def test_exchange_home_assistant_code_posts_code_and_redirect_uri():
    session = FakeSession(FakeResponse(payload={"access_token": "sc_new"}))
    client = PlaineoApiClient(session, "https://api.plaineo.com", "")

    token = run(client.async_exchange_home_assistant_code(code="abc", redirect_uri="http://ha/callback"))

    assert token == "sc_new"
    assert session.requests[0]["method"] == "POST"
    assert session.requests[0]["url"] == "https://api.plaineo.com/oauth/home-assistant/token"
    assert session.requests[0]["json"] == {
        "grant_type": "authorization_code",
        "code": "abc",
        "redirect_uri": "http://ha/callback",
    }


def test_exchange_home_assistant_code_requires_access_token():
    session = FakeSession(FakeResponse(payload={"ok": True}))
    client = PlaineoApiClient(session, "https://api.plaineo.com", "")

    with pytest.raises(CannotConnect):
        run(client.async_exchange_home_assistant_code(code="abc", redirect_uri="http://ha/callback"))


def test_revoke_home_assistant_token_posts_configured_token():
    session = FakeSession(FakeResponse())
    client = PlaineoApiClient(session, "https://api.plaineo.com", "sc_secret")

    run(client.async_revoke_home_assistant_token())

    assert session.requests == [
        {
            "method": "POST",
            "url": "https://api.plaineo.com/oauth/home-assistant/revoke",
            "headers": {"Accept": "application/json", "Content-Type": "application/json"},
            "json": {"token": "sc_secret"},
        }
    ]


def test_conversation_maps_backend_payload():
    session = FakeSession(FakeResponse(payload={
        "speech": "Added milk.",
        "continueConversation": True,
        "conversationId": "conv-2",
    }))
    client = PlaineoApiClient(session, "https://api.plaineo.com", "secret")

    result = run(client.async_conversation(
        text="buy milk",
        language="en-US",
        conversation_id="conv-1",
        home_assistant_instance_id="ha-1",
        device_id="device-1",
        satellite_id="satellite-1",
    ))

    assert result.speech == "Added milk."
    assert result.continue_conversation is True
    assert result.conversation_id == "conv-2"
    assert session.requests[0]["json"]["text"] == "buy milk"
    assert session.requests[0]["json"]["satelliteId"] == "satellite-1"


def test_unauthorized_api_response_raises_invalid_auth():
    session = FakeSession(FakeResponse(status=401, payload={"error": "invalid"}))
    client = PlaineoApiClient(session, "https://api.plaineo.com", "bad")

    with pytest.raises(InvalidAuth):
        run(client.async_validate())
