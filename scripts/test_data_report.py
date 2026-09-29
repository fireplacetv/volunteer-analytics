import datetime
import unittest

import duckdb

from data_report import (
    MARKER,
    attendance_by_month,
    recent_months,
    render,
    staging_models,
    staging_summary,
    updated_line,
)

TODAY = datetime.date(2026, 3, 15)

MODELS = [
    "stg_event_attendance",
    "stg_events",
    "stg_project_volunteers",
    "stg_projects",
    "stg_volunteers",
]


def make_db():
    con = duckdb.connect()
    con.execute("create schema stg")
    con.execute("create schema marts")
    con.execute("create table stg.stg_volunteers (id varchar, created_time timestamptz)")
    con.execute(
        "insert into stg.stg_volunteers values "
        "('a', '2026-03-01 10:00:00+00'), ('b', '2026-03-13 10:00:00+00')"
    )
    for model in ["stg_events", "stg_event_attendance", "stg_projects"]:
        con.execute(f"create table stg.{model} (id varchar, created_time timestamptz)")
        con.execute(f"insert into stg.{model} values ('x', '2026-01-02 00:00:00+00')")
    # stg_project_volunteers deliberately missing
    con.execute("create table marts.fct_attendance (attendance_id varchar, occasion_date date)")
    con.execute(
        "insert into marts.fct_attendance values "
        "('1', '2025-12-31'), ('2', '2026-01-05'), ('3', '2026-01-20'), ('4', '2026-03-02')"
    )
    return con


class DataReportTest(unittest.TestCase):
    def setUp(self):
        self.con = make_db()

    def test_staging_summary_finds_latest_record_without_row_counts(self):
        rows = {model: latest for model, latest in staging_summary(self.con, MODELS)}
        self.assertEqual(rows["stg_volunteers"], datetime.date(2026, 3, 13))
        self.assertEqual(rows["stg_project_volunteers"], None)

    def test_staging_models_come_from_the_staging_folder_of_the_manifest(self):
        manifest = {
            "nodes": {
                "model.p.stg_b": {"resource_type": "model", "name": "stg_b", "original_file_path": "models/staging/stg_b.sql"},
                "model.p.stg_a": {"resource_type": "model", "name": "stg_a", "original_file_path": "models/staging/stg_a.sql"},
                "model.p.dim_x": {"resource_type": "model", "name": "dim_x", "original_file_path": "models/marts/dim_x.sql"},
                "test.p.not_null": {"resource_type": "test", "name": "not_null", "original_file_path": "models/staging/models.yml"},
            }
        }
        self.assertEqual(staging_models(manifest), ["stg_a", "stg_b"])

    def test_recent_months_crosses_year_boundary(self):
        self.assertEqual(
            recent_months(datetime.date(2026, 2, 10), 3),
            [datetime.date(2025, 12, 1), datetime.date(2026, 1, 1), datetime.date(2026, 2, 1)],
        )

    def test_attendance_by_month_includes_empty_months(self):
        self.assertEqual(
            attendance_by_month(self.con, TODAY),
            [
                (datetime.date(2026, 1, 1), 2),
                (datetime.date(2026, 2, 1), 0),
                (datetime.date(2026, 3, 1), 1),
            ],
        )

    def test_render_shows_staging_and_attendance(self):
        report = render(staging_summary(self.con, MODELS), attendance_by_month(self.con, TODAY), TODAY)
        self.assertTrue(report.startswith(MARKER))
        self.assertIn("⚠️", report)
        self.assertIn("`stg_project_volunteers`", report)
        self.assertIn("| volunteers | 2026-03-13 (2d) |", report)
        # Check for attendance with bars but no count values
        self.assertIn("2026-01", report)  # Month shown
        self.assertNotIn("2026-01  ", report)  # But no padding for count alignment
        self.assertNotIn("rows", report.lower())  # No row count reporting

    def test_updated_line_shows_time_commit_and_run(self):
        now = datetime.datetime(2026, 3, 15, 9, 5, tzinfo=datetime.timezone.utc)
        self.assertEqual(
            updated_line(now, commit="1e6d02f19625fad4", run_url="https://example/run"),
            "<sub>Updated 2026-03-15 09:05 UTC for 1e6d02f · [run](https://example/run)</sub>",
        )
        self.assertEqual(updated_line(now), "<sub>Updated 2026-03-15 09:05 UTC</sub>")

    def test_render_puts_updated_line_under_headline(self):
        report = render(staging_summary(self.con, MODELS), None, TODAY, updated="<sub>Updated x</sub>")
        self.assertEqual(report.splitlines()[2], "<sub>Updated x</sub>")


if __name__ == "__main__":
    unittest.main()
