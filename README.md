# Dynasty+ Tools

Dynasty+ Tools is the original local dynasty companion interface for importing
a college-football dynasty save and exploring its full media universe. It
includes the dynasty library, Game Center, news, the CFP committee and playoff
bracket, recruiting, NIL, the transfer portal, hot-seat coverage, awards, and
the historical archive.

The application reads the save configured by `CFBMOD_SAVE_PATH`. The included
Simulator can create a local sample save for development until a real game-save
adapter is available; it is not the primary Dynasty+ Tools interface.

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

Open `http://127.0.0.1:5050`. Dynasty+ Tools opens to the dynasty library. Click
**Scan** to import the configured save, then **Continue** to enter it.

To create a sample save locally, run `python run_sim.py` in another terminal,
open `http://127.0.0.1:5070`, and start a season. Return to Dynasty+ Tools and
click **Scan**. The two apps communicate only through files in `data/save/`.

## Configuration

Copy `.env.example` to `.env` and edit:

| Variable | Purpose |
| --- | --- |
| `CFBMOD_SAVE_PATH` | Save file to watch. Today this can be a JSON file shaped like the dynasty schema. |
| `CFBMOD_HOST` / `CFBMOD_PORT` | Local server bind address. |

## How it works

```
Simulator (run_sim.py)                         Dynasty+ companion (run.py)
  sim + game data  -> data/save/dynasty.json ->  Scan -> pipeline -> modules -> cache -> web UI
        ^                                                     |
        |  data/save/companion_inbox.json <- inbox (coach   narrative memory (continuity)
        +------- drain + apply -------------  actions queued by the companion)
```

- **Save integration** - the Simulator writes a schema-conforming dynasty save
  (`backend/sim/adapter.build_dynasty`); `backend/schema.py` documents the target
  JSON. Dynasty+ ingests it on an explicit **Scan** (`backend/pipeline.scan`),
  registering it in the dynasty library (`backend/dynasties.py`). When the PC save
  format is known, point the reader at the real save - nothing downstream changes.
  `backend/mock_data.py` is the cold-start seed used only before any save exists.
- **Write-back** - the companion never writes game data. Coach actions (NIL
  offers from the phone, recruiting actions) are queued to the companion inbox
  (`backend/inbox.py`); the Simulator drains and applies them through the budget
  engine before each week's recruiting cycle, then rewrites the save.
- **Data modules** (`backend/modules/`) - each is independently callable and
  returns JSON for the corresponding Tools view.
- **Narrative memory** (`backend/narrative.py`) - a persistent per-season
  document that grows each week and is injected into every prompt, so a Week 4
  rumor can resurface in the offseason and committee members stay consistent.
- **Cache** (`backend/cache.py`) - content is cached per (season, week, module),
  so navigating back through weeks shows consistent history and a single section
  can be regenerated without rerunning the full pipeline.
- **File watcher** (`backend/watcher.py`) - watchdog monitors the save path,
  detects a new week, and triggers the full pipeline with a UI loading state.
- **Team icons** - real logos and accurate school colors come from the ESPN
  public teams API (cached locally), with a color-accurate helmet SVG fallback.

## API

| Endpoint | Description |
| --- | --- |
| `GET /api/config` | Runtime config + watcher state |
| `GET /api/schema` | Dynasty JSON schema description |
| `GET /api/teams` | Team logos/colors/abbreviations |
| `GET /api/dynasty?year=&week=` | Current dynasty state |
| `GET /api/state` | Current week pointer + cached weeks + status |
| `GET /api/status` | Pipeline progress (drives the loading bar) |
| `GET /api/module/<key>?regenerate=1` | Generate/fetch a single module |
| `POST /api/generate` | Run the full pipeline for the current week |
| `POST /api/advance` | Advance to a week and run the pipeline |
| `POST /api/phone/message` | Send a phone message, get an in-character reply |

Module keys: `top_stories`, `news_feed`, `cfp_committee`, `recruiting`,
`portal`, `hot_seat`, `awards`, `archive`, `phone`.

## Conventions

- No em dashes anywhere, in the app or in generated content. Hyphens only. This
  is enforced server-side (`modules/base.sanitize`) and client-side
  (`util.noEmDash`).
- Outlet and reporter names are fictional analogs, so unreliable reporting is
  never attributed to a real publication.

## Project layout

```
run.py                 entry point
backend/
  app.py               Flask app + endpoints
  config.py            env-driven configuration
  schema.py            dynasty JSON schema
  mock_data.py         Nebraska mock dynasty generator
  teams.py             ESPN-backed team metadata
  narrative.py         persistent narrative memory
  cache.py             per-week content cache
  pipeline.py          orchestration + runtime state
  watcher.py           watchdog save-file monitor
  modules/             one file per generation module
frontend/
  index.html
  simulator.html       sample-save Simulator entry point
  src/
    App.jsx            Dynasty+ Tools shell and navigation
    SimulatorApp.jsx   optional sample-save Simulator shell
    components/        shared UI components and Storybook stories
    context/           application state and API orchestration
    pages/             dynasty library and feature pages
    styles/            design tokens and global styles
```

## Contributing

Questions and early ideas belong in [GitHub Discussions](https://github.com/DaRockyRock/DynastyPlus/discussions).
Use [GitHub Issues](https://github.com/DaRockyRock/DynastyPlus/issues) for bugs
and scoped feature requests. Code contributions are made by forking the
repository and opening a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md)
for the complete setup, testing, and review workflow.
