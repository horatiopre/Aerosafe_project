"""Collecte ponctuelle OpenSky, cache horodaté et conversion du contrat v1."""
import json
import hashlib
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from .observations import normalize, serializable, iso, timestamp

API = "https://opensky-network.org/api/states/all"
TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
DEFAULT_BBOX = (48.0, 1.0, 50.0, 3.5)

class CollectionError(RuntimeError):
    pass

def check_bbox(values):
    if len(values) != 4:
        raise ValueError("Zone attendue : latitude min, longitude min, latitude max, longitude max.")
    a, b, c, d = map(float, values)
    if not all(math.isfinite(v) for v in (a, b, c, d)):
        raise ValueError("Coordonnées de zone non finies.")
    if not (-90 <= a < c <= 90 and -180 <= b < d <= 180):
        raise ValueError("Zone invalide : vérifier les bornes et leur ordre.")
    return [a, b, c, d]

def request_json(request):
    try:
        with urlopen(request, timeout=20) as response:
            content = response.read(10_000_001)
            if len(content) > 10_000_000:
                raise CollectionError("Réponse OpenSky trop volumineuse.")
            return json.loads(content)
    except HTTPError as exc:
        if exc.code == 429:
            wait = exc.headers.get("X-Rate-Limit-Retry-After-Seconds") or exc.headers.get("Retry-After")
            detail = f" Délai annoncé : {str(wait)[:80]}." if wait else ""
            raise CollectionError("Quota OpenSky atteint (429)." + detail) from None
        if exc.code in (401, 403):
            raise CollectionError("Accès OpenSky refusé. Vérifier les identifiants API (401/403).") from None
        raise CollectionError(f"Service OpenSky indisponible (HTTP {exc.code}).") from None
    except (URLError, TimeoutError, OSError):
        raise CollectionError("Connexion OpenSky impossible ou délai de 20 secondes dépassé.") from None
    except (ValueError, UnicodeError):
        raise CollectionError("Réponse OpenSky illisible : JSON attendu.") from None

def fetch(bbox):
    bbox = check_bbox(bbox)
    headers = {"User-Agent": "AeroSafe-student-project/0.2", "Accept": "application/json"}
    client_id = os.environ.get("OPENSKY_CLIENT_ID", "")
    client_secret = os.environ.get("OPENSKY_CLIENT_SECRET", "")
    if bool(client_id) != bool(client_secret):
        raise CollectionError("Renseigner ensemble OPENSKY_CLIENT_ID et OPENSKY_CLIENT_SECRET.")
    if client_id:
        body = urlencode({"grant_type": "client_credentials", "client_id": client_id,
                          "client_secret": client_secret}).encode()
        token = request_json(Request(TOKEN_URL, data=body,
                             headers={"Content-Type": "application/x-www-form-urlencoded"}))
        access = token.get("access_token") if isinstance(token, dict) else None
        if not isinstance(access, str) or not access:
            raise CollectionError("OpenSky n’a pas fourni de jeton utilisable.")
        headers["Authorization"] = "Bearer " + access
    query = urlencode(dict(zip(("lamin", "lomin", "lamax", "lomax"), bbox)))
    return request_json(Request(API + "?" + query, headers=headers))

def epoch(value, field, nullable=False):
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field} : horodatage source invalide.")
    try:
        return iso(datetime.fromtimestamp(value, timezone.utc))
    except (ValueError, OverflowError, OSError):
        raise ValueError(f"{field} : horodatage source hors plage.") from None

def convert(payload):
    if not isinstance(payload, dict) or "time" not in payload or "states" not in payload:
        raise CollectionError("Structure OpenSky invalide : time et states requis.")
    try:
        epoch(payload["time"], "time")
    except (ValueError, OverflowError):
        raise CollectionError("Horodatage de réponse OpenSky invalide.") from None
    states = payload["states"]
    if states is None:
        states = []
    if not isinstance(states, list):
        raise CollectionError("Structure OpenSky invalide : states doit être une liste.")
    records, rejected = [], []
    for index, state in enumerate(states):
        try:
            if not isinstance(state, list) or len(state) < 17:
                raise ValueError("État OpenSky incomplet.")
            record = normalize({
                "icao24": state[0], "source": "opensky", "callsign": state[1],
                "position_time": epoch(state[3], "time_position", nullable=True),
                "last_contact": epoch(state[4], "last_contact"),
                "longitude_deg": state[5], "latitude_deg": state[6],
                "baro_altitude_m": state[7], "velocity_mps": state[9],
                "true_track_deg": state[10],
            })
            records.append(record)
        except (ValueError, TypeError, OverflowError) as exc:
            rejected.append({"index": index, "raison": str(exc)})
    if states and not records:
        raise CollectionError("Tous les états OpenSky sont invalides ; cache précédent conservé.")
    return records, rejected

def atomic_json(path, value):
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)

def collect(directory, bbox=DEFAULT_BBOX, fallback=False, max_cache_age=3600):
    bbox = check_bbox(bbox)
    if not math.isfinite(max_cache_age) or max_cache_age <= 0:
        raise ValueError("La durée maximale du cache doit être positive.")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(json.dumps(bbox).encode()).hexdigest()[:16]
    cache = directory / ("cache_" + key + ".json")
    now = datetime.now(timezone.utc)
    reason = None
    try:
        payload = fetch(bbox)
        records, rejected = convert(payload)
    except CollectionError as exc:
        if not fallback:
            raise
        reason = str(exc)
        try:
            envelope = json.loads(cache.read_text(encoding="utf-8"))
            if envelope["bbox"] != bbox:
                raise ValueError("Zone différente.")
            fetched_at = timestamp(envelope["fetched_at"], "fetched_at")
            age = (now - fetched_at).total_seconds()
            if not 0 <= age <= max_cache_age:
                raise ValueError("Cache trop ancien ou date future.")
            payload = envelope["payload"]
            records, rejected = convert(payload)
        except (OSError, ValueError, KeyError, TypeError, CollectionError):
            raise CollectionError(reason + " Aucun cache valide pour cette zone.") from None
        mode = "cache"
    else:
        fetched_at = datetime.now(timezone.utc)
        mode = "live"
        envelope = {"bbox": bbox, "fetched_at": iso(fetched_at), "payload": payload}
        # Une réponse JSON non finie est refusée plutôt que de remplacer un cache sain.
        try:
            json.dumps(envelope, allow_nan=False)
        except ValueError:
            raise CollectionError("Réponse OpenSky contenant des nombres non finis.") from None
        atomic_json(cache, envelope)
    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:8]
    raw_path = directory / (tag + "_raw.json")
    data_path = directory / (tag + "_observations.jsonl")
    report_path = directory / (tag + "_report.json")
    atomic_json(raw_path, envelope)
    with data_path.open("x", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(serializable(record), ensure_ascii=False, allow_nan=False) + "\n")
    report = {
        "mode": mode, "zone": bbox, "collecte_source_utc": iso(fetched_at),
        "instant_reponse_utc": epoch(payload["time"], "time"),
        "age_cache_secondes": max(0, int((datetime.now(timezone.utc)-fetched_at).total_seconds())),
        "observations_valides": len(records), "observations_rejetees": len(rejected),
        "rejets": rejected, "raison_repli": reason,
        "fichier_brut": str(raw_path), "fichier_observations": str(data_path),
        "fichier_rapport": str(report_path),
        "aeronefs_exemples": sorted({r["icao24"] for r in records})[:5],
    }
    atomic_json(report_path, report)
    return records, report
