"""Plaineo integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CannotConnect, PlaineoApiClient
from .auth import async_setup_auth_view
from .const import CONF_API_URL, DOMAIN

PLATFORMS: list[Platform] = [Platform.CONVERSATION]
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Plaineo integration helpers."""
    await async_setup_auth_view(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Plaineo from a config entry."""
    await async_setup_auth_view(hass)
    session = async_get_clientsession(hass)
    client = PlaineoApiClient(
        session,
        entry.data[CONF_API_URL],
        entry.data[CONF_API_KEY],
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Plaineo."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Revoke the Plaineo token when the config entry is removed."""
    client = PlaineoApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_API_URL],
        entry.data[CONF_API_KEY],
    )
    try:
        await client.async_revoke_home_assistant_token()
    except CannotConnect:
        _LOGGER.warning("Could not revoke Plaineo token while removing integration")
