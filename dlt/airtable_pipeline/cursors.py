"""
Incremental cursors, read from the destination itself.

Each table's cursor is the latest Last Modified timestamp already loaded, so it
always matches what actually landed: a dropped or truncated table reloads in
full on the next run. Queries go through dlt's SQL client, so this works on
any SQL destination dlt supports.
"""

from datetime import datetime, timezone
from typing import Iterable, Optional

import dlt
from dlt.destinations.exceptions import DatabaseUndefinedRelation

CURSOR_COLUMN = "last_modified"


def format_cursor(value) -> Optional[str]:
    """
    Format a MAX(last_modified) result for an Airtable filterByFormula.

    Returns ISO 8601 in UTC (YYYY-MM-DDTHH:MM:SS.000Z), or None when there is
    no value. Milliseconds are dropped, so records changed within the same
    second as the cursor are fetched again; the merge on id deduplicates them.
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def get_cursors(pipeline, table_names: Iterable[str]) -> dict:
    """
    Map each table name to its cursor, or None if nothing is loaded yet.

    Only a missing dataset or table counts as "nothing loaded yet". Any other
    error (bad credentials, unreachable database) fails the run rather than
    silently turning into a full reload.
    """
    table_names = list(table_names)
    # Restore the schema and state from the destination if the local working
    # folder is missing (fresh checkout or container), as pipeline.run would.
    pipeline.sync_destination()
    schema = pipeline.default_schema if pipeline.default_schema_name else dlt.Schema(pipeline.pipeline_name)
    naming = schema.naming

    with pipeline.sql_client() as client:
        if not client.has_dataset():
            return {name: None for name in table_names}

        column = client.escape_column_name(naming.normalize_identifier(CURSOR_COLUMN))
        cursors = {}
        for name in table_names:
            table = client.make_qualified_table_name(naming.normalize_table_identifier(name))
            try:
                rows = client.execute_sql(f"SELECT MAX({column}) FROM {table}")
            except DatabaseUndefinedRelation:
                cursors[name] = None
                continue
            cursors[name] = format_cursor(rows[0][0] if rows else None)
        return cursors
