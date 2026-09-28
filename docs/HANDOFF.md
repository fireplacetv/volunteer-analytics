# Operational Runbook: Phase 2 Marts

This document guides day-to-day operation of the volunteer analytics pipeline after Phase 2 implementation.

## Quick Start

**To run the pipeline (nightly or manual):**

```bash
docker compose build
docker compose run --rm dev bash -c "python dlt/airtable_pipeline/airtable_source.py && cd dbt && dbt deps && dbt run && dbt test"
```

**To view schema and lineage:**

```bash
cd dbt && dbt docs generate && open target/index.html
```

---

## What's in Phase 2

### Five Mart Models

1. **dim_volunteer** — Volunteer dimension. One row per volunteer. Key: `volunteer_id` (Airtable record ID).
   - 10 columns: status, joined_date, employment_status, hours_per_month, state, timezone, board/grant experience, timestamps
   - Excludes: names, emails, demographics (PII deferred to Phase 3)

2. **dim_project** — Project dimension. One row per project. Key: `project_id` (Airtable auto-ID, human-readable).
   - 11 columns: name, status, stakeholder, description, dates, timestamps
   - Includes `airtable_record_id` for tracing back

3. **dim_event** — Event dimension. One row per event, plus synthetic row 0 for monthly meetings.
   - Key: `event_id` (Airtable auto-ID; 0 = monthly meetings)
   - Synthetic row 0: event_id=0, event_name='Monthly meetings', event_type='Monthly meeting'

4. **fct_attendance** — Attendance fact table. One row per Event attendance record.
   - Key: `attendance_id` (Airtable record ID)
   - Foreign keys: volunteer_id → dim_volunteer, event_id → dim_event
   - **Monthly meeting date logic:** For event_id=0, occasion_date comes from attendance.date (not event.event_date)

5. **fct_project_volunteer** — Project-volunteer junction fact. One row per Project volunteers record.
   - Key: `join_id` (Airtable record ID)
   - Foreign keys: volunteer_id → dim_volunteer, project_id → dim_project
   - Arrays expanded from json_blob: volunteer_id[0], project_id[0]
   - Outreach tracking: count and latest date/status derived from outreach_N_date/status

### Tests

**Generic tests** (in `dbt/models/*/models.yml`):
- `not_null` and `unique` on all primary keys
- `relationships`: both facts link to dims; orphaned rows fail (error) or warn separately
- `accepted_values` on all status fields (severity: warn)

**Singular tests** (in `dbt/tests/`):
- `no_duplicate_attendance.sql` — Fails if same (volunteer, event, date) appears 2+ times in fct_attendance
- `warn_duplicate_check_ins.sql` — Warns if Airtable has repeat check-ins (same event, date, email); stg_event_attendance collapses these, keeping the earliest
- `no_future_attendance.sql` — Fails if any attendance_date > today
- `warn_orphaned_attendance.sql` — Warns if any fct_attendance.volunteer_id is null
- `warn_orphaned_project_volunteer.sql` — Warns if any fct_project_volunteer links are null

**Source freshness** (dlt load timestamp):
- Warns if > 36 hours since last successful load

---

## If Tests Fail

### `relationships` Test Fails (fct_attendance.volunteer_id or fct_project_volunteer links)

**Symptom:** "Relationship test failed: orphaned attendance/project volunteer records."

**Root cause:** Airtable has attendance/project-volunteer rows without a linked volunteer or project.

**Fix:**
1. Open Airtable (Events > Event attendance or Projects > Project volunteers)
2. Find rows with empty volunteer_id or project_id link
3. Either link the record to the correct volunteer/project, or delete the orphaned row
4. Re-run: `dbt test -s fct_attendance` or `dbt test -s fct_project_volunteer`

---

### `warn_duplicate_check_ins` Test Warns

**Symptom:** Repeat check-ins (same event, date and email) found in Airtable.

**Root cause:** Someone checked in more than once (e.g., scanned twice). `stg_event_attendance` already keeps only the earliest check-in, so marts are unaffected; this is a non-blocking prompt to clean up the source.

**Fix (optional):** Delete the extra records in the Airtable Event attendance table.

---

### `no_duplicate_attendance` Test Fails

**Symptom:** "Duplicate check-in detected for volunteer X at event Y on date Z."

