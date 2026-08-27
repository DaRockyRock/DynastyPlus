"""Generation modules.

Each module exposes `generate(dynasty, *, year, week, use_llm, regenerate)`
and returns JSON-serializable content. Modules serve rich mock content when
the LLM is unavailable so the entire UI is populated for design work.
"""
from . import (  # noqa: F401
    top_stories,
    news_feed,
    cfp_committee,
    recruiting,
    portal,
    hot_seat,
    awards,
    archive,
    nil_budget,
    phone,
    inbound,
    feed,
    news_reactions,
)

# Registry: module key -> module object. Order drives the full pipeline.
# `inbound` runs just before `phone` so the people who text the coach first this
# week have live threads by the time the phone roster is assembled.
REGISTRY = {
    # news_feed runs first: it generates the week's shared coverage (the articles
    # and their full reader pages), which the top-stories slider then views.
    "news_feed": news_feed,
    "top_stories": top_stories,
    "cfp_committee": cfp_committee,
    "recruiting": recruiting,
    "portal": portal,
    "hot_seat": hot_seat,
    "awards": awards,
    "archive": archive,
    "nil_budget": nil_budget,
    "inbound": inbound,
    # `news_reactions` runs after `inbound` and before `phone` (same reason): the
    # people the newsroom's breaking stories pull into the coach's texts need live
    # threads by the time the phone roster is assembled. It also logs the breaking
    # feed posts, which `feed` (last) folds into the timeline.
    "news_reactions": news_reactions,
    "phone": phone,
    # `feed` runs last so it can read every other module's cached output for the
    # week (articles + bylines, rankings, recruiting, hot seat...) and turn it into
    # a social-media timeline.
    "feed": feed,
}
