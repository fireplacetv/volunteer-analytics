"""
Pipeline tests against a fake Airtable API.

Runs against a temporary DuckDB file, and also against Postgres when
TEST_POSTGRES_CREDENTIALS is set, e.g.
    TEST_POSTGRES_CREDENTIALS=postgresql://postgres:postgres@localhost:5432/dlt_test
Each Postgres test uses its own dataset and drops it afterwards.
"""

import json
import os
import re
import shutil
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest import mock

import dlt
from dlt.destinations.exceptions import DatabaseTerminalException

import source
from cursors import format_cursor, get_cursors
from run import build_pipeline, load
from source import build_params

KEY = b"test-key"

TABLES = {
    "Volunteers": {
        "id": "tblVolunteers",
        "allow": ["status", "Last Modified"],
        "pseudonymize": {"email": "hash"},
        "unused": {},
    },
    "Event attendance": {
        "id": "tblAttendance",
        "allow": ["event_id", "Last Modified"],
        "pseudonymize": {},
        "unused": {},
    },
}

FILTER = re.compile(r"^\{Last Modified\} > '(.+)'$")


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class FakeAirtable:
    """Serves records per table ID, honoring pageSize/offset and the Last Modified filter."""

    def __init__(self):
        self.records = {}
        self.requests = []

    def add(self, table_id, record_id, last_modified, **fields):
        fields["Last Modified"] = last_modified
        self.records.setdefault(table_id, {})[record_id] = {
            "id": record_id,
            "createdTime": "2026-01-01T00:00:00.000Z",
            "fields": fields,
        }

    def get(self, url, headers=None, params=None, timeout=None):
        table_id = url.rsplit("/", 1)[1]
        self.requests.append((table_id, dict(params)))
        records = sorted(self.records.get(table_id, {}).values(), key=lambda r: r["id"])
        formula = params.get("filterByFormula")
        if formula:
            cursor = ts(FILTER.match(formula).group(1))
            records = [r for r in records if ts(r["fields"]["Last Modified"]) > cursor]
        start = int(params.get("offset") or 0)
        page = records[start:start + params["pageSize"]]
        body = {"records": page}
        if start + params["pageSize"] < len(records):
            body["offset"] = str(start + params["pageSize"])
        response = mock.Mock()
        response.json.return_value = body
        return response

    def formulas(self, table_id):
        return [p.get("filterByFormula") for t, p in self.requests if t == table_id]


class BuildParamsTest(unittest.TestCase):
    def test_full_load_has_no_filter(self):
        self.assertEqual(build_params(None, None), {"pageSize": 100})

    def test_incremental_filter_and_offset(self):
        params = build_params("2026-02-01T10:00:00.000Z", "itr1")
        self.assertEqual(params["filterByFormula"], "{Last Modified} > '2026-02-01T10:00:00.000Z'")
        self.assertEqual(params["offset"], "itr1")


