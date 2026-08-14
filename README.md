# Magenta Start – Home Assistant

Unofficial Home Assistant custom integration for the Magenta Start / Inzetregistratie API.

## Purpose

This integration is designed as an **additional source for Magenta-specific information**. It does not depend on Brandweerrooster.

For the current version, Magenta is used primarily for:

- incident/plottijden
- kladblokregels (when the logged-in Magenta account has access)
- configureerbare monitoring van nieuwe kladblokregels
- deployed units and their timestamps

For a Home Assistant setup that also uses Brandweerrooster, Brandweerrooster can remain the leading source for roster/incident information and this integration can be used alongside it without mixing the two data sources.

## Installation with HACS

1. Open HACS in Home Assistant.
2. Open **Integrations**.
3. Open the three-dot menu and choose **Custom repositories**.
4. Add your GitHub repository URL.
5. Select **Integration** as the category.
6. Install **Magenta Start**.
7. Restart Home Assistant.
8. Go to **Settings → Devices & services → Add integration** and select **Magenta Start**.
9. Enter your Magenta username and password.
10. Set the kladblok monitor duration (1–120 minutes; default 10).

## Manual installation

Copy `custom_components/magenta` to `/config/custom_components/magenta` and restart Home Assistant.

## Entities

The integration currently creates sensors for:

- latest incident
- kladblokregels
- latest kladblokregel
- ingezette eenheden
- API status

The exact entity IDs depend on Home Assistant naming and the configured account.

### Kladblok monitoring

The integration can monitor new kladblokregels after a newly detected incident. The duration is configurable per Magenta integration instance (1–120 minutes, default 10).

When a new incident is detected, the integration fires `magenta_nieuw_incident`. New kladblokregels during the configured window fire `magenta_kladblok_regel`. Events include the stable Magenta `incident_id` / `gebeurtenis_id` and incident number, so automations can safely ensure messages belong to the correct incident.

Notifications are intentionally not built into this integration. Use Home Assistant automations to send these events through WhatsApp, Telegram, the Home Assistant app, or another notification service.

## Important

This is an unofficial integration and is not affiliated with or endorsed by MagentaM&T.

Never put Magenta credentials, session tickets or API tokens in GitHub, YAML, issues or screenshots.

MFA is intentionally not implemented until the exact Magenta submission flow is known; the integration does not guess at that protocol.


## Current version

`0.2.3`
