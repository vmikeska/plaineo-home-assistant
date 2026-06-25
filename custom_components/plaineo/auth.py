"""Home Assistant auth callback for Plaineo config flow."""

from __future__ import annotations

import base64
import json

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import CONF_API_URL, DOMAIN

CALLBACK_PATH = "/api/plaineo/auth/callback"


def encode_flow_state(flow_id: str) -> str:
    """Encode state carried through Plaineo auth."""
    payload = {"flow_id": flow_id}
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    return encoded.rstrip("=")


def decode_flow_state(state: str) -> dict[str, str]:
    """Decode state carried through Plaineo auth."""
    padded = state + "=" * (-len(state) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    if not isinstance(payload, dict):
        raise ValueError("Invalid Plaineo auth state")
    return {
        "flow_id": str(payload["flow_id"]),
    }


async def async_setup_auth_view(hass: HomeAssistant) -> None:
    """Register the Plaineo auth callback view once."""
    registered_key = f"{DOMAIN}_auth_view_registered"
    if hass.data.get(registered_key):
        return
    hass.http.register_view(PlaineoAuthCallbackView())
    hass.data[registered_key] = True


class PlaineoAuthCallbackView(HomeAssistantView):
    """Receive Plaineo auth redirect and complete the active config flow."""

    url = CALLBACK_PATH
    name = "api:plaineo:auth:callback"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        """Handle Plaineo auth callback."""
        hass: HomeAssistant = request.app["hass"]
        code = request.query.get("code")
        state = request.query.get("state")
        error = request.query.get("error")

        if not state:
            return self._html("Plaineo setup failed: missing state.")

        try:
            flow_state = decode_flow_state(state)
            flow_id = flow_state["flow_id"]
        except (KeyError, ValueError, json.JSONDecodeError):
            return self._html("Plaineo setup failed: invalid state.")

        auth_flows = hass.data.setdefault(DOMAIN, {}).setdefault("auth_flows", {})
        flow_data = auth_flows.pop(flow_id, None)
        if not flow_data:
            return self._html("Plaineo setup failed: authorization flow expired.")

        api_url = flow_data[CONF_API_URL]
        redirect_uri = flow_data["redirect_uri"]

        if error:
            await hass.config_entries.flow.async_configure(
                flow_id,
                {"error": error, CONF_API_URL: api_url},
            )
            return self._html("Plaineo setup was cancelled.")

        if not code:
            return self._html("Plaineo setup failed: missing authorization code.")

        await hass.config_entries.flow.async_configure(
            flow_id,
            {
                CONF_API_URL: api_url,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        return self._html("Return to Home Assistant to finish Plaineo setup.")

    def _html(self, message: str) -> web.Response:
        return web.Response(
            text=f"""
<!doctype html>
<html>
  <head><title>Plaineo</title></head>
  <body>
    <p>{message}</p>
    <script>window.close();</script>
  </body>
</html>
""",
            content_type="text/html",
        )
