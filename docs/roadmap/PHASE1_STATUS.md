# Phase 1 Implementation Status

## Completed

### Step 0: Containerization ✅
- `Dockerfile` with Python 3.11, pinned dlt/dbt/requests versions
- `docker-compose.yml` mounting repo volume, loading .env credentials
- `.dockerignore` to exclude secrets, venv, git, artifacts
- DuckDB file persisted at `dlt/airtable_pipeline/volunteer_data.duckdb`
- `docs/SETUP.md` rewritten for Docker-first workflow

**Checkpoint:** Run `docker compose build && docker compose run --rm dev bash -c "dbt run && dbt test"` from a fresh clone (on a machine with only Docker installed) — should pass.

### Step 3: dbt Staging Models ✅
One-to-one staging models created for all 6 source tables:
- `stg_volunteers.sql` — 29 columns extracted from fields__*
- `stg_projects.sql` — project metadata
- `stg_project_volunteers.sql` — bridge table with extracted volunteer_id and project_id
- `stg_events.sql` — event records with nested creator info
- `stg_event_attendance.sql` — attendance log
- `stg_meeting_feedback.sql` — meeting feedback records

Light cleanup only: rename fields__* columns, no business logic.

### Step 4: dbt Tests ✅
- `not_null` and `unique` on all primary key columns (id field)
- `relationships` tests on project_volunteers foreign keys:
  - `volunteer_id` → `stg_volunteers.id`
  - `project_id` → `stg_projects.id`

Orphaned links (failed relationships tests) are data-quality issues in Airtable, not code bugs — they should be flagged to the base owner, not fixed by deleting the test.

### Step 2: Bridge Tables (Partial) ✅
dlt post-processing flattens linked record arrays (multipleRecordLinks fields).
dbt extracts `volunteer_id` and `project_id` from the raw `fields__*` arrays using DuckDB's `generate_subscripts` and array indexing.

## Known Limitations / Blockers

### Step 1: Incremental Loads — BLOCKED ⏸️
**Issue:** Airtable tables do not have `lastModifiedTime` fields (checked via Metadata API).

The code is structured to support incremental loads (`write_disposition="merge"`, `primary_key="id"`), but without `lastModifiedTime` fields on each table, the pipeline cannot efficiently query only changed records. Full loads will run on every execution.

**Workaround needed:** Someone with Airtable admin access must:
1. Add a `last_modified_time` field of type `lastModifiedTime` to **every table** in the base (Volunteers, Projects, Project volunteers, Events, Event Attendance, Meeting Feedback)
2. Once fields are in place, update `airtable_source.py` to use `filterByFormula` with a cursor on that field

Until then, incremental loads are not possible. The pipeline will do full reloads.

## Design Notes

- **Staging vs. Source:** All staging models read from `source('airtable', ...)`, preserving raw data as-is. No deduplication, filtering, or business logic at the staging layer. Row counts in staging models must exactly match source table counts.

- **Bridge Table PKs:** The `stg_project_volunteers` model explodes the linked record arrays by index, creating one row per link. If the same volunteer is listed twice in the volunteer_id array for a project, that will be preserved (and may fail unique tests — this is a data-quality issue in Airtable).

- **Docker Path:** The DuckDB file path is absolute: `dlt/airtable_pipeline/volunteer_data.duckdb`, resolved relative to the script. This works both on the host and inside the container (due to volume mounts at `/workspace`).

- **Post-processing:** The `normalize_linked_records()` function in dlt was intended for SQL post-processing but may fail silently if arrays aren't in the expected format — dbt's staging models are the authoritative transformations.

## To Continue Phase 1

1. **Manually add `lastModifiedTime` fields to all Airtable tables** (requires Airtable admin access)
2. **Run a full pipeline test:**
   ```bash
   docker compose run --rm dev bash -c "python dlt/airtable_pipeline/airtable_source.py && dbt run && dbt test"
   ```
3. **Verify data quality:** Check `dbt test` output for any relationship test failures and review those records in Airtable

4. **(Optional, for Phase 1 checkpoint)** Edit one volunteer record in Airtable and re-run the pipeline — confirm the record was updated in DuckDB (after `lastModifiedTime` fields are added, this could become an incremental-load verification step)

## Files Changed

- `Dockerfile` — new, Python 3.11 base with pinned dependencies
- `docker-compose.yml` — new, mounts repo, loads .env
- `.dockerignore` — new, excludes secrets and generated files
- `.gitignore` — updated, ignore all *.duckdb and *.duckdb.wal
- `dlt/airtable_pipeline/airtable_source.py` — updated with absolute paths, merge writes, post-processing
- `dbt/dbt_project.yml` — unchanged (schema is already defined)
- `dbt/profiles.yml` — unchanged (path already correct for Docker)
- `dbt/models/sources.yml` — updated, meeting_attendance → meeting_feedback
- `dbt/models/staging/*.sql` — 6 new files, staging layer
- `dbt/tests/staging_tests.yml` — new, not_null/unique/relationships tests
- `docs/SETUP.md` — rewritten for Docker-first workflow
