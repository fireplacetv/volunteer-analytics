# Phase 1 Plan — Core Pipeline
**Project:** Open Oakland Volunteer Analytics Platform
**For:** Claude Code
**Prereq:** Phase 0 complete (repo scaffolded, Airtable access confirmed, dlt pipeline does a full local load into DuckDB, `docs/SETUP.md` exists and works from a clean clone)

## Scope

Phase 1 is **local only**. No deployment, no hosting, no GitHub Actions automation yet (that's Phase 3). Everything here should run and be verifiable on a developer's own machine.

Everything in this phase runs inside Docker. This is a deliberate portability choice: a new volunteer should be able to clone the repo, run one command, and have a working environment — without installing Python, dlt, dbt, or matching versions of anything by hand. Docker Desktop (or Docker Engine + Compose) is the only prerequisite.

By the end of Phase 1:
- The whole pipeline (dlt + dbt) runs via `docker compose`, no local Python install required
- dlt does incremental (not full) loads on every table
- Linked-record fields are flattened into clean bridge tables
- dbt staging models exist 1:1 with source tables
- Basic dbt tests pass (`not_null`, `unique`, `relationships`)

Tables in scope: Volunteers, Projects, Project volunteers, Events, Event attendance, Meeting attendance.

---

## Step 0 — Containerize the dev environment

**Prompt:**
> Add a `Dockerfile` and `docker-compose.yml` at the repo root that containerize this project's Python environment (dlt + dbt-duckdb + dependencies from `dlt/airtable_pipeline/requirements.txt` and `dbt/requirements.txt`). Mount the repo as a volume so edits made on the host are reflected live. Persist the DuckDB file (`dlt/airtable_pipeline/volunteer_data.duckdb`) on the host filesystem, not just inside the container, so it survives container rebuilds. Load Airtable credentials from a gitignored `.env` file via `env_file` in Compose — don't bake secrets into the image. Update `docs/SETUP.md` to document `docker compose build` and `docker compose run --rm dev bash` as the only setup steps a new volunteer needs.

**Checkpoint before moving on:**
- [ ] `docker compose build` succeeds from a completely clean clone (no pre-existing local Python env, no cached pip packages)
- [ ] `docker compose run --rm dev bash` drops into a shell where `python`, `dlt`, and `dbt` are all on PATH
- [ ] Editing a file on the host (e.g. in your normal editor) is immediately visible inside the container
- [ ] The `.duckdb` file written inside the container shows up on the host filesystem afterward, and survives `docker compose down`
- [ ] `.env` is gitignored; confirm with `git check-ignore .env`
- [ ] `docs/SETUP.md` now reads correctly for someone who has never installed Python locally — the only prerequisite is Docker

---

## Step 1 — Incremental loads

**Prompt:**
> Update the dlt resources in `dlt/airtable_pipeline/airtable_source.py` to use incremental merge loads keyed on each table's `Last Modified` field, so re-running the pipeline only pulls changed records instead of doing a full reload every time. Run and verify this inside the container, not on the host.

**Checkpoint before moving on:**
- [ ] Inside the container, run the pipeline twice back-to-back with no changes in Airtable — second run completes fast and touches ~0 rows
- [ ] Edit one record in Airtable, re-run inside the container — only that record updates in DuckDB
- [ ] Confirm no duplicate rows were created by the merge logic
- [ ] Confirm the updated `.duckdb` file is visible on the host after the container run exits

---

## Step 2 — Bridge tables for linked records

**Prompt:**
> Airtable's linked-record fields are currently loading as arrays of record IDs. Add dlt logic to flatten these into clean many-to-many bridge tables in DuckDB, matching the Project volunteers, Event attendance, and Meeting attendance junction tables described in the PRD's Data Schema section.

**Checkpoint before moving on:**
- [ ] Query each bridge table directly from inside the container (e.g. `docker compose run --rm dev duckdb dlt/airtable_pipeline/volunteer_data.duckdb`)
- [ ] Pick one volunteer known to be on 2+ projects — confirm the bridge table has exactly that many rows for them, with correct project references (not raw record-ID strings)
- [ ] Same spot-check for one volunteer with multiple event/meeting attendance records

---

## Step 3 — dbt staging models

**Prompt:**
> Set up a dbt-duckdb project in `dbt/`, pointed at the pipeline's DuckDB file (path resolved correctly from inside the container). Create one staging model per source table (1:1, light cleanup only — renaming, type casting, no business logic yet) in `dbt/models/staging/`.

**Checkpoint before moving on:**
- [ ] `docker compose run --rm dev dbt run` completes with no errors
- [ ] Row counts in each `stg_*` model exactly match the corresponding raw source table (no silent drops or duplicates)
- [ ] `dbt`'s `profiles.yml` uses a path to the DuckDB file that works inside the container (not a host-only absolute path)

---

## Step 4 — dbt tests

**Prompt:**
> Add dbt tests: `not_null` and `unique` on every table's primary key, and `relationships` tests on the foreign keys linking Project volunteers → Volunteers/Projects, Event attendance → Volunteers/Events, and Meeting attendance → Volunteers.

**Checkpoint before moving on:**
- [ ] `docker compose run --rm dev dbt test` passes clean
- [ ] Any `relationships` test failure is treated as a real Airtable data-quality issue (an orphaned link) to flag to the base owner — not silently fixed by deleting the test

---

## Definition of done for Phase 1

- [ ] `docker compose build && docker compose run --rm dev bash -c "dbt run && dbt test"` passes clean from a fresh clone, on a machine with nothing installed but Docker
- [ ] Incremental loads verified working (Step 1 checkpoint)
- [ ] Bridge tables correctly represent all many-to-many relationships in the PRD schema
- [ ] `docs/SETUP.md` reflects the Docker-first workflow — a new volunteer's setup is "install Docker, clone, `docker compose build`," nothing else
- [ ] No step in this phase requires a hosted service, container registry, or live deployment — the container is for local dev portability only; if anything here starts requiring a registry push or a deployed image, that's scope creep into Phase 3 and should be flagged, not built

## Explicitly out of scope for Phase 1

- GitHub Actions / any CI automation
- Publishing the Docker image to a registry (Docker Hub, GHCR, etc.) — Phase 1's image is built locally by each developer, never pushed anywhere
- Evidence.dev reporting
- Deployment of any kind (Netlify, GitHub Pages, etc.)
- dbt marts or metric definitions (`fct_attendance`, `dim_volunteer`, etc.) — that's Phase 2
- Dagster, Lightdash, Postgres, MotherDuck, or anything from the "learning layer" — optional, separate, not load-bearing here

## Notes for whoever picks this up

- "Active volunteer" is still an open question requiring an actual org decision from Open Oakland's steering committee — do not hardcode a definition into any model in this phase. That belongs in Phase 2's marts layer, once someone has actually answered it.
- Docker is now a first-class, committed part of this repo (not a personal side-channel) — the `Dockerfile`/`docker-compose.yml` are checked in and `docs/SETUP.md` is written assuming every contributor uses them. This is a deliberate tradeoff: it adds one prerequisite (Docker itself) in exchange for removing many (Python version, package conflicts, dbt/dlt version drift between contributors' machines). If a future maintainer wants a non-Docker path too, that should be a documented addition, not a silent alternative — two undocumented ways to run the pipeline is how environments drift apart.
- Keep the Dockerfile itself simple (pinned base image, pinned package versions) so it doesn't become its own maintenance burden — the whole point is to reduce what the next volunteer has to think about, not add a second layer of tooling to debug.
</content>
