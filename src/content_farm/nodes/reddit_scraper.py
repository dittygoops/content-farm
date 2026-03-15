import httpx
from rich.console import Console

from content_farm.filters import should_skip_post
from content_farm.state import GraphState, RedditPost
from content_farm.utils.seen_posts import load_seen_ids

REDDIT_BASE_URL = "https://www.reddit.com"
USER_AGENT = "ContentFarm/0.1 (educational project)"

console = Console()


def scrape_subreddit(subreddit: str, limit: int = 25) -> list[RedditPost]:
    """Scrape top posts from a subreddit using Reddit's JSON API."""
    url = f"{REDDIT_BASE_URL}/r/{subreddit}/hot.json"
    params = {"limit": limit}
    headers = {"User-Agent": USER_AGENT}

    response = httpx.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()

    data = response.json()
    posts: list[RedditPost] = []

    for child in data["data"]["children"]:
        post_data = child["data"]

        # Skip bots, mods, stickied, and empty posts
        if should_skip_post(post_data):
            continue

        posts.append(
            RedditPost(
                id=post_data["id"],
                title=post_data["title"],
                selftext=post_data["selftext"],
                author=post_data["author"],
                subreddit=post_data["subreddit"],
                score=post_data["score"],
                url=post_data["url"],
                num_comments=post_data["num_comments"],
                permalink=post_data["permalink"],
            )
        )

    return posts


def scrape_reddit(state: GraphState) -> GraphState:
    """Node: Scrape posts from configured subreddits."""
    subreddits = state.get("subreddits", ["AskReddit", "tifu", "AmItheAsshole"])
    all_posts: list[RedditPost] = []

    for subreddit in subreddits:
        try:
            posts = scrape_subreddit(subreddit, limit=10)
            all_posts.extend(posts)
        except Exception as e:
            print(f"Failed to scrape r/{subreddit}: {e}")

    # Filter posts we've already processed in previous runs
    seen_ids = load_seen_ids()
    if seen_ids:
        before = len(all_posts)
        all_posts = [p for p in all_posts if p["id"] not in seen_ids]
        skipped = before - len(all_posts)
        if skipped:
            console.print(f"[dim]Skipped {skipped} already-seen post(s).[/dim]")

    # Sort by score descending
    all_posts.sort(key=lambda p: p["score"], reverse=True)

    return {
        "posts": all_posts,
        "current_post_index": 0,
        "rejection_count": 0,
    }
