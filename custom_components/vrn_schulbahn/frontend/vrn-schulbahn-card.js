import {
  UI_CSS, bindUI, emptyState, feedback, iconButton, loadingState, row, section,
} from "./family-ui/1.16.1/family-ui.js";

const clock = new Intl.DateTimeFormat("de-DE", {
  timeZone: "Europe/Berlin", hour: "2-digit", minute: "2-digit",
});
const formatTime = (value) => clock.format(new Date(value));

function delayLabel(minutes) {
  return `${minutes > 0 ? "+" : ""}${minutes} min`;
}

function journeyRow(trip) {
  const time = trip.estimated ?? trip.planned;
  const title = `Abfahrt ${time} · ${trip.lines.join(" → ")}`;
  const description = [];
  if (time !== trip.scheduled) description.push(`Abfahrt geplant ${trip.scheduled}`);
  if (trip.arrival && !trip.cancelled) {
    const arrivalStatus = trip.arrival_delay == null ? "Fahrplan"
      : trip.arrival_delay === 0 ? "pünktlich" : delayLabel(trip.arrival_delay);
    description.push(`Ankunft ${trip.arrival} (${arrivalStatus})`);
  }
  if (trip.platform && !trip.cancelled) description.push(`Gleis ${trip.platform}`);
  if (trip.lines.length > 1) {
    const changes = trip.lines.length - 1;
    description.push(changes === 1 ? "1 Umstieg" : `${changes} Umstiege`);
  }

  let status = feedback("Abfahrt: keine Prognose");
  if (trip.cancelled) status = feedback("Fällt aus", { kind: "error" });
  else if (trip.delay === 0) status = feedback("Abfahrt pünktlich", { kind: "success" });
  else if (trip.delay != null) status = feedback(`Abfahrt ${delayLabel(trip.delay)}`, { kind: "warning" });

  const warnings = [...trip.messages];
  if (!trip.cancelled && trip.platform && trip.planned_platform && trip.platform !== trip.planned_platform) {
    warnings.unshift(`Gleiswechsel von ${trip.planned_platform} auf ${trip.platform}`);
  }
  return row({ title, description: description.join(" · "), trailing: status }) +
    warnings.map((warning) => feedback(warning, { kind: "warning" })).join("");
}

class VrnSchulbahnCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig({ entity = "sensor.vrn_schulbahn", title = "S-Bahn zur Schule", route = "" } = {}) {
    this.config = { entity, title, route };
    this.render();
  }

  set hass(hass) {
    const previous = this.ha?.states[this.config?.entity];
    this.ha = hass;
    if (previous !== hass.states[this.config?.entity]) this.render();
  }

  connectedCallback() {
    this.unbind = bindUI(this.shadowRoot, ({ action }) => {
      if (action === "refresh") this.refresh();
    });
    this.render();
  }

  disconnectedCallback() {
    this.unbind?.();
  }

  getCardSize() {
    return 3;
  }

  async refresh() {
    if (!this.ha || this.pending) return;
    this.pending = true;
    this.actionError = "";
    this.render();
    try {
      await this.ha.callService("vrn_schulbahn", "refresh");
    } catch {
      this.actionError = "Manueller Abruf fehlgeschlagen.";
    } finally {
      this.pending = false;
      this.render();
    }
  }

  render() {
    if (!this.config) return;
    const entity = this.ha?.states[this.config.entity];
    const data = entity?.attributes ?? {};
    const status = entity?.state;
    const labels = {
      idle: "Warte auf den nächsten Abruf.",
      school_free: "Heute ist schulfrei.",
      calendar_error: "Schulkalender nicht verfügbar. Automatischer Abruf pausiert.",
      fetch_error: "VRN-Abruf fehlgeschlagen.",
      unavailable: "VRN-Sensor nicht verfügbar.",
      unknown: "VRN-Sensor noch ohne Daten.",
    };
    const busy = this.pending || status === "refreshing";
    const action = iconButton({
      icon: "refresh", label: "Aktualisieren", action: "refresh", disabled: !this.ha || busy,
    });
    const note = this.actionError || labels[status] || (!entity ? "VRN-Sensor fehlt." : "");
    let content = this.config.route ? row({ title: this.config.route }) : "";
    if (note) {
      const error = this.actionError || ["fetch_error", "calendar_error", "unavailable"].includes(status);
      content += feedback(note, { kind: error ? "error" : "info" });
    }
    if (busy) content += loadingState("VRN-Daten werden abgerufen …");
    if (data.window_start && ["ready", "refreshing", "fetch_error"].includes(status)) {
      const label = status === "fetch_error" ? "Letzter verfügbarer Stand" : "Abfahrtsfenster";
      content += row({
        title: `${formatTime(data.window_start)}–${formatTime(data.window_end)} Uhr`,
        description: `${label} · Abruf ${formatTime(data.last_success)} Uhr · Quelle VRN`,
      });
      if (data.departures.length) content += data.departures.map(journeyRow).join("");
      else content += emptyState("Keine Verbindungen in diesem Zeitfenster gefunden.");
    }
    const expanded = this.shadowRoot.querySelector(".settings-fold")
      ?.getAttribute("aria-expanded") !== "false";
    this.shadowRoot.innerHTML = `<style>${UI_CSS}</style><ha-card>${section({
      id: "vrn-departures", title: this.config.title, trailing: action, content, expanded,
    })}</ha-card>`;
  }
}

if (!customElements.get("vrn-schulbahn-card")) {
  customElements.define("vrn-schulbahn-card", VrnSchulbahnCard);
}
