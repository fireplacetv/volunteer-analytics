import os
import json
import requests
import dlt
from dlt.common.typing import TDataItem
from typing import Iterator, Callable
import duckdb


def load_table_config():
    """Load table ID mappings from airtable_tables.json."""
    config_path = os.path.join(os.path.dirname(__file__), "airtable_tables.json")
    with open(config_path, "r") as f:
        config = json.load(f)
    return config["tables"]


def get_db_path():
    """Get absolute path to DuckDB file from DUCKDB_PATH env var or default (artifacts/openoakland.duckdb)."""
    default_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "openoakland.duckdb"))
    db_path = os.getenv("DUCKDB_PATH", default_path)
    return os.path.abspath(db_path)


def get_pipelines_dir():
    """Get absolute path to pipelines directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".dlt"))


def get_cursor_from_database(table_name: str, db_path: str) -> str:
    """
    Get the cursor (latest Last Modified timestamp) from the database for a table.
    Returns the max Last Modified timestamp, or None if table doesn't exist or has no records.
    """
    try:
        conn = duckdb.connect(db_path)
        # DuckDB converts field names to lowercase with underscores, so "Last Modified" becomes "fields__last_modified"
        result = conn.execute(f"""
            SELECT MAX(fields__last_modified)
            FROM airtable."{table_name}"
        """).fetchone()
        conn.close()

        if result and result[0]:
            return result[0]
        return None
    except Exception as e:
        # Table doesn't exist yet (first run) or error querying
        return None


def normalize_linked_records():
    """
    Post-process DuckDB to normalize linked records.
    Currently a placeholder as linked record fields are not fully expanded by dlt.
    """
    db_path = get_db_path()
    conn = duckdb.connect(db_path)

    try:
        # Verify that the project_volunteers table was created with the expected structure
        tables = conn.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'airtable' AND table_name = 'project_volunteers'
        """).fetchall()

        if tables:
            # Log the actual columns present for debugging
            columns = conn.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'airtable' AND table_name = 'project_volunteers'
                ORDER BY ordinal_position
            """).fetchall()
            col_names = [col[0] for col in columns]
            print(f"project_volunteers table loaded with columns: {col_names}")
    except Exception as e:
        print(f"Note: Could not verify project_volunteers table structure: {e}")
    finally:
        conn.close()


def create_airtable_resource(
    table_name: str, table_id: str, base_id: str, api_key: str, db_path: str
) -> Callable[[], Iterator[TDataItem]]:
    """
    Factory function to create a resource for a specific Airtable table.

    Args:
        table_name: Human-readable table name (for resource naming)
        table_id: Airtable Table ID (tblXXXXXXXXXXXXXX format)
        base_id: Airtable Base ID (appXXXXXXXXXXXXXX format)
        api_key: Airtable API key
        db_path: Path to DuckDB database for reading cursor state

    Returns:
        A dlt resource that fetches data from the table
    """

    @dlt.resource(name=table_name, write_disposition="merge", primary_key="id")
    def fetch_table() -> Iterator[TDataItem]:
        """
        Fetch records from an Airtable table with incremental loading.
        Uses the table ID (not table name) in the API endpoint.
        Filters by last_modified timestamp to only fetch changed records.
        Cursor is loaded from the database (max timestamp of already-loaded records).
        """
        url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        offset = None
        total_records = 0

        # Load cursor from database (max Last Modified timestamp)
        cursor = get_cursor_from_database(table_name, db_path)
        if cursor:
            print(f"Loaded cursor for {table_name} from database: {cursor}")

        while True:
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset

            # Add filter by last_modified if we have a cursor
            if cursor:
                # Airtable filterByFormula: find records where Last Modified > cursor
                params["filterByFormula"] = f"{{Last Modified}} > '{cursor}'"
                print(f"Fetching {table_name} with incremental filter: Last Modified > {cursor}")
            else:
                print(f"Fetching {table_name} with full load (first run or no prior state)")

            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            records = data.get("records", [])

            for record in records:
                total_records += 1
                yield {
                    "id": record["id"],
                    "fields": record["fields"],
                    "created_time": record.get("createdTime"),
                }

            offset = data.get("offset")
            if not offset:
                break

        print(f"Loaded {total_records} records from {table_name}")
        # Cursor is automatically updated in database when dlt saves records

    return fetch_table


def load_volunteer_data():
    """Load all volunteer-related tables from Airtable into DuckDB with incremental updates."""

    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    if not api_key or not base_id:
        raise ValueError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set")

    table_config = load_table_config()
    db_path = get_db_path()
    pipelines_dir = get_pipelines_dir()

    pipeline = dlt.pipeline(
        pipeline_name="openoakland",
        destination=dlt.destinations.duckdb(db_path),
        dataset_name="airtable",
        pipelines_dir=pipelines_dir,
    )

    resources = []
    for table_name, table_id in table_config.items():
        if table_id.startswith("YOUR_"):
            print(f"Skipping {table_name}: table ID not configured")
            continue

        resource = create_airtable_resource(table_name, table_id, base_id, api_key, db_path)
        resources.append(resource)

    if not resources:
        print("No tables to load (all configured table IDs start with YOUR_)")
        return None

    load_info = pipeline.run(resources)

    # Post-process to flatten linked records into clean bridge tables
    normalize_linked_records()

    return load_info


if __name__ == "__main__":
    load_info = load_volunteer_data()
    print(load_info)
