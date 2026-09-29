"""Write a short Markdown summary of the dbt output for a human smell test.

Shows attendance for the last few months as bars. Data quality is covered by
the dbt tests, so this stays aggregate-only and deliberately small.

Usage: python scripts/data_report.py [output.md]
"""

import datetime
import json
import os
import sys

import duckdb

MARKER = "<!-- data-report -->"

MANIFEST_PATH = "dbt/target/manifest.json"

ATTENDANCE_MONTHS = 3
BAR_WIDTH = 16


def staging_models(manifest):
    """Names of the models under models/staging/ in a dbt manifest, sorted."""
    return sorted(
        node["name"]
        for node in manifest["nodes"].values()
        if node["resource_type"] == "model"
        and node["original_file_path"].startswith("models/staging/")
    )


def staging_summary(con, models):
    """Latest record date for each staging model, without row counts."""
    rows = []
    for model in models:
        relation = find_relation(con, model)
        if relation is None:
            rows.append((model, None))
            continue
        latest = con.execute(
            f"select max(created_time)::date from {relation}"
        ).fetchone()[0]
        rows.append((model, latest))
    return rows


def find_relation(con, name):
    """Return the schema-qualified name of a model, whatever schema dbt built it in."""
    row = con.execute(
        "select table_schema from information_schema.tables where table_name = ?", [name]
    ).fetchone()
    return f'"{row[0]}"."{name}"' if row else None




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




def updated_line(now, commit=None, run_url=None):
    """Small print under the headline saying which run and commit the report reflects."""
    parts = [f"Updated {now:%Y-%m-%d %H:%M} UTC"]
    if commit:
        parts[0] += f" for {commit[:7]}"
    if run_url:
        parts.append(f"[run]({run_url})")
    return f"<sub>{' · '.join(parts)}</sub>"


def render(staging, attendance, today, updated=None):
    missing = [model for model, latest in staging if latest is None]
    status = "⚠️" if missing else "✅"
    headline = f"{status} **Data report** · {len(staging) - len(missing)}/{len(staging)} staging models have data"

    lines = [MARKER, headline]
    if updated:
        lines.append(updated)
    lines.append("")
    if missing:
        lines += [f"Empty or missing: {', '.join(f'`{m}`' for m in missing)}", ""]

    lines += ["| model | latest record |", "|---|---|"]
    for model, latest in staging:
        lines.append(f"| {model.removeprefix('stg_')} | {days_ago(latest, today)} |")

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

    with open(os.environ.get("DBT_MANIFEST", MANIFEST_PATH)) as f:
        models = staging_models(json.load(f))

    con = duckdb.connect(db_path, read_only=True)
    report = render(
        staging_summary(con, models),
        attendance_by_month(con, today),
        today,
        updated=updated_line(
            datetime.datetime.now(datetime.timezone.utc),
            commit=os.environ.get("COMMIT_SHA"),
            run_url=os.environ.get("RUN_URL"),
        ),
    )
    with open(output, "w") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    main()
