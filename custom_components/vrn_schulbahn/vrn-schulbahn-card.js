class VrnSchulbahnCard extends HTMLElement {
  setConfig({ entity = "sensor.vrn_schulbahn", title = "S-Bahn zur Schule",
    route = "" } = {}) {
    this.config = { entity, title, route };
    this.render();
  }

  set hass(hass) {
    const previous = this.ha?.states[this.config?.entity];
    this.ha = hass;
    if (previous !== hass.states[this.config?.entity]) this.render();
  }

  getCardSize() {
    return 3;
  }

  async refresh() {
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
    const root = this.shadowRoot ?? this.attachShadow({ mode: "open" });
    const entity = this.ha?.states[this.config.entity];
    const data = entity?.attributes ?? {};
    const status = entity?.state;
    const labels = {
      idle: "Warte auf den nächsten Abruf.",
      school_free: "Heute ist schulfrei.",
      refreshing: "VRN-Daten werden abgerufen …",
      calendar_error: "Schulkalender nicht verfügbar. Automatischer Abruf pausiert.",
      fetch_error: "VRN-Abruf fehlgeschlagen.",
      unavailable: "VRN-Sensor nicht verfügbar.",
      unknown: "VRN-Sensor noch ohne Daten.",
    };
    const style = document.createElement("style");
    style.textContent = `
      ha-card { display:block; padding:16px; }
      header { display:flex; justify-content:space-between; align-items:center; gap:12px; }
      h2 { margin:0; font-size:1.2rem; font-weight:650; }
      button { border:1px solid var(--divider-color); color:var(--primary-text-color);
        background:transparent; font:inherit; border-radius:10px; padding:8px 10px; cursor:pointer; }
      button:disabled { opacity:.55; cursor:default; }
      button:focus-visible { outline:2px solid var(--primary-color); }
      .muted { color:var(--secondary-text-color); font-size:.86rem; }
      .train { display:flex; justify-content:space-between; gap:8px 12px; flex-wrap:wrap;
        align-items:baseline; border-top:1px solid var(--divider-color); padding:10px 0; }
      .train strong { font-size:1.12rem; }
      .details, .warning { width:100%; }
      .warning { color:var(--primary-text-color); border-inline-start:3px solid var(--warning-color,#ed9a24);
        padding-inline-start:9px; margin:0; }
      .danger { color:var(--error-color,#c12929); font-weight:650; }
      footer { font-size:.78rem; margin-top:8px; }
      footer a { color:inherit; }
    `;
    const make = (tag, value, className) => {
      const element = document.createElement(tag);
      if (value) element.textContent = value;
      if (className) element.className = className;
      return element;
    };
    const card = make("ha-card");
    const header = make("header");
    const title = make("div");
    title.append(make("h2", this.config.title));
    if (this.config.route) title.append(make("div", this.config.route, "muted"));
    const button = make("button", this.pending || status === "refreshing" ? "Lädt …" : "↻ Aktualisieren");
    button.type = "button";
    button.disabled = !this.ha || this.pending || status === "refreshing";
    button.addEventListener("click", () => this.refresh());
    header.append(title, button);
    card.append(header);

    const note = this.actionError || labels[status] || (!entity ? "VRN-Sensor fehlt." : "");
    if (note) {
      const message = make("p", note, "muted");
      message.setAttribute("role", "status");
      card.append(message);
    }
    if (["ready", "refreshing", "fetch_error"].includes(status)) {
      for (const trip of data.departures ?? []) {
        const row = make("section", "", "train");
        const found = Boolean(trip.scheduled);
        const time = trip.planned || trip.scheduled || trip.requested;
        row.append(make("strong", `${data.line} · ${time}`));
        let badge = "Keine Echtzeitdaten";
        if (!found) badge = "Fahrt nicht im VRN-Ergebnis";
        else if (trip.cancelled) badge = "Fällt aus";
        else if (trip.delay === 0) badge = "Pünktlich laut Prognose";
        else if (trip.delay != null) badge = `${trip.delay > 0 ? "+" : ""}${trip.delay} min · ${trip.estimated}`;
        row.append(make("span", badge, trip.cancelled || trip.delay > 0 ? "danger" : "muted"));
        const details = [];
        if (found && time !== trip.requested) details.push(`Wunschzeit ${trip.requested}`);
        if (trip.arrival && !trip.cancelled) details.push(`Ankunft ${trip.arrival}`);
        if (trip.platform && !trip.cancelled) details.push(`Gleis ${trip.platform}`);
        if (details.length) row.append(make("div", details.join(" · "), "details muted"));
        if (trip.platform && trip.planned_platform && trip.platform !== trip.planned_platform) {
          row.append(make("p", `Gleiswechsel von ${trip.planned_platform} auf ${trip.platform}`, "warning"));
        }
        for (const message of trip.messages ?? []) row.append(make("p", message, "warning"));
        card.append(row);
      }
    }
    const footer = make("footer", "", "muted");
    if (data.last_success && ["ready", "refreshing", "fetch_error"].includes(status)) {
      const stamp = new Intl.DateTimeFormat("de-DE", { timeZone: "Europe/Berlin", dateStyle: "short",
        timeStyle: "short" }).format(new Date(data.last_success));
      footer.append(document.createTextNode(`${status === "fetch_error" ? "Veralteter Datenstand" : "Letzter Abruf"} ${stamp} · `));
    }
    const source = make("a", "Daten vom VRN");
    source.href = "https://opendata.vrn.de/datasets/open-service-rapidjson-schnittstelle";
    source.target = "_blank";
    source.rel = "noopener noreferrer";
    footer.append(source);
    card.append(footer);
    root.replaceChildren(style, card);
  }
}
if (!customElements.get("vrn-schulbahn-card")) {
  customElements.define("vrn-schulbahn-card", VrnSchulbahnCard);
}
