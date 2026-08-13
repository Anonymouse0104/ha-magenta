from __future__ import annotations

from datetime import timedelta

DOMAIN = "magenta"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_MONITOR_MINUTES = "kladblok_monitor_minutes"

DEFAULT_MONITOR_MINUTES = 10
MIN_MONITOR_MINUTES = 1
MAX_MONITOR_MINUTES = 120

API_BASE = "https://apps.magentammt.com/api"

PLATFORMS = ["sensor"]

UPDATE_INTERVAL = timedelta(seconds=30)
