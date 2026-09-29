"""
Load volunteer data from Airtable into the configured destination.

The destination is chosen by DESTINATION_TYPE (default: duckdb):
- duckdb: the file at DUCKDB_PATH (default: artifacts/openoakland.duckdb),
  shared with dbt
- anything else dlt supports, e.g. postgres: credentials come from dlt's own
  config, e.g. DESTINATION__POSTGRES__CREDENTIALS=postgresql://user:pass@host:5432/db
"""

import os

import dlt

from cursors import get_cursors
from pii import get_pii_key
from source import airtable_source, configured_tables, load_table_config

PIPELINE_NAME = "openoakland"
DATASET_NAME = "raw_airtable"


def get_duckdb_path() -> str:
    """Absolute path to the DuckDB file from DUCKDB_PATH, or artifacts/openoakland.duckdb."""
    default_path = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "openoakland.duckdb")
    return os.path.abspath(os.getenv("DUCKDB_PATH", default_path))


def get_destination():
    """The destination named by DESTINATION_TYPE, defaulting to the shared DuckDB file."""
    destination_type = os.getenv("DESTINATION_TYPE", "duckdb")
    if destination_type == "duckdb":
        return dlt.destinations.duckdb(get_duckdb_path())
    return destination_type


def get_pipelines_dir() -> str:
    """Local working folder for dlt; disposable, state is also kept in the destination."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".dlt"))


def build_pipeline(destination=None, pipelines_dir: str = None):
    return dlt.pipeline(
        pipeline_name=PIPELINE_NAME,
        destination=destination or get_destination(),
        dataset_name=DATASET_NAME,
        pipelines_dir=pipelines_dir or get_pipelines_dir(),
    )


def load(pipeline, tables: dict, base_id: str, api_key: str, pii_key: bytes):
    """Run one incremental load of `tables` into `pipeline`'s destination."""
    cursors = get_cursors(pipeline, tables)
    for table_name, cursor in cursors.items():
        if cursor:
            print(f"Loaded cursor for {table_name} from destination: {cursor}")
    return pipeline.run(airtable_source(tables, base_id, api_key, pii_key, cursors))


def load_volunteer_data():
    """Load all volunteer-related tables from Airtable with incremental updates."""

    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    if not api_key or not base_id:
        raise ValueError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set")

    pii_key = get_pii_key()
    tables = configured_tables(load_table_config())
    if not tables:
        print("No tables to load (all configured table IDs start with YOUR_)")
        return None

    return load(build_pipeline(), tables, base_id, api_key, pii_key)


if __name__ == "__main__":
    load_info = load_volunteer_data()
    print(load_info)
