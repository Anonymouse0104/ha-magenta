from __future__ import annotations

from typing import Any
import html
import re

from aiohttp import ClientError, ClientSession
from yarl import URL


class MagentaAuthError(Exception):
    """Authentication error."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


class MagentaApiError(Exception):
    """Magenta API error."""


class MagentaApi:
    """Small async client for the Magenta Start API."""

    def __init__(self, hass, base_url: str) -> None:
        self._hass = hass
        self._base_url = base_url.rstrip("/")
        self._session: ClientSession | None = None
        self._ticket: str | None = None

    async def _get_session(self) -> ClientSession:
        if self._session is None or self._session.closed:
            self._session = ClientSession()
        return self._session

    async def async_close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def login(self, username: str, password: str) -> None:
        """Log in and store the returned Magenta ticket."""
        session = await self._get_session()
        url = f"{self._base_url}/authenticatie/login"
        payload = {
            "login": username,
            "password": password,
            "login_as": "",
            "remember": False,
        }

        try:
            async with session.post(
                url,
                json=payload,
                headers={"Accept": "application/vnd.magentammt.com+json; version=1.0;"},
                timeout=20,
            ) as response:
                data = await response.json(content_type=None)
        except ClientError as err:
            raise MagentaApiError(str(err)) from err

        if response.status in (401, 403):
            raise MagentaAuthError("invalid_auth")

        if response.status >= 400:
            message = str(data.get("message", "")) if isinstance(data, dict) else ""
            if message.startswith("MFA_"):
                raise MagentaAuthError("mfa_required", message)
            raise MagentaApiError(message or f"HTTP {response.status}")

        if not isinstance(data, dict):
            raise MagentaApiError("Unexpected login response")

        result = data.get("result") or {}
        ticket = result.get("ticket")

        if not ticket:
            message = str(data.get("message", ""))
            if message.startswith("MFA_"):
                raise MagentaAuthError("mfa_required", message)
            raise MagentaAuthError("invalid_auth", "No ticket returned")

        self._ticket = ticket

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if not self._ticket:
            raise MagentaAuthError("invalid_auth", "No active ticket")

        session = await self._get_session()
        headers = kwargs.pop("headers", {})
        headers.update(
            {
                "Authorization": f"Ticket {self._ticket}",
                "Accept": "application/vnd.magentammt.com+json; version=1.0;",
            }
        )

        try:
            async with session.request(
                method,
                f"{self._base_url}/{path.lstrip('/')}",
                headers=headers,
                timeout=20,
                **kwargs,
            ) as response:
                data = await response.json(content_type=None)
        except ClientError as err:
            raise MagentaApiError(str(err)) from err

        if response.status in (401, 403):
            self._ticket = None
            raise MagentaAuthError("invalid_auth")

        if response.status >= 400:
            raise MagentaApiError(f"HTTP {response.status}")

        if not isinstance(data, dict):
            raise MagentaApiError("Unexpected API response")
        if data.get("code") not in (None, 200):
            raise MagentaApiError(str(data.get("status", "API error")))
        return data

    async def get_latest_incident(self) -> dict[str, Any] | None:
        """Return the newest incident known to Magenta."""
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
            ("columns[]", "modified_on"),
            ("limit[offset]", "0"),
            ("limit[row_count]", "1"),
            ("sort[column]", "begin_op"),
            ("sort[direction]", "DESC"),
            ("filters[hide_empty_opkomst]", "1"),
        ]
        data = await self._request("GET", "incidenten/incidenten", params=params)
        records = (data.get("result") or {}).get("records") or []
        return records[0] if records else None

    async def get_incident_details(self, incident_id: int) -> dict[str, Any]:
        """Return incident details including units and notebook lines."""
        params = [
            ("columns[]", "ingezette_eenheden"),
            ("columns[]", "kladblok"),
            ("columns[]", "modified_on"),
        ]
        data = await self._request(
            "GET",
            f"incidenten/incident/{incident_id}",
            params=params,
        )
        return data.get("result") or {}

    async def get_incident_data(self) -> dict[str, Any] | None:
        """Return the latest incident with its notebook and turnout data."""
        incident = await self.get_latest_incident()
        if not incident:
            return None

        incident_id = incident.get("gebeurtenis_id")
        if not incident_id:
            return None

        details = await self.get_incident_details(int(incident_id))
        merged = dict(incident)
        merged.update(details)
        return merged


def clean_html(value: Any) -> str:
    """Convert Magenta's simple HTML notebook message to plain text."""
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>\s*<p>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()
