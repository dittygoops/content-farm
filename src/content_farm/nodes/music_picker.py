import random
from pathlib import Path

from rich.console import Console

from content_farm.state import GraphState

console = Console()

MUSIC_DIR = Path("music")
SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def get_available_music() -> list[str]:
    """Get list of music files from the music/ directory."""
    if not MUSIC_DIR.exists():
        return []

    files = []
    for f in MUSIC_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(str(f))

    return sorted(files)


def pick_music(state: GraphState) -> GraphState:
    """Node: Pick a random music track from the music/ folder."""
    console.print("\n[bold blue]Phase 3: Music Selection[/bold blue]")

    available = get_available_music()

    if not available:
        console.print("[red]No music files found in music/ directory![/red]")
        console.print("[dim]Add .mp3, .wav, .m4a, .aac, .flac, or .ogg files to music/[/dim]")
        return {"music_path": ""}

    music_path = random.choice(available)
    console.print(f"[green]Selected:[/green] {Path(music_path).name}")

    return {"music_path": music_path}
