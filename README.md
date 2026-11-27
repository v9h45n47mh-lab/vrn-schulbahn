# VRN Schulbahn für Home Assistant

Lovelace-Karte und serverseitige Integration für direkte VRN-Verbindungen.
Die Karte zeigt Sollzeit, Echtzeitprognose, Verspätung, Gleis und vom VRN
mitgelieferte Verbindungswarnungen. Ein expliziter Ausfall wird als solcher
markiert. Fehlt eine Fahrt im Ergebnis, bleibt ihr Status offen. Bei einem
Abruffehler bleiben vorherige Ergebnisse mit ihrem Zeitstempel sichtbar.

## Installation

1. Kopiere `custom_components/vrn_schulbahn` nach `/config/custom_components/`
   und `www/vrn-schulbahn-card.js` nach `/config/www/`.
2. Ergänze die Integration in `configuration.yaml` und ersetze die
   Platzhalter für die VRN-Haltestellen-IDs durch die numerischen IDs deiner Verbindung
   und die beispielhaften Kalender-IDs durch die Entitäten aus deinem Home Assistant.
   Die Kalender dürfen ausschließlich schulfreie Tage enthalten.
3. Starte Home Assistant neu. Registriere unter **Einstellungen → Dashboards →
   Ressourcen** die URL `/local/vrn-schulbahn-card.js?v=1.0.0` als
   **JavaScript-Modul**. Bei YAML-Ressourcen trage dieselbe URL mit
   `type: module` ein.
4. Füge die manuelle Dashboardkarte mit der unten stehenden Konfiguration hinzu.

### Integration

```yaml
vrn_schulbahn:
  origin: "START_HALTESTELLEN_ID"
  destination: "ZIEL_HALTESTELLEN_ID"
  line: S3
  departure_times: ["07:05", "07:25"]
  tolerance_minutes: 2
  school_free_calendars:
    - calendar.schulferien_und_feiertage
    - calendar.schulfrei
```

### Dashboardkarte

```yaml
type: custom:vrn-schulbahn-card
title: S-Bahn zur Schule
route: Startbahnhof → Zielbahnhof
```

Der automatische Abruf läuft montags bis freitags jede Minute von 06:30 bis
07:30 Uhr einschließlich (Europe/Berlin), auch bei geschlossenem Dashboard.
Kalendereinträge für den jeweiligen Tag unterdrücken den Abruf. Der Button
**Aktualisieren** ruft an jedem Tag die konfigurierten Fahrten für heute ab.

Mit `tolerance_minutes` legst du fest, wie weit die Sollzeit von der
Wunschzeit abweichen darf. Bei einer Abweichung zeigt die Karte beide Zeiten.

Datenquelle ist der [VRN Open Service](https://opendata.vrn.de/datasets/open-service-rapidjson-schnittstelle).
Verfügbarkeit der Prognosen und Meldungen hängt von den VRN-Daten ab.
