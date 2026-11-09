import copy
import json
import subprocess
import sys
import io
from unittest.mock import patch
import unittest
from pathlib import Path
from aerosafe.observations import normalize, fingerprint, load_file, summary, timestamp

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample_observations.jsonl"

class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(SAMPLE.read_text(encoding="utf-8").splitlines()[0])

    def test_example_has_two_aircraft_six_observations_and_one_duplicate(self):
        self.assertEqual(summary(load_file(SAMPLE)), {
            "lignes_valides": 7, "observations_distinctes": 6,
            "doublons_dans_le_fichier": 1, "aeronefs": 2,
        })

    def test_timezone_variants_have_the_same_identity(self):
        alternate = copy.deepcopy(self.record)
        alternate["position_time"] = "2026-01-01T11:00:20+01:00"
        alternate["last_contact"] = "2026-01-01T11:00:22+01:00"
        self.assertEqual(fingerprint(normalize(self.record)), fingerprint(normalize(alternate)))

    def test_identifier_and_callsign_are_normalized(self):
        self.record.update(icao24=" A0B1C2 ", callsign=" FICT01 ")
        actual = normalize(self.record)
        self.assertEqual(actual["icao24"], "a0b1c2")
        self.assertEqual(actual["callsign"], "FICT01")

    def test_missing_measurements_stay_null(self):
        self.record["baro_altitude_m"] = None
        self.record.pop("velocity_mps")
        actual = normalize(self.record)
        self.assertIsNone(actual["baro_altitude_m"])
        self.assertIsNone(actual["velocity_mps"])

    def test_snapshot_without_position_is_retained(self):
        self.record.update(position_time=None, latitude_deg=None, longitude_deg=None)
        self.assertIsNone(normalize(self.record)["position_time"])

    def test_timezone_is_required(self):
        with self.assertRaisesRegex(ValueError, "fuseau"):
            timestamp("2026-01-01T10:00:00", "date")

    def test_invalid_identifiers_are_rejected(self):
        for value in (None, "123", "gggggg", 123456):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize(dict(self.record, icao24=value))

    def test_measurements_must_be_finite_numbers(self):
        for value in (float("nan"), float("inf"), float("-inf"), True, "100"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize(dict(self.record, velocity_mps=value))

    def test_units_and_bounds_are_checked(self):
        for changes in ({"latitude_deg": 91}, {"longitude_deg": -181},
                        {"velocity_mps": -1}, {"true_track_deg": 360},
                        {"true_track_deg": -1}, {"altitude_ft": 1000}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                normalize(dict(self.record, **changes))

    def test_direction_wrap_values_are_valid(self):
        for angle in (0, 1, 359, 359.99):
            self.assertEqual(normalize(dict(self.record, true_track_deg=angle))["true_track_deg"], angle)

    def test_invalid_file_reports_the_line(self):
        content = json.dumps(self.record) + '\n{"icao24":"oops"}\n'
        with patch("pathlib.Path.open", return_value=io.StringIO(content)):
            with self.assertRaisesRegex(ValueError, "Ligne 2"):
                load_file("invalid.jsonl")

    def test_empty_file_is_rejected(self):
        with patch("pathlib.Path.open", return_value=io.StringIO("\n")):
            with self.assertRaises(ValueError):
                load_file("empty.jsonl")

    def test_numeric_types_do_not_create_false_duplicates(self):
        first = normalize(dict(self.record, velocity_mps=100, latitude_deg=0))
        second = normalize(dict(self.record, velocity_mps=100.0, latitude_deg=-0.0))
        self.assertEqual(fingerprint(first), fingerprint(second))

    def test_contact_cannot_predate_position(self):
        with self.assertRaisesRegex(ValueError, "last_contact"):
            normalize(dict(self.record, last_contact="2026-01-01T09:59:00Z"))

    def test_validation_command_does_not_need_postgresql(self):
        result = subprocess.run([sys.executable, "-B", "-m", "aerosafe", "validate", str(SAMPLE)],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["observations_distinctes"], 6)

if __name__ == "__main__":
    unittest.main()
