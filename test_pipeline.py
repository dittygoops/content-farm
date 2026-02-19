#!/usr/bin/env python3
"""Quick test script with a fake short post to test the full pipeline."""

from rich.console import Console

from content_farm.graph import create_app
from content_farm.state import GraphState, RedditPost, RedditComment

console = Console()


def main():
    console.print("[bold blue]Content Farm - Pipeline Test[/bold blue]")
    console.print("[dim]Testing with fake short post...[/dim]\n")

    # Fake post with very short content
    fake_post: RedditPost = {
        "id": "test123",
        "title": "TIFU by testing my code",
        "selftext": "I spent hours debugging. Turns out it was a typo. Classic.",
        "author": "test_user",
        "subreddit": "tifu",
        "score": 9999,
        "url": "https://reddit.com/r/tifu/test123",
        "num_comments": 100,
        "permalink": "/r/tifu/comments/test123/tifu_by_testing_my_code/",
    }

    # Fake comments
    fake_comments: list[RedditComment] = [
        {
            "id": "c1",
            "body": "Happens to the best of us!",
            "author": "commenter1",
            "score": 500,
            "permalink": "/r/tifu/comments/test123/c1/",
        },
        {
            "id": "c2",
            "body": "The real TIFU is always in the comments.",
            "author": "commenter2",
            "score": 300,
            "permalink": "/r/tifu/comments/test123/c2/",
        },
    ]

    # Pre-approved state - skip straight to TTS generation
    initial_state: GraphState = {
        "subreddits": ["tifu"],
        "posts": [fake_post],
        "current_post_index": 1,  # Past the fake post
        "approved_post": fake_post,
        "rejection_count": 0,
        "all_comments": fake_comments,
        "current_comment_index": 2,
        "approved_comments": fake_comments,
    }

    app = create_app()

    # Run from generate_tts node directly
    from content_farm.nodes.tts_generator import generate_tts
    from content_farm.nodes.music_picker import pick_music
    from content_farm.nodes.video_composer import compose_video
    from content_farm.nodes.video_approval import preview_video, get_video_approval, should_continue_video

    state = initial_state

    # TTS (no approval, automatic)
    console.print("\n[bold cyan]--- TTS Generation ---[/bold cyan]")
    state = {**state, **generate_tts(state)}

    # Music
    console.print("\n[bold cyan]--- Music Selection ---[/bold cyan]")
    state = {**state, **pick_music(state)}

    # Video
    console.print("\n[bold cyan]--- Video Composition ---[/bold cyan]")
    state = {**state, **compose_video(state)}

    while True:
        preview_video(state)
        state = {**state, **get_video_approval(state)}
        result = should_continue_video(state)
        if result == "approved":
            break
        elif result == "rejected":
            state = {**state, **compose_video(state)}
        elif result in ("quit", "no_video"):
            console.print("[yellow]Done[/yellow]")
            return state
        # reopen loops back to preview

    # Summary
    console.print("\n" + "=" * 50)
    console.print(f"[green]TTS audio:[/green] {state.get('tts_audio_path')}")
    console.print(f"[green]Music:[/green] {state.get('music_path')}")
    console.print(f"[green]Video:[/green] {state.get('video_path')}")
    console.print(f"[dim]Duration: {state.get('video_duration', 0):.1f}s[/dim]")

    return state


if __name__ == "__main__":
    main()
