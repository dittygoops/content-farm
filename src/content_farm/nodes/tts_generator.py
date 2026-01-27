import asyncio
import html
import re
from pathlib import Path
import random
import edge_tts
from rich.console import Console

from content_farm.state import GraphState

console = Console()

# Output directory for generated audio
OUTPUT_DIR = Path("output")


def clean_text_for_tts(text: str) -> str:
    """Clean text for TTS - decode HTML entities and remove markdown."""
    # Decode HTML entities (&gt; -> >, &amp; -> &, etc.)
    text = html.unescape(text)

    # Remove Reddit markdown formatting
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # **bold** -> bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)  # *italic* -> italic
    text = re.sub(r"~~(.+?)~~", r"\1", text)  # ~~strike~~ -> strike
    text = re.sub(r"`(.+?)`", r"\1", text)  # `code` -> code
    text = re.sub(r"^>+\s*", "", text, flags=re.MULTILINE)  # > quotes
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # [link](url) -> link

    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)

    # Clean up extra whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)  # Max 2 newlines
    text = re.sub(r" {2,}", " ", text)  # Max 1 space

    return text.strip()

# Good voices for storytelling content (more natural/conversational ones first)
VOICES = [
    "en-US-AndrewMultilingualNeural",  # Male, very natural conversational
    "en-US-BrianMultilingualNeural",  # Male, natural
    "en-US-AvaMultilingualNeural",  # Female, very natural
]

# Speaking rate: +0% to +30% faster (20% is good for engaging content)
DEFAULT_RATE = "+40%"
DEFAULT_PITCH = "+0Hz"


def build_script(state: GraphState) -> str:
    """Build plain text script with natural pauses using punctuation."""
    post = state.get("approved_post")
    comments = state.get("approved_comments", [])

    if not post:
        return ""

    parts = []

    # Title section
    parts.append(f"Coming hot off the presses, we've got a story from u/{post['author']} on r/{post['subreddit']}")

    # Post title
    parts.append(clean_text_for_tts(post["title"]))

    # Post body
    parts.append(clean_text_for_tts(post["selftext"]))

    # Comments section
    if comments:
        parts.append("Here's what the community is saying:")

        for comment in comments:
            parts.append(f"u/{comment['author']} says:")
            parts.append(clean_text_for_tts(comment["body"]))

    # Call to action
    parts.append("If you enjoyed this story, smash that like button and subscribe for more!")

    return "\n".join(parts)


async def _generate_tts_async(text: str, output_path: Path, voice: str, rate: str, pitch: str) -> None:
    """Generate TTS audio using edge-tts with rate/pitch parameters."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(str(output_path))


def generate_tts(state: GraphState) -> GraphState:
    """Node: Generate TTS audio from approved post and comments."""
    console.print("\n[bold blue]Phase 2: TTS Generation[/bold blue]")

    post = state.get("approved_post")
    if not post:
        console.print("[red]No content to generate TTS for.[/red]")
        return {"tts_script": "", "tts_audio_path": "", "tts_voice": ""}

    # Pick voice - cycle through on regeneration
    voice = random.choice(VOICES)

    # Build plain text script
    script = build_script(state)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Generate unique filename
    post_id = post["id"]
    output_path = OUTPUT_DIR / f"tts_{post_id}.mp3"

    console.print(f"[dim]Voice: {voice}[/dim]")
    console.print(f"[dim]Rate: {DEFAULT_RATE}[/dim]")

    try:
        asyncio.run(_generate_tts_async(script, output_path, voice, DEFAULT_RATE, DEFAULT_PITCH))
        console.print(f"[green]TTS audio saved to: {output_path}[/green]")
    except Exception as e:
        console.print(f"[red]TTS generation failed: {e}[/red]")
        return {"tts_script": script, "tts_audio_path": "", "tts_voice": voice}

    return {
        "tts_script": script,
        "tts_audio_path": str(output_path),
        "tts_voice": voice,
    }
