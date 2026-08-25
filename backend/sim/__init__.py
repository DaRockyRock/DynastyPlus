"""Stateful, persisted, all-FBS season simulation for Dynasty+ Tools.

Every team has a rating and a schedule. Games are simulated week to week, and
records, polls, standings, recruiting, and player stats emerge from the results.

Layers:
  league    - the FBS universe + per-season ratings (reads data/league_seed.json)
  schedule  - conflict-free season schedule generation
  engine    - single-game score model (deterministic per game key)
  stats     - player season-stat accrual + Heisman / leaders
  polls     - emergent AP / Coaches / CFP rankings
  standings - records + conference tables
  state     - the persisted season (new / advance / scoreboard / reset)
  recruiting- the national recruiting cycle (class generation + weekly process)
  adapter   - season state to schema-conforming dynasty snapshot
"""
from __future__ import annotations

from . import adapter, engine, history, league, polls, portal, recruiting, satisfaction, schedule, standings, state, stats  # noqa: F401
