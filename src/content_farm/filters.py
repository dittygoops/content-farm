"""Filters for Reddit content to exclude bots, mods, and unwanted content."""

import re

# Known bot account names (lowercase for comparison)
KNOWN_BOTS = {
    "automoderator",
    "autotldr",
    "remindmebot",
    "sneakpeekbot",
    "repostsleuthbot",
    "savevideo",
    "savevideobot",
    "downloadvideo",
    "vredditdownloader",
    "gif_slowing_bot",
    "stabbot",
    "sub_doesnt_exist_bot",
    "haikibot",
    "nice-hierarchi",
    "wikipedia_answer_bot",
    "twitterbot",
    "tweetlinker",
    "linkifybot",
    "cooldownbot",
    "profanitycounter",
    "userleansbot",
    "botdefense",
    "anti-hierarchi",
    "totesmessenger",
    "snapshillbot",
    "originalpostsearchbot",
    "haikubot",
    "converter-bot",
    "timezone_bot",
    "metric_units_bot",
    "commonmisspellingbot",
    "grammarbot",
    "spelling-hierarchi",
}

# Patterns that indicate bot accounts
BOT_PATTERNS = [
    r"bot$",           # ends with "bot"
    r"_bot$",          # ends with "_bot"
    r"^bot_",          # starts with "bot_"
    r"_?bot_?",        # contains "bot" with optional underscores
    r"auto.*mod",      # automod variants
    r"transcriber",    # transcription bots
    r"reminder",       # reminder bots
]

# Compile patterns for efficiency
_bot_regex = re.compile("|".join(BOT_PATTERNS), re.IGNORECASE)


def is_bot_username(username: str) -> bool:
    """Check if a username appears to be a bot."""
    if not username:
        return True

    username_lower = username.lower()

    # Check known bots
    if username_lower in KNOWN_BOTS:
        return True

    # Check patterns
    if _bot_regex.search(username_lower):
        return True

    return False


def is_mod_content(data: dict) -> bool:
    """Check if content is from a moderator acting in official capacity."""
    # "distinguished" field is set for mod/admin posts
    # Values: "moderator", "admin", or null
    distinguished = data.get("distinguished")
    if distinguished in ("moderator", "admin"):
        return True

    return False


def should_skip_post(post_data: dict) -> bool:
    """Check if a post should be skipped."""
    # Stickied posts are usually mod announcements
    if post_data.get("stickied", False):
        return True

    # No text content
    selftext = post_data.get("selftext", "")
    if not selftext or selftext in ("[removed]", "[deleted]"):
        return True

    # Bot or mod post
    author = post_data.get("author", "")
    if is_bot_username(author):
        return True

    if is_mod_content(post_data):
        return True

    return False


def should_skip_comment(comment_data: dict) -> bool:
    """Check if a comment should be skipped."""
    # No content
    body = comment_data.get("body", "")
    if not body or body in ("[removed]", "[deleted]"):
        return True

    # Bot or mod comment
    author = comment_data.get("author", "")
    if not author or author == "[deleted]":
        return True

    if is_bot_username(author):
        return True

    if is_mod_content(comment_data):
        return True

    return False
