# VRN Schulbahn für Home Assistant

Lovelace-Karte und serverseitige Integration für VRN-Verbindungen im nächsten 60-Minuten-Fenster.
Die Karte zeigt Sollzeit, Echtzeitprognose, Verspätung, Gleis und vom VRN
mitgelieferte Verbindungswarnungen. Ein expliziter Ausfall wird als solcher
markiert. Bei einem
Abruffehler bleiben vorherige Ergebnisse mit ihrem Zeitstempel sichtbar.

## Installation

1. Öffne **HACS → ⋮ → Benutzerdefinierte Repositorys**. Füge
   `https://github.com/v9h45n47mh-lab/vrn-schulbahn` mit der Kategorie
   **Integration** hinzu und lade **VRN Schulbahn** herunter.
2. Ergänze den Abschnitt **Integration** unten in deiner `configuration.yaml`.
   Setze deine VRN-Haltestellen-IDs und die vorhandenen Kalender-Entitäten ein.
   Verwende Kalender, die ausschließlich schulfreie Tage enthalten.
3. Starte Home Assistant neu.
4. Lade das Home-Assistant-Frontend neu und füge die Dashboard-Karte mit der
   unten stehenden Konfiguration hinzu.

Die Integration bindet das JavaScript-Modul der Karte beim Start automatisch
ein. Wenn du die Karte in einer älteren Version als Dashboard-Ressource
eingetragen hast, kannst du diesen Eintrag nach dem Update entfernen.

### Integration

```yaml
vrn_schulbahn:
  origin: "START_HALTESTELLEN_ID"
  destination: "ZIEL_HALTESTELLEN_ID"
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
Kalendereinträge für den jeweiligen Tag unterdrücken den automatischen Abruf.
Außerhalb dieses Zeitfensters aktualisiert das Rundpfeil-Symbol die Karte.
Jeder Abruf zeigt die vom VRN gelieferten Verbindungen ab Abrufzeitpunkt
bis eine Stunde danach, einschließlich Verbindungen mit Umstieg.
Bei Verspätung zählt die prognostizierte Abfahrtszeit. Beispiel: Plan 07:01,
Prognose 07:15, Abruf 07:10. Die Karte zeigt 07:15 und +14 min.
Die VRN-Abfragen gehen bis zu einer Stunde in die Vergangenheit zurück, um
verspätete Fahrten zu finden. Ältere YAML-Felder `line`, `departure_times`
und `tolerance_minutes` werden weiterhin akzeptiert und nicht ausgewertet.

Datenquelle ist der [VRN Open Service](https://opendata.vrn.de/datasets/open-service-rapidjson-schnittstelle).
Verfügbarkeit der Prognosen und Meldungen hängt von den VRN-Daten ab.
