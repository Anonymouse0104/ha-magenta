from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_BASE,
    CONF_MONITOR_MINUTES,
    DEFAULT_MONITOR_MINUTES,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class MagentaApiError(Exception):
    """Magenta API error."""


class MagentaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls Magenta and exposes incident/kladblok data."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        monitor_minutes: int = DEFAULT_MONITOR_MINUTES,
    ) -> None:
        self.username = username
        self.password = password
        self.monitor_minutes = monitor_minutes
        self.ticket: str | None = None
        self._session: aiohttp.ClientSession | None = None

        self.current_incident_id: int | None = None
        self.current_incident_number: int | None = None
        self.monitor_until: datetime | None = None
        self._seen_kladblok: set[str] = set()
        self._initialized = False
        self._seed_kladblok = False

        super().__init__(
            hass,
            _LOGGER,
            name="Magenta Start",
            update_interval=UPDATE_INTERVAL,
        )

    async def async_login(self) -> None:
        await self._ensure_session()
        payload = {
            "login": self.username,
            "login_as": "",
            "remember": True,
            "remember_token": "",
        }
        try:
            async with self._session.post(
                f"{API_BASE}/authenticate/login",
                json=payload,
                headers={"Accept": "application/vnd.magentammt.com+json; version=1.0;"},
            ) as response:
                if response.status >= 400:
                    raise MagentaApiError(f"Login failed: {response.status}")
                data = await response.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise MagentaApiError(str(err)) from err

        # Magenta returns a ticket either directly or nested in the result.
        ticket = (
            data.get("ticket")
            or data.get("result", {}).get("ticket")
            or data.get("data", {}).get("ticket")
        )
        if not ticket:
            raise MagentaApiError("No ticket returned by Magenta")
        self.ticket = ticket

    async def _ensure_session(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

    async def _request(self, path: str, params: list[tuple[str, str]] | None = None):
        await self._ensure_session()
        if not self.ticket:
            await self.async_login()

        headers = {
            "Accept": "application/vnd.magentammt.com+json; version=1.0;",
            "Authorization": f"Ticket {self.ticket}",
        }
        try:
            async with self._session.get(
                f"{API_BASE}{path}", params=params, headers=headers
            ) as response:
                if response.status == 401:
                    self.ticket = None
                    await self.async_login()
                    headers["Authorization"] = f"Ticket {self.ticket}"
                    async with self._session.get(
                        f"{API_BASE}{path}", params=params, headers=headers
                    ) as retry:
                        if retry.status >= 400:
                            raise MagentaApiError(f"API error: {retry.status}")
                        return await retry.json(content_type=None)
                if response.status >= 400:
                    raise MagentaApiError(f"API error: {response.status}")
                return await response.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise MagentaApiError(str(err)) from err

    async def _fetch_latest(self) -> dict[str, Any]:
        params = [
            ("columns[]", "gebeurtenis_id"),
            ("columns[]", "begin_op"),
            ("columns[]", "nummer"),
            ("columns[]", "street_full"),
            ("columns[]", "huisnummer"),
            ("columns[]", "zip_code"),
            ("columns[]", "city_name"),
            ("columns[]", "prioriteit"),
            ("columns[]", "meldings_classificatie_1"),
            ("columns[]", "verslag_status"),
            ("columns[]", "opkomst_status"),
            ("limit[offset]", "0"),
            ("limit[row_count]", "1"),
            ("sort[column]", "begin_op"),
            ("sort[direction]", "DESC"),
            ("filters[hide_empty_opkomst]", "1"),
        ]
        data = await self._request("/incidenten/incidenten", params)
        records = data.get("result", {}).get("records", [])
        return records[0] if records else {}

    async def _fetch_detail(self, incident_id: int) -> dict[str, Any]:
        params = [
            ("columns[]", "ingezette_eenheden"),
            ("columns[]", "kladblok"),
            ("columns[]", "karakteristieken"),
            ("columns[]", "modified_on"),
        ]
        data = await self._request(f"/incidenten/incident/{incident_id}", params)
        return data.get("result", {}) or {}

    @staticmethod
    def _line_key(line: dict[str, Any]) -> str:
        for key in ("id", "kladblok_id", "regel_id", "created_on", "datumtijd", "timestamp"):
            if line.get(key) is not None:
                return f"{key}:{line[key]}"
        return repr(sorted(line.items()))

    @callback
    def _start_monitoring(self, incident: dict[str, Any]) -> None:
        self.current_incident_id = incident.get("gebeurtenis_id")
        self.current_incident_number = incident.get("nummer")
        self.monitor_until = datetime.now().astimezone() + timedelta(
            minutes=self.monitor_minutes
        )
        self._seen_kladblok.clear()
        self._seed_kladblok = True

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            latest = await self._fetch_latest()
            incident_id = latest.get("gebeurtenis_id")

            if incident_id and incident_id != self.current_incident_id:
                self._start_monitoring(latest)

            detail = {}
            new_lines: list[dict[str, Any]] = []

            if self.current_incident_id:
                detail = await self._fetch_detail(self.current_incident_id)
                lines = detail.get("kladblok") or []

                # Seed the lines that already existed when monitoring started.
                # Only lines that appear after that point are considered new.
                if self._seed_kladblok or not self._initialized:
                    self._seen_kladblok = {
                        self._line_key(line) for line in lines if isinstance(line, dict)
                    }
                    self._seed_kladblok = False
                    self._initialized = True
                elif self.monitor_until and datetime.now().astimezone() <= self.monitor_until:
                    for line in lines:
                        if not isinstance(line, dict):
                            continue
                        key = self._line_key(line)
                        if key not in self._seen_kladblok:
                            self._seen_kladblok.add(key)
                            new_lines.append(line)
                            self.hass.bus.async_fire(
                                "magenta_kladblok_regel",
                                {
                                    "incident_id": self.current_incident_id,
                                    "incident_nummer": self.current_incident_number,
                                    "regel": line,
                                    "monitor_minutes": self.monitor_minutes,
                                },
                            )
                else:
                    # Monitoring window has ended; keep the incident selected,
                    # but don't emit new kladblok events.
                    pass

            return {
                "latest": latest,
                "detail": detail,
                "new_kladblok": new_lines,
                "monitor_until": self.monitor_until,
                "monitoring": bool(
                    self.monitor_until
                    and datetime.now().astimezone() <= self.monitor_until
                ),
            }
        except MagentaApiError as err:
            raise UpdateFailed(str(err)) from err

    async def async_close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    @property
    def monitor_minutes(self) -> int:
        return self._monitor_minutes

    @monitor_minutes.setter
    def monitor_minutes(self, value: int) -> None:
        self._monitor_minutes = int(value)
