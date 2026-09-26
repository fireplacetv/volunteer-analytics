# Setup — Volunteer Analytics Platform (Phase 0)

This is the Phase 0 setup guide for local development. Phase 0 verifies that the dlt pipeline can load data from Airtable into DuckDB. Phase 1 will containerize this with Docker.

## Prerequisites

- Python 3.11+
- Git

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/openoakland/volunteer-analytics.git
cd volunteer-analytics
```

### 2. Create a Python virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r dlt/airtable_pipeline/requirements.txt
pip install -r dbt/requirements.txt
```

### 4. Set up your Airtable credentials

Create a `.env` file in the repo root (it will be gitignored):

```
AIRTABLE_API_KEY=your_api_key_here
AIRTABLE_BASE_ID=your_base_id_here
```

To find your credentials:
- **API Key**: Generate a personal access token at https://airtable.com/account/tokens
- **Base ID**: Open your Airtable base in the browser; the base ID is in the URL: `https://airtable.com/BASE_ID/...`

### 5. Load your credentials into your shell session

```bash
export $(cat .env | xargs)
```

(Alternatively, you can export them manually: `export AIRTABLE_API_KEY=... AIRTABLE_BASE_ID=...`)

### 6. Run the dlt pipeline

```bash
python dlt/airtable_pipeline/airtable_source.py
```

On first run, this loads all data from Airtable into `dlt/airtable_pipeline/volunteer_data.duckdb`. Subsequent runs will do a full reload (Phase 1 adds incremental logic).

### 7. Verify the pipeline worked

```bash
duckdb dlt/airtable_pipeline/volunteer_data.duckdb -c "SELECT COUNT(*) FROM airtable.volunteers;"
```

If you see a row count, the pipeline succeeded.

## Troubleshooting

### "ModuleNotFoundError: No module named 'dlt'"
Make sure your virtual environment is activated (`source .venv/bin/activate`) and you've run `pip install -r dlt/airtable_pipeline/requirements.txt`.

### "AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set"
Export them into your shell: `export $(cat .env | xargs)` or set them manually before running the pipeline.

### "Connection error" or "Invalid API key"
Verify your API key and base ID are correct. API keys expire; generate a new one at https://airtable.com/account/tokens if needed.

### The DuckDB file is not being created
Check that the pipeline ran without errors. The file is created in `dlt/airtable_pipeline/volunteer_data.duckdb`.

## Next steps

Once Phase 0 is confirmed working, Phase 1 will containerize this setup with Docker so no local Python install is needed. See `../phase1-plan.md` for the Phase 1 roadmap.
