"""Reactions to reporter-broken news.

Real life does not only react to what the coach says. When the newsroom breaks a
story this week (a program injury, a portal or recruiting move, the coach
reportedly leaving, or a big national shake-up), the world reacts the way it does
to the coach's own words: the reporter's scoop hits the social timeline as
breaking news, other media and fans pile on, and (for stories about the user's
program) players, recruits, the AD, and rivals text the coach about it.

This is the reporter-origin twin of the coach-statement cascade. world.react()
fires off something the COACH said; world.react_to_coverage() (which this module
drives) fires off something a REPORTER broke. Both write the durable world-event
log and deliver event-keyed, unread texts, so re-running the pipeline never
doubles up.

Like `inbound`, this is a side-effect pass: its real work is logging feed
reactions and delivering texts, not a tab of its own. It is registered just
before `phone` so the people it pulls in have live threads when the roster is
built, and it is held for the presser alongside the news it reacts to (so the
world reacts to the post-game coverage, not stale pre-game headlines).
"""
from __future__ import annotations

from typing import Any

from .. import progress
from . import base

MODULE = "news_reactions"


def generate(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    # Imported lazily: world pulls in the feed/news modules, so importing it at
    # module load would tangle the modules package's own import order.
    from .. import world

    progress.set_sub_step("Reactions to the week's news")
    outcome = world.react_to_coverage(dynasty, year=year, week=week, use_llm=use_llm)
    source = "llm" if (use_llm and base.llm_available()) else "mock"
    return {"module": MODULE, "source": source, "week": week,
            "reacted": outcome.get("stories", []), "texts": outcome.get("texts", [])}
