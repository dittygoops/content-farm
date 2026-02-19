import anthropic
from rich.console import Console

from content_farm.state import GraphState

console = Console()

# YouTube Shorts duration bounds (seconds)
SHORTS_MIN = 5
SHORTS_MAX = 60


def verify_length(state: GraphState) -> GraphState:
    """Node: Warn if video duration is outside YouTube Shorts bounds."""
    console.print("\n[bold blue]Phase 4: Finalization[/bold blue]")

    duration = state.get("video_duration", 0)
    warning = None

    if duration == 0:
        warning = "Could not determine video duration."
        console.print(f"[yellow]Warning: {warning}[/yellow]")
    elif duration > SHORTS_MAX:
        warning = f"Video is {duration:.1f}s — exceeds YouTube Shorts limit of {SHORTS_MAX}s."
        console.print(f"[yellow]Warning: {warning}[/yellow]")
    elif duration < SHORTS_MIN:
        warning = f"Video is {duration:.1f}s — below minimum Shorts length of {SHORTS_MIN}s."
        console.print(f"[yellow]Warning: {warning}[/yellow]")
    else:
        console.print(f"[green]Length OK:[/green] {duration:.1f}s (within {SHORTS_MIN}–{SHORTS_MAX}s)")

    return {"length_warning": warning}


def generate_meta(state: GraphState) -> GraphState:
    """Node: Use Claude to generate YouTube title, description, and hashtags."""
    console.print("\n[dim]Generating metadata with Claude...[/dim]")

    post = state.get("approved_post")
    comments = state.get("approved_comments", [])

    if not post:
        console.print("[red]No approved post to generate metadata for.[/red]")
        return {"meta_title": "", "meta_description": "", "meta_hashtags": []}

    # Build context for the prompt
    comment_snippets = "\n".join(
        f"- u/{c['author']}: {c['body'][:200]}" for c in comments[:3]
    )

    prompt = f"""You are writing metadata for a YouTube Shorts video based on a Reddit post.

Reddit post:
- Subreddit: r/{post['subreddit']}
- Title: {post['title']}
- Author: u/{post['author']}
- Body (first 500 chars): {post['selftext'][:500]}

Top comments:
{comment_snippets}

Generate the following for the YouTube Short:

1. TITLE: A punchy, curiosity-driving title (max 80 characters). Do NOT use quotation marks. Don't spoil the story. Make it irresistible to click.

2. DESCRIPTION: 2–3 sentences. Briefly tease the story, credit the subreddit (e.g. "via r/{post['subreddit']}"), and add a call-to-action to like and subscribe.

3. HASHTAGS: Exactly 8 hashtags. Mix broad ones (#shorts #reddit #story) with ones specific to the content. No spaces within tags. Output them space-separated on one line.

Respond in exactly this format (no extra text):
TITLE: <title here>
DESCRIPTION: <description here>
HASHTAGS: <hashtag1> <hashtag2> ...
"""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Parse structured response
    title = ""
    description = ""
    hashtags: list[str] = []

    for line in raw.splitlines():
        if line.startswith("TITLE:"):
            title = line[len("TITLE:"):].strip()
        elif line.startswith("DESCRIPTION:"):
            description = line[len("DESCRIPTION:"):].strip()
        elif line.startswith("HASHTAGS:"):
            raw_tags = line[len("HASHTAGS:"):].strip()
            hashtags = [t if t.startswith("#") else f"#{t}" for t in raw_tags.split()]

    if not title:
        console.print("[yellow]Warning: Could not parse title from Claude response.[/yellow]")
        console.print(f"[dim]Raw response:\n{raw}[/dim]")

    console.print("[green]Metadata generated.[/green]")

    return {
        "meta_title": title,
        "meta_description": description,
        "meta_hashtags": hashtags,
        "meta_approved": None,
    }
