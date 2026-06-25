"""Tests for the Plaineo conversation entity."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from custom_components.plaineo.api import CannotConnect, InvalidAuth, PlaineoConversationResult
from custom_components.plaineo.const import DOMAIN
from custom_components.plaineo.conversation import PlaineoConversationEntity


def run(coro):
    return asyncio.run(coro)


class FakeChatLog:
    def __init__(self):
        self.contents = []

    def async_add_assistant_content_without_tools(self, content):
        self.contents.append(content)


class FakeEntry:
    entry_id = "entry-1"

    def __init__(self):
        self.reauth_started = False
        self.reauth_hass = None

    def async_start_reauth(self, hass):
        self.reauth_started = True
        self.reauth_hass = hass


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    async def async_conversation(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.result


def make_hass(client):
    return SimpleNamespace(
        config=SimpleNamespace(uuid="ha-uuid"),
        data={DOMAIN: {"entry-1": client}},
    )


def make_input():
    return SimpleNamespace(
        text="buy milk",
        language="en-US",
        conversation_id="conv-1",
        device_id="device-1",
        satellite_id="satellite-1",
        agent_id="agent-1",
    )


def test_successful_conversation_forwards_transcript_and_returns_speech():
    client = FakeClient(PlaineoConversationResult(
        speech="Added milk.",
        continue_conversation=False,
        conversation_id="conv-2",
        raw={},
    ))
    entry = FakeEntry()
    entity = PlaineoConversationEntity(make_hass(client), entry)
    chat_log = FakeChatLog()

    result = run(entity._async_handle_message(make_input(), chat_log))

    assert client.calls == [{
        "text": "buy milk",
        "language": "en-US",
        "conversation_id": "conv-1",
        "home_assistant_instance_id": "ha-uuid",
        "device_id": "device-1",
        "satellite_id": "satellite-1",
    }]
    assert result.response.speech == "Added milk."
    assert result.conversation_id == "conv-2"
    assert result.continue_conversation is False
    assert chat_log.contents[0].content == "Added milk."


def test_invalid_auth_starts_reauth_and_returns_error_speech():
    client = FakeClient(error=InvalidAuth("bad key"))
    entry = FakeEntry()
    hass = make_hass(client)
    entity = PlaineoConversationEntity(hass, entry)

    result = run(entity._async_handle_message(make_input(), FakeChatLog()))

    assert entry.reauth_started is True
    assert entry.reauth_hass is hass
    assert result.response.speech == "Plaineo rejected the configured API key."
    assert result.continue_conversation is False


def test_cannot_connect_returns_temporary_error_without_reauth():
    client = FakeClient(error=CannotConnect("offline"))
    entry = FakeEntry()
    entity = PlaineoConversationEntity(make_hass(client), entry)

    result = run(entity._async_handle_message(make_input(), FakeChatLog()))

    assert entry.reauth_started is False
    assert result.response.speech == "I could not reach Plaineo right now."
    assert result.continue_conversation is False
