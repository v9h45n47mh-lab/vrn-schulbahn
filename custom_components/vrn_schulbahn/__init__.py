"""VRN Schulbahn Home Assistant integration."""
import asyncio
from datetime import datetime, time, timedelta
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

import aiohttp
import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .efa import select_journeys

DOMAIN = "vrn_schulbahn"
VERSION = "1.0.2"
CARD_URL = "/vrn_schulbahn/vrn-schulbahn-card.js"
SENSOR = "sensor.vrn_schulbahn"
URL = "https://trias.vrn.de/vrn/XML_TRIP_REQUEST2"
ZONE = ZoneInfo("Europe/Berlin")
LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required("origin"): vol.All(vol.Coerce(str), vol.Match(r"^\d+$")),
        vol.Required("destination"): vol.All(vol.Coerce(str), vol.Match(r"^\d+$")),
        vol.Required("school_free_calendars"): vol.All(cv.entity_ids, vol.Length(min=1)),
        vol.Optional("line", default="S3"): cv.string,
        vol.Required("departure_times"): vol.All(
            cv.ensure_list, vol.Length(min=1),
            [vol.Match(r"^(?:[01]\d|2[0-3]):[0-5]\d$")], vol.Unique()
        ),
        vol.Optional("tolerance_minutes", default=2): vol.All(int, vol.Range(min=0, max=10)),
    }),
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    settings = config[DOMAIN]
    calendars = settings["school_free_calendars"]
    times = sorted(settings["departure_times"])
    first_departure = time.fromisoformat(times[0])
    session = async_get_clientsession(hass)
    lock = asyncio.Lock()
    snapshot = {"line": settings["line"], "departures": []}

    def publish(status, **details):
        snapshot.update(status=status, **details)
        hass.states.async_set(SENSOR, status, dict(snapshot))

    async def refresh(now, manual=False):
        local = now.astimezone(ZONE)
        day = local.date()
        if not manual and (
            local.weekday() >= 5 or not time(6, 30) <= local.time().replace(second=0, microsecond=0) <= time(7, 30)
        ):
            return
        if lock.locked():
            return
        async with lock:
            if not manual:
                if any(hass.states.get(entity) is None or
                       hass.states.get(entity).state in (STATE_UNKNOWN, STATE_UNAVAILABLE)
                       for entity in calendars):
                    publish("calendar_error")
                    return
                midnight = datetime.combine(day, time.min, ZONE)
                try:
                    events = await hass.services.async_call(
                        "calendar", "get_events",
                        {"entity_id": calendars, "start_date_time": midnight.isoformat(),
                         "end_date_time": (midnight + timedelta(days=1)).isoformat()},
                        blocking=True, return_response=True,
                    )
                    if any(events[entity]["events"] for entity in calendars):
                        publish("school_free")
                        return
                except Exception as error:
                    LOGGER.debug("Schulkalender konnten nicht gelesen werden: %s", error)
                    publish("calendar_error")
                    return
            publish("refreshing")
            start = datetime.combine(day, first_departure, ZONE) - timedelta(minutes=20)
            params = {
                "outputFormat": "RapidJSON", "name_origin": settings["origin"],
                "type_origin": "stop", "name_destination": settings["destination"],
                "type_destination": "stop", "itdDate": start.strftime("%Y%m%d"),
                "itdTime": start.strftime("%H%M"), "useRealtime": "1",
                "locationServerActive": "1", "calcNumberOfTrips": "12",
                "tripReductionMacro": "1",
            }
            try:
                async with session.get(URL, params=params, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    response.raise_for_status()
                    payload = await response.json(content_type=None)
                departures = select_journeys(
                    payload, day, ZONE, settings["origin"], settings["destination"],
                    settings["line"], times, settings["tolerance_minutes"],
                )
            except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError) as error:
                LOGGER.debug("VRN-Abruf fehlgeschlagen: %s", error)
                publish("fetch_error")
                return
            publish("ready", departures=departures, date=day.isoformat(),
                    last_success=dt_util.now().isoformat())

    active_date = None

    async def scheduled(now):
        nonlocal active_date
        today = now.astimezone(ZONE).date().isoformat()
        if active_date is not None and active_date != today and snapshot.get("date") != today:
            publish("idle", departures=[], date=None, last_success=None)
        active_date = today
        await refresh(now)

    async def manual_refresh(_call):
        await refresh(dt_util.now(), manual=True)

    await hass.http.async_register_static_paths([
        StaticPathConfig(
            CARD_URL,
            str(Path(__file__).with_name("vrn-schulbahn-card.js")),
            False,
        ),
    ])
    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    publish("idle")
    hass.services.async_register(DOMAIN, "refresh", manual_refresh)
    async_track_time_change(hass, scheduled, second=0)
    return True
