"""Config flow for Plaineo."""

from __future__ import annotations

from urllib.parse import urlencode
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import get_url

from .api import CannotConnect, InvalidAuth, PlaineoApiClient
from .auth import CALLBACK_PATH, async_setup_auth_view, encode_flow_state
from .const import CONF_API_URL, DEFAULT_API_URL, DOMAIN

SETUP_GUIDE_URL = "https://dev.plaineo.com/home-assistant"
ESPHOME_INTEGRATION_URL = "/config/integrations/integration/esphome"
AUTH_CODE = "code"
REDIRECT_URI = "redirect_uri"


async def _validate_input(hass: HomeAssistant, user_input: dict[str, Any]) -> None:
    client = PlaineoApiClient(
        async_get_clientsession(hass),
        user_input[CONF_API_URL],
        user_input[CONF_API_KEY],
    )
    await client.async_validate()


class PlaineoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Plaineo config flow."""

    VERSION = 1
    _auth_data: dict[str, str] | None = None
    _auth_error: str | None = None
    _auth_url: str | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return await self._start_external_auth(DEFAULT_API_URL)

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> config_entries.ConfigFlowResult:
        """Reauthorize Plaineo when the stored token is no longer valid."""
        return await self._start_external_auth(str(entry_data.get(CONF_API_URL) or DEFAULT_API_URL))

    async def async_step_auth(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Receive data from the external Plaineo auth callback."""
        if not user_input:
            if self._auth_url:
                return self.async_external_step(
                    step_id="auth",
                    url=self._auth_url,
                )
            return await self._start_external_auth(DEFAULT_API_URL)

        if user_input.get("error"):
            self._auth_error = "auth_cancelled"
            return self.async_external_step_done(next_step_id="finish")

        self._auth_data = {
            CONF_API_URL: str(user_input[CONF_API_URL]).rstrip("/"),
            AUTH_CODE: str(user_input[AUTH_CODE]).strip(),
            REDIRECT_URI: str(user_input[REDIRECT_URI]).strip(),
        }
        return self.async_external_step_done(next_step_id="finish")

    async def async_step_finish(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Finish after external Plaineo auth."""
        if self._auth_error:
            return self.async_abort(reason=self._auth_error)

        if not self._auth_data:
            return self.async_abort(reason="cannot_connect")

        if user_input is None:
            return self.async_show_form(
                step_id="finish",
                data_schema=vol.Schema({}),
                description_placeholders=self._success_description_placeholders(),
                last_step=True,
            )

        try:
            api_key = await self._exchange_auth_code(self._auth_data)
            entry_data = {
                CONF_API_URL: self._auth_data[CONF_API_URL],
                CONF_API_KEY: api_key,
            }
            await _validate_input(self.hass, entry_data)
        except InvalidAuth:
            return self.async_abort(reason="invalid_auth")
        except CannotConnect:
            return self.async_abort(reason="cannot_connect")

        await self.async_set_unique_id(DOMAIN)
        if self.source == config_entries.SOURCE_REAUTH:
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data=entry_data,
            )

        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Plaineo", data=entry_data)

    async def _start_external_auth(self, api_url: str) -> config_entries.ConfigFlowResult:
        """Start browser-based Plaineo account linking."""
        await async_setup_auth_view(self.hass)
        api_url = api_url.rstrip("/")
        redirect_uri = self._callback_url()
        self.hass.data.setdefault(DOMAIN, {}).setdefault("auth_flows", {})[self.flow_id] = {
            CONF_API_URL: api_url,
            "redirect_uri": redirect_uri,
        }
        state = encode_flow_state(self.flow_id)
        query = urlencode({
            "response_type": "code",
            "client_id": "home-assistant",
            "redirect_uri": redirect_uri,
            "state": state,
        })
        self._auth_url = f"{api_url}/oauth/home-assistant/authorize?{query}"
        return self.async_external_step(
            step_id="auth",
            url=self._auth_url,
        )

    def _callback_url(self) -> str:
        """Return the absolute callback URL for this Home Assistant instance."""
        try:
            base_url = get_url(self.hass, prefer_external=True)
        except Exception:
            base_url = get_url(self.hass, prefer_external=False)
        return f"{base_url.rstrip('/')}{CALLBACK_PATH}"

    async def _exchange_auth_code(self, auth_data: dict[str, str]) -> str:
        """Exchange a one-time auth code for a Plaineo API key."""
        client = PlaineoApiClient(
            async_get_clientsession(self.hass),
            auth_data[CONF_API_URL],
            "",
        )
        return await client.async_exchange_home_assistant_code(
            code=auth_data[AUTH_CODE],
            redirect_uri=auth_data[REDIRECT_URI],
        )

    def _success_description_placeholders(self) -> dict[str, str]:
        """Return next-step instructions for the setup success dialog."""
        if self.hass.config_entries.async_entries("esphome"):
            esphome_next_step = (
                "ESPHome is installed. Open "
                f"[ESPHome integrations]({ESPHOME_INTEGRATION_URL}) "
                "and select your Home Assistant Voice device, then set its assistant to Plaineo."
            )
        else:
            esphome_next_step = (
                "ESPHome still needs to be installed before you can assign Plaineo "
                "to a Home Assistant Voice satellite."
            )

        return {
            "setup_guide_url": SETUP_GUIDE_URL,
            "esphome_next_step": esphome_next_step,
        }