**Root cause:** A repeat check-in that `stg_event_attendance` can't collapse: one record has a Date and the other doesn't (the mart fills a missing date from the event's date).

**Fix:**
1. Open Airtable Event attendance table
2. Sort/filter by email and date to find duplicates
3. Delete or merge the duplicate record
4. Re-run: `dbt test -s no_duplicate_attendance`

---

### `no_future_attendance` Test Fails

**Symptom:** "Future dates in attendance records."

**Root cause:** Data entry error (wrong date in check-in form or Airtable).

**Fix:**
1. Open Airtable Event attendance table
2. Filter/sort by date, identify records > today
3. Correct the date
4. Re-run: `dbt test -s no_future_attendance`

---

### `warn_orphaned_attendance` Test Warns

**Symptom:** "Orphaned attendance found: X records have no volunteer_id."

**Root cause:** Attendance records in Airtable with empty volunteer_id link (non-blocking warning).

**Action:** Decide whether to:
- Link the record to the correct volunteer (if identified)
- Delete the record (if data entry error)
- Leave as-is (if intentional, e.g., public event with anonymous attendance)

**Note:** This is a warning (severity: warn), so nightly build completes. Check logs to investigate.

---

### `accepted_values` Test Warns (Status Fields)

**Symptom:** "Unexpected status value: 'NEW_STATUS'."

**Root cause:** Airtable schema has a new status option not in the expected list.

**Action:**
1. Check Airtable field definition for the new status value
2. Update the `accepted_values` test in dbt/models/marts/models.yml
3. Re-run: `dbt test`
4. (Optional) Update DECISIONS.md to document the new status

---

## Schema Dependencies

If Airtable field names change, update `dbt/models/staging/stg_*.sql` extractions:

| Staging Model | Airtable Table | Critical Fields |
|---------------|----------------|-----------------|
| stg_volunteers | Volunteers | status, joined_date, employment_status, hours_per_month, state, timezone, board_leadership_experience, grant_writing_experience |
| stg_projects | Projects | project_id (auto-ID), name, status, stakeholder, description, start_date, end_date |
| stg_events | Events | event_id (auto-ID), name, type (or event_type field), event_date, description |
| stg_event_attendance | Event attendance | attendance_id, event_id (link), volunteer_id (link), date, status |
| stg_project_volunteers | Project volunteers | volunteer_id (link array), project_id (link array), role, commitment_date, end_date, status, outreach_N_date, declined |

**If a field name changes:**
1. Update the json_extract_string or try_cast in stg_*.sql
2. Re-run: `dbt run`
3. Re-run tests to verify

---

## Monitoring

**Nightly Build (CI):**
- Runs via `.github/workflows/dbt.yml`
- Steps: dlt ingestion → dbt run → dbt test → dbt docs generate
- On failure: GitHub Actions notification (check logs)
- On success: dbt docs site updated

**Source Freshness:**
- Monitored by dbt source freshness test (warns if > 36 hours old)
- Check in dbt logs: "Freshness threshold: ..."

**Manual Run:**
- Use docker compose (see Quick Start section above)
- Or run locally with: `cd dbt && dbt deps && dbt run && dbt test`

---

## Second Person Onboarding

### Step 1: Understand the Project

1. Read `docs/SETUP.md` — Project setup and environment
2. Read `docs/roadmap/phase-2-plan.md` — Original Phase 2 spec
3. Read `docs/roadmap/PHASE2_MASTER.md` — Consolidated Phase 2 plan
4. Read `docs/DECISIONS.md` — Design rationale (this helps with edge cases)

### Step 2: Understand the Data

1. Run `docker compose up` to start local DuckDB
2. Open Airtable and explore the 5 tables: Volunteers, Projects, Events, Event attendance, Project volunteers
3. Note field types and values (status options, date formats, etc.)
4. Trace a few example records through the pipeline

### Step 3: Understand the Code

1. Review `dbt/models/staging/stg_*.sql` — Understand field extraction
2. Review `dbt/models/marts/dim_*.sql` and `fct_*.sql` — Understand transformations
3. Run `dbt docs generate && open target/index.html` to view lineage and column metadata
4. Walk through one full record from Airtable → staging → mart (e.g., a volunteer and their attendance)

### Step 4: Run the Pipeline

1. Run the full pipeline: `docker compose run --rm dev bash -c "python dlt/airtable_pipeline/airtable_source.py && cd dbt && dbt deps && dbt run && dbt test"`
2. Check that all models build and tests pass
3. Review logs for warnings (especially orphaned_attendance or new status values)

### Step 5: Query the Marts

1. Open DuckDB: `duckdb duckdb.db` (or open from `.duckdb` file in project)
2. Query some basic facts:
   - `SELECT COUNT(*) FROM dim_volunteer WHERE status = 'Active';`
   - `SELECT volunteer_id, COUNT(*) as attendance_count FROM fct_attendance GROUP BY 1 ORDER BY 2 DESC LIMIT 5;`
3. Spot-check against Airtable to verify accuracy

---

## Troubleshooting

### Issue: "File not found: duckdb.db"

**Cause:** DuckDB doesn't exist yet or dlt hasn't run.

**Fix:** Run dlt ingestion first:
```bash
docker compose run --rm dev python dlt/airtable_pipeline/airtable_source.py
```

### Issue: "Model not found: ref('stg_volunteers')"

**Cause:** Staging model doesn't exist or hasn't been run.

**Fix:** Run `dbt run -s staging` to build staging models first.

### Issue: "Column not found: volunteer_id in json_blob"

**Cause:** Airtable field name has changed or json path is wrong.

**Fix:** Check Airtable field name, update json_extract_string in stg_*.sql, re-run dbt run.

### Issue: dbt docs not generating

**Cause:** Missing dependencies or dbt error.

**Fix:**
```bash
cd dbt && dbt parse && dbt docs generate
```

Check dbt logs for specific errors.

---

## Future Work (Phase 3+)

- **PII Filtering:** Implement dlt-level exclusion of sensitive fields before data lands in DuckDB
- **Multi-Select Parsing:** Normalize skills, availability, language_fluency into separate tables
- **Metrics:** Build `volunteer_participation_summary`, retention models, demographic reporting
- **Incremental Loads:** Optimize dbt runs with incremental strategies
- **Public Reporting:** Deploy Evidence reporting site with PII-filtered data

---

## References

- **Local Airtable base:** [Link to Airtable](https://airtable.com/app/...) (shared with team)
- **CI Workflow:** `.github/workflows/dbt.yml`
- **dbt Docs:** [Generated site](#) (deployed to GitHub Pages after nightly run)
- **dbt Cloud:** Not in use; running locally via docker compose and CI

---

**Questions?** Check DECISIONS.md for design rationale. If still unclear, reach out to the project lead or review phase-2-plan.md.
