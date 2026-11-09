"""Tests sur un schÃ©ma temporaire isolÃ©, sans modifier les tables du projet."""
import os
import unittest
import uuid
from pathlib import Path
from aerosafe.observations import load_file, timestamp
from aerosafe import storage

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample_observations.jsonl"

@unittest.skipUnless(os.environ.get("AEROSAFE_INTEGRATION") == "1",
                     "PostgreSQL requis : dÃ©finir AEROSAFE_INTEGRATION=1")
class PostgreSQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        cls.conn = storage.connect()
        cls.conn.autocommit = True
        cls.schema = "aerosafe_test_" + uuid.uuid4().hex
        cls.conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(cls.schema)))
        cls.addClassCleanup(cls.cleanup_schema)
        cls.conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(cls.schema)))
        storage.migrate(cls.conn)

    @classmethod
    def cleanup_schema(cls):
        from psycopg import sql
        try:
            cls.conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(cls.schema)))
        finally:
            cls.conn.close()

    def setUp(self):
        self.conn.execute("TRUNCATE observation, aeronef")
        self.records = load_file(SAMPLE)

    def test_repeated_import_is_idempotent(self):
        first = storage.import_records(self.conn, self.records)
        second = storage.import_records(self.conn, self.records)
        self.assertEqual(first, {"lues": 7, "ajoutees": 6, "deja_presentes": 1})
        self.assertEqual(second, {"lues": 7, "ajoutees": 0, "deja_presentes": 7})
        self.assertEqual(storage.counts(self.conn), {"aeronefs": 2, "observations": 6})

    def test_trajectory_is_sorted_and_preserves_missing_altitude(self):
        storage.import_records(self.conn, self.records)
        result = storage.trajectory(self.conn, "a0b1c2")
        self.assertEqual([row["position_time"] for row in result],
                         ["2026-01-01T10:00:00Z", "2026-01-01T10:00:10Z", "2026-01-01T10:00:20Z"])
        self.assertIsNone(result[1]["baro_altitude_m"])
        result = storage.trajectory(self.conn, "a0b1c2", start=timestamp("2026-01-01T10:00:10Z", "start"),
                                    end=timestamp("2026-01-01T10:00:20Z", "end"))
        self.assertEqual(len(result), 1)

    def test_migration_can_be_run_twice(self):
        self.assertEqual(storage.migrate(self.conn), [])
        self.assertEqual(self.conn.execute("SELECT count(*) FROM schema_migration").fetchone()[0], 1)

    def test_failed_batch_is_rolled_back(self):
        from psycopg.errors import CheckViolation
        bad = dict(self.records[0], icao24="INVALID")
        with self.assertRaises(CheckViolation):
            storage.import_records(self.conn, [self.records[0], bad])
        self.assertEqual(storage.counts(self.conn), {"aeronefs": 0, "observations": 0})

    def test_new_contact_does_not_repeat_the_same_trajectory_point(self):
        storage.import_records(self.conn, self.records)
        updated = dict(self.records[0], last_contact=timestamp("2026-01-01T10:00:25Z", "contact"))
        storage.import_records(self.conn, [updated])
        self.assertEqual(storage.counts(self.conn)["observations"], 7)
        result = storage.trajectory(self.conn, "a0b1c2")
        self.assertEqual(len(result), 3)
        self.assertEqual(result[-1]["last_contact"], "2026-01-01T10:00:25Z")

    def test_map_query_filters_source_and_period(self):
        storage.import_records(self.conn, self.records)
        start=timestamp("2026-01-01T10:00:10Z","start")
        end=timestamp("2026-01-01T10:00:20Z","end")
        result=storage.map_observations(self.conn,"synthetic",start,end)
        self.assertEqual(len(result),2)
        self.assertTrue(all(r["position_time"]=="2026-01-01T10:00:10Z" for r in result))
        self.assertEqual(storage.map_observations(self.conn,"opensky",start,end),[])

if __name__ == "__main__":
    unittest.main()
