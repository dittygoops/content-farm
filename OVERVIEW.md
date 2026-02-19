# Content Farm - Architecture Overview

Automated pipeline for creating short-form video content from Reddit posts.

## Current Status

**Phase 1: Reddit Scraping + Human Approval** (Complete)

## Tech Stack

| Component | Tool | Notes |
|-----------|------|-------|
| Orchestration | LangGraph (Python) | Graph-based workflows with human-in-the-loop |
| Reddit Scraping | Reddit JSON API | No auth needed, append `.json` to URLs |
| Console UI | Rich | Panels, prompts, colored output |
| LLM (future) | Groq | Free tier |
| TTS | edge-tts | Free Microsoft TTS |
| Video | FFmpeg | Composition with captions |
| Browser automation (future) | browser-use | For YouTube upload |

## Project Structure

```
content-farm/
├── pyproject.toml              # Dependencies & project config
├── OVERVIEW.md                 # This file
├── .gitignore
├── output/                     # Generated audio/video files
├── music/                      # YouTube Audio Library tracks (user-provided)
├── video/                      # Background videos (subway surfers, etc.)
└── src/content_farm/
    ├── __init__.py
    ├── main.py                 # Entry point
    ├── state.py                # GraphState & type definitions
    ├── graph.py                # LangGraph workflow definition
    ├── filters.py              # Bot/mod detection filters
    └── nodes/
        ├── __init__.py
        ├── reddit_scraper.py   # Fetches posts from subreddits
        ├── human_approval.py   # Post display + approval UI
        ├── comment_scraper.py  # Fetches comments from approved post
        ├── comment_approval.py # Comment display + approval UI
        ├── tts_generator.py    # Generates TTS audio with edge-tts
        ├── tts_approval.py     # TTS playback + approval UI
        ├── music_picker.py     # Random music selection
        ├── video_composer.py   # FFmpeg video composition
        └── video_approval.py   # Video preview + approval UI
```

## Graph Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           POST SELECTION                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   scrape_reddit ──► display_post ──► get_approval                       │
│                          ▲               │                              │
│                          │               ▼                              │
│                          │         ┌──────────┐                         │
│                          │         │ continue │──────┐                  │
│                          │         │ approved │──┐   │                  │
│                          │         │ exhausted│  │   │                  │
│                          │         └──────────┘  │   │                  │
│                          │               │       │   │                  │
│                          └───────────────┼───────┘   │                  │
│                                          │           │                  │
│                                     [to END]         │                  │
│                                                      ▼                  │
├─────────────────────────────────────────────────────────────────────────┤
│                         COMMENT SELECTION                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                      │                  │
│                                               fetch_comments            │
│                                                      │                  │
│                                                      ▼                  │
│   ┌──────────────────── display_comment ◄── get_comment_approval        │
│   │                          ▲                       │                  │
│   │                          │                       ▼                  │
│   │                          │              ┌─────────────────┐         │
│   │                          │              │ continue        │─────┐   │
│   │                          │              │ done (3 approved│     │   │
│   │                          │              │ exhausted       │     │   │
│   │                          │              │ post_rejected   │──┐  │   │
│   │                          │              └─────────────────┘  │  │   │
│   │                          └───────────────────────────────────┼──┘   │
│   │                                                              │      │
│   │                         [back to display_post] ◄─────────────┘      │
│   │                                                                     │
│   └────────────────────────────► END                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## State Schema

```python
class GraphState(TypedDict, total=False):
    # Post selection
    subreddits: list[str]              # Subreddits to scrape
    posts: list[RedditPost]            # All fetched posts
    current_post_index: int            # Current post being reviewed
    approved_post: RedditPost | None   # The selected post
    rejection_count: int               # Posts reviewed count

    # Comment selection
    all_comments: list[RedditComment]       # Fetched comments for review
    current_comment_index: int              # Current comment being reviewed
    approved_comments: list[RedditComment]  # User-approved comments (target: 3)
```

## User Controls

### Post Approval
| Key | Action |
|-----|--------|
| `a` | Approve post, proceed to comments |
| `r` | Reject post, show next |
| `s` | Skip 5 posts |
| `q` | Quit |

### Comment Approval
| Key | Action |
|-----|--------|
| `a` | Approve comment |
| `r` | Reject comment, show next |
| `p` | Reject entire post, go back to post selection |
| `q` | Quit |

## Filters

Bot and mod content is automatically filtered out:
- 30+ known bot accounts (AutoModerator, RepostSleuthBot, etc.)
- Username patterns (`*bot`, `*_bot`, `bot_*`, etc.)
- Distinguished mod/admin posts and comments
- Stickied posts
- Deleted/removed content

## Running

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the console app
python -m content_farm.main
```

## Complete Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PHASE 1: CONTENT SELECTION                       │
│                              (Complete)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   scrape_reddit ──► display_post ──► get_approval                       │
│                          ▲               │                              │
│                          └── continue ───┘                              │
│                                          │ approved                     │
│                                          ▼                              │
│                     fetch_comments ──► display_comment ──► get_comment  │
│                          ▲                    ▲               │         │
│                          │                    └── continue ───┘         │
│                          └── post_rejected ───────┘                     │
│                                                   │ done (3 approved)   │
└───────────────────────────────────────────────────┼─────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   PHASE 2: TTS + MUSIC (Automatic)                      │
│                              (Complete)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                  generate_tts ──► pick_music (random from music/)       │
│                                        │                                │
│                                        │ (no approval needed)           │
│                                        │                                │
└────────────────────────────────────────┼────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        PHASE 3: VIDEO COMPOSITION                       │
│                              (Complete)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│       compose_video (background + viral captions + TTS + music)         │
│                                 │                                       │
│         - 1080x1920 (YouTube Shorts format)                             │
│         - Per-letter gradient captions with liquid glass effect         │
│         - Background video from video/ directory                        │
│                                 │                                       │
│                                 ▼                                       │
│                   preview_video ──► get_video_approval                  │
│                        ▲                    │                           │
│                        │                    ▼                           │
│                        │           ┌──────────────┐                     │
│                        │           │ approved ────┼──► END              │
│                        │           │ rejected     │                     │
│                        │           │ reopen       │                     │
│                        │           └──────────────┘                     │
│                        │                    │                           │
│                        └────────────────────┘                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        PHASE 4: FINALIZATION                            │
│                              (Planned)                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                  verify_length (warn if out of bounds)                  │
│                                 │                                       │
│                                 ▼                                       │
│                  generate_meta (title / description / hashtags)         │
│                                 │                                       │
│                                 ▼                                       │
│                  approve_meta (accept / edit inline / reject)           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        PHASE 5: UPLOAD                                  │
│                              (Planned)                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                  upload_youtube (browser-use)                           │
│                                 │                                       │
│                                 ▼                                       │
│                                END                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Content Selection (Reddit + Comments) | ✅ Complete |
| 2 | TTS + Music (automatic, no approval) | ✅ Complete |
| 3 | Video Composition (viral captions) | ✅ Complete |
| 4 | Finalization (length check + metadata) | ✅ Complete |
| 5 | YouTube Upload | ✅ Complete |
