"""Shared machinery for the two customization stores.

The customization data splits along the game/media boundary that the two-app
architecture draws:

  * customization_game.py - team identity, head coach, program blueprint, staff,
    roster, recruits, the transfer portal, rivals. This is GAME data, owned and
    edited by the Simulator (a CFB 27 stand-in) and written into the save file.
  * customization.py - reporters, outlets, the CFP committee, the hot-seat board,
    award voters, awards, phone contacts. This is MEDIA flavor, owned and edited
    by the Dynasty+ companion and read directly by the generation modules.

Each store owns a disjoint set of sections persisted to its own JSON file, so the
two apps never write the same file. Everything they share - the declarative field
schema, persona enrichment, the no-em-dash / no-emoji house rules, and the
merge/persist logic - lives here as a `Store` the two modules instantiate.

This module is a leaf: it depends only on config + personality.
"""
from __future__ import annotations

import copy
import json
import re
import threading
from pathlib import Path
from typing import Any, Callable

from . import personality

# Reusable option sets, shared by the schema (frontend dropdowns) and as light
# documentation of the allowed values.
CLASS_YEARS = ["FR", "SO", "JR", "SR", "GR"]
DEALBREAKERS = [
    "Brand Exposure", "Playing Time", "NFL Readiness", "Development",
    "Proximity to Home", "Championship Culture", "Coaching Stability",
]
RECRUIT_STAGES = ["Open", "Top 10", "Top 5", "Top 3", "Verbal", "Hard Commit", "Committed"]
BEATS = ["national", "recruiting", "program", "carousel", "portal", "feature"]
TRENDS = ["up", "flat", "down"]
CONTACT_CATEGORIES = ["Staff", "Players", "Recruits", "Coaches", "Media"]
ENTITY_KINDS = ["none", "recruit", "player", "staff", "budget"]

# Precomputed option lists for the schema field definitions.
DEALBREAKER_OPTS = [{"value": d, "label": d} for d in DEALBREAKERS]
STAGE_OPTS = [{"value": s, "label": s} for s in RECRUIT_STAGES]
YEAR_OPTS = [{"value": y, "label": y} for y in CLASS_YEARS]
BEAT_OPTS = [{"value": b, "label": b.title()} for b in BEATS]
TREND_OPTS = [{"value": t, "label": t.title()} for t in TRENDS]
CATEGORY_OPTS = [{"value": c, "label": c} for c in CONTACT_CATEGORIES]
ENTITY_OPTS = [{"value": k, "label": k.title()} for k in ENTITY_KINDS]

# The options bundle handed to the frontend editor (same for both stores).
EDITOR_OPTIONS = {
    "dealbreakers": DEALBREAKERS,
    "stages": RECRUIT_STAGES,
    "class_years": CLASS_YEARS,
    "beats": BEATS,
}


def field(key: str, label: str, type_: str = "text", **extra: Any) -> dict[str, Any]:
    """A single schema field definition (the old `_f` helper)."""
    return {"key": key, "label": label, "type": type_, **extra}


# Every persona section gains a Biography + Personality editor field.
PERSONA_FIELDS = [
    field("bio", "Biography", "textarea", width="full",
          help="Backstory and character that shape how this person behaves and talks."),
    field("traits", "Personality", "personality", width="full"),
]


def attach_personas(schema: list[dict[str, Any]],
                    persona_sections: dict[str, tuple[str, str]]) -> dict[str, dict[str, Any]]:
    """Mutate a schema in place: tag persona sections with their persona mode +
    noun and append the shared Biography/Personality fields. Returns a by-key map."""
    by_key: dict[str, dict[str, Any]] = {}
    for s in schema:
        info = persona_sections.get(s["key"])
        if info:
            s["persona"], s["noun"] = info
            have = {f["key"] for f in s["fields"]}
            for pf in PERSONA_FIELDS:
                if pf["key"] not in have:
                    s["fields"].append(dict(pf))
        by_key[s["key"]] = s
    return by_key


# --- house rules (no em/en dashes, no emoji) ------------------------------
_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF"
    "\U0000FE00-\U0000FE0F\U0001F1E6-\U0001F1FF\U00002640-\U00002642"
    "\U0000200D\U000020E3]+",
    flags=re.UNICODE,
)


def clean(value: Any) -> Any:
    if isinstance(value, str):
        out = value.replace("—", "-").replace("–", "-")
        return _EMOJI.sub("", out)
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    return value


