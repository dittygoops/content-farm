import json
import random
import subprocess
from pathlib import Path
import re
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn

from content_farm.state import GraphState

console = Console()

VIDEO_DIR = Path("video")
OUTPUT_DIR = Path("output")

# YouTube Shorts format
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920

# Music volume (0.0 to 1.0) - lower so TTS is clear
MUSIC_VOLUME = 0.15


def get_media_duration(file_path: str) -> float:
    """Get duration of audio/video file using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def get_background_video() -> str | None:
    """Get the first video from the video/ directory."""
    if not VIDEO_DIR.exists():
        return None

    videos = list(VIDEO_DIR.iterdir())
    return str(videos[0]) if videos else None


def generate_subtitles(script: str, duration: float, output_path: Path) -> None:
    """Generate ASS subtitle file with viral-style centered captions."""
    # ASS header with viral TikTok/Shorts styling
    # - Centered on screen (Alignment 5 = middle center)
    # - Large bold text with black outline
    # - Per-letter gradient colors for flashy effect
    # - Liquid glass effect using blurred glow layer
    ass_header = """[Script Info]
Title: Content Farm Captions
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,115,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,5,40,40,0,1
Style: GlassGlow,Arial Black,115,&H60000000,&H000000FF,&H50000000,&H00000000,-1,0,0,0,100,100,0,0,1,50,0,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # Gradient color palettes (ASS uses BGR: &HBBGGRR)
    # Smooth gradients with more color stops for per-letter effect
    gradients = [
        ["&H00FFFF", "&H00FFAA", "&H00FF55", "&H00FF00", "&H55FF00"],  # Yellow -> Green
        ["&HFF00FF", "&HFF00AA", "&HFF0055", "&HFF0000", "&HAA0000"],  # Magenta -> Blue
        ["&HFFFF00", "&HFFAA55", "&HFF55AA", "&HFF00FF", "&HAA00FF"],  # Cyan -> Magenta
        ["&H0055FF", "&H00AAFF", "&H00FFFF", "&H55FFAA", "&HAAFF55"],  # Orange -> Yellow -> Green
        ["&HFF0055", "&HFF00AA", "&HFF00FF", "&HAA55FF", "&H55AAFF"],  # Pink -> Purple -> Blue
        ["&H00FF00", "&H55FF55", "&HAAFF00", "&HFFFF00", "&HFFAA00"],  # Green -> Yellow -> Cyan
    ]

    # Split script into chunks of 8-12 words for 2-line display
    all_words = script.replace("\n", " ").split()
    chunks = []
    current_chunk = []

    for word in all_words:
        current_chunk.append(word)
        if len(current_chunk) >= 10:
            chunks.append(current_chunk)
            current_chunk = []

    if current_chunk:
        chunks.append(current_chunk)

    if not chunks:
        chunks = [[""]]

    # Calculate timing - comfortable reading pace
    buffer = 0.3
    effective_duration = duration - (buffer * 2)
    time_per_chunk = effective_duration / len(chunks) if chunks else 1

    # Balanced timing
    min_display_time = 2.0
    max_display_time = 4.0
    time_per_chunk = max(min_display_time, min(time_per_chunk, max_display_time))

    def format_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    def interpolate_color(color1: str, color2: str, t: float) -> str:
        """Interpolate between two ASS colors (BGR format &HBBGGRR)."""
        # Parse colors
        c1 = int(color1[2:], 16)
        c2 = int(color2[2:], 16)

        b1, g1, r1 = (c1 >> 16) & 0xFF, (c1 >> 8) & 0xFF, c1 & 0xFF
        b2, g2, r2 = (c2 >> 16) & 0xFF, (c2 >> 8) & 0xFF, c2 & 0xFF

        # Interpolate
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)

        return f"&H{b:02X}{g:02X}{r:02X}"

    def get_gradient_color(gradient: list[str], position: float) -> str:
        """Get color at position (0-1) along gradient."""
        if position <= 0:
            return gradient[0]
        if position >= 1:
            return gradient[-1]

        # Find which segment we're in
        segment_size = 1.0 / (len(gradient) - 1)
        segment_idx = int(position / segment_size)
        segment_idx = min(segment_idx, len(gradient) - 2)

        # Position within segment (0-1)
        local_t = (position - segment_idx * segment_size) / segment_size

        return interpolate_color(gradient[segment_idx], gradient[segment_idx + 1], local_t)

    def apply_letter_gradient(words: list[str], gradient: list[str]) -> str:
        """Apply smooth gradient colors per letter across all text."""
        if not words:
            return ""

        # Join all words, count total letters
        full_text = " ".join(words).upper()
        total_letters = len(full_text.replace(" ", ""))

        if total_letters == 0:
            return full_text

        # Build result with per-letter colors
        result_chars = []
        letter_idx = 0

        for char in full_text:
            if char == " ":
                result_chars.append(" ")
            else:
                # Calculate position in gradient (0-1)
                pos = letter_idx / max(total_letters - 1, 1)
                color = get_gradient_color(gradient, pos)

                # Escape special ASS characters
                escaped_char = char
                if char == "\\":
                    escaped_char = "\\\\"
                elif char == "{":
                    escaped_char = "\\{"
                elif char == "}":
                    escaped_char = "\\}"

                result_chars.append("{\\c" + color + "}" + escaped_char)
                letter_idx += 1

        result = "".join(result_chars)

        # Split into two lines at roughly the middle space
        words_in_result = result.split(" ")
        if len(words_in_result) <= 3:
            return result

        mid = len(words_in_result) // 2
        line1 = " ".join(words_in_result[:mid])
        line2 = " ".join(words_in_result[mid:])
        return f"{line1}\\N{line2}"

    events = []
    current_time = buffer

    for idx, chunk_words in enumerate(chunks):
        start_time = current_time
        end_time = start_time + time_per_chunk

        if end_time > duration - buffer:
            end_time = duration - buffer

        if start_time >= duration - buffer:
            break

        start_str = format_time(start_time)
        end_str = format_time(end_time)

        # Plain text for the glass glow background (no colors)
        plain_text = " ".join(chunk_words).upper()
        words_list = plain_text.split()
        if len(words_list) > 3:
            mid = len(words_list) // 2
            plain_text = " ".join(words_list[:mid]) + "\\N" + " ".join(words_list[mid:])

        # Apply per-letter gradient for the foreground text
        gradient = gradients[idx % len(gradients)]
        gradient_text = apply_letter_gradient(chunk_words, gradient)

        # Layer 0: Liquid glass glow - heavily blurred for soft rounded effect
        # \blur30 creates soft edges, \bord50 makes it wide
        glass_text = "{\\blur30}" + plain_text
        events.append(f"Dialogue: 0,{start_str},{end_str},GlassGlow,,0,0,0,,{glass_text}")
        # Layer 1: Gradient text foreground with crisp outline
        events.append(f"Dialogue: 1,{start_str},{end_str},Default,,0,0,0,,{gradient_text}")

        current_time = end_time

    # Write ASS file
    with open(output_path, "w") as f:
        f.write(ass_header)
        f.write("\n".join(events))


