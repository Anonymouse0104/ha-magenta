# Magenta Start – Home Assistant custom integration

Unofficial Home Assistant custom integration for the Magenta Start / Inzetregistratie API.

## What this version does

- Logs in to `https://apps.magentammt.com`
- Uses the Magenta `Ticket` authorization mechanism
- Finds the newest incident in Magenta
- Retrieves:
  - incident number and details
  - notepad entries
  - deployed units and their turnout times
  - incident acceptance, dispatch handover, and closure times
- Polls every 30 seconds
- Does **not** depend on Brandweerrooster or FireServiceRota

## Entities

The integration creates:

- `sensor.magenta_start_laatste_incident`
- `sensor.magenta_start_kladblokregels`
- `sensor.magenta_start_laatste_kladblokregel`
- `sensor.magenta_start_ingezette_eenheden`
- `sensor.magenta_start_api`
- `sensor.magenta_start_aanname`
- `sensor.magenta_start_overdracht_uitgifte`
- `sensor.magenta_start_afsluiten_incident`

Entity IDs can differ depending on Home Assistant naming rules and the configured account.

### Notepad entries

`Kladblokregels` has a `regels` attribute containing the complete list. Each item contains:

- `id`
- `datum`
- `bericht`
- `voertuig_name`
- `user_id`
- `user_name`

### Deployed units

`Ingezette eenheden` has an `eenheden` attribute. Each item contains:

- `eenheid`
- `kazerne`
- `soort`
- `alarm`
- `uitgerukt`
- `ter_plaatse`
- `ingerukt`
- `beschikbaar`
- `terug`

## Installation

### Manual

Copy:

`custom_components/magenta`

to:

`/config/custom_components/magenta`

Restart Home Assistant.

Then go to:

**Settings → Devices & services → Add integration → Magenta Start**

Enter your Magenta username and password.

### HACS

This repository can be added to HACS as a custom integration repository.

## Important

This is an unofficial integration. It is not affiliated with or endorsed by MagentaM&T.

The integration stores the username and password in the Home Assistant config entry. Never put credentials in YAML, GitHub issues, or source code.

MFA is intentionally not included until the exact MFA submission flow is established. The integration does not guess at the protocol.

## Incident timestamps

The integration exposes the three main Magenta incident timestamps as Home Assistant timestamp sensors:

- Acceptance (`begin_op`)
- Dispatch handover (`begin_brw`)
- Incident closure (`einde_op`)

The incident number (`nummer`) and stable Magenta event ID (`gebeurtenis_id`) are exposed as attributes. This allows Home Assistant automations to verify that notepad entries belong to the same incident before acting on them.

The integration deliberately contains no WhatsApp, Telegram, or other notification-specific logic. Notification delivery belongs in Home Assistant automations so every user can choose their own notification service.

## Notepad monitoring

Use the integration options to configure how many minutes new notepad entries should be monitored after a new incident is detected. The integration fires `magenta_kladblok_regel` events for new entries. Notification delivery intentionally remains outside the integration.

## Version

`0.2.4`
