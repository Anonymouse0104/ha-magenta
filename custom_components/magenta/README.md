# Magenta Start – Home Assistant custom integration

Unofficial Home Assistant custom integration for the Magenta Start / Inzetregistratie API.

## What this first version does

- Logs in to `https://apps.magentammt.com`
- Uses the Magenta `Ticket` authorization mechanism
- Finds the newest incident in Magenta
- Retrieves:
  - incident number/details
  - kladblokregels
  - ingezette eenheden and their turnout times
- Polls every 30 seconds
- Does **not** depend on Brandweerrooster or FireServiceRota

## Entities

The integration creates:

- `sensor.magenta_start_laatste_incident`
- `sensor.magenta_start_kladblokregels`
- `sensor.magenta_start_laatste_kladblokregel`
- `sensor.magenta_start_ingezette_eenheden`
- `sensor.magenta_start_api`

Entity IDs can differ depending on the Home Assistant naming rules/configured account.

### Kladblokregels

`Kladblokregels` has a `regels` attribute containing the complete list. Each item contains:

- `id`
- `datum`
- `bericht`
- `voertuig_name`
- `user_id`
- `user_name`

### Ingezette eenheden

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

Then:

Settings → Devices & services → Add integration → **Magenta Start**

Enter your Magenta username and password.

### HACS development

This repository can later be registered as a HACS integration repository.

## Important

This is an unofficial integration. It is not affiliated with or endorsed by MagentaM&T.

The integration stores the username/password in the Home Assistant config entry. Never put credentials in YAML, GitHub issues or source code.

MFA is intentionally not included in v0.1.0 because the exact MFA submission flow was not established during API reverse engineering. A future release should add it rather than guessing at the protocol.


## v0.2.0

This release adds the three main Magenta incident timestamps as Home Assistant timestamp sensors:

- Aanname (`begin_op`)
- Overdracht uitgifte (`begin_brw`)
- Afsluiten incident (`einde_op`)

Incident number (`nummer`) and the stable Magenta `gebeurtenis_id` are exposed as attributes. This allows Home Assistant automations to verify that kladblokregels belong to the same incident before acting on them.

The integration deliberately contains no WhatsApp, Telegram, or other notification-specific logic. Notification delivery belongs in Home Assistant automations so every user can choose their own notification service.
