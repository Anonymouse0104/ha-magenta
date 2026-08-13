from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import (
    CONF_MONITOR_MINUTES,
    DEFAULT_MONITOR_MINUTES,
    DOMAIN,
    MAX_MONITOR_MINUTES,
    MIN_MONITOR_MINUTES,
)
from .coordinator import MagentaApiError, MagentaCoordinator


class MagentaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                coordinator = MagentaCoordinator(
                    self.hass,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    user_input.get(CONF_MONITOR_MINUTES, DEFAULT_MONITOR_MINUTES),
                )
                await coordinator.async_login()
            except MagentaApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                await coordinator.async_close()

                await self.async_set_unique_id(
                    user_input[CONF_USERNAME].strip().lower()
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Magenta Start",
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                    options={
                        CONF_MONITOR_MINUTES: user_input.get(
                            CONF_MONITOR_MINUTES, DEFAULT_MONITOR_MINUTES
                        )
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(
                        CONF_MONITOR_MINUTES, default=DEFAULT_MONITOR_MINUTES
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_MONITOR_MINUTES, max=MAX_MONITOR_MINUTES),
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    async def async_get_options_flow(config_entry):
        return MagentaOptionsFlow(config_entry)


class MagentaOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

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
