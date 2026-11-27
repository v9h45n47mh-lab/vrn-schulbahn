"""Parse journeys from the VRN EFA response."""
from datetime import datetime, timezone
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



def cancelled(part):
    return part.get("isCancelled") is True or str(
        part.get("realtimeStatus", "")
    ).lower() in {"cancelled", "canceled"}


def timestamp(value):
    return datetime.fromisoformat(value).astimezone(timezone.utc) if value else None


def itinerary_key(legs):
    return tuple(
        (leg.get("transportation", {}).get("id"),
         leg.get("transportation", {}).get("properties", {}).get("tripCode"),
         leg["origin"].get("id"), leg["destination"].get("id"),
         leg["origin"].get("departureTimeBaseTimetable")
         or leg["origin"].get("departureTimePlanned"))
        for leg in legs
    )


def select_journeys(payloads, start, end, zone):
    rows = {}
    for payload in payloads:
        journeys = payload.get("journeys")
        if not isinstance(journeys, list):
            raise ValueError("VRN hat keine auswertbare Fahrtenliste geliefert")
        for journey in journeys:
            legs = journey.get("legs", [])
            transit = [leg for leg in legs if leg.get("transportation", {}).get("number")]
            if not transit:
                continue

            first = transit[0]
            origin = first["origin"]
            destination = legs[-1]["destination"]
            planned = timestamp(origin.get("departureTimePlanned"))
            scheduled = timestamp(origin.get("departureTimeBaseTimetable")) or planned
            if scheduled is None:
                continue

            estimate = timestamp(origin.get("departureTimeEstimated"))
            prediction = estimate if first.get("isRealtimeControlled") or estimate != planned else None
            is_cancelled = cancelled(journey) or any(
                cancelled(part) for leg in transit for part in (leg, leg["origin"], leg["destination"])
            )
            departure = (planned or scheduled) if is_cancelled else (prediction or planned or scheduled)

            arrival = timestamp(destination.get("arrivalTimeEstimated") or destination.get("arrivalTimePlanned"))
            alerts = list(dict.fromkeys(message for leg in legs for message in messages(leg, journey)))
            key = itinerary_key(transit)
            previous = rows.get(key)
            if previous:
                alerts = list(dict.fromkeys([*previous["messages"], *alerts]))
            properties = origin.get("properties", {})
            row = {
                "lines": [leg["transportation"]["number"] for leg in transit],
                "scheduled": scheduled.astimezone(zone).strftime("%H:%M"),
                "planned": (planned or scheduled).astimezone(zone).strftime("%H:%M"),
                "estimated": prediction.astimezone(zone).strftime("%H:%M") if prediction else None,
                "delay": round((prediction - scheduled).total_seconds() / 60) if prediction else None,
                "arrival": arrival.astimezone(zone).strftime("%H:%M") if arrival else None,
                "platform": properties.get("platformName"),
                "planned_platform": properties.get("plannedPlatformName"),
                "cancelled": is_cancelled,
                "messages": alerts,
                "departure": departure.isoformat(),
            }
            if previous and (previous["cancelled"] or
                             (previous["estimated"] and not prediction and not is_cancelled)):
                previous["messages"] = alerts
            else:
                rows[key] = row
    return sorted(
        (row for row in rows.values() if start <= timestamp(row["departure"]) <= end),
        key=lambda row: row["departure"],
    )
