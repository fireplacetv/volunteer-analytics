# Phase 2 TODO: Marts & Metrics

**Branch:** `phase-2/marts-and-metrics`

**Target:** Build dimensional and fact models from staging, with PII excluded and tests in place.

**Ground truth:** The phase-2-plan.md is correct. Code must be updated to match the plan, not vice versa.

---

## Pre-work: Code Alignment with Plan

### [ ] Task 0.0: Remove Meeting Attendance artifacts (code cleanup)
**Files to modify/delete:**
- `dlt/airtable_pipeline/airtable_tables.json` — remove "Meeting attendance" entry
- `dbt/models/sources.yml` — remove meeting_attendance source table
- `dbt/models/staging/stg_meeting_feedback.sql` — DELETE FILE
- `dbt/models/staging/models.yml` — remove stg_meeting_feedback entry

**Why:** The plan consolidates all attendance into Event attendance (with event_id = 0 for monthly meetings). Meeting Attendance table doesn't exist in the real schema; these are leftovers.

**Verify after:** Ensure dbt run/test still works with 5 source tables (Volunteers, Projects, Project volunteers, Events, Event attendance).

**Estimate:** 0.5h

**Status:** —

---

### [ ] Task 0.1: Implement dlt-level PII filtering
**File:** `dlt/airtable_pipeline/airtable_source.py`

Add field-level exclusion before json_blob serialization:
- **Volunteers:** exclude first_name, last_name, email, pronouns, age_range, city, linkedin, github, website_portfolio, slack_handle, accommodations, other_notes, vetting_status, vesting_notes, internal_admin_notes
- **Event attendance:** exclude Name, Email
- **Project volunteers:** exclude notes

**Design:** Make configurable via `INCLUDE_PII` env var for future admin analysis (separate restricted pipeline if demographic analysis is needed).

**Why:** PII never reaches DuckDB. No accidental exposure risk. Cleaner than mart-layer-only filtering.

**Estimate:** 0.5h

**Status:** —

---

### [ ] Task 0.2: Expand stg_projects.sql
**File:** `dbt/models/staging/stg_projects.sql`

Extract from json_blob:
- `project_number` (integer from `project_id` field)
- `project_name` (from `name`)
- `status` (Intake / Active / Complete / On hold)
- `stakeholder`
- `description`
- `start_date` (cast to date)
- `end_date` (cast to date)

Keep: `id`, `created_time`, `last_modified`

**Why:** Currently only extracts `project_id`; dim_project can't be built.

**Estimate:** 0.5h

**Status:** —

---

### [ ] Task 0.3: Expand stg_event_attendance.sql
**File:** `dbt/models/staging/stg_event_attendance.sql`

