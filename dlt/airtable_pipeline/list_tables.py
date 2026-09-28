#!/usr/bin/env python
"""
Utility to list all tables in an Airtable base and their IDs.
Helps populate airtable_tables.json with the correct table IDs, and lists
each table's field names so they can be classified (allow / pseudonymize).
"""

import os
import json
import requests
import sys


def list_airtable_tables():
    """Fetch and display all tables from the configured Airtable base."""

    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    if not api_key or not base_id:
        print("Error: AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set")
        print("Load them with: export $(cat .env | xargs)")
        sys.exit(1)

    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {"Authorization": f"Bearer {api_key}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 403:
        print("Error: 403 Forbidden")
        print("Verify your API key has the required scopes:")
        print("  - data.records:read")
        print("  - schema.bases:read")
        sys.exit(1)

    response.raise_for_status()

    data = response.json()
    tables = data.get("tables", [])

    if not tables:
        print("No tables found in base")
        sys.exit(0)

    print(f"Found {len(tables)} tables in base {base_id}:\n")
    print("Table Name" + " " * 40 + "Table ID")
    print("-" * 70)

    table_config = {}
    for table in tables:
        name = table["name"]
        table_id = table["id"]
        table_config[name] = {"id": table_id, "allow": [], "pseudonymize": {}}
        print(f"{name:<50} {table_id}")
        for field in table.get("fields", []):
            print(f"    - {field['name']} ({field['type']})")

    print("\n" + "=" * 70)
    print("JSON format for airtable_tables.json:")
    print("=" * 70)
    print(json.dumps({"tables": table_config}, indent=2))


if __name__ == "__main__":
    list_airtable_tables()
