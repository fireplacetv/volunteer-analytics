"""
Field-level PII handling for Airtable records.

Every field is treated one of three ways, per table, in airtable_tables.json:
- allow: passed through unchanged
- pseudonymize: replaced before the record leaves memory
    - "hash": keyed HMAC-SHA256 of the normalized value, stored as <field>_hash
    - "first_name" / "last_name" / "full_name": a stable word-based fake name
- unused: known fields deliberately left out (dropped, but documented here
  so they are easy to find later and are not reported as unclassified)
- anything else: dropped and reported as unclassified
"""

import hashlib
import hmac
import os

PII_KEY_ENV = "PII_HASH_KEY"

PSEUDONYM_METHODS = {"hash", "first_name", "last_name", "full_name"}

WORDLIST_DIR = os.path.join(os.path.dirname(__file__), "wordlists")


def load_wordlist(name: str) -> list[str]:
    """Load one word per line from wordlists/<name>.txt, ignoring blanks."""
    with open(os.path.join(WORDLIST_DIR, f"{name}.txt")) as f:
        return [line.strip() for line in f if line.strip()]


# Fake names are built from these lists, e.g. "Brave Otter". They are for
# readability only: two people can share a fake name, so never join or count
# on them. Use the *_hash fields or record IDs instead. Editing the lists
# changes existing fake names on the next full reload.
ADJECTIVES = load_wordlist("adjectives")
ANIMALS = load_wordlist("animals")


def get_pii_key() -> bytes:
    """Return the HMAC key. Fails the run rather than loading unmasked PII."""
    key = os.getenv(PII_KEY_ENV)
    if not key:
        raise ValueError(
            f"{PII_KEY_ENV} must be set; refusing to load PII without it. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return key.encode()


def normalize(value) -> str:
    return str(value).strip().lower()


def hash_value(value, key: bytes) -> str:
    """Keyed hash of a normalized value, so equal emails match across tables."""
    return hmac.new(key, normalize(value).encode(), hashlib.sha256).hexdigest()


def fake_name(digest: str, method: str) -> str:
    """Pick a stable fake name from a hex digest."""
    first = ADJECTIVES[int(digest[:16], 16) % len(ADJECTIVES)]
    last = ANIMALS[int(digest[16:32], 16) % len(ANIMALS)]
    if method == "first_name":
        return first
    if method == "last_name":
        return last
    return f"{first} {last}"


def hashed_field_name(field: str) -> str:
    return f"{field.lower()}_hash"


def validate_table_config(table_name: str, config: dict) -> None:
    groups = {
        "allow": set(config.get("allow", [])),
        "pseudonymize": set(config.get("pseudonymize", {})),
        "unused": set(config.get("unused", [])),
    }
    names = list(groups)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            overlap = groups[a] & groups[b]
            if overlap:
                raise ValueError(f"{table_name}: fields in both {a} and {b}: {sorted(overlap)}")
    pseudonymize = config.get("pseudonymize", {})
    unknown = {m for m in pseudonymize.values() if m not in PSEUDONYM_METHODS}
    if unknown:
        raise ValueError(f"{table_name}: unknown pseudonymize methods: {sorted(unknown)}")


def filter_fields(record_id: str, fields: dict, config: dict, key: bytes) -> tuple[dict, set]:
    """
    Apply a table's allow/pseudonymize config to one record's fields.

    Returns the filtered fields and the set of field names that were dropped
    because they are not classified at all (fields listed as unused are dropped
    silently). Values of dropped fields are discarded.
    """
    allow = config.get("allow", [])
    pseudonymize = config.get("pseudonymize", {})

    out = {f: fields[f] for f in allow if f in fields}

    # Fake names are seeded from the record's hashed identifier (e.g. email) so
    # the same person gets the same fake name in every table. Records without
    # one fall back to their record ID.
    seed = None
    for field, method in pseudonymize.items():
        if method == "hash" and fields.get(field):
            seed = hash_value(fields[field], key)
            break
    if seed is None:
        seed = hash_value(record_id, key)

    for field, method in pseudonymize.items():
        value = fields.get(field)
        if not value:
            continue
        if method == "hash":
            out[hashed_field_name(field)] = hash_value(value, key)
        else:
            out[field] = fake_name(seed, method)

    dropped = set(fields) - set(allow) - set(pseudonymize) - set(config.get("unused", []))
    return out, dropped
