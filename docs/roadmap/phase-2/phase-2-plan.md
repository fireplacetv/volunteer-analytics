# Volunteer Analytics — Phase 2 Plan: Marts & Metrics

Sep 27, 2026 · @Derrick Low

## Summary

Phase 2 builds the basic dimensional model: three dimension tables and two fact tables, tested and documented. It is done when every Airtable table in the volunteer system maps to a clean, ID-keyed dim or fact that later reporting can join without touching staging.

**Entry criteria (from Phase 1)**

- Staging models exist 1:1 for the five Airtable tables: Volunteers, Projects, Project volunteers, Events, Event attendance
- Linked-record fields are resolved into bridge tables
- `not_null`, `unique` and `relationships` tests pass in the nightly GitHub Actions run

**Exit criteria**

- [ ] `dim_volunteer`, `dim_project`, `dim_event`, `fct_attendance` and `fct_project_volunteer` build and pass tests nightly
- [ ] Internal-only and identifying fields are excluded from every mart
- [ ] dbt docs are generated in CI and hosted

**Deferred to a later phase:** `volunteer_participation_summary`, the "active volunteer" definition, retention and repeat-attendance metrics. The facts built here carry the raw columns those metrics will need.

## Model design

Phase 2 builds five models straight from staging, with no intermediate layer, and each staging table maps to exactly one dim or fact. All attendance lives in Event attendance: monthly meetings are recorded there with `event_id` = 0, so `fct_attendance` reads one source and joins `stg_events` only for event type and date.

&#91;embedded content: dbt lineage for Phase 2 · 6 staging, 2 intermediate, 4 mart models\]

Each Airtable table becomes one dim or fact, keyed on its Airtable record ID so later marts can join without going back to staging.

| Model | One row per | Key | Built from |
| --- | --- | --- | --- |
| `dim_volunteer` | volunteer | `volunteer_id` | `stg_volunteers` |
| `dim_project` | project | `project_id` | `stg_projects` |
| `dim_event` | event (row 0 = monthly meetings) | `event_id` | `stg_events` |
| `fct_attendance` | Event attendance row | `attendance_id` | `stg_event_attendance`, `stg_events` |
| `fct_project_volunteer` | Project volunteers row | `join_id` | `stg_project_volunteers` |

### Schemas

Types are DuckDB types. Multiple-select fields land as `varchar[]`. Every model also carries `airtable_created_at` and `airtable_modified_at` (`timestamp`) for auditing and incremental loads; they are left out of the tables below.

**dim\_volunteer**

| Column | Type | Source field | Notes |
| --- | --- | --- | --- |
| `volunteer_id` | `varchar` | record ID | Primary key |
| `status` | `varchar` | `status` | Pending / Active / Inactive / Alumni |
| `joined_date` | `date` | `joined_date` | Admin-set on activation; null while Pending |
| `source` | `varchar` | `source` | CityCamp Oakland / Meetup / Community event / Word of mouth / Social media / Other |
| `employment_status` | `varchar` | `employment_status` |  |
| `hours_per_month` | `varchar` | `hours_per_month` | Self-reported band: 0–4 / 5–9 / 10–19 / 20–39 / 40+ |
| `availability` | `varchar[]` | `availability` |  |
| `state` | `varchar` | `state` |  |
| `timezone` | `varchar` | `timezone` |  |
| `language_fluency` | `varchar[]` | `language_fluency` |  |
| `nonprofit_skills` | `varchar[]` | `nonprofit_skills` |  |
| `tech_skills` | `varchar[]` | `tech_skills` |  |
| `skills_to_develop` | `varchar[]` | `skills_to_develop` |  |
| `roles_interested_in` | `varchar[]` | `roles_interested_in` |  |
| `has_board_leadership_experience` | `boolean` | `board_leadership_experience` | Null checkbox → false |
| `has_grant_writing_experience` | `boolean` | `grant_writing_experience` | Null checkbox → false |

Left out on purpose: names, email, pronouns, race, age range, city, profile links, Slack handle, all long-text answers, and the three vetting fields (which dlt never extracts). If demographic reporting is needed later, it gets its own restricted, aggregate-only model.

**dim\_project**

| Column | Type | Source field | Notes |
| --- | --- | --- | --- |
| `project_id` | `varchar` | record ID | Primary key |
| `project_number` | `integer` | `project_id` (Airtable auto ID) | Human-readable ID |
| `project_name` | `varchar` | `name` |  |
| `status` | `varchar` | `status` | Intake / Active / Complete / On hold |
| `stakeholder` | `varchar` | `stakeholder` | Partner org name |
| `description` | `varchar` | `description` |  |
| `start_date` | `date` | `start_date` |  |
| `end_date` | `date` | `end_date` | Null until the project is formally closed |

**dim\_event**

| Column | Type | Source field | Notes |
| --- | --- | --- | --- |
| `event_id` | `integer` | `event_id` (Airtable auto ID) | Primary key. 0 = monthly meetings |
| `airtable_record_id` | `varchar` | record ID | For tracing back to Airtable |
| `event_name` | `varchar` | `name` |  |
| `event_type` | `varchar` | `type` | Monthly meeting / CityCamp / Community event / Other |
| `event_date` | `date` | `event_date` | Null for row 0, which covers every monthly meeting |
| `description` | `varchar` | `description` |  |
| `is_monthly_meeting` | `boolean` | derived | True when `event_id` = 0 |

If Events has no actual row for ID 0, the model adds a fixed "Monthly meeting" row so the `relationships` test from `fct_attendance` passes.

**fct\_attendance**

