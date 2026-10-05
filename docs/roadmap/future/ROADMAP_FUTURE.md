# Volunteer Analytics — Future Roadmap

**Status:** Project in development. Not yet launched. Backlog of work that doesn't block Phase 2 but should be done before production.

---

## Phase 3: Production Hardening & Reporting

### PII & Security

#### [x] Implement dlt-level PII filtering
**Status:** Done. Implemented as a per-table allowlist with keyed-hash and fake-name pseudonymization rather than an `INCLUDE_PII` blocklist; see "PII Handled at dlt Ingestion" in DECISIONS.md. The notes below are the original plan.

**Priority:** HIGH (before public launch)  
**When:** Phase 3, before Evidence site deployment

Exclude sensitive fields at Airtable ingestion:
- **Volunteers table:** first_name, last_name, email, pronouns, age_range, city, linkedin, github, website_portfolio, slack_handle, accommodations, other_notes, vetting_status, vetting_notes, internal_admin_notes
- **Event attendance:** Name, Email (attendee fields)
- **Project volunteers:** notes (internal-only free text)

**Why:** PII never reaches DuckDB if it's not ingested. Prevents accidental exposure if DuckDB file is shared/backed up.

**Design:** Make configurable via `INCLUDE_PII` env var:
- **Production (public Evidence site):** Run with `INCLUDE_PII=false` → no PII in DuckDB
- **Admin analysis (future):** Run with `INCLUDE_PII=true` → separate restricted DuckDB for demographic reporting

**Implementation:**
```python
# In airtable_source.py
PII_EXCLUSIONS = {
    "Volunteers": [...list of fields...],
    "Event attendance": ["Name", "Email"],
    "Project volunteers": ["notes"]
}

# When yielding records:
if not INCLUDE_PII:
    excluded = PII_EXCLUSIONS.get(table_name, [])
    filtered_fields = {k: v for k, v in fields.items() if k not in excluded}
else:
    filtered_fields = fields

yield {
    "id": record["id"],
    "json_blob": json.dumps(filtered_fields),
    ...
}
```

**Estimate:** 1h  
**Depends on:** Phase 2 complete (marts stable)  
**Blocks:** Evidence site deployment to public URL

---

#### [ ] DuckDB file access control
**Priority:** HIGH (before launch)  
**When:** Phase 3

- Restrict DuckDB file to private bucket (R2, B2, or private S3)
- Document: DuckDB holds staging-level PII; bucket must remain private
- Set up read-only access for Evidence (if Evidence runs separately)

**Estimate:** 0.5h  
**Depends on:** Infrastructure decisions (R2 vs. B2 vs. S3)

---

#### [ ] Airtable API token scoping (optional, defense-in-depth)
**Priority:** MEDIUM (nice-to-have)  
**When:** Phase 3 or later

Research: Can we scope the Airtable API token to exclude PII fields?
- If Airtable supports field-level access control: create a restricted token for production
- Use restricted token in production, unrestricted in dev

**Estimate:** TBD (research phase)  
**Depends on:** Airtable plan capabilities

---

### Reporting & Metrics

#### [ ] Build volunteer_participation_summary
**Priority:** MEDIUM  
**When:** Phase 3+

Aggregate metric: volunteers' event attendance, project involvement, engagement score.

**Depends on:** fct_attendance, fct_project_volunteer (Phase 2)

**Design notes:**
- Active volunteer definition (how many events/projects in last 90 days?)
- Engagement tiers (active, occasional, inactive)
- Retention: repeat attendees vs. one-time

**Estimate:** 3-4h

---

#### [ ] Build retention & churn metrics
**Priority:** MEDIUM  
**When:** Phase 3+

- Repeat attendance rate (same volunteer, multiple events)
- Project completion rate (volunteers who completed projects vs. departed)
- Churn risk: volunteers with no activity in last 180 days

**Depends on:** fct_attendance, fct_project_volunteer (Phase 2)

**Estimate:** 2-3h

---

#### [ ] Demographic reporting (aggregate-only)
**Priority:** MEDIUM  
**When:** Phase 3+

