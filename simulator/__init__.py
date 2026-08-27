"""The Simulator app: a CFB 27 stand-in.

A separate process from the Dynasty+ companion. It owns all game data (the
season simulation, program identity/roster/recruiting/portal, and the NIL/budget
engine) and is where the user drives the season. On every change it writes the
dynasty save file the companion watches. When the real CFB 27 save format is
known, the game writes that same file and this app goes away.

Shares the importable core with Dynasty+ via the `backend` package (absolute
imports), exactly as run.py does.
"""
