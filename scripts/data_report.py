"""Write a short Markdown summary of the dbt output for a human smell test.

Shows that data is landing: row count and latest record per staging model,
plus attendance for the last few months as bars. Data quality is covered by
the dbt tests, so this stays aggregate-only and deliberately small.

Usage: python scripts/data_report.py [output.md]
"""

import datetime
import os
import sys

import duckdb

MARKER = "<!-- data-report -->"

STAGING_MODELS = [
    "stg_volunteers",
    "stg_events",
    "stg_event_attendance",
    "stg_projects",
    "stg_project_volunteers",
]

ATTENDANCE_MONTHS = 3
BAR_WIDTH = 16


def find_relation(con, name):
    """Return the schema-qualified name of a model, whatever schema dbt built it in."""
    row = con.execute(
        "select table_schema from information_schema.tables where table_name = ?", [name]
    ).fetchone()
    return f'"{row[0]}"."{name}"' if row else None


def staging_summary(con):
    rows = []
    for model in STAGING_MODELS:
        relation = find_relation(con, model)
        if relation is None:
            rows.append((model, None, None))
            continue
        count, latest = con.execute(
            f"select count(*), max(created_time)::date from {relation}"
        ).fetchone()
        rows.append((model, count, latest))
    return rows


def recent_months(today, n):
    """First day of each of the last n calendar months, oldest first, ending with today's month."""
    months = []
    year, month = today.year, today.month
    for _ in range(n):
        months.append(datetime.date(year, month, 1))
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return months[::-1]


def attendance_by_month(con, today):
    months = recent_months(today, ATTENDANCE_MONTHS)
    relation = find_relation(con, "fct_attendance")
    if relation is None:
        return None
    counts = dict(
        con.execute(
            f"""
            select date_trunc('month', occasion_date)::date, count(*)
            from {relation}
            where occasion_date >= ?
            group by 1
            """,
            [months[0]],
        ).fetchall()
    )
    return [(m, counts.get(m, 0)) for m in months]


def bar(value, max_value, width=BAR_WIDTH):
    if max_value == 0:
        return ""
    return "█" * round(value / max_value * width)


def days_ago(latest, today):
    if latest is None:
        return "–"
    days = (today - latest).days
    return f"{latest.isoformat()} ({days}d)"


def render(staging, attendance, today, run_url=None):
    missing = [model for model, count, _ in staging if not count]
    status = "⚠️" if missing else "✅"
    headline = f"{status} **Data report** · {len(staging) - len(missing)}/{len(staging)} staging models have rows"
    if run_url:
        headline += f" · [run]({run_url})"

    lines = [MARKER, headline, ""]
    if missing:
        lines += [f"Empty or missing: {', '.join(f'`{m}`' for m in missing)}", ""]

    lines += ["| model | rows | latest record |", "|---|--:|---|"]
    for model, count, latest in staging:
        rows = "missing" if count is None else f"{count:,}"
        lines.append(f"| {model.removeprefix('stg_')} | {rows} | {days_ago(latest, today)} |")

    lines += ["", "**Attendance by month**", ""]
    if attendance is None:
        lines.append("`fct_attendance` not found")
    else:
        top = max(count for _, count in attendance)
        width = len(f"{top:,}")
        lines.append("```")
        for month, count in attendance:
            lines.append(f"{month:%Y-%m} {count:>{width},} {bar(count, top)}")
        lines.append("```")

    return "\n".join(lines) + "\n"


def main():
    output = sys.argv[1] if len(sys.argv) > 1 else "artifacts/data_report.md"
    db_path = os.environ.get("DUCKDB_PATH", "artifacts/openoakland.duckdb")
    today = datetime.date.today()

    con = duckdb.connect(db_path, read_only=True)
    report = render(
        staging_summary(con),
        attendance_by_month(con, today),
        today,
        run_url=os.environ.get("RUN_URL"),
    )
    with open(output, "w") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    main()
