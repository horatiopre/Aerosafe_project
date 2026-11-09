"""Commandes du premier exercice AeroSafe."""
import argparse
import json
import sys
from pathlib import Path
from .observations import load_file, summary, timestamp
from . import storage, opensky, map_export

def parser():
    root = argparse.ArgumentParser(description="AeroSafe : observations et trajectoires")
    sub = root.add_subparsers(dest="command", required=True)
    for name in ("validate", "import", "demo"):
        cmd = sub.add_parser(name)
        cmd.add_argument("file", help="Fichier JSONL au format observation v1")
    cmd = sub.add_parser("collect", help="Collecter un instantanÃ© OpenSky")
    cmd.add_argument("--bbox", type=float, nargs=4, default=opensky.DEFAULT_BBOX,
                     metavar=("LAT_MIN", "LON_MIN", "LAT_MAX", "LON_MAX"))
    cmd.add_argument("--directory", default="captures")
    cmd.add_argument("--import-db", action="store_true")
    cmd.add_argument("--use-cache-on-error", action="store_true")
    cmd.add_argument("--max-cache-age", type=float, default=3600)
    cmd = sub.add_parser("map", help="Exporter une carte des positions enregistrées")
    cmd.add_argument("--source", choices=("opensky", "synthetic"), default="opensky")
    cmd.add_argument("--hours", type=float, default=24)
    cmd.add_argument("--output", default="maps/carte.html")
    cmd.add_argument("--from-captures", action="store_true")
    sub.add_parser("init-db")
    sub.add_parser("stats")
    cmd = sub.add_parser("trajectory")
    cmd.add_argument("icao24")
    cmd.add_argument("--source", choices=("synthetic", "opensky"), default="synthetic")
    cmd.add_argument("--from", dest="start")
    cmd.add_argument("--to", dest="end")
    return root

def run(args):
    if args.command == "map":
        if args.from_captures:
            return map_export.export_map(output=args.output, source=args.source,
                                         hours=args.hours, captures="captures")
        with storage.connect() as conn:
            return map_export.export_map(conn, args.output, args.source, args.hours)
    if args.command == "collect":
        records, report = opensky.collect(args.directory, args.bbox,
                                         args.use_cache_on_error, args.max_cache_age)
        if args.import_db:
            try:
                with storage.connect() as conn:
                    storage.migrate(conn)
                    report["import"] = storage.import_records(
                        conn, records, mode="live" if report["mode"] == "live" else "replay")
            except Exception as exc:
                raise RuntimeError(
                    "Collecte sauvegardÃ©e dans " + report["fichier_observations"]
                    + "; import PostgreSQL non confirmÃ© (" + type(exc).__name__ + ")."
                ) from None
            opensky.atomic_json(Path(report["fichier_rapport"]), report)
        return report
    records = load_file(args.file) if args.command in ("validate", "import", "demo") else None
    if args.command == "validate":
        return summary(records)
    start = timestamp(args.start, "--from") if getattr(args, "start", None) else None
    end = timestamp(args.end, "--to") if getattr(args, "end", None) else None
    with storage.connect() as conn:
        if args.command == "init-db":
            return {"migrations_appliquees": storage.migrate(conn)}
        if args.command == "import":
            return storage.import_records(conn, records)
        if args.command == "stats":
            return storage.counts(conn)
        if args.command == "trajectory":
            return storage.trajectory(conn, args.icao24, args.source, start, end)
        if args.command == "demo":
            storage.migrate(conn)
            first = storage.import_records(conn, records)
            after_first = storage.counts(conn)
            second = storage.import_records(conn, records)
            after_second = storage.counts(conn)
            if second["ajoutees"] or after_first != after_second:
                raise RuntimeError("Ã‰chec du contrÃ´le de dÃ©duplication.")
            return {
                "premier_import": first, "second_import": second,
                "totaux": after_second,
                "trajectoire": storage.trajectory(conn, records[0]["icao24"], records[0]["source"]),
            }

def main():
    args = parser().parse_args()
    try:
        result = run(args)
    except (ValueError, OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        # Ne jamais afficher une chaÃ®ne de connexion ou un secret dans un diagnostic.
        print(f"OpÃ©ration interrompue ({type(exc).__name__}). VÃ©rifier la base et les migrations.",
              file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
