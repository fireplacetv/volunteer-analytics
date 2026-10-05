# Architecture

How data moves from Airtable to a report, and why each layer exists. For
setup steps see `SETUP.md`; for the reasoning behind specific choices see
`DECISIONS.md`.

## Pipeline overview

```
Airtable  →  dlt (extract + PII filter)  →  DuckDB raw_airtable  →  dbt staging (views)  →  dbt marts (tables)  →  reporting
```

- **Airtable** is the source of truth: Volunteers, Projects, Project
  volunteers, Events, Event attendance.
- **dlt** (`dlt/airtable_pipeline/`) pulls records over the Airtable REST
  API, applies PII filtering in memory, and writes one JSON-blob row per
  record into DuckDB.
- **DuckDB** (`artifacts/openoakland.duckdb`) holds both the raw load
  (`raw_airtable` schema) and everything dbt builds on top of it. One file,
  shared by dlt and dbt, so there's no separate database to stand up.
- **dbt staging models** (`dbt/models/staging/`) are thin views that unpack
  each table's `json_blob` into typed columns, 1:1 with the source table. No
  business logic.
- **dbt marts** (`dbt/models/marts/`) are the dimensional model — three dims
  and two facts — built as tables for downstream query performance.
- **Reporting** reads the marts: a GitHub Actions job posts an aggregate
  attendance summary as a PR comment (`scripts/data_report.py`), and
  `dbt docs` publishes schema/lineage docs to GitHub Pages.

## Extraction: dlt

`dlt/airtable_pipeline/run.py` is the entry point. For each table listed in
`airtable_tables.json`, it builds a dlt resource (`source.py`) that pages
through the Airtable list endpoint and yields one row per record:

```
{id, json_blob, created_time, last_modified}
```

`json_blob` holds only the fields that survive PII filtering (see below) —
raw Airtable field values for excluded fields never reach this dict, let
alone the destination.

Loads are incremental: each resource is `write_disposition="merge"` keyed on
`id`, filtered server-side by `Last Modified > cursor`. Two things keep this
reliable rather than approximate:

- **The cursor comes from the destination, not dlt's local state**
  (`cursors.py`): each run reads `MAX(last_modified)` out of the table it's
  about to update. A missing table (first run, or one dropped to force a
  backfill) reads as "no cursor", so that table does a full load. This means
  the pipeline is correct from a fresh checkout or container with no local
  `.dlt/` state — state lives in the data itself.
- **The destination is pluggable.** `run.py` resolves a destination from
  `DESTINATION_TYPE` (DuckDB by default; anything else dlt supports, e.g.
  Postgres, via `DESTINATION__*` env vars). Because the cursor logic queries
  through dlt's own SQL client, incremental loads work unchanged on any SQL
  destination — only dbt is DuckDB-specific today.

## PII defense

PII is handled once, at the earliest possible point — inside the dlt
resource, before a record is ever written anywhere — not downstream in dbt.
Two reasons that matters: dbt staging models are views over `raw_airtable`,
so masking there would still leave raw PII sitting in the DuckDB file; and
SQL written into dbt's `target/` directory gets published to GitHub Pages by
CI, which would leak a masking key if the hash salt were ever expressed in
model code instead.

Every field, per table, is classified in `airtable_tables.json`
(`pii.py` enforces this):

| Classification | Effect |
|---|---|
| `allow` | passed through unchanged |
| `pseudonymize` | replaced before the record leaves memory — `hash` (keyed HMAC-SHA256, stored as `<field>_hash`) or `first_name`/`last_name`/`full_name` (a stable word-based fake name) |
| `unused` | dropped, with a one-line reason recorded for future readers |
| *(unlisted)* | dropped, and the field name (never its value) is logged as unclassified |

This is an **allowlist**, not a blocklist: a new sensitive field added in
Airtable is dropped by default until someone explicitly classifies it. The
hash is keyed (`PII_HASH_KEY`, required — the pipeline refuses to run
without it) so it can't be reversed by guessing and hashing a list of known
emails. `fct_attendance` joins check-ins to volunteers on `email_hash`
rather than a raw email, so the hash is the only form an email takes
anywhere past `pii.py`.

Full rationale and the current field-by-field classification live in
`DECISIONS.md` under "PII Handled at dlt Ingestion".

## Transformation: dbt

**Staging** (`dbt/models/staging/`, materialized as views, schema
`stg_airtable`) extracts `json_blob` into named, typed columns — one model
per Airtable table, no joins, no filtering, no derived columns. Row counts
here should always match the source table.

**Marts** (`dbt/models/marts/`, materialized as tables, schema `marts`) hold
the actual dimensional model:

| Model | Grain | Key |
|---|---|---|
| `dim_volunteer` | volunteer | `volunteer_id` |
| `dim_project` | project | `project_id` |
| `dim_event` | event (synthetic row `0` = monthly meetings) | `event_id` |
| `fct_attendance` | one Event attendance record | `attendance_id` |
| `fct_project_volunteer` | one Project volunteers record | `join_id` |

Every dim/fact is keyed on its Airtable record ID (or, for `dim_project`
and `dim_event`, Airtable's human-readable auto-ID) so later models can join
against marts without going back through staging. Full column-level schemas
and the reasoning behind each model's design (why monthly meetings share
`event_id = 0`, why linked-record arrays are expanded in marts rather than
staging, how outreach attempts are derived) are in `DECISIONS.md` and
`docs/roadmap/phase-2/phase-2-plan.md`.

Tests are layered by how much they should block a build: `not_null`/`unique`
on every key are errors; `relationships` on foreign keys are errors (an
orphaned link is a real data-quality bug to flag); `accepted_values` on
status/type fields are warnings (a new Airtable option shouldn't break the
nightly build); a handful of singular tests catch duplicate check-ins and
future-dated attendance.

## Docker: dev and CI

The whole pipeline — dlt and dbt, pinned Python/package versions — runs
inside a single Docker image (`Dockerfile`), so a contributor's only
prerequisite is Docker itself. `docker-compose.yml` mounts the repo as a
volume (edits on the host are live inside the container) and persists
`artifacts/openoakland.duckdb` on the host so it survives container
rebuilds. Credentials come from a gitignored `.env` loaded via
`env_file` — never baked into the image.

CI (`.github/workflows/dbt.yml`) builds the same image and runs the same
steps a contributor would run locally — unit tests, dlt ingestion, `dbt
run`, `dbt test` — then adds two things a local run doesn't: posting
`scripts/data_report.py`'s summary as a PR comment, and (on `main`)
publishing `dbt docs generate` output to GitHub Pages. Using the same image
in CI and locally means "works in Docker" and "works in CI" are the same
claim.

## Known gap

Phase 2 specified a source-freshness check (`loaded_at_field: last_modified`,
`warn_after: 36 hours`) to catch a silently stalled Airtable load. It's
documented in `DECISIONS.md` but not yet implemented in
`dbt/models/sources.yml` — it has no `loaded_at_field`/`freshness` block
today. Tracked in `docs/roadmap/future/ROADMAP_FUTURE.md`.