class FormatCursorTest(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(format_cursor(None))

    def test_aware_datetime_is_converted_to_utc_and_truncated(self):
        value = datetime(2026, 2, 1, 3, 0, 5, 123000, tzinfo=timezone(timedelta(hours=-7)))
        self.assertEqual(format_cursor(value), "2026-02-01T10:00:05.000Z")

    def test_naive_datetime_is_treated_as_utc(self):
        self.assertEqual(format_cursor(datetime(2026, 2, 1, 10, 0, 5)), "2026-02-01T10:00:05.000Z")

    def test_string(self):
        self.assertEqual(format_cursor("2026-02-01T10:00:05.456Z"), "2026-02-01T10:00:05.000Z")


class PipelineTestMixin:
    """Load scenarios run against whichever destination the subclass provides."""

    def destination(self):
        raise NotImplementedError

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.pipelines_dir = os.path.join(self.workdir, "pipelines")
        self.airtable = FakeAirtable()
        patcher = mock.patch.object(source.requests, "get", side_effect=self.airtable.get)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self.workdir, ignore_errors=True)
        self.pipeline = self.make_pipeline()

    def make_pipeline(self):
        return build_pipeline(self.destination(), self.pipelines_dir)

    def load(self):
        return load(self.pipeline, TABLES, "appTest", "key", KEY)

    def rows(self, table):
        with self.pipeline.sql_client() as client:
            name = client.make_qualified_table_name(table)
            return {r[0]: json.loads(r[1]) for r in client.execute_sql(f"SELECT id, json_blob FROM {name}")}

    def test_fresh_destination_has_no_cursors(self):
        self.assertEqual(get_cursors(self.pipeline, TABLES), {"Volunteers": None, "Event attendance": None})

    def test_incremental_load(self):
        self.airtable.add("tblVolunteers", "rec1", "2026-02-01T10:00:00.000Z", status="Active", email="a@x.org")
        self.airtable.add("tblVolunteers", "rec2", "2026-02-03T09:30:15.250Z", status="Active", email="b@x.org")
        self.load()

        # Nothing loaded for attendance, so its table does not exist yet.
        cursors = get_cursors(self.pipeline, TABLES)
        self.assertEqual(cursors, {"Volunteers": "2026-02-03T09:30:15.000Z", "Event attendance": None})
        self.assertEqual(self.airtable.formulas("tblVolunteers"), [None])

        self.airtable.add("tblVolunteers", "rec2", "2026-02-04T08:00:00.000Z", status="Inactive", email="b@x.org")
        self.airtable.add("tblVolunteers", "rec3", "2026-02-04T09:00:00.000Z", status="Active", email="c@x.org")
        self.airtable.add("tblAttendance", "att1", "2026-02-04T09:00:00.000Z", event_id="evt1")
        self.load()

        self.assertEqual(
            self.airtable.formulas("tblVolunteers")[-1], "{Last Modified} > '2026-02-03T09:30:15.000Z'"
        )
        self.assertIsNone(self.airtable.formulas("tblAttendance")[-1])
        volunteers = self.rows("volunteers")
        self.assertEqual(set(volunteers), {"rec1", "rec2", "rec3"})
        self.assertEqual(volunteers["rec2"]["status"], "Inactive")
        self.assertNotIn("email", volunteers["rec1"])
        self.assertIn("email_hash", volunteers["rec1"])
        self.assertEqual(set(self.rows("event_attendance")), {"att1"})
        self.assertEqual(
            get_cursors(self.pipeline, TABLES),
            {"Volunteers": "2026-02-04T09:00:00.000Z", "Event attendance": "2026-02-04T09:00:00.000Z"},
        )

    def test_cursor_survives_losing_local_state(self):
        self.airtable.add("tblVolunteers", "rec1", "2026-02-01T10:00:00.000Z", status="Active")
        self.load()
        shutil.rmtree(self.pipelines_dir)

        self.pipeline = self.make_pipeline()
        self.assertEqual(get_cursors(self.pipeline, TABLES)["Volunteers"], "2026-02-01T10:00:00.000Z")

    def test_dropped_table_reloads_in_full(self):
        self.airtable.add("tblVolunteers", "rec1", "2026-02-01T10:00:00.000Z", status="Active")
        self.load()
        with self.pipeline.sql_client() as client:
            client.execute_sql(f"DROP TABLE {client.make_qualified_table_name('volunteers')}")

        self.assertIsNone(get_cursors(self.pipeline, TABLES)["Volunteers"])

    def test_other_errors_are_not_swallowed(self):
        self.airtable.add("tblVolunteers", "rec1", "2026-02-01T10:00:00.000Z", status="Active")
        self.load()
        with self.pipeline.sql_client() as client:
            client.execute_sql(
                f"ALTER TABLE {client.make_qualified_table_name('volunteers')} DROP COLUMN last_modified"
            )

        with self.assertRaises(DatabaseTerminalException):
            get_cursors(self.pipeline, TABLES)


class DuckDBPipelineTest(PipelineTestMixin, unittest.TestCase):
    def destination(self):
        return dlt.destinations.duckdb(os.path.join(self.workdir, "test.duckdb"))


@unittest.skipUnless(os.getenv("TEST_POSTGRES_CREDENTIALS"), "TEST_POSTGRES_CREDENTIALS not set")
class PostgresPipelineTest(PipelineTestMixin, unittest.TestCase):
    def destination(self):
        return dlt.destinations.postgres(os.environ["TEST_POSTGRES_CREDENTIALS"])

    def make_pipeline(self):
        # A separate dataset per test, so runs never see each other's tables.
        if not hasattr(self, "dataset_name"):
            self.dataset_name = f"raw_airtable_{uuid.uuid4().hex[:8]}"
            self.addCleanup(self.drop_dataset)
        return dlt.pipeline(
            pipeline_name="openoakland",
            destination=self.destination(),
            dataset_name=self.dataset_name,
            pipelines_dir=self.pipelines_dir,
        )

    def drop_dataset(self):
        with self.pipeline.sql_client() as client:
            if client.has_dataset():
                client.drop_dataset()


if __name__ == "__main__":
    unittest.main()
