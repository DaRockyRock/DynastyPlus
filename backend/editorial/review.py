"""The editorial-review pass: a capable model adds taste, never breaks the floor.

On mid+ tiers only, one bounded call lets the model improve the deterministic
rundown in strictly WHITELISTED ways: reorder the slate, sharpen the one-line
angle, or promote a single near-miss from the bench. Code applies only those
changes (unknown ids ignored, no new facts), so the deterministic slate is the
floor and the model's judgment is the ceiling. CoVe-lite is a second-pass
fact-check on the lead story for the same tiers.
"""
from __future__ import annotations

import re
from typing import Any

from .. import llm

_REVIEW_SYSTEM = (
    "You are the executive editor reviewing a college football news desk's ranked "
    "rundown. You may ONLY: reorder the stories, rewrite a story's one-line angle to be "
    "sharper (no new facts), and promote at most one bench story you think was "
    "underrated. You may NOT invent stories or facts. Return strict JSON: "
    '{"order_national": [ids], "order_program": [ids], "promote": "id or null", '
    '"angles": {"id": "sharper one-line angle"}}.')


def _summary(c: dict) -> str:
    facts = "; ".join(str(v) for k, v in (c.get("facts") or {}).items() if v and k != "note")
    return f"[{c.get('id')}] ({c.get('type')}) {facts[:140]}"


def _apply(rv: dict, national: list[dict], program: list[dict],
           bench: list[dict]) -> tuple[list[dict], list[dict]]:
    """Apply ONLY whitelisted changes. Pure and safe against garbage: unknown ids are
    ignored, every original story is preserved, no facts are added."""
    by_id = {c["id"]: c for c in national + program + bench}

    def reorder(items: list[dict], order_ids: Any) -> list[dict]:
        present = {c["id"]: c for c in items}
        order_ids = order_ids if isinstance(order_ids, list) else []
        ordered = [present[i] for i in order_ids if i in present]
        rest = [c for c in items if c not in ordered]      # preserve anything not listed
        return ordered + rest

    nat = reorder(national, rv.get("order_national"))
    prog = reorder(program, rv.get("order_program"))
    pid = rv.get("promote")
    if isinstance(pid, str) and pid in {c["id"] for c in bench}:
        c = by_id[pid]
        (prog if c.get("scope") == "program" else nat).append(c)
    angles = rv.get("angles") if isinstance(rv.get("angles"), dict) else {}
    for c in nat + prog:
        a = angles.get(c["id"])
        if isinstance(a, str) and a.strip():
            c["review_angle"] = a.strip()[:160]
    return nat, prog


def review_slate(national: list[dict], program: list[dict], bench: list[dict],
                 *, enabled: bool) -> tuple[list[dict], list[dict]]:
    """Reorder/sharpen/promote via the model (mid+ only). Falls back to the input
    unchanged on any failure, so the deterministic slate is always the floor."""
    if not enabled or not (national or program):
        return national, program
    try:
        prompt = ("NATIONAL slate:\n" + "\n".join("  " + _summary(c) for c in national)
                  + "\n\nPROGRAM slate:\n" + "\n".join("  " + _summary(c) for c in program)
                  + "\n\nBENCH (promote at most one):\n"
                  + "\n".join("  " + _summary(c) for c in bench[:6])
                  + "\n\nReturn your edits as JSON.")
        rv = llm.generate_json(_REVIEW_SYSTEM, prompt, max_tokens=400, temperature=0.3)
        if isinstance(rv, dict):
            return _apply(rv, national, program, bench)
    except Exception:
        pass
    return national, program


# --- CoVe-lite: a focused fact self-check on the lead -----------------------
_COVE_SYSTEM = (
    "You verify a sports article against its source facts. List every proper-noun "
    "name and every number in the ARTICLE, and for each say whether it is supported by "
    "the FACTS. Return strict JSON: {\"unsupported\": [\"the name or number not in the "
    "facts\", ...]}. Empty list if everything checks out.")


def cove_unsupported(article: dict, facts: list[str], *, enabled: bool) -> list[str]:
    """Model self-check on the lead story; returns items it judges unsupported by the
    facts. Best-effort (empty on any failure), mid+ only. The deterministic validator
    remains the always-on floor; this is extra scrutiny on the most important article."""
    if not enabled:
        return []
    body = article.get("body") or ""
    if isinstance(body, list):
        body = " ".join(str(x) for x in body)
    try:
        prompt = ("FACTS:\n" + "\n".join("  - " + f for f in facts)
                  + f"\n\nARTICLE:\n{article.get('headline', '')}. {body}\n\nVerify:")
        rv = llm.generate_json(_COVE_SYSTEM, prompt, max_tokens=200, temperature=0.0)
        items = rv.get("unsupported") if isinstance(rv, dict) else None
        return [str(x) for x in items][:6] if isinstance(items, list) else []
    except Exception:
        return []
