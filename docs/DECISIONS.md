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

## PII Handled at dlt Ingestion (Allowlist + Pseudonymization)

**Decision:** Every Airtable field is classified per table in `dlt/airtable_pipeline/airtable_tables.json`:

- `allow`: passed through unchanged
- `pseudonymize`: replaced in memory before the record is written
  - `hash`: keyed HMAC-SHA256 of the lower-cased, trimmed value, stored as `<field>_hash` (e.g. `email` → `email_hash`)
  - `first_name` / `last_name` / `full_name`: a stable word-based fake name (e.g. "Brave Otter")
- anything not listed: dropped (names of dropped fields are logged, never values)

Raw PII never reaches DuckDB, dlt's local state, or the dbt docs site.

**Why:**
- *Allowlist, not blocklist:* a new sensitive field added in Airtable stays out until someone classifies it.
- *At dlt, not dbt staging:* staging models are views over `raw_airtable`, so masking in dbt would leave raw PII in the DuckDB file. A key in model SQL would also be rendered into `dbt/target/`, which CI publishes to GitHub Pages.
- *Keyed hash, not plain SHA-256:* emails are guessable, so anyone with a list of addresses could hash them and match. Without `PII_HASH_KEY` they can't.
- *Email hash as the join key:* `fct_attendance` matches check-ins to volunteers on `email_hash`, read from `stg_volunteers` so the hash never enters the marts.

**Trade-offs:**
- Fake names can collide (two people can both be "Brave Otter"). They are for readability only; join on record IDs or `email_hash`.
- Pseudonymized data is still personal data: a hash plus state, employment status and join date can point to one person. The DuckDB file stays private; public reporting stays aggregate-only.
- Changing `PII_HASH_KEY` changes every hash and fake name, so it requires a full reload.
- The pipeline fails if `PII_HASH_KEY` is unset rather than loading unmasked data.

**Field classification** (from the fields the staging models read; unlisted fields are dropped):

| Table | Pseudonymized | Dropped (examples) |
|-------|---------------|--------------------|
| Volunteers | `email` (hash), `first_name`, `last_name` (fake) | pronouns, age_range, race, city, accommodations, linkedin, github, website_portfolio, slack_handle, Profile Update Link, other_notes, prior_volunteer_experience, project_interests, vetting fields |
| Event attendance | `Email` (hash), `Name` (fake) | notes |
| Events | — | created_by_email, created_by_name, check_in_url, qr_code |
| Project volunteers | — | notes, decline_reason (may be free text) |
| Projects | — | — |

To add a field: list it under `allow` (or `pseudonymize`) in `airtable_tables.json`, then extract it in the staging model. `python dlt/airtable_pipeline/list_tables.py` prints every field per table.

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
| PII Filtering | ✅ dlt-level allowlist + pseudonymization | Aggregate-only public reporting |
| Multi-Select Parsing | Deferred (raw in staging) | Normalized tables |
| Incremental Loads | Full refresh | Optimized incremental |
| Public Reporting | Not yet | Evidence site (PII-filtered) |
| Metrics | Not in scope | volunteer_participation_summary, retention, etc. |

---

## References

- See `PHASE2_MASTER.md` for full implementation guide
- See `HANDOFF.md` for operational runbook
- See phase-2-plan.md for original spec
