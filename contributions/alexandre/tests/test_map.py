import json
import os
import shutil
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from aerosafe.observations import load_file, timestamp, normalize
from aerosafe.map_export import group_points, export_map

ROOT=Path(__file__).resolve().parents[1]

class MapTests(unittest.TestCase):
    def setUp(self):
        self.records=load_file(ROOT/'data/sample_observations.jsonl')
        self.start=timestamp('2026-01-01T09:00:00Z','start')
        self.end=timestamp('2026-01-01T11:00:00Z','end')

    def test_points_are_grouped_sorted_and_deduplicated(self):
        result=group_points(self.records,'synthetic',self.start,self.end)
        self.assertEqual(len(result),2)
        self.assertEqual(len(result[0]['points']),3)
        self.assertEqual(result[0]['points'][0]['position_time'],'2026-01-01T10:00:00Z')

    def test_sources_do_not_mix(self):
        self.assertEqual(group_points(self.records,'opensky',self.start,self.end),[])

    def test_latest_contact_wins_for_same_position(self):
        updated=dict(self.records[0],last_contact=timestamp('2026-01-01T10:00:25Z','contact'),callsign='UPDATED')
        result=group_points(self.records+[updated],'synthetic',self.start,self.end)
        self.assertEqual(result[0]['points'][-1]['callsign'],'UPDATED')
        self.assertEqual(len(result[0]['points']),3)

    def test_missing_coordinates_are_excluded(self):
        record=dict(self.records[0],latitude_deg=None)
        self.assertEqual(group_points([record],'synthetic',self.start,self.end),[])

    def test_end_of_period_is_exclusive(self):
        start=timestamp('2026-01-01T10:00:10Z','start')
        end=timestamp('2026-01-01T10:00:20Z','end')
        result=group_points(self.records,'synthetic',start,end)
        self.assertTrue(all(len(a['points'])==1 for a in result))

    def test_invalid_period_is_rejected_before_database_access(self):
        for hours in (0,-1,float('nan'),169):
            with self.subTest(hours=hours),self.assertRaises(ValueError):
                export_map(hours=hours)

    def test_html_cannot_be_closed_by_callsign(self):
        directory=Path(os.environ.get('AEROSAFE_TEST_TMP',tempfile.gettempdir()))/('aerosafe-map-test-'+uuid.uuid4().hex)
        directory.mkdir(parents=True)
        now=datetime.now(timezone.utc)-timedelta(minutes=1)
        record=dict(self.records[0],source='opensky',callsign='</script>',position_time=now,last_contact=now)
        try:
            with patch('aerosafe.storage.map_observations',return_value=[record]):
                result=export_map(object(),directory/'map.html')
            html=(directory/'map.html').read_text(encoding='utf-8')
            self.assertEqual(result['positions'],1)
            self.assertIn('\\u003c/script\\u003e',html)
            self.assertNotIn('__AEROSAFE_DATA__',html)
            self.assertNotIn('__AEROSAFE_REPLAY__',html)
            self.assertIn('class ReplayClock',html)
            self.assertIn('id="timeline"',html)
        finally:
            assert directory.name.startswith('aerosafe-map-test-')
            shutil.rmtree(directory)
