import asyncio
import sys
from pathlib import Path

from browser_use import Agent
from browser_use.browser.profile import BrowserProfile
from browser_use.browser.session import BrowserSession
from rich.console import Console
from rich.prompt import Prompt

from content_farm.llm.claude import ChatClaude
from content_farm.state import GraphState

console = Console()

# macOS default Chrome user data dir
_CHROME_USER_DATA = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"


def _build_task(state: GraphState) -> str:
    video_path = Path(state["video_path"]).resolve()
    title = state.get("meta_title", "")
    description = state.get("meta_description", "")
    hashtags = state.get("meta_hashtags", [])

    # Combine description + hashtags into YT description field
    full_description = description
    if hashtags:
        full_description += "\n\n" + " ".join(hashtags)

    return f"""Upload a YouTube Short using YouTube Studio.

Video file path: {video_path}

Title: {title}
Description (copy exactly, including hashtags):
{full_description}

Steps:
1. Go to https://studio.youtube.com
2. Click the "Create" button (camera+ icon, top right)
3. Click "Upload videos"
4. Click "SELECT FILES" and upload the file at: {video_path}
5. Wait for the upload to finish processing
6. In the "Details" step:
   - Set the title to exactly: {title}
   - Set the description to exactly: {full_description}
   - Under "Audience", select "No, it's not made for kids"
7. In the "Video elements" step: click "Next"
8. In the "Checks" step: click "Next"
9. In the "Visibility" step: select "Public", then click "Publish"
10. Confirm the video was published and return the video URL

Important: Do not change any settings not mentioned above."""


async def _run_upload(task: str, profile_dir: str) -> str:
    """Run the browser-use agent to upload the video."""
    llm = ChatClaude(model="claude-haiku-4-5-20251001", max_tokens=4096)

    profile = BrowserProfile(
        user_data_dir=str(_CHROME_USER_DATA),
        profile_directory=profile_dir,
        headless=False,  # Must be visible for file picker
    )
    session = BrowserSession(browser_profile=profile)

    agent = Agent(
        task=task,
        llm=llm,
        browser_session=session,
        max_failures=5,
        use_vision=True,
        vision_detail_level="low",
        max_actions_per_step=10,
    )

    history = await agent.run(max_steps=40)
    return history.final_result() or ""


def upload_youtube(state: GraphState) -> GraphState:
    """Node: Upload the composed video to YouTube using browser-use + Claude."""
    console.print("\n[bold blue]Phase 5: YouTube Upload[/bold blue]")

    video_path = state.get("video_path", "")
    if not video_path or not Path(video_path).exists():
        console.print("[red]No video file found to upload.[/red]")
        return {"youtube_url": ""}

    title = state.get("meta_title", "")
    if not title:
        console.print("[red]No metadata found. Run generate_meta first.[/red]")
        return {"youtube_url": ""}

    # Let user pick Chrome profile if they have multiple
    console.print(f"\n[dim]Chrome user data dir: {_CHROME_USER_DATA}[/dim]")
    profile_dir = Prompt.ask(
        "[bold]Chrome profile directory[/bold]",
        default="Default",
    )

    console.print(f"\n[bold]Uploading:[/bold] {title}")
    console.print("[dim]A browser window will open. Do not interact with it.[/dim]\n")

    task = _build_task(state)

    try:
        result = asyncio.run(_run_upload(task, profile_dir))
        console.print(f"\n[green]Upload complete![/green]")
        if result:
            console.print(f"[dim]{result}[/dim]")
        # Try to extract URL from result
        import re
        url_match = re.search(r"https://(?:www\.)?youtube\.com/\S+", result)
        youtube_url = url_match.group(0) if url_match else ""
        return {"youtube_url": youtube_url}
    except Exception as e:
        console.print(f"[red]Upload failed: {e}[/red]")
        return {"youtube_url": ""}
