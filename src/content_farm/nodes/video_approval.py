import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from content_farm.state import GraphState

console = Console()


def play_video(video_path: str) -> bool:
    """Open video in default player."""
    path = Path(video_path)
    if not path.exists():
        console.print(f"[red]Video file not found: {video_path}[/red]")
        return False

    console.print(f"[dim]Opening video: {path.name}[/dim]")

    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(["open", video_path], check=True)
        elif sys.platform == "win32":  # Windows
            subprocess.run(["start", "", video_path], shell=True, check=True)
        else:  # Linux
            subprocess.run(["xdg-open", video_path], check=True)
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to open video: {e}[/red]")
        return False


def preview_video(state: GraphState) -> GraphState:
    """Node: Open video for preview."""
    video_path = state.get("video_path", "")
    duration = state.get("video_duration", 0)

    if not video_path:
        console.print("[red]No video generated.[/red]")
        return {}

    console.print(f"\n[bold]Video Preview[/bold]")
    console.print(f"[dim]Duration: {duration:.1f}s[/dim]")
    console.print(f"[dim]Path: {video_path}[/dim]")

    play_video(video_path)

    return {}


def get_video_approval(state: GraphState) -> GraphState:
    """Node: Get human approval for composed video."""
    video_path = state.get("video_path", "")

    if not video_path:
        return {"video_approved": False}

    console.print("\n[dim](a)pprove | (r)eopen video | (j)reject & recompose | (q)uit[/dim]")
    choice = Prompt.ask(
        "[bold]Action[/bold]",
        choices=["a", "r", "j", "q"],
        default="a",
        show_choices=False,
    )

    if choice == "a":
        console.print("[green]Video approved![/green]")
        return {"video_approved": True}
    elif choice == "r":
        play_video(video_path)
        return {"video_approved": None}  # Loop back to approval
    elif choice == "q":
        console.print("[yellow]Quitting...[/yellow]")
        return {"video_approved": False, "quit": True}
    else:  # reject
        console.print("[yellow]Video rejected, will recompose...[/yellow]")
        return {"video_approved": False}


def should_continue_video(state: GraphState) -> str:
    """Conditional edge: Determine next step in video flow."""
    if state.get("quit"):
        return "quit"

    video_path = state.get("video_path", "")
    video_approved = state.get("video_approved")

    if not video_path:
        return "no_video"

    if video_approved is True:
        return "approved"
    elif video_approved is None:
        return "reopen"
    else:
        return "rejected"