class Store:
    """A persisted, schema-described set of customization sections.

    Defaults are the canonical seed; only what the user changed is written to
    `store_file`, overlaid on the defaults at read time. `on_change` fires after
    any mutation (e.g. invalidate the per-week cache, or rewrite the save file).
    """

    def __init__(self, *, store_file: Path, defaults: dict[str, Any],
                 schema: list[dict[str, Any]], persona_sections: dict[str, tuple[str, str]],
                 on_change: Callable[[], None] | None = None):
        self._lock = threading.Lock()
        self._file = store_file
        self._defaults = defaults
        self._schema = schema
        self._by_key = attach_personas(schema, persona_sections)
        self._on_change = on_change

    # --- persistence ------------------------------------------------------
    def _load_store(self) -> dict[str, Any]:
        if self._file.exists():
            try:
                with self._file.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    return data if isinstance(data, dict) else {}
            except (OSError, ValueError):
                return {}
        return {}

    def _save_store(self, store: dict[str, Any]) -> None:
        try:
            with self._file.open("w", encoding="utf-8") as fh:
                json.dump(store, fh, indent=2)
        except OSError:
            pass

    @staticmethod
    def _merge_object(default: dict[str, Any], stored: Any) -> dict[str, Any]:
        """Field-wise overlay so new default fields always surface."""
        out = copy.deepcopy(default)
        if isinstance(stored, dict):
            out.update(stored)
        return out

    def _enrich(self, key: str, value: Any) -> Any:
        """Ensure person sections carry a full personality + bio."""
        meta = self._by_key.get(key)
        if not meta or not meta.get("persona"):
            return value
        mode, noun = meta["persona"], meta.get("noun", "person")
        if meta["kind"] == "object":
            return personality.enrich(value, noun=noun, mode=mode)
        if isinstance(value, list):
            return [personality.enrich(it, noun=noun, mode=mode) for it in value]
        return value

    # --- reads ------------------------------------------------------------
    def section(self, key: str) -> Any:
        """The current value for one section (defaults overlaid with edits),
        with personalities and bios filled in for person sections."""
        default = self._defaults.get(key)
        stored = self._load_store().get(key)
        if isinstance(default, dict):
            value = self._merge_object(default, stored)
        elif isinstance(default, list):
            value = copy.deepcopy(stored) if isinstance(stored, list) else copy.deepcopy(default)
        else:
            value = stored if stored is not None else copy.deepcopy(default)
        return self._enrich(key, value)

    def load(self) -> dict[str, Any]:
        """Every section in this store, merged."""
        return {key: self.section(key) for key in self._defaults}

    def get_state(self) -> dict[str, Any]:
        """Schema + current values + the modified-section list, for the frontend."""
        store = self._load_store()
        return {
            "schema": self._schema,
            "values": {key: self.section(key) for key in self._defaults},
            "modified": sorted(k for k in store if k in self._defaults),
            "options": {**EDITOR_OPTIONS, "personality_traits": personality.PERSONALITY_TRAITS},
        }

    def generate_person(self, key: str, seed: dict[str, Any] | None = None,
                        *, use_llm: bool = False) -> dict[str, Any]:
        """A fresh persona (random sliders + a bio) for a new person in a section."""
        if key not in self._defaults:
            raise KeyError(f"unknown customization section: {key}")
        meta = self._by_key.get(key) or {}
        noun = meta.get("noun", "person")
        return personality.generate_person(seed or {}, noun=noun, use_llm=use_llm)

    # --- writes -----------------------------------------------------------
    def set_section(self, key: str, value: Any) -> dict[str, Any]:
        """Persist one section. Returns the merged value."""
        if key not in self._defaults:
            raise KeyError(f"unknown customization section: {key}")
        with self._lock:
            store = self._load_store()
            store[key] = clean(value)
            self._save_store(store)
        self._fire_change()
        return self.section(key)

    def reset_section(self, key: str) -> dict[str, Any]:
        """Drop user edits for one section, reverting to the default."""
        if key not in self._defaults:
            raise KeyError(f"unknown customization section: {key}")
        with self._lock:
            store = self._load_store()
            store.pop(key, None)
            self._save_store(store)
        self._fire_change()
        return self.section(key)

    def reset_all(self) -> None:
        with self._lock:
            self._save_store({})
        self._fire_change()

    def has_section(self, key: str) -> bool:
        return key in self._defaults

    def _fire_change(self) -> None:
        if self._on_change is not None:
            try:
                self._on_change()
            except Exception:
                pass
