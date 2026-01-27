import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from content_farm.state import GraphState

console = Console()


def play_audio(audio_path: str) -> bool:
    """Play audio file using system command."""
    path = Path(audio_path)
    if not path.exists():
        console.print(f"[red]Audio file not found: {audio_path}[/red]")
        return False

    console.print(f"[dim]Playing audio: {audio_path}[/dim]")

    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(["afplay", audio_path], check=True)
        elif sys.platform == "win32":  # Windows
            subprocess.run(
                ["powershell", "-c", f'(New-Object Media.SoundPlayer "{audio_path}").PlaySync()'],
                check=True,
            )
        else:  # Linux
            # Try common players
            for player in ["aplay", "paplay", "mpv", "ffplay"]:
                try:
                    subprocess.run([player, audio_path], check=True)
                    break
                except FileNotFoundError:
                    continue
            else:
                console.print("[yellow]No audio player found. Please play manually.[/yellow]")
                return True  # Continue anyway
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to play audio: {e}[/red]")
        return False


def display_tts(state: GraphState) -> GraphState:
    """Node: Display TTS info and play audio for review."""
    audio_path = state.get("tts_audio_path", "")
    script = state.get("tts_script", "")
    voice = state.get("tts_voice", "")

    if not audio_path:
        console.print("[red]No TTS audio generated.[/red]")
        return {}

    # Show script preview
    preview = script[:500]
    if len(script) > 500:
        preview += "\n[dim]...(truncated)[/dim]"

    console.print()
    console.print(
        Panel(
            preview,
            title=f"TTS Script (voice: {voice})",
            border_style="blue",
        )
    )

    # Play the audio
    console.print("\n[bold]Playing TTS audio...[/bold]")
    play_audio(audio_path)

    return {}


def get_tts_approval(state: GraphState) -> GraphState:
    """Node: Get human approval for TTS audio."""
    audio_path = state.get("tts_audio_path", "")

    if not audio_path:
        # No audio, skip to regenerate
        return {}

    console.print("\n[dim](a)pprove | (r)eplay | (j)reject & regenerate | (q)uit[/dim]")
    choice = Prompt.ask(
        "[bold]Action[/bold]",
        choices=["a", "r", "j", "q"],
        default="a",
        show_choices=False,
    )

    if choice == "a":
        console.print("[green]TTS approved![/green]")
        return {"tts_approved": True}
    elif choice == "r":
        # Replay audio
        play_audio(audio_path)
        return {"tts_approved": None}  # Will loop back
    elif choice == "q":
        console.print("[yellow]Quitting...[/yellow]")
        return {"tts_approved": False, "quit": True}
    else:  # reject
        console.print("[yellow]TTS rejected, will regenerate...[/yellow]")
        return {"tts_approved": False, "tts_audio_path": ""}


def should_continue_tts(state: GraphState) -> str:
    """Conditional edge: Determine next step in TTS flow."""
    if state.get("quit"):
        return "quit"

    tts_approved = state.get("tts_approved")

    if tts_approved is True:
        return "approved"
    elif tts_approved is False:
        return "rejected"
    else:
        # None means replay requested
        return "replay"
