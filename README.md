# Volunteer Analytics Platform

A data pipeline and analytics platform for Open Oakland to track volunteer engagement, project participation, and event attendance.

## What is this?

This project extracts volunteer data from Airtable, transforms it with dlt and dbt, and loads it into DuckDB for analysis and reporting.

## Getting started

See `docs/SETUP.md` for setup instructions.

## Project structure

```
├── dlt/airtable_pipeline/          # dlt pipeline to extract data from Airtable
│   ├── airtable_source.py          # dlt resource definitions
│   └── requirements.txt             # Python dependencies for dlt
├── dbt/                            # dbt transformations
│   ├── dbt_project.yml             # dbt project config
│   ├── profiles.yml                # dbt connection config
│   ├── requirements.txt            # Python dependencies for dbt
│   └── models/staging/             # dbt staging models (Phase 1+)
├── docs/
│   ├── SETUP.md                    # Setup and troubleshooting guide
│   └── roadmap/                    # Phase planning and status
│       ├── phase1-plan.md          # Roadmap for Phase 1 work
│       └── PHASE1_STATUS.md        # Phase 1 implementation status
└── README.md                       # This file
```

## Phases

- **Phase 0**: Basic dlt pipeline loads Airtable tables into DuckDB
- **Phase 1** (current): Containerize with Docker, incremental loads, bridge tables, dbt staging models
- **Phase 2**: dbt marts, metrics, and business logic
- **Phase 3**: CI/CD, GitHub Actions automation, deployment

## Data sources

- **Airtable**: Source of truth for volunteer, project, and event data

## Data output

Data is loaded into a local DuckDB database at `artifacts/openoakland.duckdb`.

## Questions or issues?

See `docs/SETUP.md` for troubleshooting.
