import os
import requests
import dlt
from dlt.common.typing import TDataItem
from typing import Iterator, Callable


def create_airtable_resource(
    table_name: str, base_id: str, api_key: str
) -> Callable[[], Iterator[TDataItem]]:
    """
    Factory function to create a resource for a specific Airtable table.
    Returns a resource with the table name as its identifier.
    """

    @dlt.resource(name=table_name, write_disposition="replace")
    def fetch_table() -> Iterator[TDataItem]:
        """
        Fetch records from an Airtable table and yield them as data items.
        """
        url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
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

    table_names = [
        "Volunteers",
        "Projects",
        "Project volunteers",
        "Events",
        "Event attendance",
        "Meeting attendance",
    ]

    pipeline = dlt.pipeline(
        pipeline_name="airtable_pipeline",
        destination="duckdb",
        dataset_name="airtable",
        pipelines_dir="dlt/airtable_pipeline",
    )

    load_info = None
    for table_name in table_names:
        resource = create_airtable_resource(table_name, base_id, api_key)
        load_info = pipeline.run(resource)

    return load_info


if __name__ == "__main__":
    load_info = load_volunteer_data()
    print(load_info)
