from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from content_farm.state import GraphState
from content_farm.utils.seen_posts import mark_seen

console = Console()


def display_post(state: GraphState) -> GraphState:
    """Node: Display current post for human review."""
    posts = state.get("posts", [])
    index = state.get("current_post_index", 0)

    if index >= len(posts):
        console.print("[red]No more posts available![/red]")
        return {"approved_post": None}

    post = posts[index]

    # Build display
    header = Text()
    header.append(f"r/{post['subreddit']}", style="cyan")
    header.append(" | ", style="dim")
    header.append(f"u/{post['author']}", style="green")
    header.append(" | ", style="dim")
    header.append(f"{post['score']} upvotes", style="yellow")
    header.append(" | ", style="dim")
    header.append(f"{post['num_comments']} comments", style="blue")

    content = f"[bold]{post['title']}[/bold]\n\n{post['selftext'][:1500]}"
    if len(post["selftext"]) > 1500:
        content += "\n[dim]...(truncated)[/dim]"

    console.print()
    console.print(f"[dim]Post {index + 1} of {len(posts)}[/dim]")
    console.print(Panel(content, title=header, border_style="blue"))

    return {}


def get_approval(state: GraphState) -> GraphState:
    """Node: Get human approval decision via console input."""
    posts = state.get("posts", [])
    index = state.get("current_post_index", 0)

    if index >= len(posts):
        return {"approved_post": None}

    post = posts[index]

    console.print("\n[dim](a)pprove | (r)eject | (s)kip 5 | (q)uit[/dim]")

    choice = Prompt.ask(
        "\n[bold]Action[/bold]",
        choices=["a", "r", "s", "q"],
        default="r",
        show_choices=False,
    )

    if choice == "a":
        console.print("[green]Post approved![/green]")
        mark_seen(post["id"])
        return {"approved_post": post}
    elif choice == "s":
        new_index = min(index + 5, len(posts))
        return {
            "current_post_index": new_index,
            "rejection_count": state.get("rejection_count", 0) + 5,
        }
    elif choice == "q":
        console.print("[yellow]Quitting...[/yellow]")
        return {"approved_post": None, "current_post_index": len(posts)}
    else:  # reject
        return {
            "current_post_index": index + 1,
            "rejection_count": state.get("rejection_count", 0) + 1,
        }


def should_continue(state: GraphState) -> str:
    """Conditional edge: Determine if we should show another post or end."""
    if state.get("approved_post") is not None:
        return "approved"

    posts = state.get("posts", [])
    index = state.get("current_post_index", 0)

    if index >= len(posts):
        return "exhausted"

    return "continue"
