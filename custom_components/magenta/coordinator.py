from __future__ import annotations

from datetime import timedelta
import datetime as dt
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MagentaApi, MagentaApiError, MagentaAuthError, clean_html
from .const import (
    API_BASE,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    UPDATE_INTERVAL_SECONDS,
    CONF_MONITOR_MINUTES,
    DEFAULT_MONITOR_MINUTES,
)

_LOGGER = logging.getLogger(__name__)


class MagentaCoordinator(DataUpdateCoordinator[dict]):
    """Coordinate Magenta API polling."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.api = MagentaApi(hass, API_BASE)
        self.username = entry.data[CONF_USERNAME]
        self.password = entry.data[CONF_PASSWORD]
        self.monitor_minutes = int(
            entry.options.get(CONF_MONITOR_MINUTES, DEFAULT_MONITOR_MINUTES)
        )
        self._initialized = False
        self._monitored_incident_id: int | None = None
        self._monitor_until: dt.datetime | None = None
        self._seen_kladblok_ids: set[str] = set()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )

    @staticmethod
    def _kladblok_key(item: dict) -> str:
        """Return a stable key for a kladblokregel."""
        if item.get("id") is not None:
            return f"id:{item['id']}"
        return "fallback:" + repr(
            (item.get("datum"), item.get("bericht"), item.get("user_id"), item.get("user_name"))
        )

    def _start_monitoring(self, incident: dict, notebook: list[dict]) -> None:
        """Start a new monitoring window for a newly detected incident."""
        incident_id = incident.get("gebeurtenis_id") or incident.get("id")
        self._monitored_incident_id = int(incident_id) if incident_id is not None else None
        self._monitor_until = dt.datetime.now(dt.timezone.utc) + timedelta(
            minutes=self.monitor_minutes
        )
        self._seen_kladblok_ids = {
            self._kladblok_key(item) for item in notebook if isinstance(item, dict)
        }
        self.hass.bus.async_fire(
            "magenta_nieuw_incident",
            {
                "incident_id": self._monitored_incident_id,
                "incident_nummer": incident.get("nummer"),
                "monitor_minutes": self.monitor_minutes,
            },
        )

    def _process_new_kladblok(self, incident: dict, notebook: list[dict]) -> None:
        """Fire events for new lines during the active incident window."""
        incident_id = incident.get("gebeurtenis_id") or incident.get("id")
        if incident_id is None or self._monitored_incident_id != int(incident_id):
            return
        now = dt.datetime.now(dt.timezone.utc)
        if not self._monitor_until or now > self._monitor_until:
            return

        for item in notebook:
            if not isinstance(item, dict):
                continue
            key = self._kladblok_key(item)
            if key in self._seen_kladblok_ids:
                continue
            self._seen_kladblok_ids.add(key)
            self.hass.bus.async_fire(
                "magenta_kladblok_regel",
                {
                    "incident_id": int(incident_id),
                    "incident_nummer": incident.get("nummer"),
                    "regel_id": item.get("id"),
                    "datum": item.get("datum"),
                    "bericht": item.get("bericht"),
                    "regel": item,
                    "monitor_minutes": self.monitor_minutes,
                },
            )

    async def _async_update_data(self) -> dict:
        try:
            if not self.api._ticket:
                await self.api.login(self.username, self.password)

            result = await self.api.get_incident_data()
            if result is None:
                return {"available": True, "incident": None}

            notebook = []
            for item in result.get("kladblok") or []:
                notebook.append(
                    {
                        "id": item.get("id"),
                        "datum": item.get("datum"),
                        "bericht": clean_html(item.get("bericht")),
                        "voertuig_name": item.get("voertuig_name"),
                        "user_id": item.get("user_id"),
                        "user_name": item.get("user_name"),
                    }
                )

            units = []
            for unit in result.get("ingezette_eenheden") or []:
                units.append(
                    {
                        "id": unit.get("id"),
                        "eenheid": unit.get("eenheid_naam"),
                        "kazerne": unit.get("kazerne_naam"),
                        "soort": unit.get("soort"),
                        "alarm": unit.get("alarm"),
                        "uitgerukt": unit.get("uitgerukt"),
                        "ter_plaatse": unit.get("ter_plaatse"),
                        "ingerukt": unit.get("ingerukt"),
                        "beschikbaar": unit.get("beschikbaar"),
                        "terug": unit.get("terug"),
                    }
                )

            incident = {
                "id": result.get("gebeurtenis_id"),
                "gebeurtenis_id": result.get("gebeurtenis_id"),
                "nummer": result.get("nummer"),
                "begin_op": result.get("begin_op"),
                "begin_brw": result.get("begin_brw"),
                "einde_op": result.get("einde_op"),
                "modified_on": result.get("modified_on"),
                "prioriteit": result.get("prioriteit"),
                "classificatie": result.get("meldings_classificatie_1"),
                "straat": result.get("street_full"),
                "huisnummer": result.get("huisnummer"),
                "postcode": result.get("zip_code"),
                "plaats": result.get("city_name"),
                "notebook": notebook,
                "units": units,
            }

            incident_id = incident.get("gebeurtenis_id")
            if incident_id is not None:
                if not self._initialized:
                    # Initial sync: do not treat the current historical incident as new.
                    self._monitored_incident_id = int(incident_id)
                    self._seen_kladblok_ids = {
                        self._kladblok_key(item) for item in notebook if isinstance(item, dict)
                    }
                    self._initialized = True
                elif self._monitored_incident_id != int(incident_id):
                    self._start_monitoring(incident, notebook)
                else:
                    self._process_new_kladblok(incident, notebook)

            return {
                "available": True,
                "monitoring": bool(
                    self._monitor_until
                    and dt.datetime.now(dt.timezone.utc) <= self._monitor_until
                    and self._monitored_incident_id == incident_id
                ),
                "monitor_until": self._monitor_until.isoformat() if self._monitor_until else None,
                "incident": incident,
            }
        except MagentaAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except MagentaApiError as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:
            _LOGGER.exception("Unexpected Magenta error")
            raise UpdateFailed(str(err)) from err
