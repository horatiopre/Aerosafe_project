"""Validation du contrat v1, indépendante de la base de données."""
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

ICAO24 = re.compile(r"^[0-9a-f]{6}$")
FIELDS = {
    "icao24", "source", "last_contact", "position_time", "callsign",
    "latitude_deg", "longitude_deg", "baro_altitude_m", "velocity_mps",
    "true_track_deg",
}
MEASURES = {
    "latitude_deg": (-90, 90),
    "longitude_deg": (-180, 180),
    "baro_altitude_m": (None, None),
    "velocity_mps": (0, None),
    "true_track_deg": (0, 360),
}

def aircraft_id(value):
    if not isinstance(value, str) or not ICAO24.fullmatch(value.strip().lower()):
        raise ValueError("icao24 doit contenir exactement 6 caractères hexadécimaux.")
    return value.strip().lower()

def timestamp(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field} doit être une date ISO 8601 avec fuseau horaire.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} : date ISO 8601 invalide.") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field} doit préciser son fuseau horaire.")
    return result.astimezone(timezone.utc)

def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def normalize(record):
    if not isinstance(record, dict):
        raise ValueError("Une observation doit être un objet JSON.")
    unknown = record.keys() - FIELDS
    if unknown:
        raise ValueError("Champs inconnus : " + ", ".join(sorted(unknown)))
    result = {"icao24": aircraft_id(record.get("icao24"))}
    source = record.get("source")
    if source not in ("synthetic", "opensky"):
        raise ValueError("source doit valoir synthetic ou opensky.")
    result["source"] = source
    result["last_contact"] = timestamp(record.get("last_contact"), "last_contact")
    position_time = record.get("position_time")
    result["position_time"] = (
        timestamp(position_time, "position_time") if position_time is not None else None
    )
    if result["position_time"] and result["position_time"] > result["last_contact"]:
        raise ValueError("position_time ne peut pas dépasser last_contact.")
    callsign = record.get("callsign")
    if callsign is not None and (not isinstance(callsign, str) or len(callsign.strip()) > 16):
        raise ValueError("callsign doit être un texte de 16 caractères maximum ou null.")
    result["callsign"] = callsign.strip() or None if callsign is not None else None
    for field, (low, high) in MEASURES.items():
        value = record.get(field)
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{field} doit être un nombre ou null.")
            try:
                value = float(value)
            except OverflowError as exc:
                raise ValueError(f"{field} doit être un nombre fini.") from exc
            if not math.isfinite(value):
                raise ValueError(f"{field} doit être un nombre fini.")
            if low is not None and value < low:
                raise ValueError(f"{field} est inférieur à {low}.")
            if high is not None and (value >= high if field == "true_track_deg" else value > high):
                raise ValueError(f"{field} dépasse la plage autorisée.")
            if value == 0:
                value = 0.0
        result[field] = value
    return result

def serializable(record):
    return {k: iso(v) if isinstance(v, datetime) else v for k, v in record.items()}

def fingerprint(record):
    payload = json.dumps(serializable(record), sort_keys=True, ensure_ascii=True,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def load_file(path):
    records = []
    errors = []
    with Path(path).open(encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                records.append(normalize(json.loads(line)))
            except (ValueError, TypeError) as exc:
                errors.append(f"Ligne {line_number} : {exc}")
    if errors:
        raise ValueError("Import refusé ; aucune donnée écrite.\n" + "\n".join(errors))
    if not records:
        raise ValueError("Le fichier ne contient aucune observation.")
    return records

def summary(records):
    unique = len({fingerprint(record) for record in records})
    return {
        "lignes_valides": len(records),
        "observations_distinctes": unique,
        "doublons_dans_le_fichier": len(records) - unique,
        "aeronefs": len({record["icao24"] for record in records}),
    }
