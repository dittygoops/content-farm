# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.2.2] - 2026-03-16

### Changed
- Updated `CHANGELOG.md` for testing tamago 

## [0.2.1] - 2026-03-16

### Changed
- Updated `CHANGELOG.md` for testing tamago 

## [0.2.0] - 2026-03-14

### Added
- Persistent seen-post cache (`.seen_posts.json`) that records every approved Reddit post ID so it is never surfaced again in future pipeline runs.
- New `content_farm.utils.seen_posts` module with `load_seen_ids`, `mark_seen`, `mark_seen_batch`, and `is_seen` helpers.
- Scraper now filters already-seen posts before presenting them, logging how many were skipped.

### Changed
- `get_approval` in `human_approval.py` calls `mark_seen` on approval so the cache is updated automatically without extra user interaction.

---

## [0.1.0] - 2026-01-01

### Added
- Initial pipeline: Reddit scraping, TTS generation, video composition, metadata generation, and YouTube upload via browser automation.
