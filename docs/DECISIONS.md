# Phase 2 Design Decisions

## event_id = 0 for Monthly Meetings

**Decision:** All monthly meetings share a synthetic pseudo-event with event_id = 0 rather than individual event rows.

**Why:** Meetings are recurring all-hands with the same organizers and agenda; the actual attendance date varies per attendance. Storing a single pseudo-event reduces duplication and simplifies the fact table.

**Trade-off:** Every fct_attendance row for a monthly meeting must have occasion_date populated (hard not_null test). The check-in form must always capture the date for monthly meetings to work.

**Implementation:**
- `dim_event` includes a synthetic row 0 (event_id=0, name='Monthly meetings', event_type='Monthly meeting')
- `fct_attendance.event_id = 0` indicates a monthly meeting
- `fct_attendance.occasion_date` comes from the attendance row, not the event row (since all monthly meetings share the same pseudo-event)

---

## Array Expansion in Marts, Not Staging

**Decision:** Linked record fields (volunteer_id, project_id) are stored as arrays in staging json_blob. Extraction to [0] index happens in `fct_project_volunteer` SQL, not in staging.

**Why:** Staging is 1:1 with Airtable (raw extraction only). Marts handle business logic and interpretation. This keeps the separation of concerns clean.

**Trade-off:** `fct_project_volunteer` SQL is more complex (json extraction + type casting). However, this preserves raw data and allows future phases to access the full arrays if needed.

**Implementation:**
- `stg_project_volunteers` stores the full json_blob with arrays intact
- `fct_project_volunteer` extracts `volunteer_id[0]` and `project_id[0]` using json_extract_string

---

## PII Excluded at Mart SELECT, Not dlt

**Decision:** Volunteer PII (names, emails, demographics) is extracted in `stg_volunteers` but excluded from `dim_volunteer` SELECT clause.

**Why:** The project is in development. Focusing Phase 2 on correct dims/facts without adding dlt-level filtering complexity. Phase 3 will harden PII handling before public launch.

**Trade-off:** Staging tables hold PII; the DuckDB file must remain private until Phase 3. Documented in project README and operational runbook.

**Implementation:**
- `stg_volunteers` has all Airtable fields (including first_name, last_name, email, pronouns, age_range, etc.)
- `dim_volunteer` SELECT excludes these fields and includes only: id, status, joined_date, employment_status, hours_per_month, state, timezone, board_leadership_experience, grant_writing_experience, timestamps
- Phase 3 task: add dlt-level exclusion via environment variable (INCLUDE_PII)

---

## Deferred Multi-Select Parsing (Phase 3)

**Decision:** Fields like availability[], language_fluency[], nonprofit_skills[], tech_skills[], skills_to_develop[], roles_interested_in[] are extracted in `stg_volunteers` but not normalized (stored as raw json).

**Why:** Phase 2 focuses on core dims/facts for reporting structure. Phase 3 will parse these multi-select arrays into normalized tables for metrics and reporting.

**Trade-off:** Deferred fields available in staging for urgent queries, but not in marts. Adds Phase 3 work to complete the schema.

**Implementation:**
- `stg_volunteers` contains json_extract of these fields as-is (arrays or json objects)
- `dim_volunteer` does not include these columns
- Phase 3 task: create normalized tables (e.g., `volunteer_skills`, `volunteer_availability`) and populate from staging

---

## Relationship Test for Orphaned Attendance

**Decision:** `fct_attendance.volunteer_id` has a hard `relationships` test (severity: error). Warn tests catch orphaned rows separately.

**Why:** Foreign key integrity is critical for fact table joins. However, data-entry errors (missing volunteer link) shouldn't break the nightly build; they should be visible.

**Trade-off:** The `relationships` test will fail if orphaned attendance exists. A separate singular `warn_orphaned_attendance` test reports count without blocking.

**Implementation:**
- `fct_attendance.volunteer_id` includes `relationships` test (error by default)
- Separate singular test `warn_orphaned_attendance.sql` counts and warns
- If nightly build fails on relationships, check Airtable for unlinked attendance records and fix the source data

---

## Deferred: Incremental Loading

**Decision:** Phase 2 does full refreshes. Incremental dbt runs deferred to Phase 3.

**Why:** The project has small data volumes. Full refreshes are fast and guarantee correctness. Incremental logic adds complexity without current benefit.

**Trade-off:** Pipeline runs full `dbt build` each nightly. Phase 3 can optimize with incremental strategies once data volume warrants it.

---

## Freshness Check

**Decision:** A source freshness check warns if dlt load timestamp is > 36 hours old.

**Why:** Monitors that the Airtable ingestion is running. Non-blocking (severity: warn) to avoid false outages.

**Implementation:**
- `sources.yml` includes `loaded_at_field: last_modified` (or appropriate dlt timestamp column)
- Configured with `warn_after: {count: 36, period: hour}`

---

## Documentation Audience

**Decision:** dbt docs are generated in CI and deployed to GitHub Pages (or equivalent). Audience is internal (project team).

**Why:** Enables stakeholders to understand schema, lineage, and column definitions without touching SQL. Public Evidence reporting is Phase 3+ (with PII filtering).

**Implementation:**
- `.github/workflows/dbt.yml` includes `dbt docs generate` step
- Docs deployed to GitHub Pages on main branch
- Link in README: `[dbt Docs](#)` → team can browse lineage and column metadata

---

## Summary of Phase 2 vs. Phase 3

| Aspect | Phase 2 | Phase 3+ |
|--------|---------|----------|
| Dims/Facts | ✅ Built | — |
| PII Filtering | Mart-level (not dlt) | dlt-level filtering |
| Multi-Select Parsing | Deferred (raw in staging) | Normalized tables |
| Incremental Loads | Full refresh | Optimized incremental |
| Public Reporting | Not yet | Evidence site (PII-filtered) |
| Metrics | Not in scope | volunteer_participation_summary, retention, etc. |

---

## References

- See `PHASE2_MASTER.md` for full implementation guide
- See `HANDOFF.md` for operational runbook
- See phase-2-plan.md for original spec
