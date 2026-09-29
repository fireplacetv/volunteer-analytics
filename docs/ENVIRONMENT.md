# Environment Configuration

This project uses environment variables for configuration. Set these in your `.env` file (see `.env.example` for defaults).

## Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```bash
   AIRTABLE_API_KEY=your_key_here
   AIRTABLE_BASE_ID=your_base_id_here
   DUCKDB_PATH=artifacts/openoakland.duckdb
   ```

3. Load the environment before running the pipeline:
   ```bash
   set -a
   source .env
   set +a
   ```

## Configuration Variables

### AIRTABLE_API_KEY
Your Airtable API token. Required to authenticate with Airtable.

**Example:**
```
AIRTABLE_API_KEY=patXXXXXXXXXXXXXX
```

### AIRTABLE_BASE_ID
Your Airtable Base ID. Identifies which Airtable workspace to pull data from.

**Example:**
```
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
```

### DESTINATION_TYPE
Which database dlt loads into. Defaults to `duckdb`. Any destination dlt supports works; the requirements install `duckdb` and `postgres`.

For anything other than DuckDB, credentials come from dlt's standard variables:
```
DESTINATION_TYPE=postgres
DESTINATION__POSTGRES__CREDENTIALS=postgresql://user:password@host:5432/database
```
Switching destinations needs no code change: the incremental cursor is read from whichever destination is configured. dbt still reads only DuckDB for now.

### DUCKDB_PATH
Path to the DuckDB database file, used when `DESTINATION_TYPE` is `duckdb` (the default). Both dlt and dbt use this same path.

**Options:**
- **Relative path** (default, relative to project root):
  ```
  DUCKDB_PATH=artifacts/openoakland.duckdb
  ```

- **Absolute path** (same for all environments):
  ```
  DUCKDB_PATH=/var/data/volunteer_analytics/openoakland.duckdb
  ```

- **Docker mounted volume**:
  ```
  DUCKDB_PATH=/data/openoakland.duckdb
  ```

### DBT_PACKAGES_DIR
Where dbt installs and looks for packages (`packages-install-path` in `dbt/dbt_project.yml`). Leave it unset.

- **Docker:** the image sets it to `/opt/dbt_packages` and runs `dbt deps` at build time. The packages can't live under `/workspace` because the repo is mounted there at runtime, which would hide them. Rebuild the image after changing `dbt/packages.yml`.
- **Outside Docker:** defaults to `dbt/dbt_packages`; run `dbt deps` once.

## How It Works

Both dlt and dbt use the same `DUCKDB_PATH` environment variable:

- **dlt** (`run.py`): Reads `DUCKDB_PATH` to determine where to write extracted data
- **dbt** (`profiles.yml`): Reads `DUCKDB_PATH` to determine where to read source data for transformations

This ensures both tools are always pointing to the same database.

## Running the Pipeline

```bash
# Load environment
set -a
source .env
set +a

# Run dlt extraction
python dlt/airtable_pipeline/run.py

# Run dbt transformations
dbt run
```

## Docker Setup

In `docker-compose.yml`, pass the environment file:

```yaml
services:
  pipeline:
    build: .
    env_file: .env
    volumes:
      - /data:/data  # If using absolute paths
```

## Different Environments

### Development
In `.env`:
```
DUCKDB_PATH=artifacts/openoakland.duckdb
```

### Production
In `.env.prod`:
```
DUCKDB_PATH=/mnt/shared-storage/prod/openoakland.duckdb
```

Load it:
```bash
set -a
source .env.prod
set +a
```

## Security

- **Never commit `.env` to version control** (it's in `.gitignore`)
- `.env.example` is safe to commit (it's a template with no secrets)
- Keep API keys secure and rotate them regularly
