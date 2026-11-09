CREATE TABLE aeronef (
    icao24 text PRIMARY KEY CHECK (icao24 ~ '^[0-9a-f]{6}$')
);

CREATE TABLE observation (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fingerprint char(64) NOT NULL UNIQUE,
    icao24 text NOT NULL REFERENCES aeronef(icao24),
    source text NOT NULL CHECK (source IN ('synthetic', 'opensky')),
    callsign text,
    position_time timestamptz,
    last_contact timestamptz NOT NULL,
    collected_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ingest_mode text NOT NULL CHECK (ingest_mode IN ('replay', 'live')),
    latitude_deg double precision CHECK (latitude_deg BETWEEN -90 AND 90),
    longitude_deg double precision CHECK (longitude_deg BETWEEN -180 AND 180),
    baro_altitude_m double precision,
    velocity_mps double precision CHECK (velocity_mps >= 0),
    true_track_deg double precision CHECK (true_track_deg >= 0 AND true_track_deg < 360),
    CHECK (position_time IS NULL OR position_time <= last_contact)
);

CREATE INDEX observation_trajectory_idx
    ON observation (icao24, source, position_time, last_contact DESC, id DESC);
