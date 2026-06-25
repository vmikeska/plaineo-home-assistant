"""Constants for the Plaineo Home Assistant integration."""

from __future__ import annotations

from homeassistant.const import CONF_API_KEY

DOMAIN = "plaineo"
DEFAULT_API_URL = "https://api.plaineo.com"

CONF_API_URL = "api_url"
CONF_INSTANCE_ID = "home_assistant_instance_id"

REQUEST_TIMEOUT_SECONDS = 65

__all__ = [
    "CONF_API_KEY",
    "CONF_API_URL",
    "CONF_INSTANCE_ID",
    "DEFAULT_API_URL",
    "DOMAIN",
    "REQUEST_TIMEOUT_SECONDS",
]