def compose_video(state: GraphState) -> GraphState:
    """Node: Compose final video with background, TTS, music, and captions."""
    console.print("\n[bold blue]Phase 4: Video Composition[/bold blue]")

    tts_path = state.get("tts_audio_path", "")
    music_path = state.get("music_path", "")
    script = state.get("tts_script", "")

    if not tts_path or not Path(tts_path).exists():
        console.print("[red]TTS audio not found![/red]")
        return {"video_path": "", "video_duration": 0}

    # Get background video
    bg_video = get_background_video()
    if not bg_video:
        console.print("[red]No background video found in video/ directory![/red]")
        return {"video_path": "", "video_duration": 0}

    console.print(f"[dim]Background: {Path(bg_video).name}[/dim]")

    # Get durations
    tts_duration = get_media_duration(tts_path)
    bg_duration = get_media_duration(bg_video)

    console.print(f"[dim]TTS duration: {tts_duration:.1f}s[/dim]")

    # Check duration limit (3 minutes)
    if tts_duration > 180:
        console.print(f"[yellow]Warning: Video will be {tts_duration:.1f}s (over 3 min limit)[/yellow]")

    # Pick random start point in background video
    max_start = max(0, bg_duration - tts_duration - 1)
    start_time = random.uniform(0, max_start) if max_start > 0 else 0

    console.print(f"[dim]Background start: {start_time:.1f}s[/dim]")

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Generate subtitle file
    post = state.get("approved_post")
    post_id = post["id"] if post else "unknown"
    subtitle_path = OUTPUT_DIR / f"subs_{post_id}.ass"
    generate_subtitles(script, tts_duration, subtitle_path)

    # Output path
    output_path = OUTPUT_DIR / f"video_{post_id}.mp4"

    console.print("[dim]Composing video with FFmpeg...[/dim]")

    # Build FFmpeg command
    # 1. Take background video from start_time for tts_duration
    # 2. Scale/crop to 9:16 (1080x1920)
    # 3. Add TTS audio
    # 4. Mix in background music at lower volume
    # 5. Burn in subtitles

    # 1. More robust escaping for the subtitle path
    # FFmpeg's subtitle filter requires colons to be escaped and the whole path to be single-quoted
    sub_path_escaped = str(subtitle_path).replace("\\", "/").replace(":", "\\:").replace("'", "'\\\\''")

    # 2. Build filter_complex using filename='...' explicitly
    if music_path and Path(music_path).exists():
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,setsar=1,"
            f"subtitles=filename='{sub_path_escaped}'[outv];"  # added filename=
            f"[1:a]volume=1.0[tts];"
            f"[2:a]volume={MUSIC_VOLUME}[music];"
            f"[tts][music]amix=inputs=2:duration=first:dropout_transition=2[outa]"
        )
        audio_output = "[outa]"
        video_output = "[outv]"
        has_music = True
    else:
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,setsar=1,"
            f"subtitles=filename='{sub_path_escaped}'[outv]"  # added filename=
        )
        audio_output = "1:a"
        video_output = "[outv]"
        has_music = False

    # Debug: print filter_complex (escape brackets for rich)
    debug_filter = filter_complex[:150].replace("[", "\\[").replace("]", "\\]")
    console.print(f"[dim]Filter: {debug_filter}...[/dim]")

    # 1. Prepare the Command (Same as before)
    cmd = [
        "ffmpeg", "-y", "-ss", str(start_time), "-i", bg_video,
        "-i", tts_path,
    ]
    if has_music:
        cmd.extend(["-i", music_path])

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", video_output, "-map", audio_output,
        "-t", str(tts_duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        str(output_path),
    ])

    # 2. Progress Bar Logic
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
    ) as progress:
        
        task = progress.add_task("[cyan]Composing Video...", total=100)
        
        # We use subprocess.Popen to read the output line by line
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, universal_newlines=True
        )

        # Regex to find 'time=HH:MM:SS.ms' in FFmpeg output
        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

        for line in process.stdout:
            match = time_pattern.search(line)
            if match:
                # Convert FFmpeg time to seconds
                hours, minutes, seconds = map(float, match.groups())
                current_time = hours * 3600 + minutes * 60 + seconds
                
                # Calculate percentage
                percentage = min(100, (current_time / tts_duration) * 100)
                progress.update(task, completed=percentage)

        process.wait()

        if process.returncode != 0:
            console.print("[red]FFmpeg failed. Check logs.[/red]")
            return {"video_path": "", "video_duration": 0}

        console.print(f"[green]✔ Video saved: {output_path.name}[/green]")

    return {"video_path": str(output_path), "video_duration": tts_duration}
