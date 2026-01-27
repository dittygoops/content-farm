import httpx
from rich.console import Console

from content_farm.filters import should_skip_comment
from content_farm.state import GraphState, RedditComment

REDDIT_BASE_URL = "https://www.reddit.com"
USER_AGENT = "ContentFarm/0.1 (educational project)"

console = Console()


def scrape_comments(permalink: str, limit: int = 3) -> list[RedditComment]:
    """Scrape top comments from a Reddit post."""
    url = f"{REDDIT_BASE_URL}{permalink}.json"
    params = {"limit": 100, "sort": "top"}
    headers = {"User-Agent": USER_AGENT}

    response = httpx.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()

    data = response.json()

    # Reddit returns [post_data, comments_data]
    if len(data) < 2:
        return []

    comments_data = data[1]["data"]["children"]
    comments: list[RedditComment] = []

    for child in comments_data:
        if child["kind"] != "t1":  # t1 = comment
            continue

        comment_data = child["data"]

        # Skip bots, mods, and deleted comments
        if should_skip_comment(comment_data):
            continue

        comments.append(
            RedditComment(
                id=comment_data["id"],
                body=comment_data["body"],
                author=comment_data["author"],
                score=comment_data.get("score", 0),
                permalink=comment_data.get("permalink", ""),
            )
        )

        if len(comments) >= limit:
            break

    return comments


def fetch_comments(state: GraphState) -> GraphState:
    """Node: Fetch all comments from the approved post for review."""
    approved_post = state.get("approved_post")

    if not approved_post:
        console.print("[yellow]No approved post to scrape comments from.[/yellow]")
        return {"all_comments": [], "current_comment_index": 0, "approved_comments": []}

    console.print(f"\n[dim]Fetching comments from the approved post...[/dim]")

    try:
        # Fetch more comments than we need to allow for rejections
        comments = scrape_comments(approved_post["permalink"], limit=20)
    except Exception as e:
        console.print(f"[red]Failed to scrape comments: {e}[/red]")
        return {"all_comments": [], "current_comment_index": 0, "approved_comments": []}

    console.print(f"[dim]Found {len(comments)} comments to review.[/dim]")

    return {
        "all_comments": comments,
        "current_comment_index": 0,
        "approved_comments": [],
    }
