"""Requêtes PostgreSQL ; le pilote est chargé seulement à la connexion."""
import hashlib
from pathlib import Path
from .observations import aircraft_id, fingerprint, serializable

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"

def connect():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "Pilote PostgreSQL absent. Utiliser Docker ou installer requirements.txt."
        ) from exc
    try:
        return psycopg.connect(connect_timeout=5, options="-c timezone=UTC")
    except psycopg.OperationalError as exc:
        raise RuntimeError(
            "Connexion PostgreSQL impossible. Vérifier le service et les variables PG*."
        ) from exc

def migrate(conn):
    applied = []
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(7418351)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migration (
                name text PRIMARY KEY,
                sha256 char(64) NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        known = dict(conn.execute("SELECT name, sha256 FROM schema_migration").fetchall())
        for path in sorted(MIGRATIONS.glob("*.sql")):
            sql = path.read_text(encoding="utf-8")
            digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
            if path.name in known:
                if known[path.name] != digest:
                    raise ValueError(f"Migration déjà appliquée et modifiée : {path.name}")
                continue
            conn.execute(sql)
            conn.execute("INSERT INTO schema_migration (name, sha256) VALUES (%s, %s)",
                         (path.name, digest))
            applied.append(path.name)
    return applied

def import_records(conn, records, mode="replay"):
    if mode not in ("live", "replay"):
        raise ValueError("Mode invalide.")
    inserted = 0
    with conn.transaction():
        for record in records:
            conn.execute("INSERT INTO aeronef (icao24) VALUES (%s) ON CONFLICT DO NOTHING",
                         (record["icao24"],))
            params = dict(record, fingerprint=fingerprint(record), ingest_mode=mode)
            row = conn.execute("""
                INSERT INTO observation
                    (fingerprint, icao24, source, callsign, position_time, last_contact,
                     ingest_mode, latitude_deg, longitude_deg, baro_altitude_m,
                     velocity_mps, true_track_deg)
                VALUES
                    (%(fingerprint)s, %(icao24)s, %(source)s, %(callsign)s,
                     %(position_time)s, %(last_contact)s, %(ingest_mode)s,
                     %(latitude_deg)s, %(longitude_deg)s, %(baro_altitude_m)s,
                     %(velocity_mps)s, %(true_track_deg)s)
                ON CONFLICT (fingerprint) DO NOTHING
                RETURNING id
            """, params).fetchone()
            inserted += row is not None
    return {"lues": len(records), "ajoutees": inserted,
            "deja_presentes": len(records) - inserted}

def counts(conn):
    return {
        "aeronefs": conn.execute("SELECT count(*) FROM aeronef").fetchone()[0],
        "observations": conn.execute("SELECT count(*) FROM observation").fetchone()[0],
    }

def trajectory(conn, icao24, source="synthetic", start=None, end=None):
    icao24 = aircraft_id(icao24)
    if source not in ("synthetic", "opensky"):
        raise ValueError("Source invalide.")
    if start is not None and end is not None and start >= end:
        raise ValueError("Le début doit précéder la fin de la période.")
    filters = [
        "icao24 = %s", "source = %s", "position_time IS NOT NULL",
        "latitude_deg IS NOT NULL", "longitude_deg IS NOT NULL",
    ]
    values = [icao24, source]
    if start is not None:
        filters.append("position_time >= %s"); values.append(start)
    if end is not None:
        filters.append("position_time < %s"); values.append(end)
    # Les fragments SQL ci-dessus sont constants ; toutes les entrées restent paramétrées.
    cursor = conn.execute("""
        SELECT DISTINCT ON (position_time)
            icao24, source, callsign, position_time, last_contact,
            latitude_deg, longitude_deg, baro_altitude_m, velocity_mps, true_track_deg
        FROM observation WHERE """ + " AND ".join(filters) + """
        ORDER BY position_time ASC, last_contact DESC, id DESC
        LIMIT 10001
    """, values)
    rows = cursor.fetchall()
    if len(rows) > 10000:
        raise ValueError("Plus de 10000 points : sélectionner une période plus courte.")
    columns = [column.name for column in cursor.description]
    return [serializable(dict(zip(columns, row))) for row in rows]

def map_observations(conn, source, start, end):
    if source not in ('opensky', 'synthetic') or start >= end:
        raise ValueError('Source ou période invalide.')
    cursor = conn.execute('''
        SELECT DISTINCT ON (icao24, position_time)
            icao24, source, callsign, position_time, last_contact,
            latitude_deg, longitude_deg, baro_altitude_m, velocity_mps, true_track_deg
        FROM observation
        WHERE source = %s AND position_time >= %s AND position_time < %s
          AND latitude_deg IS NOT NULL AND longitude_deg IS NOT NULL
        ORDER BY icao24, position_time, last_contact DESC, id DESC
        LIMIT 50001
    ''', (source, start, end))
    rows = cursor.fetchall()
    if len(rows) > 50000:
        raise ValueError('Plus de 50000 positions : réduire la période avec --hours.')
    names = [column.name for column in cursor.description]
    return [serializable(dict(zip(names, row))) for row in rows]
