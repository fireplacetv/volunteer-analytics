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
docker compose run --rm dev bash -c "python dlt/airtable_pipeline/airtable_source.py && dbt run && dbt test"
```

This single command:
- Loads data from Airtable into DuckDB (`dlt/airtable_pipeline/volunteer_data.duckdb`)
- Transforms it with dbt staging models
- Runs automated tests on all staging models

### 5. Verify the pipeline worked

```bash
docker compose run --rm dev duckdb dlt/airtable_pipeline/volunteer_data.duckdb -c "SELECT COUNT(*) FROM airtable.volunteers;"
```

If you see a row count, the pipeline succeeded.

## Interactive shell access

To poke around, run a shell inside the container:

```bash
docker compose run --rm dev bash
```

Then you can run dlt, dbt, and duckdb commands directly:

```bash
python dlt/airtable_pipeline/airtable_source.py
dbt run
dbt test
duckdb dlt/airtable_pipeline/volunteer_data.duckdb
```

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
Run `docker compose run --rm dev bash -c "python dlt/airtable_pipeline/airtable_source.py"` and check the output for errors. The file should appear at `dlt/airtable_pipeline/volunteer_data.duckdb` on your host machine.

## Next steps

The pipeline runs all tests on each run (Step 4 above). If a test fails, check `dbt test` output to see which records are missing required fields — these are data-quality issues in Airtable, not code issues. See `../phase1-plan.md` for more context on Phase 1 and beyond.
