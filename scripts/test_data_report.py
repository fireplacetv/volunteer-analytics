import datetime
import unittest

import duckdb

from data_report import MARKER, attendance_by_month, recent_months, render, staging_summary

TODAY = datetime.date(2026, 3, 15)


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

    def test_staging_summary_counts_rows_and_finds_latest_record(self):
        rows = {model: (count, latest) for model, count, latest in staging_summary(self.con)}
        self.assertEqual(rows["stg_volunteers"], (2, datetime.date(2026, 3, 13)))
        self.assertEqual(rows["stg_project_volunteers"], (None, None))

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

    def test_render_flags_missing_models(self):
        report = render(staging_summary(self.con), attendance_by_month(self.con, TODAY), TODAY)
        self.assertTrue(report.startswith(MARKER))
        self.assertIn("⚠️", report)
        self.assertIn("`stg_project_volunteers`", report)
        self.assertIn("| volunteers | 2 | 2026-03-13 (2d) |", report)
        self.assertIn("2026-01 2 ████████████████", report)


if __name__ == "__main__":
    unittest.main()
