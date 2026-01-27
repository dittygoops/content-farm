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
from content_farm.nodes.tts_approval import display_tts, get_tts_approval, should_continue_tts
from content_farm.nodes.music_picker import pick_music


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

    # Add nodes - TTS generation
    graph.add_node("generate_tts", generate_tts)
    graph.add_node("display_tts", display_tts)
    graph.add_node("get_tts_approval", get_tts_approval)

    # Add nodes - Music selection
    graph.add_node("pick_music", pick_music)

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

    # TTS generation flow
    graph.add_edge("generate_tts", "display_tts")
    graph.add_edge("display_tts", "get_tts_approval")

    graph.add_conditional_edges(
        "get_tts_approval",
        should_continue_tts,
        {
            "approved": "pick_music",  # Proceed to music selection
            "rejected": "generate_tts",
            "replay": "display_tts",
            "quit": END,
        },
    )

    # Music selection flow (auto-pick, no approval needed)
    graph.add_edge("pick_music", END)  # TODO: Next phase (compose_video)

    return graph


def create_app():
    """Create the compiled LangGraph application."""
    graph = build_graph()
    return graph.compile()
