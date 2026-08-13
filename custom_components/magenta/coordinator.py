from __future__ import annotations

from datetime import timedelta
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
)

_LOGGER = logging.getLogger(__name__)


class MagentaCoordinator(DataUpdateCoordinator[dict]):
    """Coordinate Magenta API polling."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.api = MagentaApi(hass, API_BASE)
        self.username = entry.data[CONF_USERNAME]
        self.password = entry.data[CONF_PASSWORD]

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
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

            return {
                "available": True,
                "incident": {
                    # Magenta has two identifiers for an incident:
                    # "nummer" is the human-visible incident number and
                    # "gebeurtenis_id" is the stable API identifier.
                    "id": result.get("gebeurtenis_id"),
                    "gebeurtenis_id": result.get("gebeurtenis_id"),
                    "nummer": result.get("nummer"),
                    # Main incident/planning times from Magenta.
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
                },
            }
        except MagentaAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except MagentaApiError as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:
            _LOGGER.exception("Unexpected Magenta error")
            raise UpdateFailed(str(err)) from err
