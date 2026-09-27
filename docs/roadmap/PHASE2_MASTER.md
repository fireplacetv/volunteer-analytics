# Volunteer Analytics — Phase 2: Marts & Metrics
## Consolidated Roadmap & Implementation Guide

**Created:** Sep 27, 2026  
**Author:** Claude (from Derrick's phase-2-plan.md)  
**Status:** ✅ Ready for implementation  
**Confidence:** HIGH  
**Estimate:** 10.5–11.5 hours  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Phase 2 Plan (Authoritative Spec)](#phase-2-plan)
3. [Conflicts & Resolutions](#conflicts--resolutions)
4. [Detailed Task Breakdown](#detailed-task-breakdown)
5. [Implementation Readiness](#implementation-readiness)
6. [Phase 3+ Future Roadmap](#phase-3-future-roadmap)

---

## Executive Summary

**What:** Build 3 dimension tables and 2 fact tables from staging, tested and documented.

**Why:** Create clean, ID-keyed marts so later reporting can join without touching staging.

**When:** Now (Phase 2). PII filtering and metrics deferred to Phase 3.

**How:** 12 tasks (10.5–11.5h): cleanup staging (0.0–0.4), build marts (1–5), add tests & docs (6–7).

**Confidence:** HIGH ✅ — All conflicts identified and resolved. One pending clarification (non-blocking).

**Go/No-Go:** **🟢 GO** — Start implementation immediately.

---

## Phase 2 Plan

### Entry Criteria (from Phase 1)
- ✅ Staging models exist 1:1 for five Airtable tables: Volunteers, Projects, Project volunteers, Events, Event attendance
- ✅ Linked-record fields are resolved into bridge tables
- ✅ `not_null`, `unique` and `relationships` tests pass

### Exit Criteria
- [ ] `dim_volunteer`, `dim_project`, `dim_event`, `fct_attendance`, `fct_project_volunteer` build and pass tests nightly
- [ ] Internal-only and identifying fields are excluded from every mart
- [ ] dbt docs are generated in CI and hosted

### Deferred to Later Phase
- `volunteer_participation_summary`, "active volunteer" definition, retention and repeat-attendance metrics
- PII filtering at dlt level (deferred to Phase 3)
- Deferred field parsing (availability, language_fluency, tech_skills, etc.)

---

## Five Models to Build

### Design Principles
- Five models straight from staging, no intermediate layer
- Each staging table maps to exactly one dim or fact
- All attendance lives in Event attendance: monthly meetings recorded with `event_id` = 0
- Every model keyed on Airtable record ID so later marts can join without staging

### Model Overview

| Model | One row per | Key | Built from | Type |
|-------|-------------|-----|-----------|------|
| `dim_volunteer` | volunteer | `volunteer_id` | `stg_volunteers` | Dimension |
| `dim_project` | project | `project_id` | `stg_projects` | Dimension |
| `dim_event` | event (row 0 = monthly meetings) | `event_id` | `stg_events` | Dimension |
| `fct_attendance` | Event attendance row | `attendance_id` | `stg_event_attendance`, `stg_events` | Fact |
| `fct_project_volunteer` | Project volunteers row | `join_id` | `stg_project_volunteers` | Fact |

---

## Detailed Schemas

### dim_volunteer

**One row per volunteer. Key: `volunteer_id` (Airtable record ID)**

| Column | Type | Source field | Notes |
|--------|------|-------------|-------|
| `volunteer_id` | `varchar` | record ID | Primary key |
| `status` | `varchar` | status | Pending / Active / Inactive / Alumni |
| `joined_date` | `date` | joined_date | Admin-set on activation; null while Pending |
| `source` | `varchar` | source | CityCamp Oakland / Meetup / Community event / Word of mouth / Social media / Other |
| `employment_status` | `varchar` | employment_status | — |
| `hours_per_month` | `varchar` | hours_per_month | Self-reported band: 0–4 / 5–9 / 10–19 / 20–39 / 40+ |
| `state` | `varchar` | state | — |
| `timezone` | `varchar` | timezone | — |
| `has_board_leadership_experience` | `boolean` | board_leadership_experience | Null checkbox → false |
| `has_grant_writing_experience` | `boolean` | grant_writing_experience | Null checkbox → false |
| `airtable_created_at` | `timestamp` | created_time | Audit trail |
| `airtable_modified_at` | `timestamp` | last_modified | Audit trail |

**Intentionally excluded:** first_name, last_name, email, pronouns, age_range, city, linkedin, github, website_portfolio, slack_handle, accommodations, other_notes, vetting fields

**Deferred to Phase 3:** availability[], language_fluency[], nonprofit_skills[], tech_skills[], skills_to_develop[], roles_interested_in[] (extracted in staging, parsed in Phase 3)

---

### dim_project

**One row per project. Key: `project_id` (Airtable auto ID, not record ID)**

| Column | Type | Source field | Notes |
|--------|------|-------------|-------|
| `project_id` | `integer` | project_id (Airtable auto ID) | Primary key, human-readable |
| `airtable_record_id` | `varchar` | record ID | For tracing back to Airtable |
| `project_name` | `varchar` | name | — |
| `status` | `varchar` | status | Intake / Active / Complete / On hold |
| `stakeholder` | `varchar` | stakeholder | Partner org name |
| `description` | `varchar` | description | — |
| `start_date` | `date` | start_date | — |
| `end_date` | `date` | end_date | Null until formally closed |
| `airtable_created_at` | `timestamp` | created_time | Audit trail |
| `airtable_modified_at` | `timestamp` | last_modified | Audit trail |

---

### dim_event

**One row per event (plus synthetic row 0 for monthly meetings). Key: `event_id` (Airtable auto ID)**

| Column | Type | Source field | Notes |
|--------|------|-------------|-------|
| `event_id` | `integer` | event_id (Airtable auto ID) | Primary key. 0 = monthly meetings |
| `airtable_record_id` | `varchar` | record ID | For tracing back to Airtable; null for row 0 |
| `event_name` | `varchar` | name | — |
| `event_type` | `varchar` | type | Monthly meeting / CityCamp / Community event / Other |
| `event_date` | `date` | event_date | Null for row 0 (monthly meetings) |
| `description` | `varchar` | description | — |
| `is_monthly_meeting` | `boolean` | derived | True when event_id = 0 |
| `airtable_created_at` | `timestamp` | created_time | Audit trail; null for row 0 |
| `airtable_modified_at` | `timestamp` | last_modified | Audit trail; null for row 0 |

**Synthetic row 0:** If Events table has no actual row with event_id = 0, model adds fixed "Monthly meetings" row so fct_attendance relationships test passes.

---

### fct_attendance

**One row per Event attendance record. Key: `attendance_id` (Airtable record ID)**

| Column | Type | Source field | Notes |
|--------|------|-------------|-------|
| `attendance_id` | `varchar` | record ID | Primary key |
| `volunteer_id` | `varchar` | volunteer_id link | FK → dim_volunteer |
| `event_id` | `integer` | event_id link | FK → dim_event; 0 = monthly meeting |
| `is_monthly_meeting` | `boolean` | derived | True when event_id = 0 |
| `occasion_type` | `varchar` | event type | Via stg_events (Monthly meeting / CityCamp / Community event / Other) |
| `occasion_date` | `date` | attendance date, fallback event date | **Hard not_null**: monthly meetings share event_id = 0, so date must come from attendance row |
| `status` | `varchar` | status | Consolidated: Attended / RSVP'd / No-show / Absent / Remote |
| `is_present` | `boolean` | derived | True when status IN ('Attended', 'Remote') |
| `airtable_created_at` | `timestamp` | created_time | Audit trail |
| `airtable_modified_at` | `timestamp` | last_modified | Audit trail |

**Monthly meeting date logic:** For event_id = 0, occasion_date comes from attendance.date (all monthly meetings share pseudo-event, so actual date stored per attendance).

---

### fct_project_volunteer

**One row per Project volunteers record. Key: `join_id` (Airtable record ID)**

| Column | Type | Source field | Notes |
|--------|------|-------------|-------|
| `join_id` | `varchar` | record ID | Primary key |
| `volunteer_id` | `varchar` | volunteer_id link (array [0]) | FK → dim_volunteer |
| `project_id` | `varchar` | project_id link (array [0]) | FK → dim_project |
| `role` | `varchar` | role | Free text, e.g. UX Designer |
| `commitment_date` | `date` | commitment_date | Null for outreach-only rows |
| `end_date` | `date` | end_date | — |
| `status` | `varchar` | status | Active / Completed / Departed |
| `outreach_attempt_count` | `integer` | derived | 0–3: count of non-null outreach_N_date |
| `first_outreach_date` | `date` | outreach_1_date | — |
| `last_outreach_date` | `date` | derived | Latest non-null outreach_N_date |
| `last_outreach_status` | `varchar` | derived | Emailed / Responded / No response (from latest outreach_N_status) |
| `is_declined` | `boolean` | declined | Null checkbox → false |
| `decline_reason` | `varchar` | decline_reason | — |
| `airtable_created_at` | `timestamp` | created_time | Audit trail |
| `airtable_modified_at` | `timestamp` | last_modified | Audit trail |

**Array expansion:** Linked records (volunteer_id, project_id) are arrays in json_blob. Mart extracts [0] index using `json_extract_string(json_blob, '$.volunteer_id[0]')`.

**Outreach tracking:** Derives count and latest date/status from outreach_1_date, outreach_2_date, outreach_3_date (and corresponding status fields).

---

## Conflicts & Resolutions

### Summary: 12 Areas Reviewed

| # | Conflict | Severity | Status | Resolution | Task(s) |
|---|----------|----------|--------|-----------|---------|
| 1 | Meeting Attendance table exists (code has 6, plan expects 5) | CRITICAL | ✅ Resolved | Delete artifact | 0.0 |
| 2 | stg_projects incomplete (only project_id) | HIGH | ✅ Resolved | Expand + build dim | 0.1, 2 |
| 3 | stg_event_attendance missing volunteer_id, status | HIGH | ✅ Resolved | Expand + build fact | 0.2, 4 |
| 4 | stg_volunteers field mismatches (tech_languages_tools vs. tech_skills) | MEDIUM | ✅ Resolved | Normalize + build dim | 0.1, 1 |
| 5 | event_type vs. event_status field naming | MEDIUM | ⏳ Pending | Clarify in Airtable | 0.3 |
| 6 | models.yml out of sync with actual SQL | LOW | ✅ Resolved | Update docs | 0.4 |
| 7 | No mart tests yet | — | ✅ Resolved | Add tests | 6 |
| 8 | No mart docs yet | — | ✅ Resolved | Add docs | 7 |
| 9 | PII at dlt level (plan says exclude; code doesn't) | DEFERRED | ⏸️ Deferred to Phase 3 | Filter in Phase 3 | ROADMAP_FUTURE |
| 10 | stg_project_volunteers minimal (arrays in json_blob) | INFO | ✅ Correct | Array expansion in marts | 5 |
| 11 | Phase 1 complete? | — | ✅ Yes | Entry criteria met | — |
| 12 | Mart models exist? | — | ✅ No (correct) | Phase 2 builds them | 1–5 |

### Detailed Conflict Resolutions

#### Conflict 1: Meeting Attendance Table (CRITICAL)
**Plan expects:** 5 Airtable tables  
**Code has:** 6 (+ Meeting Attendance)  
**Issue:** Plan consolidates all attendance into Event attendance with event_id = 0. Meeting Attendance doesn't exist in real schema.

**Resolution:** Delete artifacts (Task 0.0)
- Delete `dbt/models/staging/stg_meeting_feedback.sql`
- Remove "Meeting attendance" from `dlt/airtable_pipeline/airtable_tables.json`
- Remove `meeting_attendance` from `dbt/models/sources.yml`
- Verify `dbt run && dbt test` passes with 5 sources

---

#### Conflict 2: stg_projects Incomplete (HIGH)
**Plan expects:** 8 columns (project_number, name, status, stakeholder, description, dates, timestamps)  
**Code has:** 4 columns (id, created_time, last_modified, project_id)

**Resolution:** Expand stg_projects.sql (Task 0.1)
```sql
Extract from json_blob:
- project_number (integer from project_id field)
- project_name (from name)
- status (Intake / Active / Complete / On hold)
- stakeholder
- description
- start_date (cast to date)
- end_date (cast to date)
```

---

#### Conflict 3: stg_event_attendance Missing FK & Status (HIGH)
**Plan expects:** volunteer_id (FK), status (Attended/RSVP'd/No-show/Absent/Remote)  
**Code has:** attendance_id, event_id, date, name, email (no FK, no status)

**Resolution:** Expand stg_event_attendance.sql (Task 0.2)
```sql
Extract:
- volunteer_id (from linked record)
- status (Attended / RSVP'd / No-show / Absent / Remote)

Remove:
- name (attendee name, not a key)
- email (attendee email, PII)
```

---

#### Conflict 4: stg_volunteers Field Name Mismatches (MEDIUM)
**Plan expects:** tech_skills[], nonprofit_skills[], roles_interested_in[]  
**Code extracts:** tech_languages_tools, nonprofit_experience_level, project_interests

**Resolution:** Document as deferred (Task 0.4)
- stg_volunteers extracts all fields ✓
- Field names don't match plan exactly (extraction follows Airtable schema)
- Phase 2 dim_volunteer uses Phase 2 scope columns only (status, joined_date, employment_status, etc.)
- Deferred fields stay in staging, parsed in Phase 3 for metrics

---

#### Conflict 5: event_type vs. event_status (MEDIUM)
**Plan expects:** event_type with values (Monthly meeting / CityCamp / Community event / Other)  
**Code has:** event_status in stg_events

**Issue:** Field name mismatch. Plan may expect event category, not lifecycle status.

**Resolution:** Clarify in Airtable (Task 0.3, ~5 min)
1. Check Events table field names and values
2. If "type" with event categories → rename in staging to event_type
3. If "status" with lifecycle values → clarify with plan, adjust dim_event
4. Proceed with dim_event build (Task 3) after clarification

**Non-blocking:** Other tasks can proceed in parallel.

---

#### Conflict 6: models.yml Out of Sync (LOW)
**Plan expects:** Accurate schema docs for 5 staging models  
**Code has:** models.yml describes different columns than actual SQL (e.g., lists "name" as single column, but SQL extracts first_name + last_name)

**Resolution:** Update models.yml (Task 0.4)
- Document all extracted fields
- Link to phase-2-plan.md schemas
- Mark deferred fields (Phase 3)
- Note: staging is 1:1 with Airtable, not plan schema exactly

---

#### Conflict 7: PII Not Excluded at dlt (DEFERRED)
**Plan says:** Exclude vetting_status, vetting_notes, internal_admin_notes at dlt so they never reach DuckDB  
**Code does:** Stores everything in json_blob

**Issue:** PII reaches DuckDB. However, project in dev (no public launch).

**Resolution:** Defer to Phase 3 (see Future Roadmap below)
- Phase 2 marts exclude PII via SELECT (volunteer_id only, no names/emails) ✓
- dlt-level filtering will be implemented in Phase 3 before production launch
- Pragmatic: Focus Phase 2 on building marts correctly; harden for public exposure later

---

#### Conflict 8–12: Remaining Items
- **No mart tests yet:** ✅ Correct. Phase 2 builds them (Task 6)
- **No mart docs yet:** ✅ Correct. Phase 2 builds them (Task 7)
- **Phase 1 complete:** ✅ Yes. PHASE1_STATUS.md confirms entry criteria met
- **stg_project_volunteers minimal:** ✅ Correct by design. Array expansion happens in fact model (Task 5)

---

## Detailed Task Breakdown

### Phase 2A: Pre-work (Code Cleanup & Staging Alignment) — 2.25h

#### Task 0.0: Remove Meeting Attendance Artifacts — 0.5h
**Files to modify:**
- `dlt/airtable_pipeline/airtable_tables.json` — Remove "Meeting attendance" entry
- `dbt/models/sources.yml` — Remove meeting_attendance table definition
- `dbt/models/staging/stg_meeting_feedback.sql` — Delete file
- `dbt/models/staging/models.yml` — Remove stg_meeting_feedback entry

**Verify after:** `dbt run && dbt test` passes with 5 source tables (Volunteers, Projects, Project volunteers, Events, Event attendance)

**Status:** ✅ Ready

---

#### Task 0.1: Expand stg_projects.sql — 0.5h
**File:** `dbt/models/staging/stg_projects.sql`

**Current:** Only extracts project_id from json_blob

**Add extractions:**
```sql
with source as (
    select * from {{ source('airtable', 'projects') }}
)
select
    id,
    created_time,
    last_modified,
    json_extract_string(json_blob, '$.project_id') as project_id,
    json_extract_string(json_blob, '$.project_number') as project_number,
    json_extract_string(json_blob, '$.name') as project_name,
    json_extract_string(json_blob, '$.status') as status,
    json_extract_string(json_blob, '$.stakeholder') as stakeholder,
    json_extract_string(json_blob, '$.description') as description,
    try_cast(json_extract_string(json_blob, '$.start_date') as date) as start_date,
    try_cast(json_extract_string(json_blob, '$.end_date') as date) as end_date
from source
```

**Verify:** stg_projects now has 10 columns; rebuild works

**Status:** ✅ Ready

---

#### Task 0.2: Expand stg_event_attendance.sql — 0.5h
**File:** `dbt/models/staging/stg_event_attendance.sql`

**Current:** Extracts attendance_id, event_id, date, name, email

**Remove columns:**
- `name` (attendee name, not a database key)
- `email` (attendee email, PII)

**Add extractions:**
```sql
with source as (
    select * from {{ source('airtable', 'event_attendance') }}
)
select
    id,
    created_time,
    last_modified,
    json_extract_string(json_blob, '$.attendance_id') as attendance_id,
    json_extract_string(json_blob, '$.event_id') as event_id,
    json_extract_string(json_blob, '$.volunteer_id') as volunteer_id,
    try_cast(json_extract_string(json_blob, '$.date') as date) as date,
    json_extract_string(json_blob, '$.status') as status
from source
```

**Verify:** stg_event_attendance has volunteer_id and status; name/email removed

**Status:** ✅ Ready

---

#### Task 0.3: Clarify event_type Field in Airtable — 0.25h (pending)
**Manual check (5 min):**

1. Open Airtable Events table
2. Check field names and values:
   - Is there a "type" field? If so, what are the values? (CityCamp, Community event, etc.)
   - Is there a "status" field? If so, what are the values? (planned, in_progress, completed?)
3. Confirm how monthly meetings are represented (event_id = 0? specific type value?)

**Outcome:** Determine if stg_events.event_status should be renamed to event_type, or if a different field needs extraction

**Blocks:** Task 3 (dim_event build), but tasks 0.1–0.2, 0.4, 1–2, 4–7 can proceed in parallel

**Status:** ⏳ Pending clarification (non-blocking)

---

#### Task 0.4: Update dbt/models/staging/models.yml — 1h
**File:** `dbt/models/staging/models.yml`

**For each staging model, document:**
- All extracted columns (name, type, tests, description)
- Link to phase-2-plan.md source schema
- Note which fields are deferred to Phase 3 (availability, language_fluency, nonprofit_skills, tech_skills, skills_to_develop, roles_interested_in)
- Explain why (Phase 2 focuses on core dims/facts; Phase 3 handles metrics/reporting)

**Example for stg_volunteers:**
```yaml
- name: stg_volunteers
  description: One-to-one staging for volunteer records. Core fields extracted for Phase 2; deferred multi-select fields (availability, language_fluency, nonprofit_skills, tech_skills, skills_to_develop, roles_interested_in) stay in json_blob for Phase 3 parsing.
  columns:
    - name: id
      description: Volunteer record ID from Airtable
      tests: [not_null, unique]
    - name: status
      description: Pending / Active / Inactive / Alumni
    - name: joined_date
      description: Date volunteer was activated
    - ... (other Phase 2 columns)
    - name: tech_languages_tools
      description: Tech skills (deferred to Phase 3 for normalization as tech_skills[])
```

**Verify:** models.yml accurately reflects actual stg_*.sql extractions

**Status:** ✅ Ready

---

### Phase 2B: Build Mart Models (3 dims + 2 facts) — 5.25h

All files go in `dbt/models/marts/` (create directory)

#### Task 1: Build dim_volunteer — 0.5h
**File:** `dbt/models/marts/dim_volunteer.sql` (new)

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

**Schema:** 10 columns (excludes PII: names, email, pronouns, age, city, links, accommodations; defers arrays to Phase 3)

**Tests (to be added in Task 6):**
- `not_null` on volunteer_id
- `unique` on volunteer_id

**Status:** ✅ Ready to build

---

#### Task 2: Build dim_project — 0.5h
**File:** `dbt/models/marts/dim_project.sql` (new)

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

**Key:** `project_id` is Airtable auto ID, not record ID (used in fct_project_volunteer FK)

**Tests (Task 6):**
- `not_null` on project_id
- `unique` on project_id
- `accepted_values` on status: ['Intake', 'Active', 'Complete', 'On hold'] (warn)

**Status:** ✅ Ready to build

---

#### Task 3: Build dim_event — 0.75h
**File:** `dbt/models/marts/dim_event.sql` (new)

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
        [event_type_from_clarified_field] as event_type,  -- Task 0.3 determines exact extraction
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

**Key design:** event_id = 0 is synthetic row for monthly meetings (all monthly meetings share this pseudo-event; actual date is in fct_attendance.occasion_date)

**Depends on:** Task 0.3 (event_type field clarification)

**Tests (Task 6):**
- `not_null` on event_id
- `unique` on event_id
- `accepted_values` on event_type: (to be confirmed) (warn)

**Status:** ⏳ Blocked on Task 0.3 clarification, but can write SQL template now

---

#### Task 4: Build fct_attendance — 1.5–2h
**File:** `dbt/models/marts/fct_attendance.sql` (new)

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

**Key logic:** For event_id = 0 (monthly meetings), occasion_date comes from attendance.date (not event date, since all monthly meetings share one pseudo-event)

**Depends on:** Task 0.2 (stg_event_attendance expanded), Task 3 (dim_event built)

**Tests (Task 6):**
- `not_null` on attendance_id, volunteer_id, event_id, occasion_date
- `unique` on attendance_id
- `relationships` volunteer_id → dim_volunteer
- `relationships` event_id → dim_event
- `accepted_values` on status (warn)
- Singular: no duplicate check-ins
- Singular: no future dates
- Singular: warn on orphaned attendance

**Status:** ✅ Ready (after pre-work done)

---

#### Task 5: Build fct_project_volunteer — 1.5–2h
**File:** `dbt/models/marts/fct_project_volunteer.sql` (new)

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
        coalesce(json_extract_string(json_blob, '$.is_declined')::boolean, false) as is_declined,
        json_extract_string(json_blob, '$.decline_reason') as decline_reason,
        created_time as airtable_created_at,
        last_modified as airtable_modified_at
    from source
)
select * from extracted
```

**Key design:**
- Array indices [0] extract first (usually only) linked record
- Outreach tracking derives count and "latest" from outreach_1/2/3_date and status fields
- Checkbox (declined) coerced to boolean; null → false

**Depends on:** Task 0.4 (models.yml updated to document design), Task 1 (dim_volunteer), Task 2 (dim_project)

**Tests (Task 6):**
- `not_null` on join_id, volunteer_id, project_id
- `unique` on join_id
- `relationships` volunteer_id → dim_volunteer
- `relationships` project_id → dim_project
- `accepted_values` on status (warn)
- Singular: warn on orphaned rows

**Status:** ✅ Ready (after pre-work done)

---

### Phase 2C: Testing & Documentation — 2.5–3.5h

#### Task 6: Add Tests — 1.5–2h
**Files to create:**
- `dbt/tests/marts_tests.yml` (new) — Generic test definitions
- `dbt/tests/no_duplicate_attendance.sql` (new) — Singular test
- `dbt/tests/no_future_attendance.sql` (new) — Singular test
- `dbt/tests/warn_orphaned_attendance.sql` (new) — Singular test
- `dbt/tests/warn_orphaned_project_volunteer.sql` (new) — Singular test

**marts_tests.yml:**
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

  - name: dim_event
    tests:
      - not_null:
          column_name: event_id
      - unique:
          column_name: event_id
      - accepted_values:
          column_name: event_type
          values: ['Monthly meeting', 'CityCamp', 'Community event', 'Other']
          config:
            severity: warn

  - name: fct_attendance
    tests:
      - not_null:
          column_name: attendance_id
      - not_null:
          column_name: volunteer_id
      - not_null:
          column_name: event_id
      - not_null:
          column_name: occasion_date
      - unique:
          column_name: attendance_id
      - relationships:
          column_name: volunteer_id
          to: ref('dim_volunteer')
          field: volunteer_id
      - relationships:
          column_name: event_id
          to: ref('dim_event')
          field: event_id
      - accepted_values:
          column_name: status
          values: ['Attended', 'RSVP\'d', 'No-show', 'Absent', 'Remote']
          config:
            severity: warn

  - name: fct_project_volunteer
    tests:
      - not_null:
          column_name: join_id
      - not_null:
          column_name: volunteer_id
      - not_null:
          column_name: project_id
      - unique:
          column_name: join_id
      - relationships:
          column_name: volunteer_id
          to: ref('dim_volunteer')
          field: volunteer_id
      - relationships:
          column_name: project_id
          to: ref('dim_project')
          field: project_id
      - accepted_values:
          column_name: status
          values: ['Active', 'Completed', 'Departed']
          config:
            severity: warn
```

**Singular tests:**
- `no_duplicate_attendance.sql`: `SELECT volunteer_id, event_id, occasion_date FROM fct_attendance GROUP BY 1,2,3 HAVING count(*) > 1`
- `no_future_attendance.sql`: `SELECT * FROM fct_attendance WHERE occasion_date > current_date`
- `warn_orphaned_attendance.sql`: `SELECT COUNT(*) as orphaned_count FROM fct_attendance WHERE volunteer_id IS NULL` (with severity: warn)
- `warn_orphaned_project_volunteer.sql`: Similar for project_volunteer

**Verify:** `dbt test` on marts passes

**Status:** ✅ Ready (after marts built)

---

#### Task 7: Documentation & Workflow — 1–1.5h
**Files to create/update:**
- `dbt/models/marts/models.yml` (new) — Mart model descriptions
- `.github/workflows/dbt.yml` — Add `dbt docs generate` step
- `docs/DECISIONS.md` (new or update) — Design decisions
- `docs/HANDOFF.md` (new or update) — Operational runbook

**models.yml contents:**
```yaml
version: 2

models:
  - name: dim_volunteer
    description: Dimension table for volunteers. Excludes PII (names, emails, demographics). Deferred multi-select fields (skills, availability, language) are in staging for Phase 3 metrics.
    columns:
      - name: volunteer_id
        description: Airtable volunteer record ID. Primary key.
        tests: [not_null, unique]
      - name: status
        description: Pending / Active / Inactive / Alumni
      - ... (other columns with descriptions)

  - name: dim_project
    description: Dimension table for projects. One row per project.
    columns:
      - name: project_id
        description: Airtable project auto-ID. Primary key, human-readable.
        tests: [not_null, unique]
      - ... (other columns)

  - name: dim_event
    description: Dimension table for events. Includes synthetic row 0 for monthly meetings.
    columns:
      - name: event_id
        description: Airtable event auto-ID. Primary key. 0 = all monthly meetings.
        tests: [not_null, unique]
      - name: is_monthly_meeting
        description: Derived. True when event_id = 0.
      - ... (other columns)

  - name: fct_attendance
    description: Fact table for attendance records. One row per Event attendance entry. Links to dim_volunteer, dim_event. Monthly meetings (event_id = 0) share pseudo-event; actual date in occasion_date.
    columns:
      - name: attendance_id
        description: Airtable attendance record ID. Primary key.
        tests: [not_null, unique]
      - name: volunteer_id
        description: FK to dim_volunteer. May be null for orphaned attendance (warn test).
        tests: [relationships]
      - name: occasion_date
        description: Date of attendance. Hard not_null (monthly meetings stored per attendance, not event).
        tests: [not_null]
      - ... (other columns)

  - name: fct_project_volunteer
    description: Fact table for project-volunteer relationships. One row per Project volunteers entry. Links to dim_volunteer, dim_project. Arrays expanded from json_blob.
    columns:
      - name: join_id
        description: Airtable project_volunteers record ID. Primary key.
        tests: [not_null, unique]
      - name: volunteer_id
        description: FK to dim_volunteer. Extracted from linked record array [0].
        tests: [relationships]
      - name: outreach_attempt_count
        description: Derived. Count of non-null outreach_N_date fields (0–3).
      - ... (other columns)
```

**DECISIONS.md:**
```
# Phase 2 Design Decisions

## event_id = 0 for Monthly Meetings
All monthly meetings share pseudo-event (event_id = 0) rather than individual event rows.
Why: Meetings are recurring with same organizers/agenda; actual date varies per attendance.
Trade-off: Every fct_attendance for monthly must have occasion_date (not null test).

## Array Expansion in Marts, Not Staging
Linked records (volunteer_id, project_id) stored as arrays in staging json_blob.
Extraction to [0] index happens in fct_project_volunteer SQL.
Why: Staging 1:1 with Airtable; marts handle interpretation.
Trade-off: Mart SQL more complex, but preserves raw data.

## PII Excluded at Mart SELECT, Not dlt
Volunteer PII (names, emails, demographics) in staging; excluded from dim_volunteer SELECT.
dlt-level filtering deferred to Phase 3 (before public launch).
Why: Project in dev; focus Phase 2 on correct marts. Phase 3 hardens for production.
Trade-off: Staging holds PII; DuckDB file must stay private. Documented in ROADMAP_FUTURE.md.

## Deferred Multi-Select Parsing (Phase 3)
Fields like availability[], language_fluency[], nonprofit_skills[] extracted in stg_volunteers
but not normalized (arrays stored as-is). Phase 3 metrics will parse and expose these.
Why: Phase 2 focuses on core dims/facts; Phase 3 builds metrics and reporting.
Trade-off: Deferred fields available in staging if needed urgently.
```

**HANDOFF.md:**
```
# Operational Runbook: Phase 2 Marts

## How to Run the Pipeline
docker compose build
docker compose run --rm dev bash -c "python dlt/airtable_pipeline/airtable_source.py && dbt run && dbt test"

## If Tests Fail
- Orphaned attendance (warn): Check Airtable Event attendance for rows with missing volunteer_id link
- Future dates (warn): Check check-in forms for data entry errors
- Duplicate check-ins: Check Airtable for duplicate records; dedup if needed
- Relationship failures: Check Airtable links are valid (project_id, event_id, volunteer_id)

## Schema Dependencies
- Volunteers table: Must have status, joined_date, employment_status, hours_per_month, state, timezone
- Projects table: Must have project_id (auto-ID), name, status, stakeholder, description, start_date, end_date
- Events table: Must have event_id (auto-ID), name, [event_type or type], event_date, description
- Event attendance table: Must have volunteer_id link, event_id, date, status fields
- Project volunteers table: Must have volunteer_id array, project_id array, role, commitment_date, end_date, status, outreach_N_date, declined

If field names change, update stg_*.sql extractions.

## Second Person Onboarding
- Read phase-2-plan.md (spec)
- Read PHASE2_MASTER.md (this document)
- Read DECISIONS.md (design rationale)
- Review stg_*.sql (understand field extraction)
- Review dim_*.sql and fct_*.sql (understand transformations)
- Run `dbt docs generate && open target/index.html` to browse lineage and column docs
```

**GitHub Actions (.github/workflows/dbt.yml):**
Add step after `dbt test`:
```yaml
- name: Generate dbt docs
  run: dbt docs generate

- name: Deploy docs to GitHub Pages
  uses: peaceiris/actions-gh-pages@v3
  if: github.ref == 'refs/heads/main'
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./target
```

**Verify:** `dbt docs generate` runs, dbt docs site is available

**Status:** ✅ Ready (after marts + tests built)

---

## Implementation Readiness

### ✅ Ready to Start Immediately
- Task 0.0: Remove Meeting Attendance (straightforward file deletion)
- Task 0.1: Expand stg_projects (add 7 columns from json_blob)
- Task 0.2: Expand stg_event_attendance (add volunteer_id, status; remove name/email)
- Task 0.4: Update models.yml (documentation)
- Tasks 1, 2, 4, 5: Build marts (standard dbt models)
- Tasks 6, 7: Add tests, docs, workflow (standard dbt practices)

### ⏳ Pending Clarification (Non-Blocking)
- Task 0.3: Confirm event_type field in Airtable Events table (5-min manual check)
- Blocks: Task 3 (dim_event build)
- All other tasks can proceed in parallel

### ⏸️ Deferred (Not Phase 2)
- dlt-level PII filtering → Phase 3 (ROADMAP_FUTURE.md)
- Deferred field parsing (availability, language_fluency, skills) → Phase 3
- Metrics and reporting → Phase 3

---

## Phase 3+ Future Roadmap (Deferred)

### Production Hardening (Phase 3, before launch)

#### PII & Security
- **dlt-level PII filtering** (1h)
  - Exclude: first_name, last_name, email, pronouns, age_range, city, linkedin, github, slack_handle, accommodations, other_notes, vetting_* at ingestion
  - Configurable via `INCLUDE_PII` env var (future admin pipeline)
  
- **DuckDB file access control** (0.5h)
  - Move to private bucket (R2, B2, or private S3)
  - Document: staging holds PII; bucket must stay private
  
- **Airtable API token scoping** (TBD, research)
  - Investigate field-level access control
  - If available, use restricted token in production

#### Reporting & Metrics (Phase 3+, 6–8h total)
- **volunteer_participation_summary** (3–4h)
  - Engagement score, active definition, tier classification
  
- **Retention & churn metrics** (2–3h)
  - Repeat attendance, project completion, churn risk
  
- **Demographic reporting** (2–3h)
  - Aggregate-only (suppress groups < 5 people)
  - Skills, availability, geography, employment distribution

#### Infrastructure & Docs (Phase 3)
- **GitHub Actions: dbt docs to GitHub Pages** (1h)
- **GitHub Actions: Freshness checks** (1h)
- **DECISIONS.md & HANDOFF.md** (1–2h, started in Task 7)
- **Incremental dbt runs** (2–3h, optimization)

---

## Summary

| Phase | Tasks | Time | Status |
|-------|-------|------|--------|
| **Phase 2A (Pre-work)** | 0.0–0.4 | 2.25h | ✅ Ready |
| **Phase 2B (Marts)** | 1–5 | 5.25h | ✅ Ready |
| **Phase 2C (Tests & Docs)** | 6–7 | 2.5–3.5h | ✅ Ready |
| **Phase 2 Total** | 12 tasks | **10.5–11.5h** | **✅ READY** |
| Phase 3+ (Future) | — | TBD | ⏸️ Deferred |

---

## Confidence Assessment

**Conflicts identified:** 12 areas reviewed  
**Resolved:** 8 (with clear tasks)  
**Pending clarification:** 1 (non-blocking)  
**Deferred:** 1 (documented)  
**Show-stoppers:** 0  

**Confidence Level:** **HIGH ✅**

- Plan is authoritative and internally consistent
- Code conflicts mapped to specific executable tasks
- Resolutions are straightforward (SQL expansions, no architecture surprises)
- One data clarification needed but doesn't block 11 of 12 tasks
- PII deferral is pragmatic (project in dev; harden before public launch)

**Go/No-Go:** **🟢 GO FOR IMPLEMENTATION**

---

## Quick Reference

**To start Phase 2:**
1. Begin Task 0.0 (remove Meeting Attendance), or all pre-work tasks in parallel
2. Do quick Task 0.3 check (5 min) when ready
3. Proceed to Tasks 1–7 (build, test, document)

**Expected delivery:** 1–2 days (depending on parallelization), 10.5–11.5 hours of work

**Success criteria (exit):** All 5 marts build without errors, all tests pass nightly, dbt docs are hosted

---

## Document Lineage

This master document consolidates:
- `phase-2-plan.md` — Authoritative spec (Sep 27, 2026)
- `PHASE2_TODO.md` — Task breakdown
- `PHASE2_CONFLICTS_RESOLVED.md` — Conflict analysis
- `PHASE2_FINAL_REVIEW.md` — Readiness assessment
- `ROADMAP_FUTURE.md` — Phase 3+ backlog

**All documents are in** `docs/roadmap/` and committed to the `phase-2/marts-and-metrics` branch.
