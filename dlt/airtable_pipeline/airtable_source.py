import os
import dlt
from dlt.sources.airtable import airtable_source


def load_volunteer_data():
    """Load all volunteer-related tables from Airtable into DuckDB."""

    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    if not api_key or not base_id:
        raise ValueError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set")

    source = airtable_source(
        base_id=base_id,
        api_key=api_key,
        table_names=[
            "Volunteers",
            "Projects",
            "Project volunteers",
            "Events",
            "Event attendance",
            "Meeting attendance",
        ],
    )

    pipeline = dlt.pipeline(
        pipeline_name="airtable_pipeline",
        destination="duckdb",
        dataset_name="airtable",
        pipelines_dir="dlt/airtable_pipeline",
    )

    load_info = pipeline.run(source)
    return load_info


if __name__ == "__main__":
    load_info = load_volunteer_data()
    print(load_info)
