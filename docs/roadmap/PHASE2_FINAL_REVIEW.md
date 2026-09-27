# Phase 2 Final Review: Plan vs. Codebase

**Date:** Sep 27, 2026  
**Status:** Ready for implementation. All conflicts identified and resolved or deferred.

---

## Executive Summary

✅ **Plan is authoritative. Code alignment strategy determined.**

| Category | Count | Status |
|----------|-------|--------|
| Conflicts identified | 6 | — |
| Resolved in Phase 2 | 4 | Ready |
| Deferred to Phase 3 | 1 | Documented |
| Pending clarification | 1 | Task 0.3 |

**Phase 2 scope:** 12 tasks, 10.5–11.5 hours. Start with cleanup (Task 0.0), then pre-work (0.1–0.4), then build 5 marts (1–5), then test + doc (6–7).

---

## Detailed Conflict Review

### 1. ✅ Entry Criteria: Five Staging Tables
**Plan says:**
> Staging models exist 1:1 for the five Airtable tables: Volunteers, Projects, Project volunteers, Events, Event attendance

**Code has:** 6 staging models (same + stg_meeting_feedback)

**Conflict:** Extra Meeting Attendance table doesn't exist in real Airtable schema.

**Resolution:** ✅ RESOLVED (Task 0.0)
- Delete `stg_meeting_feedback.sql`
- Remove "Meeting attendance" from `airtable_tables.json`
- Remove `meeting_attendance` from `sources.yml`
- Verify dbt run/test passes with 5 sources

**Status:** Ready to execute

---

### 2. ✅ Model Design: Five Marts (3 dims + 2 facts)
**Plan says:**
> Phase 2 builds five models straight from staging: dim_volunteer, dim_project, dim_event, fct_attendance, fct_project_volunteer

**Code has:** No mart models yet (correct, Phase 2 will build them)

**Conflict:** None—this is the work to be done.

**Status:** ✅ No conflict

---

### 3. ✅ Schema: dim_volunteer Columns
**Plan specifies 17 columns** (lines 47–62):
- volunteer_id, status, joined_date, source, employment_status, hours_per_month
- availability[], state, timezone, language_fluency[], nonprofit_skills[], tech_skills[], skills_to_develop[], roles_interested_in[]
- has_board_leadership_experience, has_grant_writing_experience
- Plus: airtable_created_at, airtable_modified_at

**Code has (stg_volunteers):**
- Extracts ~30 fields including first_name, last_name, email, state, timezone, employment_status, hours_per_month, joined_date
- Has tech_languages_tools (not tech_skills), nonprofit_experience_level (not nonprofit_skills), project_interests (not roles_interested_in)
- Missing: source, availability, language_fluency, nonprofit_skills (as array), tech_skills (as array), skills_to_develop, roles_interested_in

**Conflict:** Field name mismatches. Some expected fields not extracted. Deferred fields need parsing.

**Resolution:** ✅ RESOLVED (Tasks 0.1–0.4)
- Task 0.1: Expand stg_volunteers to extract/rename fields matching plan
- Task 0.4: Update models.yml to document deferred fields (Phase 3 parsing)
- Build dim_volunteer (Task 1) to include only Phase 2 scope (exclude deferred)

**Note:** Deferred fields (availability[], language_fluency[], nonprofit_skills[], etc.) are extracted in staging but deferred to Phase 3 for normalization and metrics.

**Status:** Ready to execute

---

### 4. ✅ Schema: dim_project Columns
**Plan specifies 8 columns** (lines 70–77):
- project_id, project_number, project_name, status, stakeholder, description, start_date, end_date
- Plus: airtable_created_at, airtable_modified_at

**Code has (stg_projects):**
- Only extracts: id, created_time, last_modified, project_id (4 columns!)

**Conflict:** Staging is a stub; most fields not extracted.

**Resolution:** ✅ RESOLVED (Task 0.1)
- Expand stg_projects.sql to extract: project_number, project_name, status, stakeholder, description, start_date, end_date
- Build dim_project (Task 2) from expanded staging

**Status:** Ready to execute

---

### 5. ✅ Schema: dim_event Columns
**Plan specifies 9 columns** (lines 83–89):
- event_id, airtable_record_id, event_name, event_type, event_date, description, is_monthly_meeting
- Plus: airtable_created_at, airtable_modified_at

**Code has (stg_events):**
- Extracts: id, created_time, last_modified, event_id, name, event_date, description, location, event_status, check_in_url, qr_code, created_by_*

**Conflict:** `event_status` in staging, but plan expects `event_type` (different semantics).

**Resolution:** ⏳ CLARIFICATION NEEDED (Task 0.3)
1. Check Airtable Events table: What field holds event category (CityCamp, Community event, Monthly meeting, Other)?
   - If it's called "type" → extract as event_type
   - If it's called "status" with lifecycle values → clarify with plan