Extract:
- `volunteer_id` (from linked record)
- `status` (Attended / RSVP'd / No-show / Absent / Remote)
- `date` (rename to `occasion_date` for clarity, or keep as `date` and rename in mart)

**Remove from staging:**
- `name` (attendee name, not a database key)
- `email` (attendee email, PII)

Keep: `id`, `attendance_id`, `event_id`, `created_time`, `last_modified`

**Why:** fct_attendance needs volunteer FK and status. Staging shouldn't carry attendee PII.

**Estimate:** 0.5h

**Status:** —

---

### [ ] Task 0.4: Confirm Airtable schema for Event attendance
**Manual verification:**

1. In Airtable Event attendance table, confirm:
   - Are there records with `event_id = 0`? (These represent monthly meetings per the plan)
   - What are the actual field names? (Check exact spelling: "event_id", "volunteer_id", "status", "Date", etc.)
   - What are valid status values? (e.g., Attended, RSVP'd, No-show, Absent, Remote)

2. If event_id = 0 doesn't exist, the mart (task 4) will create a synthetic row.

**Outcome:** Confirm field names and values. Update Task 0.3 / Task 4 SQL as needed.

**Estimate:** 0.25h

**Status:** —

---

### [ ] Task 0.5: Update dbt/models/staging/models.yml
**File:** `dbt/models/staging/models.yml`

Rewrite to match actual staging SQL:
- **stg_volunteers:** Document ~30 extracted fields. Mark deferred fields (availability, language_fluency, nonprofit_skills, roles_interested_in, etc.) with a note: "Extracted from Airtable but deferred to Phase 3 for normalization."
- **stg_projects:** Update with newly extracted fields (project_number, project_name, status, stakeholder, description, start_date, end_date)
- **stg_events:** Verify field names and types
- **stg_event_attendance:** Update with volunteer_id, status; remove name, email
- **stg_project_volunteers:** Document that arrays are in json_blob; note that array expansion happens in the mart layer (fct_project_volunteer)
- **Remove:** stg_meeting_feedback section entirely

**Why:** models.yml is the schema reference. Must match actual code.

**Estimate:** 1h

**Status:** —

---

## Mart Models

### [ ] Task 1: Build dim_volunteer
**File:** `dbt/models/marts/dim_volunteer.sql` (new, create file)

Select from stg_volunteers:
```sql
with source as (
    select * from {{ ref('stg_volunteers') }}
)
select
    id as volunteer_id,
    status,
    joined_date,
    employment_status,
    hours_per_month,
    state,
    timezone,
    created_time as airtable_created_at,
    last_modified as airtable_modified_at
from source
```

**Schema note:** Includes only fields from Phase 2 scope. Fields like availability, language_fluency, nonprofit_skills, tech_skills, skills_to_develop, roles_interested_in are extracted in staging but deferred to Phase 3 metrics.

**Tests (schema.yml):**
- `not_null` on volunteer_id
- `unique` on volunteer_id

**Estimate:** 0.5h

**Depends on:** Task 0.1, 0.5

**Status:** —

---

### [ ] Task 2: Build dim_project
**File:** `dbt/models/marts/dim_project.sql` (new, create file)

Select from stg_projects (expanded):
```sql
with source as (
    select * from {{ ref('stg_projects') }}
)
select
    id as airtable_record_id,
    json_extract_string(json_blob, '$.project_id') as project_id,
    project_number,
    project_name,
    status,
    stakeholder,
    description,
    start_date,
    end_date,
    created_time as airtable_created_at,
    last_modified as airtable_modified_at
from source
```

**Key:** `project_id` is the Airtable auto-increment integer (NOT the record id). This is the FK used in fct_project_volunteer.

**Tests (schema.yml):**
- `not_null` on project_id
- `unique` on project_id
- `accepted_values` on status: ['Intake', 'Active', 'Complete', 'On hold'] (warn)

**Estimate:** 0.5h

**Depends on:** Task 0.2, 0.5

**Status:** —

---

### [ ] Task 3: Build dim_event
**File:** `dbt/models/marts/dim_event.sql` (new, create file)

Select from stg_events with synthetic row 0 for monthly meetings:
```sql
with source as (
    select * from {{ ref('stg_events') }}
),
synthetic_monthly as (
    select
        0 as event_id,
        null as airtable_record_id,
        'Monthly meetings' as event_name,
        'Monthly meeting' as event_type,
        null as event_date,
        'Recurring monthly all-hands meeting' as description,
        current_timestamp as airtable_created_at,
        current_timestamp as airtable_modified_at
),
all_events as (
    select
        json_extract_string(json_blob, '$.event_id') as event_id,
        id as airtable_record_id,
        name as event_name,
        event_type,  -- confirm field name from Task 0.4
        event_date,
        description,
        created_time as airtable_created_at,
        last_modified as airtable_modified_at
    from source
    union all
    select * from synthetic_monthly
    where not exists (select 1 from source where json_extract_string(json_blob, '$.event_id') = 0)
)
select
    event_id,
    airtable_record_id,
    event_name,
    event_type,
    event_date,
    description,
    airtable_created_at,
    airtable_modified_at,
    (event_id = 0) as is_monthly_meeting
from all_events
```

**Key:** event_id = 0 is synthetic (represents all monthly meetings). Monthly meetings don't have a specific event_date; the attendance date comes from fct_attendance.occasion_date.

**Tests (schema.yml):**
- `not_null` on event_id
- `unique` on event_id
- `accepted_values` on event_type: (to be confirmed from Airtable in Task 0.4) (warn)

**Estimate:** 0.75h

**Depends on:** Task 0.4, 0.5

**Status:** —

---

### [ ] Task 4: Build fct_attendance
**File:** `dbt/models/marts/fct_attendance.sql` (new, create file)

Join stg_event_attendance + stg_events:
```sql
with attendance as (
    select * from {{ ref('stg_event_attendance') }}
),
events as (
    select * from {{ ref('dim_event') }}
),
joined as (
    select
        a.id as attendance_id,
        a.volunteer_id,
        a.event_id,
        (a.event_id = 0) as is_monthly_meeting,
        e.event_type as occasion_type,
        coalesce(a.date, e.event_date) as occasion_date,
        a.status,
        (a.status in ('Attended', 'Remote')) as is_present,
        a.created_time as airtable_created_at,
        a.last_modified as airtable_modified_at
    from attendance a
    left join events e on a.event_id = e.event_id
)
select * from joined
```

**Monthly meeting date logic:** For event_id = 0 (monthly meetings), the occasion_date comes from attendance.date (not from a specific event date, since all monthly meetings share event_id = 0). The COALESCE handles fallback gracefully.

**Tests (schema.yml):**
- `not_null` on attendance_id, volunteer_id, event_id, occasion_date (hard constraint; every attendance must have a date)
- `unique` on attendance_id
- `relationships` volunteer_id → dim_volunteer.volunteer_id
- `relationships` event_id → dim_event.event_id
- `accepted_values` on status: (to be confirmed from Airtable) (warn)
- **Singular test:** `tests/no_duplicate_attendance.sql` — (volunteer_id, event_id, occasion_date) is unique
- **Singular test:** `tests/no_future_attendance.sql` — occasion_date ≤ current_date
- **Singular test:** `tests/warn_orphaned_attendance.sql` — warn if any rows have null volunteer_id

**Estimate:** 1.5h

**Depends on:** Task 0.3, 0.4, 1, 3

**Status:** —

---

### [ ] Task 5: Build fct_project_volunteer
**File:** `dbt/models/marts/fct_project_volunteer.sql` (new, create file)

Select from stg_project_volunteers, extracting linked-record arrays inline in the mart:
```sql
with source as (
    select * from {{ ref('stg_project_volunteers') }}
),
extracted as (
    select
        id as join_id,
        json_extract_string(json_blob, '$.volunteer_id[0]') as volunteer_id,
        json_extract_string(json_blob, '$.project_id[0]') as project_id,
        json_extract_string(json_blob, '$.role') as role,
        try_cast(json_extract_string(json_blob, '$.commitment_date') as date) as commitment_date,
        try_cast(json_extract_string(json_blob, '$.end_date') as date) as end_date,
        json_extract_string(json_blob, '$.status') as status,
        (
            (case when json_extract_string(json_blob, '$.outreach_1_date') is not null then 1 else 0 end) +
            (case when json_extract_string(json_blob, '$.outreach_2_date') is not null then 1 else 0 end) +
            (case when json_extract_string(json_blob, '$.outreach_3_date') is not null then 1 else 0 end)
        ) as outreach_attempt_count,
        try_cast(json_extract_string(json_blob, '$.outreach_1_date') as date) as first_outreach_date,
        try_cast(
            case
                when json_extract_string(json_blob, '$.outreach_3_date') is not null then json_extract_string(json_blob, '$.outreach_3_date')
                when json_extract_string(json_blob, '$.outreach_2_date') is not null then json_extract_string(json_blob, '$.outreach_2_date')
                else json_extract_string(json_blob, '$.outreach_1_date')
            end
        as date) as last_outreach_date,
        case
            when json_extract_string(json_blob, '$.outreach_3_date') is not null then json_extract_string(json_blob, '$.outreach_3_status')
            when json_extract_string(json_blob, '$.outreach_2_date') is not null then json_extract_string(json_blob, '$.outreach_2_status')
            else json_extract_string(json_blob, '$.outreach_1_status')
        end as last_outreach_status,
        coalesce(json_extract_string(json_blob, '$.declined')::boolean, false) as is_declined,
        json_extract_string(json_blob, '$.decline_reason') as decline_reason,
        created_time as airtable_created_at,
        last_modified as airtable_modified_at
    from source
)
select * from extracted
```

**Notes:**
- Array expansion happens here in the mart, not in staging. Index [0] gets the first (usually only) linked record.
- Outreach tracking: count non-null dates, and derive "last" from the latest non-null outreach_N_date/status.
- Checkbox field (declined) coerced to boolean; null → false.

**Tests (schema.yml):**
- `not_null` on join_id, volunteer_id, project_id
- `unique` on join_id
- `relationships` volunteer_id → dim_volunteer.volunteer_id
- `relationships` project_id → dim_project.project_id
- `accepted_values` on status: (to be confirmed) (warn)
- **Singular test:** `tests/warn_orphaned_project_volunteer.sql` — warn if any rows have null volunteer_id or project_id

**Estimate:** 1.5h

**Depends on:** Task 0.5, 1, 2

**Status:** —

---

## Testing & Documentation

### [ ] Task 6: Create test definitions
**File:** `dbt/tests/marts_tests.yml` (new)

Generic tests for all models (macro-based):
```yaml
version: 2

models:
  - name: dim_volunteer
    tests:
      - not_null:
          column_name: volunteer_id
      - unique:
          column_name: volunteer_id
  - name: dim_project
    tests:
      - not_null:
          column_name: project_id
      - unique:
          column_name: project_id
      - accepted_values:
          column_name: status
          values: ['Intake', 'Active', 'Complete', 'On hold']
          config:
            severity: warn
  # ... etc for dim_event, fct_attendance, fct_project_volunteer
  - name: fct_attendance
    tests:
      - relationships:
          column_name: volunteer_id
          to: ref('dim_volunteer')
          field: volunteer_id
      - relationships:
          column_name: event_id
          to: ref('dim_event')
          field: event_id
```

**Singular test files:**
- `tests/no_duplicate_attendance.sql` — SELECT volunteer_id, event_id, occasion_date FROM fct_attendance GROUP BY 1, 2, 3 HAVING count(*) > 1
- `tests/no_future_attendance.sql` — SELECT * FROM fct_attendance WHERE occasion_date > current_date
- `tests/warn_orphaned_attendance.sql` — SELECT COUNT(*) as orphaned_count FROM fct_attendance WHERE volunteer_id IS NULL (add config.severity: warn)
- `tests/warn_orphaned_project_volunteer.sql` — SELECT COUNT(*) FROM fct_project_volunteer WHERE volunteer_id IS NULL OR project_id IS NULL

**Estimate:** 1.5h

**Depends on:** Tasks 4, 5

**Status:** —

---

### [ ] Task 7: Write model documentation and add dbt docs to workflow
**Files:**
- Create `dbt/models/marts/models.yml` with descriptions for all dim and fact models and their columns
- Update `.github/workflows/dbt.yml` to add `dbt docs generate` and publish to GitHub Pages (if not present)
- Create/update `docs/roadmap/PHASE2_STATUS.md` with completion summary
- Create `DECISIONS.md` (if missing) to document design choices

**Documentation checklist:**
- [ ] Model: dim_volunteer — describe what it contains, PII exclusions, deferred fields
- [ ] Model: dim_project — describe keys, deferred fields
- [ ] Model: dim_event — explain synthetic row 0 for monthly meetings
- [ ] Model: fct_attendance — explain monthly meeting date logic, consolidation of two attendance types
- [ ] Model: fct_project_volunteer — explain array expansion, outreach tracking
- [ ] Every column: description, source field name, any transformations
- [ ] Note: "PII is excluded at dlt pipeline level; marts carry volunteer_id only"
- [ ] Add freshness check to sources.yml (dlt load timestamp, warn after 36h)

**Estimate:** 1-2h

**Depends on:** Tasks 1–6

**Status:** —

---

## Summary

| Phase | Tasks | Estimate | Status |
|-------|-------|----------|--------|
| Code cleanup | 0.0 | 0.5h | — |
| Pre-work | 0.1 – 0.5 | 2.75h | — |
| Mart models | 1 – 5 | 5.25h | — |
| Testing & docs | 6 – 7 | 2.5-3.5h | — |
| **Total** | | **11-13h** | — |

---

## Decisions Already Made (Per Plan)

- ✅ No Meeting Attendance table; consolidate to Event attendance with event_id = 0
- ✅ PII excluded from marts (volunteer_id only)
- ✅ Deferred to Phase 3: availability, language_fluency, nonprofit_skills, tech_skills, roles_interested_in, volunteer_participation_summary, retention metrics, demographic reporting
- ✅ Array expansion in mart layer (fct_project_volunteer), not staging
- ✅ Synthetic row 0 in dim_event for monthly meetings

---

## Key Design Notes

1. **PII strategy:** Excluded at dlt ingestion (Task 0.1). Marts SELECT only ID and safe columns. No risk of accidental exposure.

2. **Monthly meetings:** Event attendance records with event_id = 0. All monthly meetings share this pseudo-event. Actual meeting date comes from attendance.occasion_date.

3. **Deferred fields:** Extracted in staging (preserved from Airtable) but NOT in Phase 2 marts. Phase 3 will build metrics using these: availability, language_fluency, nonprofit_skills, tech_skills, skills_to_develop, roles_interested_in.

4. **Array expansion:** Linked records (volunteer_id, project_id, outreach_N_date) are stored as arrays in json_blob. dbt extracts them in the fact models using json_extract_string with [0], [1], [2] indices.

5. **Reconciliation:** After cleanup (Task 0.0), code and plan are aligned. No further decisions needed; proceed straight to implementation.
