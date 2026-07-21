import unittest
from runner_v2 import validate_schema

class TestRunnerV2Validation(unittest.TestCase):
    
    def test_valid_raw_json(self):
        raw = '{"incident_id": "1", "event_type": "a", "severity": "LOW", "entities": ["x"], "occurred_utc": "2026-07-20T17:50:27Z", "summary": "test"}'
        valid, repaired, errors = validate_schema(raw)
        self.assertTrue(valid)
        self.assertFalse(repaired)
        self.assertEqual(len(errors), 0)
        
    def test_json_inside_fence(self):
        raw = '''```json
{"incident_id": "1", "event_type": "a", "severity": "MEDIUM", "entities": ["x"], "occurred_utc": "2026-07-20T17:50:27+00:00", "summary": "test"}
```'''
        valid, repaired, errors = validate_schema(raw)
        self.assertFalse(valid)
        self.assertTrue(repaired)
        # Should have a JSON Parse error originally
        self.assertTrue(any("JSON Parse Error" in e for e in errors))
        
    def test_missing_key(self):
        raw = '{"event_type": "a", "severity": "LOW", "entities": ["x"], "occurred_utc": "2026-07-20T17:50:27Z", "summary": "test"}'
        valid, repaired, errors = validate_schema(raw)
        self.assertFalse(valid)
        self.assertTrue(any("Missing keys:" in e for e in errors))

    def test_extra_key(self):
        raw = '{"incident_id": "1", "event_type": "a", "severity": "LOW", "entities": ["x"], "occurred_utc": "2026-07-20T17:50:27Z", "summary": "test", "extra": 1}'
        valid, repaired, errors = validate_schema(raw)
        self.assertFalse(valid)
        self.assertTrue(any("Extra keys:" in e for e in errors))

    def test_invalid_severity(self):
        raw = '{"incident_id": "1", "event_type": "a", "severity": "CRITICAL", "entities": ["x"], "occurred_utc": "2026-07-20T17:50:27Z", "summary": "test"}'
        valid, repaired, errors = validate_schema(raw)
        self.assertFalse(valid)
        self.assertTrue(any("Invalid severity: CRITICAL" in e for e in errors))

    def test_entities_non_string(self):
        raw = '{"incident_id": "1", "event_type": "a", "severity": "LOW", "entities": ["x", 17], "occurred_utc": "2026-07-20T17:50:27Z", "summary": "test"}'
        valid, repaired, errors = validate_schema(raw)
        self.assertFalse(valid)
        self.assertTrue(any("Entity at index 1 is not a string" in e for e in errors))

    def test_valid_utc_timestamp(self):
        raw = '{"incident_id": "1", "event_type": "a", "severity": "LOW", "entities": ["x"], "occurred_utc": "2026-07-20T17:50:27.123456Z", "summary": "test"}'
        valid, repaired, errors = validate_schema(raw)
        self.assertTrue(valid)

    def test_invalid_timestamp(self):
        raw = '{"incident_id": "1", "event_type": "a", "severity": "LOW", "entities": ["x"], "occurred_utc": "yesterday", "summary": "test"}'
        valid, repaired, errors = validate_schema(raw)
        self.assertFalse(valid)
        self.assertTrue(any("Invalid ISO-8601 UTC timestamp: yesterday" in e for e in errors))

    def test_null_timestamp(self):
        raw = '{"incident_id": "1", "event_type": "a", "severity": "LOW", "entities": ["x"], "occurred_utc": null, "summary": "test"}'
        valid, repaired, errors = validate_schema(raw)
        self.assertTrue(valid)

if __name__ == '__main__':
    unittest.main()
