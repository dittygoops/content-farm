from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from content_farm.state import GraphState

console = Console()


def _display_meta(state: GraphState) -> None:
    """Print current metadata in a Rich panel."""
    title = state.get("meta_title", "")
    description = state.get("meta_description", "")
    hashtags = state.get("meta_hashtags", [])
    warning = state.get("length_warning")

    content = Text()

    if warning:
        content.append(f"⚠  {warning}\n\n", style="yellow")

    content.append("Title\n", style="bold")
    content.append(f"{title}\n", style="cyan")
    content.append(f"[{len(title)}/80 chars]\n\n", style="dim")

    content.append("Description\n", style="bold")
    content.append(f"{description}\n\n", style="white")

    content.append("Hashtags\n", style="bold")
    content.append(" ".join(hashtags), style="blue")

    console.print(Panel(content, title="[bold]YouTube Metadata[/bold]", border_style="blue"))


def _edit_meta(state: GraphState) -> dict:
    """Let the user edit each metadata field inline."""
    console.print("[dim]Press Enter to keep current value.[/dim]\n")

    current_title = state.get("meta_title", "")
    current_description = state.get("meta_description", "")
    current_hashtags = state.get("meta_hashtags", [])

    new_title = Prompt.ask(
        "[bold]Title[/bold]",
        default=current_title,
    )

    new_description = Prompt.ask(
        "[bold]Description[/bold]",
        default=current_description,
    )

    hashtags_str = Prompt.ask(
        "[bold]Hashtags[/bold] (space-separated)",
        default=" ".join(current_hashtags),
    )
    new_hashtags = [t if t.startswith("#") else f"#{t}" for t in hashtags_str.split()]

    return {
        "meta_title": new_title,
        "meta_description": new_description,
        "meta_hashtags": new_hashtags,
    }


def approve_meta(state: GraphState) -> GraphState:
    """Node: Display generated metadata and get human approval."""
    _display_meta(state)

    console.print("\n[dim](a)pprove | (e)dit | (r)egenerate | (q)uit[/dim]")
    choice = Prompt.ask(
        "[bold]Action[/bold]",
        choices=["a", "e", "r", "q"],
        default="a",
        show_choices=False,
    )

    if choice == "a":
        console.print("[green]Metadata approved![/green]")
        return {"meta_approved": True}

    elif choice == "e":
        updated = _edit_meta(state)
        console.print("[green]Metadata updated.[/green]")
        # Re-display after editing
        merged = {**state, **updated}
        _display_meta(merged)  # type: ignore[arg-type]
        # Confirm after edit
        confirm = Prompt.ask(
            "[bold]Approve edited metadata?[/bold]",
            choices=["y", "n"],
            default="y",
        )
        if confirm == "y":
            return {**updated, "meta_approved": True}
        else:
            return {**updated, "meta_approved": None}  # loop back to approve_meta

    elif choice == "r":
        console.print("[yellow]Regenerating metadata...[/yellow]")
        return {"meta_approved": None, "meta_title": "", "meta_description": "", "meta_hashtags": []}

    else:  # quit
        console.print("[yellow]Quitting...[/yellow]")
        return {"meta_approved": False, "quit": True}


def should_continue_meta(state: GraphState) -> str:
    """Conditional edge: Determine next step after metadata approval."""
    if state.get("quit"):
        return "quit"

    approved = state.get("meta_approved")
    title = state.get("meta_title", "")

    if approved is True:
        return "approved"
    elif not title:
        # Empty title means regenerate was chosen
        return "regenerate"
    else:
        # Has title but not approved = edited but not confirmed, loop back
        return "edit"
