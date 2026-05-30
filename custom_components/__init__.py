"""The Ecowitt Weather Station Component — patched to handle missing 'model' field (GW1200 firmware)."""

from __future__ import annotations

import aioecowitt.station as _station_module
from aioecowitt import EcoWittListener
from aiohttp import web

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant, callback

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

type EcowittConfigEntry = ConfigEntry[EcoWittListener]

# ── Patch: add default 'model' if device (e.g. GW1200) does not send it ──────
_orig_extract_station = _station_module.extract_station


def _patched_extract_station(data: dict) -> _station_module.EcoWittStation:
    if "model" not in data:
        data["model"] = data.get("stationtype", "GW1200A")
    return _orig_extract_station(data)


_station_module.extract_station = _patched_extract_station

try:
    import aioecowitt.server as _server_module
    if hasattr(_server_module, "extract_station"):
        _server_module.extract_station = _patched_extract_station
except Exception:
    pass
# ─────────────────────────────────────────────────────────────────────────────


async def async_setup_entry(hass: HomeAssistant, entry: EcowittConfigEntry) -> bool:
    """Set up the Ecowitt component from UI."""
    ecowitt = entry.runtime_data = EcoWittListener()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_webhook(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Handle webhook callback."""
        return await ecowitt.handler(request)

    webhook.async_register(
        hass, DOMAIN, entry.title, entry.data[CONF_WEBHOOK_ID], handle_webhook
    )

    @callback
    def _stop_ecowitt(_: Event) -> None:
        """Stop the Ecowitt listener."""
        webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _stop_ecowitt)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EcowittConfigEntry) -> bool:
    """Unload a config entry."""
    webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