| Column | Type | Source field | Notes |
| --- | --- | --- | --- |
| `attendance_id` | `varchar` | record ID | Primary key |
| `volunteer_id` | `varchar` | `volunteer_id` link | FK → `dim_volunteer` |
| `event_id` | `integer` | `event_id` link | FK → `dim_event`; 0 = monthly meeting |
| `is_monthly_meeting` | `boolean` | derived | True when `event_id` = 0 |
| `occasion_type` | `varchar` | event `type` | Via `stg_events` |
| `occasion_date` | `date` | attendance date, else event `event_date` | Monthly meetings share `event_id` = 0, so the date must come from the attendance row |
| `status` | `varchar` | `status` | Consolidated option list to confirm (was Attended / RSVP'd / No-show for events, Attended / Absent / Remote for meetings) |
| `is_present` | `boolean` | derived | True when status is Attended or Remote |

**fct\_project\_volunteer**

| Column | Type | Source field | Notes |
| --- | --- | --- | --- |
| `join_id` | `varchar` | record ID | Primary key |
| `volunteer_id` | `varchar` | `volunteer_id` link | FK → `dim_volunteer` |
| `project_id` | `varchar` | `project_id` link | FK → `dim_project` |
| `role` | `varchar` | `role` | Free text, e.g. UX Designer |
| `commitment_date` | `date` | `commitment_date` | Null for outreach-only rows |
| `end_date` | `date` | `end_date` |  |
| `status` | `varchar` | `status` | Active / Completed / Departed |
| `outreach_attempt_count` | `integer` | derived | 0–3: count of non-null `outreach_N_date` |
| `first_outreach_date` | `date` | `outreach_1_date` |  |
| `last_outreach_date` | `date` | derived | Latest non-null `outreach_N_date` |
| `last_outreach_status` | `varchar` | derived | Emailed / Responded / No response, from the latest attempt |
| `is_declined` | `boolean` | `declined` | Null checkbox → false |
| `decline_reason` | `varchar` | `decline_reason` |  |

Free-text `notes` fields on Event attendance and Project volunteers stay out of both facts, since they are internal.

Because every monthly meeting shares `event_id` = 0, the meeting date has to come from the attendance row itself. A missing date would make one meeting indistinguishable from another, so `occasion_date` gets a hard `not_null` test.

**Keep PII out of the marts.** Evidence builds a static site on Netlify or GitHub Pages, which is public unless access is restricted.

- Exclude `vetting_status`, `vetting_notes` and `internal_admin_notes` in the dlt resource so they never reach DuckDB
- Marts carry `volunteer_id` only: no names, emails, profile links, race, age range or accommodations
- Demographic breakdowns are aggregates only, with any group under 5 people suppressed
- Named follow-up lists stay in Airtable views, not in the report
- The DuckDB file in R2/B2 still holds staging-level PII, so the bucket stays private

## Testing and documentation

Tests should fail the nightly run only for pipeline bugs; data-entry problems from Airtable should warn, so one mistyped check-in doesn't block the build.

**Generic tests (schema.yml)**

- `unique` + `not_null` on every dim and fact key
- `relationships`: both facts' `volunteer_id` → `dim_volunteer`; `fct_attendance.event_id` → `dim_event`; `fct_project_volunteer.project_id` → `dim_project`
- `accepted_values` on every status field and `occasion_type`, set to `warn` so a new Airtable option flags without breaking the build

**Singular tests**

- No volunteer is counted present twice at the same event on the same date (catches duplicate check-ins)
- No `occasion_date` in the future
- Attendance rows with no linked volunteer: warn, with a count

**Freshness:** a source freshness check on the dlt load timestamp, warning after 36 hours without a successful load.

**Docs**

- A description on every model and every column
- `dbt docs generate` runs in the nightly workflow and publishes to GitHub Pages; the docs site shows SQL and column metadata only, no row data

## Work plan

Build the dims first so the facts' relationship tests have something to point at. Estimates total roughly 10–14 hours.

| # | Task | Depends on | Estimate |
| --- | --- | --- | --- |
| 1 | Build `dim_volunteer`; add the internal-only column exclusions to the dlt resource | Phase 1 | 2–3 h |
| 2 | Build `dim_project` | Phase 1 | 1 h |
| 3 | Build `dim_event` | Phase 1 | 1 h |
| 4 | Build `fct_attendance`, including the monthly-meeting date logic for event 0 | 1, 3 | 2–3 h |
| 5 | Build `fct_project_volunteer` | 1, 2 | 1–2 h |
| 6 | Add generic, singular and freshness tests | 4, 5 | 2 h |
| 7 | Write model docs, add `dbt docs` to the workflow, update `DECISIONS.md` and `HANDOFF.md` | 6 | 1–2 h |

## Risks and open questions

The biggest risk is volunteer PII ending up on a public static page once Phase 3 reporting reads these tables.

| Risk | Mitigation |
| --- | --- |
| PII or vetting notes reach the public Evidence site | Exclude internal-only fields at dlt; keep dims and facts ID-only |
| Monthly meeting rows missing a date collapse into one undated meeting | `not_null` on `occasion_date` (error), plus a check-in form that always sets the date |
| Admins rename Airtable fields or add select options | `accepted_values` on warn; note the dependency in `HANDOFF.md` |

**Open questions**

- [ ] Which Event attendance field holds the date for monthly meetings (`event_id` = 0), and is it always filled?
- [ ] What is the consolidated status option list on Event attendance?
- [ ] Will the Evidence site be public or access-restricted? This sets how much the marts may expose
- [ ] Model the 3 special events as rows in the existing Events table? The volunteer system schema already supports this with the CityCamp and Community event types
- [ ] Who is the second person with full access to run and debug the pipeline?
