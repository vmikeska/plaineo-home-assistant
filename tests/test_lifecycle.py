"""Tests for Plaineo Home Assistant setup/unload/remove hooks."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import custom_components.plaineo as integration
from custom_components.plaineo.api import CannotConnect
from custom_components.plaineo.const import CONF_API_URL
from homeassistant.const import CONF_API_KEY


def run(coro):
    return asyncio.run(coro)


class FakeConfigEntries:
    def __init__(self, unload_ok=True):
        self.unload_ok = unload_ok
        self.unloaded = []

    async def async_unload_platforms(self, entry, platforms):
        self.unloaded.append((entry, platforms))
        return self.unload_ok

    async def async_forward_entry_setups(self, entry, platforms):
        self.forwarded = (entry, platforms)


class FakeEntry:
    entry_id = "entry-1"
    data = {
        CONF_API_URL: "https://api.plaineo.com",
        CONF_API_KEY: "sc_secret",
    }


class FakeClient:
    instances = []
    fail_revoke = False

    def __init__(self, session, api_url, api_key):
        self.session = session
        self.api_url = api_url
        self.api_key = api_key
        self.revoked = False
        FakeClient.instances.append(self)

    async def async_revoke_home_assistant_token(self):
        if self.fail_revoke:
            raise CannotConnect("offline")
        self.revoked = True


def test_unload_removes_client_without_revoking(monkeypatch):
    hass = SimpleNamespace(
        data={integration.DOMAIN: {"entry-1": object()}},
        config_entries=FakeConfigEntries(unload_ok=True),
    )
    entry = FakeEntry()

    result = run(integration.async_unload_entry(hass, entry))

    assert result is True
    assert "entry-1" not in hass.data[integration.DOMAIN]


def test_failed_unload_keeps_client_registered():
    client = object()
    hass = SimpleNamespace(
        data={integration.DOMAIN: {"entry-1": client}},
        config_entries=FakeConfigEntries(unload_ok=False),
    )
    entry = FakeEntry()

    result = run(integration.async_unload_entry(hass, entry))

    assert result is False
    assert hass.data[integration.DOMAIN]["entry-1"] is client


def test_remove_entry_revokes_configured_token(monkeypatch):
    FakeClient.instances = []
    FakeClient.fail_revoke = False
    monkeypatch.setattr(integration, "PlaineoApiClient", FakeClient)
    monkeypatch.setattr(integration, "async_get_clientsession", lambda hass: "session")
    hass = SimpleNamespace()

    run(integration.async_remove_entry(hass, FakeEntry()))

    assert len(FakeClient.instances) == 1
    assert FakeClient.instances[0].api_key == "sc_secret"
    assert FakeClient.instances[0].revoked is True


def test_remove_entry_does_not_raise_when_revoke_fails(monkeypatch):
    FakeClient.instances = []
    FakeClient.fail_revoke = True
    monkeypatch.setattr(integration, "PlaineoApiClient", FakeClient)
    monkeypatch.setattr(integration, "async_get_clientsession", lambda hass: "session")
    hass = SimpleNamespace()

    run(integration.async_remove_entry(hass, FakeEntry()))

    assert len(FakeClient.instances) == 1
