from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_MONITOR_MINUTES,
    DEFAULT_MONITOR_MINUTES,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import MagentaCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = MagentaCoordinator(
        hass,
        entry.data["username"],
        entry.data["password"],
        entry.options.get(CONF_MONITOR_MINUTES, DEFAULT_MONITOR_MINUTES),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: MagentaCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_close()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