2. Update stg_events to extract the correct field with the correct name
3. Build dim_event (Task 3) from clarified staging

**Status:** Task 0.3 pending

**Assumption for Task 3:** Field is either correctly named or will be renamed during pre-work.

---

### 6. ✅ Schema: fct_attendance Columns
**Plan specifies 10 columns** (lines 97–104):
- attendance_id, volunteer_id, event_id, is_monthly_meeting, occasion_type, occasion_date, status, is_present
- Plus: airtable_created_at, airtable_modified_at

**Code has (stg_event_attendance):**
- Extracts: id, created_time, last_modified, attendance_id, event_id, date, name, email (8 columns)
- Missing: volunteer_id link, status field

**Conflict:** No volunteer_id FK, no status field. Has attendee PII (name, email) which shouldn't be in fact.

**Resolution:** ✅ RESOLVED (Task 0.2)
- Expand stg_event_attendance to extract: volunteer_id (from linked record), status
- Remove from staging: name, email (PII; not database keys)
- Build fct_attendance (Task 4) with monthly-meeting date logic (event_id=0 → occasion_date from attendance.date)

**Status:** Ready to execute

---

### 7. ✅ Schema: fct_project_volunteer Columns
**Plan specifies 13 columns** (lines 110–122):
- join_id, volunteer_id, project_id, role, commitment_date, end_date, status, outreach_attempt_count, first_outreach_date, last_outreach_date, last_outreach_status, is_declined, decline_reason
- Plus: airtable_created_at, airtable_modified_at

**Code has (stg_project_volunteers):**
- Only extracts: id, created_time, last_modified, join_id (4 columns!)
- All other fields in json_blob as arrays (to be expanded in mart)

**Conflict:** Staging is minimal; array expansion deferred to mart layer (correct per design).

**Resolution:** ✅ RESOLVED (Plan design + Tasks 0.4, 5)
- Staging stores raw json_blob with arrays (1:1 with Airtable) ✓
- Task 0.4: Document this design in models.yml
- Task 5: Build fct_project_volunteer with inline array expansion using json_extract_string
- Mart extracts arrays: volunteer_id[0], project_id[0], outreach_1_date, outreach_2_date, outreach_3_date, etc.

**Status:** ✅ Design confirmed; no staging change needed

---

### 8. ⏸️ PII Exclusion (Originally CRITICAL)
**Plan says** (lines 130–134):
> Exclude `vetting_status`, `vetting_notes` and `internal_admin_notes` in the dlt resource so they never reach DuckDB.
> Marts carry `volunteer_id` only: no names, emails, profile links, race, age range or accommodations.

**Code has:**
- dlt stores everything in json_blob; no filtering
- stg_volunteers extracts first_name, last_name, email, city, linkedin, github, slack_handle, accommodations, etc.

**Conflict:** Plan says exclude at dlt; code doesn't. However, project in dev (no public launch).

**Resolution:** ⏸️ DEFERRED TO PHASE 3 (See ROADMAP_FUTURE.md)
- Phase 2 marts exclude PII via SELECT (volunteer_id only, no names/demographics)
- dlt-level filtering will be implemented in Phase 3 before production launch
- Rationale: No immediate public exposure risk; focus Phase 2 on building marts correctly

**Status:** Not a Phase 2 blocker

---

### 9. ✅ Testing Strategy
**Plan requires** (lines 140–152):
- `not_null` + `unique` on every dim and fact key
- `relationships` tests on FKs
- `accepted_values` on status/occasion_type (warn severity)
- Singular tests: no duplicate check-ins, no future dates, warn on orphaned attendance

**Code has:**
- staging tests exist (not_null, unique, relationships) ✓
- No mart tests yet (correct, Phase 2 will add them)

**Conflict:** None—tests will be built in Phase 2.

**Resolution:** ✅ RESOLVED (Task 6)
- Create `dbt/tests/marts_tests.yml` with all generic tests
- Create singular test files (.sql): no_duplicate_attendance, no_future_attendance, warn_orphaned_*

**Status:** Ready to execute

---

### 10. ✅ Documentation
**Plan requires** (lines 154–157):
- Description on every model and column
- `dbt docs generate` runs in nightly workflow
- Docs published to GitHub Pages

**Code has:**
- No mart models yet (correct, Phase 2 will build them)
- Workflow may or may not have dbt docs step (unclear)

**Conflict:** None—docs will be built and wired up in Phase 2.

**Resolution:** ✅ RESOLVED (Task 7)
- Create `dbt/models/marts/models.yml` with descriptions
- Add/update `dbt docs generate` in GitHub Actions workflow
- Update `DECISIONS.md` and `HANDOFF.md` (or create if missing)

