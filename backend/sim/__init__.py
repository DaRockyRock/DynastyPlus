"""Season simulation engine.

A stateful, persisted, all-FBS season that stands in for the static mock behind
pipeline.load_dynasty: every team has a rating and a schedule, games are
simulated week to week, and records, polls, standings, and player stats all
emerge from the results. Drives the in-app Debug mode (start a season, advance
and override results). Forward-compatible with the real CFB 27 save parser, which
becomes a third dynasty source alongside mock and sim.

Layers:
  league    - the FBS universe + per-season ratings (reads data/league_seed.json)
  schedule  - conflict-free season schedule generation
  engine    - single-game score model (deterministic per game key)
  stats     - player season-stat accrual + Heisman / leaders
  polls     - emergent AP / Coaches / CFP rankings
  standings - records + conference tables
  state     - the persisted season (new / advance / scoreboard / reset)
  recruiting- the national recruiting cycle (class generation + weekly process)
  adapter   - sim -> schema-conforming dynasty dict
"""
from __future__ import annotations

from . import adapter, engine, history, league, polls, portal, recruiting, satisfaction, schedule, standings, state, stats  # noqa: F401
