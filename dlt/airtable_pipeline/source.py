"""
Airtable source: fetches records, applies PII filtering, and yields rows.

Knows nothing about the destination. Incremental cursors are passed in by the
runner (see cursors.py), so the same source loads into any dlt destination.
"""

import json
import os
from typing import Callable, Iterator, Optional

import dlt
import requests
from dlt.common.typing import TDataItem

from pii import filter_fields, validate_table_config

# Declared rather than inferred, so the cursor column has the same type on
# every destination.
COLUMNS = {
    "id": {"data_type": "text", "nullable": False},
    "json_blob": {"data_type": "text"},
    "created_time": {"data_type": "timestamp"},
    "last_modified": {"data_type": "timestamp"},
}


def load_table_config() -> dict:
    """Load per-table IDs and field classifications from airtable_tables.json."""
    config_path = os.path.join(os.path.dirname(__file__), "airtable_tables.json")
    with open(config_path, "r") as f:
        config = json.load(f)
    return config["tables"]


def configured_tables(table_config: dict) -> dict:
    """Validated table configs, skipping tables whose ID is still a placeholder."""
    tables = {}
    for table_name, config in table_config.items():
        if config["id"].startswith("YOUR_"):
            print(f"Skipping {table_name}: table ID not configured")
            continue
        validate_table_config(table_name, config)
        tables[table_name] = config
    return tables


def build_params(cursor: Optional[str], offset: Optional[str]) -> dict:
    """Query parameters for one page of an Airtable list request."""
    params = {"pageSize": 100}
    if offset:
        params["offset"] = offset
    if cursor:
        # Airtable filterByFormula: find records where Last Modified > cursor
        params["filterByFormula"] = f"{{Last Modified}} > '{cursor}'"
    return params


def create_airtable_resource(
    table_name: str,
    table_config: dict,
    base_id: str,
    api_key: str,
    pii_key: bytes,
    cursor: Optional[str],
) -> Callable[[], Iterator[TDataItem]]:
    """
    Factory function to create a resource for a specific Airtable table.

    Args:
        table_name: Human-readable table name (for resource naming)
        table_config: Table ID (tblXXXXXXXXXXXXXX format) and field classifications
        base_id: Airtable Base ID (appXXXXXXXXXXXXXX format)
        api_key: Airtable API key
        pii_key: HMAC key for pseudonymizing PII fields
        cursor: Only fetch records with Last Modified after this ISO 8601
            timestamp; None for a full load

    Returns:
        A dlt resource that fetches data from the table
    """

    @dlt.resource(name=table_name, write_disposition="merge", primary_key="id", columns=COLUMNS)
    def fetch_table() -> Iterator[TDataItem]:
        """
        Fetch records from an Airtable table with incremental loading.
        Uses the table ID (not table name) in the API endpoint.
        """
        url = f"https://api.airtable.com/v0/{base_id}/{table_config['id']}"
        headers = {"Authorization": f"Bearer {api_key}"}
        offset = None
        total_records = 0
        dropped_fields = set()

        if cursor:
            print(f"Fetching {table_name} with incremental filter: Last Modified > {cursor}")
        else:
            print(f"Fetching {table_name} with full load (first run or no prior state)")

        while True:
            response = requests.get(url, headers=headers, params=build_params(cursor, offset), timeout=30)
            response.raise_for_status()

            data = response.json()
            records = data.get("records", [])

            for record in records:
                total_records += 1
                # Only allowed and pseudonymized fields are kept; raw PII
                # values never leave this function.
                fields, dropped = filter_fields(record["id"], record["fields"], table_config, pii_key)
                dropped_fields |= dropped
                yield {
                    "id": record["id"],
                    "json_blob": json.dumps(fields),
                    "created_time": record.get("createdTime"),
                    "last_modified": record["fields"].get("Last Modified"),
                }

            offset = data.get("offset")
            if not offset:
                break

        print(f"Loaded {total_records} records from {table_name}")
        if dropped_fields:
            # Names only, never values: new Airtable fields show up here until
            # they are classified in airtable_tables.json.
            print(f"Dropped unclassified fields from {table_name}: {sorted(dropped_fields)}")

    return fetch_table


@dlt.source(name="openoakland")
def airtable_source(tables: dict, base_id: str, api_key: str, pii_key: bytes, cursors: dict):
    """
    One resource per configured Airtable table.

    Named after the pipeline so loads keep using the existing "openoakland"
    schema in the destination. `cursors` maps table name to its cursor, or
    None for a full load.
    """
    return [
        create_airtable_resource(name, config, base_id, api_key, pii_key, cursors.get(name))
        for name, config in tables.items()
    ]
