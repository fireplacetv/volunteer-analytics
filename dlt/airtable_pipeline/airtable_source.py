import os
import requests
import dlt
from dlt.common.typing import TDataItem
from typing import Iterator


@dlt.resource(name="airtable_table", write_disposition="replace")
def airtable_resource(
    base_id: str,
    table_name: str,
    api_key: str,
) -> Iterator[TDataItem]:
    """
    Fetch records from an Airtable table and yield them as data items.

    Args:
        base_id: Airtable Base ID
        table_name: Name of the table to fetch
        api_key: Airtable API key

    Yields:
        Records from the Airtable table
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
        source = airtable_resource(
            base_id=base_id,
            table_name=table_name,
            api_key=api_key,
        )
        source.name = table_name
        load_info = pipeline.run(source)

    return load_info


if __name__ == "__main__":
    load_info = load_volunteer_data()
    print(load_info)
