# Magenta Start – Home Assistant

Onofficiële Home Assistant custom integration voor de Magenta Start / Inzetregistratie API.

## Doel

Deze integratie is bedoeld als **aanvullende bron** naast bijvoorbeeld Brandweerrooster.

De integratie mengt de gegevens niet met Brandweerrooster. Je kunt Brandweerrooster dus als leidende bron blijven gebruiken voor rooster- en incidentinformatie en Magenta uitsluitend gebruiken voor Magenta-specifieke gegevens.

### Magenta levert onder andere

- aanname / `begin_op`
- overdracht uitgifte / `begin_brw`
- afsluiten incident / `einde_op`
- ingezette eenheden
- kladblokregels
- laatste incidentnummer
- monitoringstatus van het kladblok

## Kladblokmonitor

Na het detecteren van een nieuw incident start de integratie automatisch een monitorvenster.

De duur daarvan stel je **per Magenta-configuratie** in via:

**Instellingen → Apparaten & diensten → Magenta Start → Configureren**

De standaardwaarde is **10 minuten**. Je kunt een waarde van **1 t/m 120 minuten** instellen.

De integratie controleert daarbij altijd het **gebeurtenis-ID / incident-ID**. Een kladblokregel wordt dus nooit als nieuwe regel van het actieve incident behandeld wanneer deze bij een ander incident hoort.

### Waarom geen WhatsApp-integratie?

De integratie kent bewust geen voorkeur voor WhatsApp, Telegram, Pushover, de Home Assistant-app of een andere notificatiedienst.

Wanneer tijdens het monitorvenster een **nieuwe** kladblokregel wordt gevonden, wordt het Home Assistant-event `magenta_kladblok_regel` aangemaakt. De event-data bevat onder andere `incident_id`, `incident_nummer` en `regel`.

Daardoor kan iedere gebruiker zelf bepalen welke notificatiedienst op dit event reageert.

De integratie levert de Magenta-data aan Home Assistant. De gebruiker kan daarna zelf een automation maken die een gewenste notificatieservice gebruikt.

Dit maakt de integratie bruikbaar voor verschillende Home Assistant-installaties en notificatieoplossingen.

## Installatie via HACS

1. Open HACS.
2. Ga naar **Integraties**.
3. Kies **Aangepaste repositories**.
4. Voeg de GitHub-repository toe.
5. Kies als categorie **Integratie**.
6. Installeer **Magenta Start**.
7. Herstart Home Assistant.
8. Ga naar **Instellingen → Apparaten & diensten**.
9. Kies **Integratie toevoegen**.
10. Zoek naar **Magenta Start**.
11. Vul je Magenta gebruikersnaam en wachtwoord in.
12. Stel indien gewenst de kladblokmonitor-duur in.

## Belangrijk

De kladblokgegevens zijn afhankelijk van de rechten van het gebruikte Magenta-account. Niet ieder Magenta-account heeft toegang tot kladblokregels.

De integratie gebruikt de Magenta API waarvoor je zelf geldige Magenta-toegang nodig hebt.

## Automations

De integratie is bewust zo opgezet dat notificaties buiten de integratie blijven.

Een toekomstige automation kan bijvoorbeeld reageren op een nieuwe kladblokregel en vervolgens:

- WhatsApp gebruiken
- Telegram gebruiken
- de Home Assistant Notify-service gebruiken
- Pushover gebruiken
- of helemaal niets versturen

De integratie hoeft hiervoor niet aangepast te worden.

## Disclaimer

Dit project is niet officieel verbonden aan, goedgekeurd door of ondersteund door MagentaM&T. Wijzigingen in de Magenta Start API kunnen de werking van deze integratie beïnvloeden.
