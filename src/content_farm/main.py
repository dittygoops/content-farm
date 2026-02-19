#!/usr/bin/env python3
"""Main entry point for the content farm console app."""

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console

from content_farm.graph import create_app
from content_farm.state import GraphState

console = Console()


def main():
    console.print("[bold blue]Content Farm - Reddit Scraper[/bold blue]")
    console.print("[dim]Fetching top posts from subreddits...[/dim]\n")

    # Default subreddits good for story content
    initial_state: GraphState = {
        "subreddits": [
            "tifu",
            "AmItheAsshole",
            "relationship_advice",
            "pettyrevenge",
            "MaliciousCompliance",
        ],
        "posts": [],
        "current_post_index": 0,
        "approved_post": None,
        "rejection_count": 0,
    }

    app = create_app()
    final_state = app.invoke(initial_state)

    # Summary
    console.print("\n" + "=" * 50)
    if final_state.get("approved_post"):
        post = final_state["approved_post"]
        console.print(f"[green]Approved post:[/green] {post['title']}")
        console.print(f"[dim]From r/{post['subreddit']} with {post['score']} upvotes[/dim]")
        console.print(f"[dim]Permalink: https://reddit.com{post['permalink']}[/dim]")

        comments = final_state.get("approved_comments", [])
        if comments:
            console.print(f"[green]Approved {len(comments)} comments:[/green]")
            for i, comment in enumerate(comments, 1):
                preview = comment["body"][:80].replace("\n", " ")
                if len(comment["body"]) > 80:
                    preview += "..."
                console.print(f"  [dim]{i}. u/{comment['author']}: {preview}[/dim]")

        # TTS info
        tts_path = final_state.get("tts_audio_path")
        if tts_path:
            console.print(f"[green]TTS audio:[/green] {tts_path}")

        # Music info
        music_path = final_state.get("music_path")
        if music_path:
            from pathlib import Path
            console.print(f"[green]Music:[/green] {Path(music_path).name}")

        # Video info
        video_path = final_state.get("video_path")
        if video_path:
            duration = final_state.get("video_duration", 0)
            console.print(f"[green]Video:[/green] {video_path}")
            console.print(f"[dim]Duration: {duration:.1f}s[/dim]")

        # Metadata info
        meta_title = final_state.get("meta_title")
        if meta_title:
            console.print(f"[green]Title:[/green] {meta_title}")
            description = final_state.get("meta_description", "")
            hashtags = final_state.get("meta_hashtags", [])
            if description:
                console.print(f"[dim]Description: {description}[/dim]")
            if hashtags:
                console.print(f"[dim]Hashtags: {' '.join(hashtags)}[/dim]")

        # Upload info
        youtube_url = final_state.get("youtube_url")
        if youtube_url:
            console.print(f"[green]YouTube URL:[/green] {youtube_url}")
    else:
        console.print("[yellow]No post was approved.[/yellow]")

    console.print(f"[dim]Posts reviewed: {final_state.get('rejection_count', 0) + (1 if final_state.get('approved_post') else 0)}[/dim]")

    return final_state


if __name__ == "__main__":
    main()
