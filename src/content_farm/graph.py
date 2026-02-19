from langgraph.graph import StateGraph, END

from content_farm.state import GraphState
from content_farm.nodes.reddit_scraper import scrape_reddit
from content_farm.nodes.human_approval import display_post, get_approval, should_continue
from content_farm.nodes.comment_scraper import fetch_comments
from content_farm.nodes.comment_approval import (
    display_comment,
    get_comment_approval,
    should_continue_comments,
)
from content_farm.nodes.tts_generator import generate_tts
from content_farm.nodes.music_picker import pick_music
from content_farm.nodes.video_composer import compose_video
from content_farm.nodes.video_approval import (
    preview_video,
    get_video_approval,
    should_continue_video,
)
from content_farm.nodes.meta_generator import verify_length, generate_meta
from content_farm.nodes.meta_approval import approve_meta, should_continue_meta
from content_farm.nodes.youtube_uploader import upload_youtube


def build_graph() -> StateGraph:
    """Build the content farm approval workflow graph."""
    graph = StateGraph(GraphState)

    # Add nodes - Post selection
    graph.add_node("scrape_reddit", scrape_reddit)
    graph.add_node("display_post", display_post)
    graph.add_node("get_approval", get_approval)

    # Add nodes - Comment selection
    graph.add_node("fetch_comments", fetch_comments)
    graph.add_node("display_comment", display_comment)
    graph.add_node("get_comment_approval", get_comment_approval)

    # Add nodes - TTS generation (no approval, auto-proceeds)
    graph.add_node("generate_tts", generate_tts)

    # Add nodes - Music selection
    graph.add_node("pick_music", pick_music)

    # Add nodes - Video composition
    graph.add_node("compose_video", compose_video)
    graph.add_node("preview_video", preview_video)
    graph.add_node("get_video_approval", get_video_approval)

    # Add nodes - Phase 4: Finalization
    graph.add_node("verify_length", verify_length)
    graph.add_node("generate_meta", generate_meta)
    graph.add_node("approve_meta", approve_meta)

    # Add nodes - Phase 5: Upload
    graph.add_node("upload_youtube", upload_youtube)

    # Set entry point
    graph.set_entry_point("scrape_reddit")

    # Post selection flow
    graph.add_edge("scrape_reddit", "display_post")
    graph.add_edge("display_post", "get_approval")

    graph.add_conditional_edges(
        "get_approval",
        should_continue,
        {
            "continue": "display_post",
            "approved": "fetch_comments",
            "exhausted": END,
        },
    )

    # Comment selection flow
    graph.add_edge("fetch_comments", "display_comment")
    graph.add_edge("display_comment", "get_comment_approval")

    graph.add_conditional_edges(
        "get_comment_approval",
        should_continue_comments,
        {
            "continue": "display_comment",
            "done": "generate_tts",
            "exhausted": END,
            "post_rejected": "display_post",
        },
    )

    # TTS generation flow (no approval, auto-proceeds to music)
    graph.add_edge("generate_tts", "pick_music")

    # Music selection flow (auto-pick, no approval needed)
    graph.add_edge("pick_music", "compose_video")

    # Video composition flow
    graph.add_edge("compose_video", "preview_video")
    graph.add_edge("preview_video", "get_video_approval")

    graph.add_conditional_edges(
        "get_video_approval",
        should_continue_video,
        {
            "approved": "verify_length",
            "rejected": "compose_video",
            "reopen": "preview_video",
            "no_video": END,
            "quit": END,
        },
    )

    # Finalization flow
    graph.add_edge("verify_length", "generate_meta")
    graph.add_edge("generate_meta", "approve_meta")

    graph.add_conditional_edges(
        "approve_meta",
        should_continue_meta,
        {
            "approved": "upload_youtube",
            "regenerate": "generate_meta",
            "edit": "approve_meta",
            "quit": END,
        },
    )

    # Upload flow
    graph.add_edge("upload_youtube", END)

    return graph


def create_app():
    """Create the compiled LangGraph application."""
    graph = build_graph()
    return graph.compile()
