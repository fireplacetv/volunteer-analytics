# Phase 2 Plan vs. Code: Conflicts & Resolutions

**Status:** Plan is authoritative. Code must align.

---

## Conflicts Found

### 1. Meeting Attendance Table (CRITICAL)
**Plan expects:** 5 Airtable tables (Volunteers, Projects, Project volunteers, Events, Event attendance)  
**Code has:** 6 tables (same + Meeting attendance)  

**Conflict:** Plan consolidates all attendance into Event attendance with event_id = 0 (monthly meetings). Meeting Attendance table doesn't exist in real schema.

**Resolution:** Remove artifacts (Task 0.0 in PHASE2_TODO.md)
- Delete `dbt/models/staging/stg_meeting_feedback.sql`
- Remove "Meeting attendance" from `dlt/airtable_pipeline/airtable_tables.json`
- Remove `meeting_attendance` source from `dbt/models/sources.yml`

**Status:** — Cleanup task ready

---

### 2. PII Exclusion (DEFERRED TO PHASE 3)
**Plan expects:** Exclude vetting_status, vetting_notes, internal_admin_notes at dlt level (lines 130-134)  
**Code does:** Stores everything in json_blob; no filtering

**Conflict:** Plan says exclude at dlt. Code doesn't. However, project is in dev (no public launch yet).

**Resolution:** DEFERRED — Move to Phase 3 (see ROADMAP_FUTURE.md)
- Phase 2 marts already exclude PII via SELECT (volunteer_id only, no names/emails)
- dlt-level filtering will be implemented before production launch
- Makes sense: no public exposure risk until after Phase 3 when Evidence site is deployed

**Status:** — Deferred to Phase 3; not a Phase 2 blocker

---

### 3. Staging Layer Incomplete
**Plan expects dim_volunteer to have:**
- status, joined_date, source, employment_status, hours_per_month
- availability[], language_fluency[], nonprofit_skills[], tech_skills[], skills_to_develop[], roles_interested_in[]
- has_board_leadership_experience, has_grant_writing_experience

**Code has:** Most of these extracted but with name mismatches (e.g., tech_languages_tools vs. tech_skills)

**Conflict:** Field names don't match plan. Some expected fields not extracted.

**Resolution:** Expand staging models (Tasks 0.1–0.4 in PHASE2_TODO.md)
- stg_projects: extract name, status, dates, stakeholder (currently only project_id)
- stg_event_attendance: extract volunteer_id link, status (currently missing)
- Rename/normalize fields to match plan schema
- Update models.yml to reflect actual extractable fields

**Status:** — Pre-work tasks ready

---

### 4. Bridge Table Logic (MEDIUM)
**Plan design:** Array expansion happens in mart models (fct_project_volunteer), not staging  
**Code state:** stg_project_volunteers only extracts join_id; no array expansion documented

**Conflict:** Staging is minimalist; array logic deferred to marts. PHASE1_STATUS.md claims "dbt extracts arrays" but code doesn't show it.

**Resolution:** This is correct by plan design.
- Staging stores raw json_blob with linked arrays (1:1 with Airtable)
- Fact model (fct_project_volunteer) expands arrays using `json_extract_string(json_blob, '$.volunteer_id[0]')` etc.
- Update models.yml to document this design (Task 0.5)

**Status:** — Design confirmed; no code change needed for staging

---

### 5. Field Naming (event_type vs. event_status)
**Plan expects:** `event_type` with values (Monthly meeting / CityCamp / Community event / Other)  
**Code has:** `event_status` in stg_events

**Conflict:** Field name mismatch. Plan may expect event category (type), not lifecycle status.

**Resolution:** Verify in Airtable (Task 0.3 in PHASE2_TODO.md)
- Check Events table field names and values
- If field is called "type" with event categories → rename in staging to `event_type`
- If called "status" with lifecycle values → clarify with plan/use differently
- Update dim_event SQL accordingly

**Status:** — Data review task pending

---

### 6. models.yml Out of Sync (LOW)
**Plan expectations:** Accurate schema documentation for 5 staging models  
**Code state:** models.yml describes different columns than actual SQL

**Conflict:** Documentation misleading. Example:
- models.yml lists stg_volunteers columns as: id, email, name, created_time
- Actual stg_volunteers.sql extracts ~30 columns (first_name, last_name, email, state, timezone, etc.)

**Resolution:** Update models.yml (Task 0.4 in PHASE2_TODO.md)
- Document all extracted fields
- Mark deferred fields (Phase 3 metrics)
- Link to plan schema tables for reference

**Status:** — Documentation task ready

---

## Summary Table

| Conflict | Severity | Plan says | Code has | Resolution | Task | Status |
|----------|----------|-----------|----------|------------|------|--------|
| Meeting Attendance | CRITICAL | 5 tables | 6 tables | Remove artifact | 0.0 | Ready |
| PII at dlt | DEFERRED | Excluded | Not excluded | Filter in Phase 3 | — | Deferred |
| Staging incomplete | HIGH | Full schema | Partial schema | Expand stg_*.sql | 0.1–0.2 | Ready |
| Field names | MEDIUM | event_type | event_status | Verify/rename | 0.3 | Pending |
| models.yml | LOW | 5 tables documented | Outdated | Update docs | 0.4 | Ready |
| Array expansion | INFO | Mart layer | Mart layer ✓ | Confirm design | 0.4 | Confirmed |

---

## What's Ready to Build

Once Tasks 0.0–0.5 are done (code cleanup + staging alignment), the plan's 5 models are buildable:

**Dimensions (no dependencies):**
- `dim_volunteer` (from expanded stg_volunteers)
- `dim_project` (from expanded stg_projects)  
- `dim_event` (from stg_events; synthetic row 0 if needed)

**Facts (depend on dims):**
- `fct_attendance` (from expanded stg_event_attendance + stg_events)
- `fct_project_volunteer` (from stg_project_volunteers; arrays exploded in SQL)

**Tests & Docs:**
- Generic tests: not_null, unique, relationships, accepted_values (with warn severity)
- Singular tests: no duplicates, no future dates, warn on orphaned rows
- dbt docs: every model and column described, published to GitHub Pages

---

## Reference

- **Plan details:** See `phase-2-plan.md` (lines 39–158 for schemas)
- **Implementation plan:** See `PHASE2_TODO.md` (12 tasks, 10.5–11.5h)
- **Future roadmap:** See `ROADMAP_FUTURE.md` (Phase 3+: PII filtering, metrics, docs, CI/CD)
- **Conflict analysis:** See `phase2-conflicts.md` (original detailed report)

**Next step:** Start Task 0.0 (remove Meeting Attendance), or begin in parallel if confident on other tasks.

---

## What Changed (Project in Dev)

**PII conflict moved from CRITICAL to DEFERRED:**
- Was flagged as must-fix for Phase 2 (per original plan)
- But project hasn't launched yet; no public exposure risk
- Marts already exclude PII via SELECT
- dlt-level filtering will be done in Phase 3 before production launch
- Pragmatic: focus Phase 2 on building marts correctly; harden for launch later
