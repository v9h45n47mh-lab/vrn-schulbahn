# VRN Schulbahn für Home Assistant

Lovelace-Karte und serverseitige Integration für direkte VRN-Verbindungen.
Die Karte zeigt Sollzeit, Echtzeitprognose, Verspätung, Gleis und vom VRN
mitgelieferte Verbindungswarnungen. Ein expliziter Ausfall wird als solcher
markiert. Fehlt eine Fahrt im Ergebnis, bleibt ihr Status offen. Bei einem
Abruffehler bleiben vorherige Ergebnisse mit ihrem Zeitstempel sichtbar.

## Installation

1. Öffne **HACS → ⋮ → Benutzerdefinierte Repositorys**. Füge
   `https://github.com/v9h45n47mh-lab/vrn-schulbahn` mit der Kategorie
   **Integration** hinzu und lade **VRN Schulbahn** herunter.
2. Ergänze den Abschnitt **Integration** unten in deiner `configuration.yaml`.
   Setze deine VRN-Haltestellen-IDs und die vorhandenen Kalender-Entitäten ein.
   Verwende Kalender, die ausschließlich schulfreie Tage enthalten.
3. Starte Home Assistant neu.
4. Registriere unter **Einstellungen → Dashboards → ⋮ → Ressourcen** die URL
   `/vrn_schulbahn/vrn-schulbahn-card.js` als **JavaScript-Modul**.
   Bei Ressourcen im YAML-Modus verwende dieselbe URL mit `type: module`.
   Wenn du von der manuellen Installation wechselst, ersetze den bisherigen
   Eintrag `/local/vrn-schulbahn-card.js` durch diese URL.
5. Füge die manuelle Dashboard-Karte mit der unten stehenden Konfiguration hinzu.

HACS installiert und aktualisiert die Integration zusammen mit der JavaScript-Datei.

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
