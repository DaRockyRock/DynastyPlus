"""The editorial engine: code is the editor, the model is the writer.

Deterministic weekly pipeline (see docs/editorial-engine.md): world state ->
expectation model (Elo/surprisal) -> Stakes Computer -> candidate detection ->
salience scoring -> seeded MMR selection -> rundown -> grounding briefs for the
generators. Build-plan step 1 feeds the existing news prompts; later steps add
the entity canon, per-beat realization, personas, and the arc registry.
"""
from . import arcs, claims, promises
from .briefs import build_rundown, feed_brief, national_brief, presser_brief, program_brief
from .canon import Canon, build as build_canon
from .profile import ModelProfile, current as current_profile, record_latency
from .realize import realize_coverage
from .social import social_posts
from .state import WorldState, extract as extract_state
from .validate import check_article, passes as validate_passes

__all__ = [
    "build_rundown", "feed_brief", "national_brief", "presser_brief", "program_brief",
    "realize_coverage", "social_posts",
    "Canon", "build_canon", "check_article", "validate_passes",
    "ModelProfile", "current_profile", "record_latency",
    "WorldState", "extract_state",
    "arcs", "claims", "promises",
]
