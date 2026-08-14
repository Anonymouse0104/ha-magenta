from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import MagentaCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    coordinator: MagentaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            MagentaIncidentSensor(coordinator, entry),
            MagentaNotebookSensor(coordinator, entry),
            MagentaLatestNotebookSensor(coordinator, entry),
            MagentaUnitsSensor(coordinator, entry),
            MagentaAannameSensor(coordinator, entry),
            MagentaOverdrachtSensor(coordinator, entry),
            MagentaAfsluitenSensor(coordinator, entry),
            MagentaApiSensor(coordinator, entry),
        ]
    )


class BaseMagentaSensor(CoordinatorEntity[MagentaCoordinator], SensorEntity):
    """Base Magenta sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MagentaCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Magenta Start",
            manufacturer="MagentaM&T",
            model="Magenta Start API",
        )

    @property
    def incident(self) -> dict[str, Any] | None:
        return (self.coordinator.data or {}).get("incident")

    @staticmethod
    def _timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        return dt_util.parse_datetime(value)


class MagentaIncidentSensor(BaseMagentaSensor):
    _attr_name = "Laatste incident"
    _attr_icon = "mdi:fire-truck"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_latest_incident"

    @property
    def native_value(self):
        incident = self.incident
        return incident.get("nummer") if incident else None

    @property
    def extra_state_attributes(self):
        incident = self.incident
        if not incident:
            return {}
        return {
            "incident_id": incident.get("id"),
            "gebeurtenis_id": incident.get("gebeurtenis_id"),
            "incident_nummer": incident.get("nummer"),
            "prioriteit": incident.get("prioriteit"),
            "classificatie": incident.get("classificatie"),
            "straat": incident.get("straat"),
            "huisnummer": incident.get("huisnummer"),
            "postcode": incident.get("postcode"),
            "plaats": incident.get("plaats"),
            "begin_op": incident.get("begin_op"),
            "modified_on": incident.get("modified_on"),
        }


class MagentaNotebookSensor(BaseMagentaSensor):
    _attr_name = "Kladblokregels"
    _attr_icon = "mdi:notebook-outline"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_notebook"

    @property
    def native_value(self):
        incident = self.incident
        return len(incident.get("notebook", [])) if incident else 0

    @property
    def extra_state_attributes(self):
        incident = self.incident
        if not incident:
            return {"regels": []}
        return {"regels": incident.get("notebook", [])}


class MagentaLatestNotebookSensor(BaseMagentaSensor):
    _attr_name = "Laatste kladblokregel"
    _attr_icon = "mdi:message-text-outline"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_latest_notebook"

    @property
    def native_value(self):
        incident = self.incident
        if not incident or not incident.get("notebook"):
            return None
        return incident["notebook"][-1].get("bericht")

    @property
    def extra_state_attributes(self):
        incident = self.incident
        if not incident or not incident.get("notebook"):
            return {}
        line = incident["notebook"][-1]
        return {
            "datum": line.get("datum"),
            "regel_id": line.get("id"),
            "incident_id": incident.get("id"),
            "gebeurtenis_id": incident.get("gebeurtenis_id"),
            "incident_nummer": incident.get("nummer"),
        }


class MagentaUnitsSensor(BaseMagentaSensor):
    _attr_name = "Ingezette eenheden"
    _attr_icon = "mdi:fire-truck"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_units"

    @property
    def native_value(self):
        incident = self.incident
        return len(incident.get("units", [])) if incident else 0

    @property
    def extra_state_attributes(self):
        incident = self.incident
        if not incident:
            return {"eenheden": []}
        return {"eenheden": incident.get("units", [])}


class MagentaIncidentTimeSensor(BaseMagentaSensor):
    """Expose one Magenta incident/planning timestamp."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry, key: str, name: str, unique_key: str) -> None:
        super().__init__(coordinator, entry)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_key}"
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> datetime | None:
        incident = self.incident
        if not incident:
            return None
        return self._timestamp(incident.get(self._key))

    @property
    def extra_state_attributes(self):
        incident = self.incident
        if not incident:
            return {}
        return {
            "incident_nummer": incident.get("nummer"),
            "gebeurtenis_id": incident.get("gebeurtenis_id"),
        }


class MagentaAannameSensor(MagentaIncidentTimeSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "begin_op", "Aanname", "aanname"
        )


class MagentaOverdrachtSensor(MagentaIncidentTimeSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "begin_brw", "Overdracht uitgifte", "overdracht"
        )


class MagentaAfsluitenSensor(MagentaIncidentTimeSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "einde_op", "Afsluiten incident", "afsluiten"
        )


class MagentaApiSensor(BaseMagentaSensor):
    _attr_name = "API"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:cloud-check-outline"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_api"

    @property
    def native_value(self):
        return "online" if self.coordinator.last_update_success else "offline"
