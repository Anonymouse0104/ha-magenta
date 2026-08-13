from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MONITOR_MINUTES, DEFAULT_MONITOR_MINUTES, DOMAIN
from .coordinator import MagentaCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: MagentaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            MagentaSensor(coordinator, entry, "Aanname", "begin_op"),
            MagentaSensor(coordinator, entry, "Overdracht uitgifte", "begin_brw"),
            MagentaSensor(coordinator, entry, "Afsluiten incident", "einde_op"),
            MagentaSensor(coordinator, entry, "Ingezette eenheden", "units"),
            MagentaSensor(coordinator, entry, "Kladblokregels", "kladblok_count"),
            MagentaSensor(coordinator, entry, "Laatste incident", "incident_number"),
            MagentaSensor(coordinator, entry, "Laatste kladblokregel", "last_kladblok"),
            MagentaSensor(coordinator, entry, "Kladblokmonitor actief", "monitoring"),
            MagentaSensor(
                coordinator,
                entry,
                "Kladblokmonitor tot",
                "monitor_until",
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
        ]
    )


class MagentaSensor(CoordinatorEntity[MagentaCoordinator], SensorEntity):
    def __init__(
        self,
        coordinator: MagentaCoordinator,
        entry: ConfigEntry,
        name: str,
        key: str,
        entity_category: EntityCategory | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_entity_category = entity_category
        self._attr_icon = {
            "Aanname": "mdi:clock-outline",
            "Overdracht uitgifte": "mdi:clock-outline",
            "Afsluiten incident": "mdi:clock-outline",
            "Ingezette eenheden": "mdi:fire-truck",
            "Kladblokregels": "mdi:notebook-outline",
            "Laatste incident": "mdi:fire-truck",
            "Laatste kladblokregel": "mdi:message-text-outline",
            "Kladblokmonitor actief": "mdi:timer-outline",
            "Kladblokmonitor tot": "mdi:timer-outline",
        }.get(name)

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        latest = data.get("latest") or {}
        detail = data.get("detail") or {}

        if self._key == "begin_op":
            return _format_dt(latest.get("begin_op"))
        if self._key == "begin_brw":
            return _format_dt(detail.get("begin_brw"))
        if self._key == "einde_op":
            return _format_dt(detail.get("einde_op"))
        if self._key == "units":
            return len(detail.get("ingezette_eenheden") or [])
        if self._key == "kladblok_count":
            return len(detail.get("kladblok") or [])
        if self._key == "incident_number":
            return latest.get("nummer")
        if self._key == "last_kladblok":
            lines = detail.get("kladblok") or []
            if not lines:
                return None
            line = lines[-1]
            return _line_text(line)
        if self._key == "monitoring":
            return "aan" if data.get("monitoring") else "uit"
        if self._key == "monitor_until":
            return _format_dt(data.get("monitor_until"))
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        latest = data.get("latest") or {}
        detail = data.get("detail") or {}
        attrs: dict[str, Any] = {
            "incident_id": latest.get("gebeurtenis_id"),
            "incident_nummer": latest.get("nummer"),
            "monitor_minutes": self.coordinator.monitor_minutes,
        }

        if self._key == "last_kladblok":
            lines = detail.get("kladblok") or []
            if lines:
                attrs["kladblok"] = lines[-1]
        return attrs


def _format_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().isoformat()
    except (ValueError, TypeError):
        return value


def _line_text(line: dict[str, Any]) -> str:
    for key in ("regel", "tekst", "omschrijving", "commentaar", "message", "text"):
        if line.get(key):
            return str(line[key])
    return str(line)
