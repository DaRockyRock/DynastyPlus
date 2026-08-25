# Dynasty+ Tools

Dynasty+ Tools is a local toolkit for running a modeled college football
dynasty. It provides one web app for season simulation, program customization,
NIL budgeting, and recruiting. Changes are persisted locally, and each season
update writes an exportable dynasty snapshot.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
npm run build
cd ..

python run.py
```

Open `http://127.0.0.1:5050`. Use the Season tab to select a program, start a
season, simulate games, and advance the schedule. The other tabs edit program
data, manage the Dynasty Points and NIL budget, and work the national recruit
board.

For frontend development, run `npm run dev` from `frontend/`. Vite serves the
app at `http://127.0.0.1:5173` and proxies `/api` to the Python server on port
5050.

## Configuration

Copy `.env.example` to `.env` when you need to override a default.

| Variable | Purpose |
| --- | --- |
| `CFBMOD_DATA_DIR` | Runtime storage directory. Source checkouts default to `data/`. |
| `CFBMOD_SAVE_PATH` | Exported dynasty snapshot. Defaults to `data/save/dynasty.json`. |
| `CFBMOD_HOST` | Local bind address. Defaults to `127.0.0.1`. |
| `CFBMOD_PORT` | Local server port. Defaults to `5050`. |
| `CFBMOD_DP_PER_DOLLAR` | Dynasty Points charged per NIL dollar. Defaults to `0.0004`. |
| `CFBMOD_WEEKLY_HOURS` | Weekly recruiting hours. Defaults to `1500`. |

## Tools

- **Season**: choose an FBS program, start or reset a season, simulate the
  current game, override its score, advance the week, and review scoreboards.
- **Customize**: edit team identity, program resources, staff, roster, rivals,
  commits, and targets.
- **NIL**: allocate Dynasty Points and manage recruiting and roster NIL offers.
- **Recruiting**: filter the national board and spend recruiting actions.

The season model is deterministic for a given seed. Its FBS universe comes from
`data/league_seed.json`; rebuild that shared seed with
`python scripts/build_league_seed.py` when needed.

## Runtime data

Runtime state is stored beneath `CFBMOD_DATA_DIR`:

```text
data/
  customization_game.json   Program, roster, and recruiting edits
  sim/                       Season state
  budget/                    Dynasty Points and NIL state
  save/dynasty.json          Current exported dynasty snapshot
  uploads/                   Custom images
  teams_cache.json           Cached team metadata
```

Use **Delete Dynasty** in the Season tab to clear simulated seasons, budgets,
the exported snapshot, and customization data.

## Development

```bash
# Backend and production frontend
python run.py

# Frontend
cd frontend
npm run dev
npm run build
npm run storybook
npm run build-storybook
```

The Flask app lives in `simulator/app.py`; shared game logic lives under
`backend/`; the React entry is `frontend/src/ToolsApp.jsx`.

Every rendered UI element should be a reusable component under
`frontend/src/components/` with a colocated Storybook story. Export reusable
components from `frontend/src/components/index.js` and verify frontend changes
with both `npm run build` and `npm run build-storybook`.
