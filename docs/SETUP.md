# Setup — Volunteer Analytics Platform (Phase 1+)

This is the Phase 1+ setup guide for local development. Everything runs in Docker containers, so **you only need Docker Desktop installed** — no Python, dlt, or dbt installation needed.

## Prerequisites

- **Docker Desktop** (or Docker Engine + Docker Compose)
- Git

That's it. No Python version management, no pip conflicts, no version drift between contributors' machines.

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/openoakland/volunteer-analytics.git
cd volunteer-analytics
```

### 2. Set up your Airtable credentials

Create a `.env` file in the repo root (it will be gitignored):

```
AIRTABLE_API_KEY=your_api_key_here
AIRTABLE_BASE_ID=your_base_id_here
```

#### Getting your API Key

1. Go to https://airtable.com/account/tokens
2. Click **Create token** (or use an existing one)
3. When creating a new token, grant these **required scopes**:
   - `data.records:read` — to read volunteer records from Airtable
   - `schema.bases:read` — to read base metadata (table schemas, field definitions)
4. Under **Access**, select the base you want to sync (usually your volunteer database)
5. Copy the token and paste it into your `.env` file as `AIRTABLE_API_KEY`

#### Getting your Base ID

The Base ID uniquely identifies your Airtable database. It's a 17-character alphanumeric string.

1. **Open your Airtable base** in a web browser (at https://airtable.com)
2. **Find the Base ID in the URL**:
   - The URL looks like: `https://airtable.com/appXXXXXXXXXXXXXX/tblYYYYYYYYYYYYYY/...`
   - The Base ID is the part starting with `app`: `appXXXXXXXXXXXXXX`
   - Example: `appK9pz1A2b3C4dEf`
3. **Copy the entire Base ID** (including the `app` prefix)
4. **Paste it** into your `.env` file:
   ```
   AIRTABLE_BASE_ID=appK9pz1A2b3C4dEf
   ```

### 3. Build the Docker container

```bash
docker compose build
```

This builds the image locally with Python 3.11, dlt, dbt, and all dependencies pinned to exact versions. It takes a couple of minutes the first time.

### 4. Run the data pipeline and tests

```bash
docker compose run --rm dev bash -c "python dlt/airtable_pipeline/run.py && dbt run && dbt test"
```

This single command:
- Loads data from Airtable into DuckDB (`artifacts/openoakland.duckdb`)
- Transforms it with dbt staging models
- Runs automated tests on all staging models

### 5. Verify the pipeline worked

```bash
docker compose run --rm dev dbt show --inline "select count(*) from {{ source('airtable', 'volunteers') }}"
```

If you see a row count, the pipeline succeeded.

## Interactive shell access

To poke around, run a shell inside the container:

```bash
docker compose run --rm dev bash
```

Then you can run dlt and dbt commands directly:

```bash
python dlt/airtable_pipeline/run.py
dbt run
dbt test
dbt show --inline "select * from {{ ref('dim_volunteer') }}"
```

The image doesn't include the `duckdb` CLI. To run arbitrary SQL, use the DuckDB Python package, e.g. `python -c "import duckdb; duckdb.connect('artifacts/openoakland.duckdb').sql('show all tables').show()"`.

dbt packages (`dbt/packages.yml`) are installed into the image when it's built, so there's no need to run `dbt deps`. Rebuild the image (`docker compose build`) after changing `packages.yml`.

## Troubleshooting

### "Cannot connect to Docker daemon"
Make sure Docker Desktop is running (or `docker daemon` if you use Docker Engine separately).

### "Build failed: pip install error"
Check that `dlt/airtable_pipeline/requirements.txt` and `dbt/requirements.txt` are not corrupted. If they are, regenerate them and commit the changes.

### "AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set"
Make sure your `.env` file exists in the repo root and contains both variables. The `docker-compose.yml` loads them via `env_file: .env`.

### "Connection error" or "Invalid API key"
Verify your API key and base ID are correct. API keys expire; generate a new one at https://airtable.com/account/tokens if needed.

### The DuckDB file is not being created
Run `docker compose run --rm dev bash -c "python dlt/airtable_pipeline/run.py"` and check the output for errors. The file should appear at `artifacts/openoakland.duckdb` on your host machine.

## Backfilling and Data History

### How Incremental Loads Work

The pipeline uses the `last_modified` timestamp field in Airtable to load only changed records on each run:
- **First run:** Full load of all records from all tables
- **Subsequent runs:** Only records with `last_modified` newer than the latest one already in the destination are fetched. The cursor is read from the loaded tables (`dlt/airtable_pipeline/cursors.py`), so it always matches what actually landed
- dlt's merge logic (`primary_key="id"`) ensures records are updated in-place, not duplicated

### What Happens During a Backfill

If you need to force a full reload of all records (e.g., after a schema change, or to verify data consistency), drop the raw table. The cursor is computed from the table itself, so a missing table means a full load for that table. Deleting `dlt/airtable_pipeline/.dlt/` does **not** reset it.

```bash
# Drop the raw table(s) to reset the cursor
docker compose run --rm dev python -c "import duckdb; duckdb.connect('artifacts/openoakland.duckdb').execute('DROP TABLE raw_airtable.volunteers')"

# Then run the pipeline — it will do a full load of the dropped table(s)
docker compose run --rm dev bash -c "python dlt/airtable_pipeline/run.py && dbt run && dbt test"
```

**Important:** The dropped table is empty until the reload finishes, and the reload brings back only records that still exist in Airtable. Records deleted in Airtable are gone from the reloaded table. **If you delete and recreate the DuckDB file, all historical data is lost**. Plan data recovery strategies before doing full table replacements.

### Data History Limitations (Phase 1)

- DuckDB stores the **current state** of all Airtable records, not a full audit trail
- Deleted records in Airtable remain in DuckDB (not actively removed)
- If a record is modified retroactively in Airtable and `last_modified` is set to an earlier date, it will not be caught by incremental loads
- **Phase 2 will add proper historical tracking** (SCD2 or dedicated history tables)

## Next steps

The pipeline runs all tests on each run (Step 4 above). If a test fails, check `dbt test` output to see which records are missing required fields — these are data-quality issues in Airtable, not code issues. See `../phase1-plan.md` for more context on Phase 1 and beyond.
