"""Parse direct journeys from the VRN EFA response."""
from datetime import datetime
from html.parser import HTMLParser


class MessageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        if data.strip():
            self.parts.append(data.strip())


def messages(leg, journey):
    result = []
    for item in [*journey.get("infos", []), *leg.get("infos", []),
                 *(hint for hint in leg.get("hints", []) if hint.get("type") != "Timetable")]:
        raw = item.get("content") or item.get("subtitle") or item.get("title")
        if isinstance(raw, str):
            parser = MessageText()
            parser.feed(raw)
            message = " ".join(parser.parts)
            if message and message not in result:
                result.append(message)
    return result


def stop_id(point):
    return str(point.get("parent", {}).get("properties", {}).get("stopId")
               or point.get("properties", {}).get("stopId") or point.get("id", ""))


def clock(value, zone):
    return datetime.fromisoformat(value).astimezone(zone)


def select_journeys(payload, day, zone, origin, destination, line, times, tolerance):
    if not isinstance(payload.get("journeys"), list):
        raise ValueError("VRN hat keine auswertbare Fahrtenliste geliefert")
    candidates = []
    for journey in payload["journeys"]:
        legs = journey.get("legs", [])
        if len(legs) != 1:
            continue
        leg = legs[0]
        start, end = leg["origin"], leg["destination"]
        if (stop_id(start), stop_id(end), leg.get("transportation", {}).get("number")) != (
                origin, destination, line):
            continue
        scheduled = start.get("departureTimeBaseTimetable") or start.get("departureTimePlanned")
        if not scheduled:
            continue
        departure = clock(scheduled, zone)
        if departure.date() != day:
            continue
        planned = start.get("departureTimePlanned") or scheduled
        estimate = start.get("departureTimeEstimated")
        realtime = bool(estimate and (leg.get("isRealtimeControlled") or estimate != planned))
        cancelled = any(part.get("isCancelled") is True or
                        str(part.get("realtimeStatus", "")).lower() in {"cancelled", "canceled"}
                        for part in (journey, leg, start, end))
        predicted = clock(estimate, zone) if realtime else None
        arrival = end.get("arrivalTimeEstimated") if realtime else None
        candidates.append((departure.hour * 60 + departure.minute, {
            "scheduled": departure.strftime("%H:%M"),
            "planned": clock(planned, zone).strftime("%H:%M"),
            "estimated": predicted.strftime("%H:%M") if predicted else None,
            "delay": round((predicted - departure).total_seconds() / 60) if predicted else None,
            "arrival": clock(arrival or end["arrivalTimePlanned"], zone).strftime("%H:%M")
            if arrival or end.get("arrivalTimePlanned") else None,
            "platform": start.get("properties", {}).get("platformName"),
            "planned_platform": start.get("properties", {}).get("plannedPlatformName"),
            "cancelled": cancelled,
            "messages": messages(leg, journey),
        }))
    remaining = set(range(len(candidates)))
    matches = {}
    pairs = []
    for requested in times:
        hour, minute = map(int, requested.split(":"))
        for index, (actual, _) in enumerate(candidates):
            distance = abs(actual - hour * 60 - minute)
            if distance <= tolerance:
                pairs.append((distance, requested, index))
    for _, requested, index in sorted(pairs):
        if requested not in matches and index in remaining:
            matches[requested] = candidates[index][1]
            remaining.remove(index)
    return [{"requested": time, **matches.get(time, {})} for time in times]
