import io
import json
import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import patch
from aerosafe import opensky

def payload():
    return {"time": 1767261622, "states": [
        ["a0b1c2", "TEST01  ", "France", 1767261600, 1767261602,
         2.3, 48.7, None, False, 100, 359, 0, None, 1100, None, False, 0]]}

class OpenSkyTests(unittest.TestCase):
    def setUp(self):
        base = Path(os.environ.get("AEROSAFE_TEST_TMP", tempfile.gettempdir()))
        self.directory = base / ("aerosafe-test-" + uuid.uuid4().hex)
        self.directory.mkdir(parents=True)

    def tearDown(self):
        assert self.directory.name.startswith("aerosafe-test-")
        shutil.rmtree(self.directory)

    def test_mapping_and_null_altitude(self):
        records, rejected = opensky.convert(payload())
        self.assertFalse(rejected)
        self.assertEqual(records[0]["longitude_deg"], 2.3)
        self.assertEqual(records[0]["latitude_deg"], 48.7)
        self.assertIsNone(records[0]["baro_altitude_m"])
        self.assertEqual(records[0]["source"], "opensky")
        self.assertEqual(records[0]["callsign"], "TEST01")

    def test_missing_position_is_retained(self):
        data = payload()
        for index in (3, 5, 6):
            data["states"][0][index] = None
        records, _ = opensky.convert(data)
        self.assertIsNone(records[0]["position_time"])

    def test_empty_region_is_valid(self):
        self.assertEqual(opensky.convert({"time": 1767261622, "states": None}), ([], []))
        with patch.object(opensky, "fetch", return_value={"time": 1767261622, "states": []}):
            records, report = opensky.collect(self.directory)
        self.assertEqual(report["observations_valides"], 0)

    def test_malformed_response_is_rejected(self):
        for data in ({}, {"time": True, "states": []}, {"time": 1, "states": {}}):
            with self.subTest(data=data), self.assertRaises(opensky.CollectionError):
                opensky.convert(data)

    def test_partial_rejection_is_reported(self):
        data = payload()
        data["states"].append(["bad"])
        records, rejected = opensky.convert(data)
        self.assertEqual(len(records), 1)
        self.assertEqual(rejected[0]["index"], 1)

    def test_total_rejection_does_not_replace_cache(self):
        with patch.object(opensky, "fetch", return_value=payload()):
            opensky.collect(self.directory)
        cache = next(self.directory.glob("cache_*.json"))
        before = cache.read_bytes()
        with patch.object(opensky, "fetch", return_value={"time": 1767261622, "states": [[]]}):
            with self.assertRaises(opensky.CollectionError):
                opensky.collect(self.directory)
        self.assertEqual(cache.read_bytes(), before)

    def test_cache_reuse_preserves_source_dates(self):
        with patch.object(opensky, "fetch", return_value=payload()):
            first, report1 = opensky.collect(self.directory)
        with patch.object(opensky, "fetch", side_effect=opensky.CollectionError("Panne")):
            second, report2 = opensky.collect(self.directory, fallback=True)
        self.assertEqual(first, second)
        self.assertEqual(report2["mode"], "cache")
        self.assertEqual(report1["collecte_source_utc"], report2["collecte_source_utc"])

    def test_cache_cannot_be_used_for_another_region(self):
        with patch.object(opensky, "fetch", return_value=payload()):
            opensky.collect(self.directory)
        with patch.object(opensky, "fetch", side_effect=opensky.CollectionError("Panne")):
            with self.assertRaisesRegex(opensky.CollectionError, "Aucun cache"):
                opensky.collect(self.directory, [40, 1, 41, 2], fallback=True)

    def test_expired_cache_is_rejected(self):
        with patch.object(opensky, "fetch", return_value=payload()):
            opensky.collect(self.directory)
        cache = next(self.directory.glob("cache_*.json"))
        data = json.loads(cache.read_text())
        data["fetched_at"] = "2000-01-01T00:00:00Z"
        cache.write_text(json.dumps(data))
        with patch.object(opensky, "fetch", side_effect=opensky.CollectionError("Panne")):
            with self.assertRaisesRegex(opensky.CollectionError, "Aucun cache"):
                opensky.collect(self.directory, fallback=True)

    def test_invalid_bbox_never_calls_network(self):
        with patch.object(opensky, "fetch") as fetch:
            with self.assertRaises(ValueError):
                opensky.collect(self.directory, [50, 1, 48, 3])
            fetch.assert_not_called()

    def test_quota_error_does_not_retry(self):
        error = HTTPError("https://example.test", 429, "quota",
                          {"X-Rate-Limit-Retry-After-Seconds": "120"}, io.BytesIO())
        with patch.object(opensky, "urlopen", side_effect=error) as request:
            with self.assertRaisesRegex(opensky.CollectionError, "120"):
                opensky.request_json(opensky.Request(opensky.API))
            self.assertEqual(request.call_count, 1)

    def test_network_error_is_readable(self):
        with patch.object(opensky, "urlopen", side_effect=URLError("private details")):
            with self.assertRaisesRegex(opensky.CollectionError, "Connexion OpenSky"):
                opensky.request_json(opensky.Request(opensky.API))

    def test_authentication_uses_token_without_saving_secrets(self):
        with patch.dict(os.environ, {"OPENSKY_CLIENT_ID": "client", "OPENSKY_CLIENT_SECRET": "secret"}):
            with patch.object(opensky, "request_json", side_effect=[{"access_token": "token"}, payload()]) as request:
                opensky.fetch(opensky.DEFAULT_BBOX)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args.args[0].get_header("Authorization"), "Bearer token")


    def test_invalid_response_timestamp_can_use_cache(self):
        with patch.object(opensky, "fetch", return_value=payload()):
            opensky.collect(self.directory)
        with patch.object(opensky, "fetch", return_value={"time": True, "states": []}):
            _, report = opensky.collect(self.directory, fallback=True)
        self.assertEqual(report["mode"], "cache")
