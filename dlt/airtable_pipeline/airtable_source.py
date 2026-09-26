import os
import json
import requests
import dlt
from dlt.common.typing import TDataItem
from typing import Iterator, Callable


def load_table_config():
    """Load table ID mappings from airtable_tables.json."""
    config_path = os.path.join(os.path.dirname(__file__), "airtable_tables.json")
    with open(config_path, "r") as f:
        config = json.load(f)
    return config["tables"]


def create_airtable_resource(
    table_name: str, table_id: str, base_id: str, api_key: str
) -> Callable[[], Iterator[TDataItem]]:
    """
    Factory function to create a resource for a specific Airtable table.

    Args:
        table_name: Human-readable table name (for resource naming)
        table_id: Airtable Table ID (tblXXXXXXXXXXXXXX format)
        base_id: Airtable Base ID (appXXXXXXXXXXXXXX format)
        api_key: Airtable API key

    Returns:
        A dlt resource that fetches data from the table
    """

    @dlt.resource(name=table_name, write_disposition="replace")
    def fetch_table() -> Iterator[TDataItem]:
        """
        Fetch records from an Airtable table and yield them as data items.
        Uses the table ID (not table name) in the API endpoint.
        """
        url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        offset = None

        while True:
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            records = data.get("records", [])

            for record in records:
                yield {
                    "id": record["id"],
                    "fields": record["fields"],
                    "created_time": record.get("createdTime"),
                }

            offset = data.get("offset")
            if not offset:
                break

    return fetch_table


def load_volunteer_data():
    """Load all volunteer-related tables from Airtable into DuckDB."""

    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    if not api_key or not base_id:
        raise ValueError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set")

    table_config = load_table_config()

    pipeline = dlt.pipeline(
        pipeline_name="airtable_pipeline",
        destination="duckdb",
        dataset_name="airtable",
        pipelines_dir="dlt/airtable_pipeline",
    )

    load_info = None
    for table_name, table_id in table_config.items():
        if table_id.startswith("YOUR_"):
            print(f"Skipping {table_name}: table ID not configured")
            continue

        resource = create_airtable_resource(table_name, table_id, base_id, api_key)
        load_info = pipeline.run(resource)

    return load_info


if __name__ == "__main__":
    load_info = load_volunteer_data()
    print(load_info)