**Status:** Ready to execute

---

### 11. ✅ Entry Criteria: Phase 1 Complete
**Plan assumes:**
> - Staging models exist 1:1 for five Airtable tables
> - Linked-record fields are resolved into bridge tables
> - not_null, unique and relationships tests pass

**Code status:**
- PHASE1_STATUS.md says Phase 1 is complete ✓
- 6 staging models exist (1 extra to be removed) ✓
- Bridge table logic claims to be done, but stg_project_volunteers is minimal (design correct) ✓
- Tests pass ✓

**Conflict:** None—Phase 1 complete, ready for Phase 2.

**Status:** ✅ Entry criteria met

---

### 12. ✅ Exit Criteria: Phase 2 Success
**Plan defines success as:**
> - dim_volunteer, dim_project, dim_event, fct_attendance, fct_project_volunteer build and pass tests nightly
> - Internal-only and identifying fields are excluded from every mart
> - dbt docs are generated in CI and hosted

**Code status:**
- No mart models yet (will be built in Phase 2)
- No mart tests yet (will be added in Phase 2)
- No dbt docs for marts yet (will be added in Phase 2)

**Conflict:** None—Phase 2 is the work to achieve these criteria.

**Status:** Exit criteria are the Phase 2 deliverables

---

## Conflict Summary Table

| # | Conflict | Severity | Status | Resolution | Task(s) |
|---|----------|----------|--------|-----------|---------|
| 1 | Meeting Attendance table exists | CRITICAL | ✅ Resolved | Delete artifact | 0.0 |
| 2 | stg_projects incomplete | HIGH | ✅ Resolved | Expand + build dim | 0.1, 2 |
| 3 | stg_event_attendance missing FK/status | HIGH | ✅ Resolved | Expand + build fact | 0.2, 4 |
| 4 | stg_volunteers field mismatches | MEDIUM | ✅ Resolved | Normalize + build dim | 0.1, 1 |
| 5 | event_type vs. event_status | MEDIUM | ⏳ Pending | Clarify in Airtable | 0.3 |
| 6 | models.yml out of sync | LOW | ✅ Resolved | Update docs | 0.4 |
| 7 | No mart tests yet | — | ✅ Resolved | Add tests | 6 |
| 8 | No mart docs yet | — | ✅ Resolved | Add docs | 7 |
| 9 | PII at dlt level | DEFERRED | ⏸️ Deferred | Phase 3 | ROADMAP_FUTURE |
| 10 | stg_project_volunteers minimal | INFO | ✅ Correct | Array expansion in marts | 5 |

---

## Implementation Readiness

### ✅ Ready Now
- Task 0.0: Remove Meeting Attendance (straightforward deletion)
- Task 0.1: Expand stg_projects (add 7 columns from json_blob)
- Task 0.2: Expand stg_event_attendance (add volunteer_id, status; remove name/email)
- Task 0.4: Update models.yml (documentation)
- Tasks 1–7: Build marts, tests, docs (standard dbt work)

### ⏳ Needs Clarification First
- Task 0.3: Confirm event_type field in Airtable Events table
  - Required before building Task 3 (dim_event)
  - Quick 15-min manual check in Airtable
  - Can proceed with other tasks in parallel while waiting

### ⏸️ Deferred (Not Phase 2)
- PII filtering at dlt level → Phase 3 (ROADMAP_FUTURE.md)
- Deferred field parsing (availability, language_fluency, tech_skills, etc.) → Phase 3

---

## Confidence Level

**HIGH ✅**

- All conflicts identified
- Clear resolutions for each
- One clarification needed (Task 0.3) but non-blocking for most work
- Plan is internally consistent and achievable
- Code alignment path is clear

**Go/No-Go:** GO for Phase 2 implementation

---

## Next Steps

1. **Immediate:** Execute Task 0.0 (remove Meeting Attendance artifacts)
2. **Parallel:** Execute Tasks 0.1, 0.2, 0.4 (expand staging, update docs)
3. **Quick pause:** Task 0.3 (5-min Airtable check for event_type field)
4. **Build:** Tasks 1–7 (marts, tests, docs)
5. **Deliver:** All 5 marts + tests + GitHub Pages docs

**Estimated timeline:** 10.5–11.5 hours wall-clock, 1–2 days depending on parallelization.

---

## Reference Documents

- `phase-2-plan.md` — Authoritative spec (Sep 27, 2026)
- `PHASE2_TODO.md` — Detailed task breakdown (12 tasks)
- `PHASE2_CONFLICTS_RESOLVED.md` — Conflict-by-conflict resolution
- `ROADMAP_FUTURE.md` — Deferred work (Phase 3+)
- `PHASE2_FINAL_REVIEW.md` — This document
