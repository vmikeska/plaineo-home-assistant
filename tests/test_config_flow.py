"""Tests for the Plaineo Home Assistant config flow."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import custom_components.plaineo.config_flow as config_flow
from custom_components.plaineo.const import CONF_API_URL, DEFAULT_API_URL, DOMAIN
from homeassistant.const import CONF_API_KEY


def run(coro):
    return asyncio.run(coro)


class FakeHttp:
    def __init__(self):
        self.views = []

    def register_view(self, view):
        self.views.append(view)


class FakeConfigEntries:
    def __init__(self, has_esphome=True):
        self.has_esphome = has_esphome

    def async_entries(self, domain):
        if domain == "esphome" and self.has_esphome:
            return [object()]
        return []


def make_hass(*, has_esphome=True):
    return SimpleNamespace(
        data={},
        http=FakeHttp(),
        base_url="http://homeassistant.local:8123",
        session="session",
        config_entries=FakeConfigEntries(has_esphome=has_esphome),
    )


def make_flow(*, source="user", has_esphome=True):
    flow = config_flow.PlaineoConfigFlow()
    flow.hass = make_hass(has_esphome=has_esphome)
    flow.flow_id = "flow-123"
    flow.source = source
    return flow


async def noop_validate(hass, user_input):
    return None


def auth_query(result):
    parsed = urlparse(result["url"])
    return parse_qs(parsed.query)


def test_user_step_starts_external_auth_with_home_assistant_oauth_params():
    flow = make_flow()

    result = run(flow.async_step_user())
    query = auth_query(result)

    assert result["type"] == "external"
    assert result["url"].startswith(f"{DEFAULT_API_URL}/oauth/home-assistant/authorize?")
    assert query["client_id"] == ["home-assistant"]
    assert query["response_type"] == ["code"]
    assert query["redirect_uri"] == ["http://homeassistant.local:8123/api/plaineo/auth/callback"]
    assert query["state"]
    assert flow.hass.data[DOMAIN]["auth_flows"]["flow-123"] == {
        CONF_API_URL: DEFAULT_API_URL,
        "redirect_uri": "http://homeassistant.local:8123/api/plaineo/auth/callback",
    }


def test_auth_callback_stores_code_without_exchanging_token(monkeypatch):
    flow = make_flow()
    run(flow.async_step_user())

    async def fail_exchange(auth_data):
        raise AssertionError("Token exchange must not happen during callback")

    monkeypatch.setattr(flow, "_exchange_auth_code", fail_exchange)
    result = run(flow.async_step_auth({
        CONF_API_URL: DEFAULT_API_URL,
        "code": "short-code",
        "redirect_uri": "http://homeassistant.local:8123/api/plaineo/auth/callback",
    }))

    assert result == {"type": "external_done", "step_id": "finish"}
    assert flow._auth_data == {
        CONF_API_URL: DEFAULT_API_URL,
        "code": "short-code",
        "redirect_uri": "http://homeassistant.local:8123/api/plaineo/auth/callback",
    }


def test_reopening_external_auth_step_returns_external_step_instead_of_abort():
    flow = make_flow()
    first = run(flow.async_step_user())

    second = run(flow.async_step_auth(None))

    assert second["type"] == "external"
    assert second["step_id"] == "auth"
    assert second["url"] == first["url"]


def test_cancelled_auth_moves_to_finish_then_aborts():
    flow = make_flow()
    run(flow.async_step_user())

    auth_result = run(flow.async_step_auth({"error": "access_denied"}))
    finish_result = run(flow.async_step_finish({}))

    assert auth_result == {"type": "external_done", "step_id": "finish"}
    assert finish_result == {"type": "abort", "reason": "auth_cancelled"}


def test_finish_before_submit_shows_confirmation_without_exchanging_token(monkeypatch):
    flow = make_flow()
    run(flow.async_step_user())
    run(flow.async_step_auth({
        CONF_API_URL: DEFAULT_API_URL,
        "code": "short-code",
        "redirect_uri": "http://homeassistant.local:8123/api/plaineo/auth/callback",
    }))

    async def fail_exchange(auth_data):
        raise AssertionError("Token exchange must wait for Submit")

    monkeypatch.setattr(flow, "_exchange_auth_code", fail_exchange)
    result = run(flow.async_step_finish(None))

    assert result["type"] == "form"
    assert result["step_id"] == "finish"
    assert result["last_step"] is True
    assert "ESPHome is installed" in result["description_placeholders"]["esphome_next_step"]


def test_final_submit_exchanges_code_validates_and_creates_entry(monkeypatch):
    flow = make_flow()
    run(flow.async_step_user())
    run(flow.async_step_auth({
        CONF_API_URL: DEFAULT_API_URL,
        "code": "short-code",
        "redirect_uri": "http://homeassistant.local:8123/api/plaineo/auth/callback",
    }))

    async def exchange(auth_data):
        assert auth_data["code"] == "short-code"
        return "sc_new"

    monkeypatch.setattr(flow, "_exchange_auth_code", exchange)
    monkeypatch.setattr(config_flow, "_validate_input", noop_validate)

    result = run(flow.async_step_finish({}))

    assert result == {
        "type": "create_entry",
        "title": "Plaineo",
        "data": {
            CONF_API_URL: DEFAULT_API_URL,
            CONF_API_KEY: "sc_new",
        },
    }


def test_reauth_updates_existing_entry_instead_of_creating_duplicate(monkeypatch):
    flow = make_flow(source="reauth")
    flow.reauth_entry = SimpleNamespace(data={CONF_API_URL: DEFAULT_API_URL, CONF_API_KEY: "old"})
    run(flow.async_step_reauth({CONF_API_URL: DEFAULT_API_URL}))
    run(flow.async_step_auth({
        CONF_API_URL: DEFAULT_API_URL,
        "code": "short-code",
        "redirect_uri": "http://homeassistant.local:8123/api/plaineo/auth/callback",
    }))

    async def exchange(auth_data):
        return "sc_reauth"

    monkeypatch.setattr(flow, "_exchange_auth_code", exchange)
    monkeypatch.setattr(config_flow, "_validate_input", noop_validate)

    result = run(flow.async_step_finish({}))

    assert result == {"type": "abort", "reason": "reauth_successful"}
    assert flow.reauth_entry.data == {
        CONF_API_URL: DEFAULT_API_URL,
        CONF_API_KEY: "sc_reauth",
    }
    assert flow.reauth_entry.reload_scheduled is True
