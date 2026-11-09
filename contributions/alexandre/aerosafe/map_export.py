"""Export d'un instantané cartographique, sans serveur API."""
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .observations import load_file, serializable, timestamp

def group_points(records, source, start, end):
    if source not in ("opensky", "synthetic") or start >= end:
        raise ValueError("Source ou période invalide.")
    latest = {}
    for record in records:
        record = serializable(record)
        value = record.get("position_time")
        if record.get("source") != source or value is None:
            continue
        when = timestamp(value, "position_time")
        if not start <= when < end:
            continue
        if record.get("latitude_deg") is None or record.get("longitude_deg") is None:
            continue
        key = (record["icao24"], when)
        previous = latest.get(key)
        if previous is None or timestamp(record["last_contact"], "last_contact") >= timestamp(previous["last_contact"], "last_contact"):
            latest[key] = record
    if len(latest) > 50000:
        raise ValueError("Plus de 50000 positions : réduire la période avec --hours.")
    grouped = defaultdict(list)
    for _, record in sorted(latest.items(), key=lambda pair: pair[0]):
        grouped[record["icao24"]].append(record)
    return [{"icao24": key, "callsign": points[-1].get("callsign"),
             "points": points} for key, points in sorted(grouped.items())]

def export_map(conn=None, output="maps/carte.html", source="opensky",
               hours=24, captures=None):
    if not math.isfinite(hours) or not 0 < hours <= 168:
        raise ValueError("--hours doit être compris entre 0 exclus et 168 heures.")
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    if captures is not None:
        records = []
        for path in sorted(Path(captures).glob("*_observations.jsonl")):
            if path.stat().st_size:
                records.extend(load_file(path))
        origin = "captures locales"
    else:
        from .storage import map_observations
        records = map_observations(conn, source, start, end)
        origin = "PostgreSQL"
    aircraft = group_points(records, source, start, end)
    data = {
        "source": source, "origin": origin,
        "generated_at": end.isoformat(), "start": start.isoformat(), "end": end.isoformat(),
        "aircraft": aircraft,
    }
    # Même un indicatif malveillant ne peut pas fermer le bloc JSON de la page.
    payload = json.dumps(data, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = (Path(__file__).parent / "templates" / "map.html").read_text(encoding="utf-8")
    rendered = template.replace("__AEROSAFE_DATA__", payload)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    return {"fichier": str(destination), "source": source, "origine": origin,
            "aeronefs": len(aircraft), "positions": sum(len(a["points"]) for a in aircraft),
            "debut_utc": start.isoformat(), "fin_utc": end.isoformat()}
