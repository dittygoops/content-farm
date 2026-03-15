"""Persistent cache for seen Reddit post IDs.

Tracks which post IDs have already been processed (approved or rejected) so
the scraper can skip them on future runs. The cache is stored as a JSON file
at ``.seen_posts.json`` in the current working directory.
"""

import json
from pathlib import Path

CACHE_PATH = Path(".seen_posts.json")


def load_seen_ids() -> set[str]:
    """Return the set of post IDs that have already been processed."""
    if not CACHE_PATH.exists():
        return set()
    try:
        data = json.loads(CACHE_PATH.read_text())
        return set(data.get("seen_ids", []))
    except (json.JSONDecodeError, OSError):
        return set()


def mark_seen(post_id: str) -> None:
    """Add *post_id* to the persistent cache."""
    seen = load_seen_ids()
    seen.add(post_id)
    _write(seen)


def mark_seen_batch(post_ids: list[str]) -> None:
    """Add multiple post IDs to the persistent cache in a single write."""
    seen = load_seen_ids()
    seen.update(post_ids)
    _write(seen)


def is_seen(post_id: str) -> bool:
    """Return True if *post_id* is already in the cache."""
    return post_id in load_seen_ids()


def _write(seen: set[str]) -> None:
    CACHE_PATH.write_text(json.dumps({"seen_ids": sorted(seen)}, indent=2))
