from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from .api import MagentaAuthError, MagentaApi
from .const import (
    API_BASE,
    CONF_MONITOR_MINUTES,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_MONITOR_MINUTES,
    DOMAIN,
    MAX_MONITOR_MINUTES,
    MIN_MONITOR_MINUTES,
)


class CannotConnect(HomeAssistantError):
    """Unable to connect to Magenta."""


class InvalidAuth(HomeAssistantError):
    """Invalid Magenta credentials."""


class MagentaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Magenta config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME].strip().lower())
            self._abort_if_unique_id_configured()

            api = MagentaApi(self.hass, API_BASE)
            try:
                await api.login(
                    user_input[CONF_USERNAME].strip(),
                    user_input[CONF_PASSWORD],
                )
            except MagentaAuthError as err:
                if err.code == "invalid_auth":
                    errors["base"] = "invalid_auth"
                elif err.code == "mfa_required":
                    errors["base"] = "mfa_required"
                else:
                    errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Magenta Start ({user_input[CONF_USERNAME].strip()})",
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME].strip(),
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                    options={
                        CONF_MONITOR_MINUTES: user_input.get(
                            CONF_MONITOR_MINUTES, DEFAULT_MONITOR_MINUTES
                        )
                    },
                )
            finally:
                await api.async_close()

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): vol.All(str, vol.Length(min=1)),
                vol.Optional(
                    CONF_MONITOR_MINUTES, default=DEFAULT_MONITOR_MINUTES
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_MONITOR_MINUTES, max=MAX_MONITOR_MINUTES),
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )


    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MagentaOptionsFlow()


class MagentaOptionsFlow(config_entries.OptionsFlow):
    """Handle Magenta options."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_MONITOR_MINUTES, DEFAULT_MONITOR_MINUTES
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MONITOR_MINUTES, default=current
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_MONITOR_MINUTES, max=MAX_MONITOR_MINUTES),
                    )
                }
            ),
        )
