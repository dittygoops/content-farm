from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from content_farm.state import GraphState

console = Console()

TARGET_COMMENTS = 3


def display_comment(state: GraphState) -> GraphState:
    """Node: Display current comment for human review."""
    comments = state.get("all_comments", [])
    index = state.get("current_comment_index", 0)
    approved = state.get("approved_comments", [])

    if index >= len(comments):
        console.print("[red]No more comments available![/red]")
        return {}

    comment = comments[index]

    # Build header
    header = Text()
    header.append(f"u/{comment['author']}", style="green")
    header.append(" | ", style="dim")
    header.append(f"{comment['score']} pts", style="yellow")

    body = comment["body"][:800]
    if len(comment["body"]) > 800:
        body += "\n[dim]...(truncated)[/dim]"

    console.print()
    console.print(
        f"[dim]Comment {index + 1} of {len(comments)} | "
        f"Approved: {len(approved)}/{TARGET_COMMENTS}[/dim]"
    )
    console.print(Panel(body, title=header, border_style="cyan"))

    return {}


def get_comment_approval(state: GraphState) -> GraphState:
    """Node: Get human approval decision for current comment."""
    comments = state.get("all_comments", [])
    index = state.get("current_comment_index", 0)
    approved = state.get("approved_comments", []).copy()  # Copy to avoid mutation

    if index >= len(comments):
        return {}

    comment = comments[index]

    console.print("[dim](a)pprove | (r)eject | (p)ost reject - go back to posts | (q)uit[/dim]")
    choice = Prompt.ask(
        "[bold]Action[/bold]",
        choices=["a", "r", "p", "q"],
        default="a",
        show_choices=False,
    )

    if choice == "a":
        approved.append(comment)
        console.print(f"[green]Comment approved! ({len(approved)}/{TARGET_COMMENTS})[/green]")
        return {
            "approved_comments": approved,
            "current_comment_index": index + 1,
        }
    elif choice == "p":
        # Reject entire post, go back to post selection
        console.print("[yellow]Rejecting post, going back to post selection...[/yellow]")
        return {
            "approved_post": None,
            "all_comments": [],
            "approved_comments": [],
            "current_comment_index": 0,
            "current_post_index": state.get("current_post_index", 0) + 1,
        }
    elif choice == "q":
        console.print("[yellow]Quitting...[/yellow]")
        # Mark as exhausted by clearing comments
        return {
            "all_comments": [],
            "current_comment_index": 0,
        }
    else:  # reject comment
        console.print("[dim]Comment rejected, showing next...[/dim]")
        return {
            "current_comment_index": index + 1,
        }


def should_continue_comments(state: GraphState) -> str:
    """Conditional edge: Determine next step in comment approval flow."""
    approved = state.get("approved_comments", [])
    comments = state.get("all_comments", [])
    index = state.get("current_comment_index", 0)
    approved_post = state.get("approved_post")

    # User rejected the post - go back to post selection
    if approved_post is None:
        return "post_rejected"

    # Got enough approved comments
    if len(approved) >= TARGET_COMMENTS:
        return "done"

    # Ran out of comments
    if index >= len(comments):
        return "exhausted"

    # Keep reviewing comments
    return "continue"