Create a restricted reporting layer for aggregate demographics:
- Skills distribution (what skills do volunteers have? what are they developing?)
- Availability patterns (when can volunteers help?)
- Geographic spread (states, timezones)
- Employment status breakdown

**Design constraints:**
- Aggregates only, no individual data
- Suppress any group under 5 people
- Never expose PII or vetting status
- Separate model from public marts (access-controlled)

**Depends on:** Deferred fields in stg_volunteers (availability, language_fluency, nonprofit_skills, tech_skills, skills_to_develop, roles_interested_in)

**Estimate:** 2-3h (once deferred fields are parsed)

---

### Infrastructure & CI/CD

#### [ ] GitHub Actions: dbt docs generation and hosting
**Priority:** HIGH  
**When:** Phase 2 / Phase 3

Add `dbt docs generate` to nightly workflow and publish to GitHub Pages.

**Blocked by:** Phase 2 (need models to document)  
**Estimate:** 1h

---

#### [ ] GitHub Actions: freshness checks
**Priority:** MEDIUM  
**When:** Phase 2 / Phase 3

Add source freshness checks to catch failed dlt loads:
- Alert if dlt hasn't loaded data in >36 hours
- Test: Check `max(dlt_load_timestamp)` in staging tables

**Estimate:** 1h

---

#### [ ] Incremental dbt runs (optimization)
**Priority:** LOW  
**When:** Phase 3+

Optimize nightly runs to only reprocess changed records (use dlt state).

**Current:** Full refresh of all staging + all marts  
**Future:** Only staging rows with `last_modified > cursor`, then cascade to affected facts

**Estimate:** 2-3h

---

### Documentation

#### [ ] Create DECISIONS.md
**Priority:** MEDIUM  
**When:** Phase 2 / Phase 3

Document design decisions:
- Why event_id = 0 for monthly meetings (not separate table)
- Why array expansion in marts, not staging
- Why volunteer_id only in public marts (no names/demographics)
- Why vetting fields excluded entirely (never ingested)

**Estimate:** 1-2h

---

#### [ ] Create HANDOFF.md
**Priority:** MEDIUM  
**When:** Phase 3 (before launch)

Runbook for operations team:
- How to run the pipeline
- Common troubleshooting (missing fields, new Airtable options)
- How to onboard a second person to the pipeline
- Dependencies on Airtable schema (which fields can't be renamed without breaking pipeline?)

**Estimate:** 2h

---

### Nice-to-Have (Phase 3+)

#### [ ] dbt macros for common patterns
- Checkbox to boolean coercion (null → false)
- Outreach date/status derivation (already in fct_project_volunteer, could generalize)
- Array expansion helpers

**Estimate:** 2h

---

#### [ ] Data quality dashboards
- Count of orphaned attendance (no volunteer_id)
- Count of duplicate check-ins (same volunteer + event + date)
- Trend: new volunteers per month, event attendance trends

**Estimate:** 3h

---

#### [ ] Airtable automations
- Auto-set `joined_date` when status changes to Active
- Auto-fill check-in date on Event attendance (prevent null occasion_date)
- Auto-increment `project_id` if not already done

**Estimate:** 2h (Airtable-side, not pipeline)

---

## Phase 4+: Advanced Analytics

- Volunteer skills matching (recommend volunteers for projects based on skills)
- Event recommendation engine
- Project success prediction (which projects complete on time?)
- Network analysis (who works together?)

---

## Decisions Made (Dev Phase)

✅ **PII deferral:** Since project hasn't launched, dlt-level PII filtering deferred to Phase 3. Staging layer can hold PII; marts exclude it (SELECT columns only). When preparing for public/production launch, implement dlt filtering.

✅ **Airtable API token:** Currently using unrestricted token (dev mode is fine). Phase 3 will scope it before production.

✅ **DuckDB privacy:** Currently local file. Phase 3 will move to private cloud bucket before launch.

---

## Timeline Assumptions

- **Phase 2:** Now (build marts, ~11-13h)
- **Phase 3:** When ready to launch (hardening, docs, GitHub Pages, ~1-2 weeks)
- **Phase 4+:** Post-launch (advanced analytics, ongoing optimization)

**Note:** This timeline is flexible. If launch is delayed, we can pull forward Phase 3 work.
