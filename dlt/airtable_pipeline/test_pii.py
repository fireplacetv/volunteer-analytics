import os
import unittest
from unittest import mock

from pii import (
    ADJECTIVES,
    ANIMALS,
    filter_fields,
    get_pii_key,
    hash_value,
    validate_table_config,
)

KEY = b"test-key"

VOLUNTEERS = {
    "id": "tblVolunteers",
    "allow": ["status", "Last Modified"],
    "pseudonymize": {"email": "hash", "first_name": "first_name", "last_name": "last_name"},
    "unused": {"city": "PII"},
}

ATTENDANCE = {
    "id": "tblAttendance",
    "allow": ["event_id"],
    "pseudonymize": {"Email": "hash", "Name": "full_name"},
}


class FilterFieldsTest(unittest.TestCase):
    def test_allowed_fields_pass_through_and_unclassified_are_dropped(self):
        fields = {"status": "Active", "pronouns": "they/them", "accommodations": "x"}
        out, dropped = filter_fields("rec1", fields, VOLUNTEERS, KEY)
        self.assertEqual(out, {"status": "Active"})
        self.assertEqual(dropped, {"pronouns", "accommodations"})

    def test_unused_fields_are_dropped_but_not_reported(self):
        out, dropped = filter_fields("rec1", {"status": "Active", "city": "Oakland"}, VOLUNTEERS, KEY)
        self.assertEqual(out, {"status": "Active"})
        self.assertEqual(dropped, set())

    def test_raw_pii_values_never_appear_in_output(self):
        fields = {"email": "Jo@Example.org", "first_name": "Jo", "last_name": "Smith"}
        out, _ = filter_fields("rec1", fields, VOLUNTEERS, KEY)
        self.assertNotIn("email", out)
        for value in out.values():
            self.assertNotIn("jo", value.lower().split())
            self.assertNotIn("example", value.lower())
            self.assertNotEqual(value, "Smith")

    def test_email_hash_is_normalized_and_matches_across_tables(self):
        vol, _ = filter_fields("rec1", {"email": "Jo@Example.org"}, VOLUNTEERS, KEY)
        att, _ = filter_fields("rec2", {"Email": " jo@example.ORG "}, ATTENDANCE, KEY)
        self.assertEqual(vol["email_hash"], att["email_hash"])

    def test_same_person_gets_same_fake_name_in_both_tables(self):
        vol, _ = filter_fields(
            "rec1", {"email": "jo@example.org", "first_name": "Jo", "last_name": "Smith"}, VOLUNTEERS, KEY
        )
        att, _ = filter_fields("rec2", {"Email": "JO@example.org", "Name": "Jo Smith"}, ATTENDANCE, KEY)
        self.assertEqual(att["Name"], f"{vol['first_name']} {vol['last_name']}")

    def test_hash_depends_on_key(self):
        self.assertNotEqual(hash_value("jo@example.org", b"a"), hash_value("jo@example.org", b"b"))

    def test_fake_name_without_email_is_stable_per_record(self):
        first, _ = filter_fields("rec1", {"Name": "Jo Smith"}, ATTENDANCE, KEY)
        again, _ = filter_fields("rec1", {"Name": "Jo Smith"}, ATTENDANCE, KEY)
        self.assertEqual(first["Name"], again["Name"])
        self.assertNotEqual(first["Name"], "Jo Smith")

    def test_empty_pii_fields_are_omitted(self):
        out, _ = filter_fields("rec1", {"status": "Active"}, VOLUNTEERS, KEY)
        self.assertEqual(out, {"status": "Active"})


class ConfigTest(unittest.TestCase):
    def test_missing_key_fails(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                get_pii_key()

    def test_field_cannot_be_both_allowed_and_pseudonymized(self):
        with self.assertRaises(ValueError):
            validate_table_config("T", {"id": "t", "allow": ["email"], "pseudonymize": {"email": "hash"}})

    def test_field_cannot_be_both_allowed_and_unused(self):
        with self.assertRaises(ValueError):
            validate_table_config("T", {"id": "t", "allow": ["city"], "unused": {"city": "PII"}})

    def test_wordlists_are_large_and_unique(self):
        for words in (ADJECTIVES, ANIMALS):
            self.assertGreaterEqual(len(words), 250)
            self.assertEqual(len(words), len(set(words)))

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            validate_table_config("T", {"id": "t", "allow": [], "pseudonymize": {"email": "sha1"}})

    def test_repo_config_is_valid(self):
        import json

        path = os.path.join(os.path.dirname(__file__), "airtable_tables.json")
        with open(path) as f:
            tables = json.load(f)["tables"]
        for name, config in tables.items():
            validate_table_config(name, config)


if __name__ == "__main__":
    unittest.main()
