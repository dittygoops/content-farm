from typing import TypedDict


class RedditPost(TypedDict):
    id: str
    title: str
    selftext: str
    author: str
    subreddit: str
    score: int
    url: str
    num_comments: int
    permalink: str


class RedditComment(TypedDict):
    id: str
    body: str
    author: str
    score: int
    permalink: str


class GraphState(TypedDict, total=False):
    # Post selection
    subreddits: list[str]
    posts: list[RedditPost]
    current_post_index: int
    approved_post: RedditPost | None
    rejection_count: int
    # Comment selection
    all_comments: list[RedditComment]  # All fetched comments
    current_comment_index: int
    approved_comments: list[RedditComment]  # User-approved comments (target: 3)
    # TTS generation
    tts_script: str  # Full script for TTS (post + comments + CTA)
    tts_audio_path: str  # Path to generated audio file
    tts_voice: str  # Voice used for generation
    tts_approved: bool | None  # None = replay, True = approved, False = rejected
    # Global
    quit: bool  # User requested quit
