# CLAUDE.md

Guidance for working in this repository.

## What this app is

CFBMod is a desktop companion app for EA Sports College Football 27 dynasty
mode. It runs alongside the game, watches the dynasty save file, and on each new
week generates immersive sports-media content with an LLM. It is meant to fully
replace the game's built-in news and rankings with a richer, persistent media
universe: top-stories slider, national/program news feed, a 12-member CFP
committee, recruiting board, transfer portal, coaching hot seat, awards watch, a
growing dynasty archive, and an in-app phone for texting recruits/staff/players/
media in character.

The PC version of CFB 27 ships ~July 2026. Until the save format is reverse
engineered, a separate **Simulator** app stands in for the game: it owns all
game data and writes the dynasty save that Dynasty+ watches. When the real save
format is known, the game writes that same save file and the Simulator goes
away. The seam to swap is `backend/watcher.read_save` (the save reader) feeding
`backend/pipeline.load_dynasty`; nothing downstream changes.

## Architecture (two apps, one repo)

The project is two processes that share one importable Python core (`backend/`)
and one React component library (`frontend/src/components/`). They communicate
only through files under `data/save/`, so either can run with the other closed.

- **Simulator** (`simulator/`, Python + Flask on port 5070, launched by
  `run_sim.py`): a CFB 27 stand-in. Owns the season simulation (`backend/sim/`),
  the game-data identity store (`backend/customization_game.py`), and the
  NIL/budget engine (`backend/budget.py`). The user drives the season here
  (start / simulate / override / edit roster / spend NIL). On every change it
  writes the dynasty save (`data/save/dynasty.json`) via `simulator/save_writer`,
  and drains coach actions from the companion inbox before each advance.
- **Dynasty+** (`backend/`, Python + Flask on port 5050, launched by `run.py`):
  the media companion, trimmed. It is **passive**: it opens to a dynasty library
  and does nothing until the user clicks **Scan**, which reads the save
  (`backend/pipeline.scan`) and registers/updates a dynasty
  (`backend/dynasties.py`). There is no auto-watch and no auto-generate; media
  generates on demand per tab once a dynasty is entered. It owns media-flavor data
  (`backend/customization.py`: reporters, committee, awards, phone contacts), the
  per-week cache, narrative memory, and the phone. It never writes game data;
  coach actions (NIL offers, recruiting actions) are queued to
  `data/save/companion_inbox.json` via `backend/inbox.py` for the Simulator to
  apply ("update it if it can").
- **The file boundary**: the save embeds the live budget snapshot under
  `dynasty["budget"]` and a content hash under `meta.hash`. Dynasty+ reads budget
  and all game data from the save (never the Simulator's stores). The flow is
  explicit: create/advance the dynasty in the Simulator, then Scan in Dynasty+ to
  pull it in (`pipeline.load_dynasty` serves the current week from the save and
  past weeks from per-week snapshots under `data/dynasty_archive/`).
- **Where data lives** (`backend/config.DATA_DIR`): the single seam every runtime
  store derives from (per-dynasty stores under `data/dynasties/<dynasty_id>/`, the
  save boundary, the archive, uploads). It resolves in three tiers: (1) the
  `CFBMOD_DATA_DIR` env var wins everywhere if set; (2) a frozen/bundled build
  (`sys.frozen`, i.e. PyInstaller/py2app/Electron-packed Python) uses the OS
  per-user data dir (`~/Library/Application Support/CFBMod`,
  `%LOCALAPPDATA%\CFBMod`, `$XDG_DATA_HOME/CFBMod`) so writes survive updates and
  never hit a read-only install dir; (3) a source checkout (dev) uses the repo's
  `./data`, unchanged. All of `data/` except the shared seeds (`league_seed.json`,
  `local_media.json`) is per-playthrough runtime state and is gitignored. When
  packaging: the seeds ship read-only with the app, and if the two apps ever ship
  as separate installers they must share `DATA_DIR` so the `data/save/` boundary
  lines up.
- **Frontend** (`frontend/`, React + Vite + Storybook): one shared component
  library + two Vite entries. `index.html` -> Dynasty+ (`src/App.jsx`,
  `AppContext`); `simulator.html` -> the Simulator (`src/SimulatorApp.jsx`,
  `SimContext`). Each backend serves its own built HTML from `frontend/dist/`.
  The Simulator reuses companion pages (Customize, NIL) by providing the same
  `AppContext` with a sim-flavored value.

## The component rule (IMPORTANT)

**Every single thing rendered on screen must be a reusable component in the
component library, and every component must have a Storybook story.**

When adding ANY new element to the UI - a button, a tag, a card, a row, a modal,
a chart, anything:

1. Create it as a component under `frontend/src/components/`:
   - primitives -> `components/ui/`
   - feature/domain pieces -> `components/domain/`
   - app shell/chrome -> `components/layout/`
   - phone/messages -> `components/phone/`
   - person name + hover-to-text -> `components/people/`
2. Add a `*.stories.jsx` next to it with at least one example (more if it has
   variants/states). Use `src/components/fixtures.js` for sample data.
3. Export it from the barrel `frontend/src/components/index.js`.
4. Compose pages ONLY from `components/index.js`. Do NOT write ad-hoc markup
   (raw styled `<div>`s, inline component shapes) directly in a page. If a page
   needs a new shape, make a component for it first.
5. Verify it renders in Storybook: `npm run build-storybook` (or `npm run
   storybook` to view).

Rationale: the whole UI is driven from a shared design system, so a styling
change in one place updates everywhere, and Storybook is the catalog/source of
truth for the visual language.

## Design system + conventions

- Styling lives in `frontend/src/styles/tokens.css` (design tokens, fonts,
  background) and `frontend/src/styles/global.css` (component classes).
  Components use these classes; prefer extending the system over one-off inline
  styles.
- Aesthetic: "Saturday Night Broadcast HUD" - condensed athletic type, team-color
  energy on a deep field, varied broadcast motifs (sheared week badge, capped
  labels, corner readouts, pentagon seeds, segmented gauges). Do not make
  everything a parallelogram; give each component its own treatment.
- Fonts: **Saira Condensed** (display, italic uppercase headlines/labels) +
  **Saira** (body). Loaded via `@fontsource`. No system fonts, no Inter/Roboto.
- The active team's color is injected at runtime as the CSS var `--team`
  (with `--team-alt`). Accent colors live in `tokens.css`.
- **Team marks are always real ESPN logos** via the `TeamLogo` component (logos
  only - no helmet graphics), with a neutral monogram fallback. Logo URL:
  `https://a.espncdn.com/i/teamlogos/ncaa/500/<espnId>.png`.
- **No dashes used as punctuation anywhere**, in the app or in generated
  content. That means no em dashes, no en dashes, and no spaced hyphens used as
  dashes (like `word - word`); use commas, periods, or parentheses instead.
  Hyphens are allowed only inside compound words and scores (`top-15`, `28-24`,
  `7-2`). Enforced server-side (`backend/modules/base.sanitize`, which rewrites
  dash punctuation to commas) and client-side (`frontend/src/lib/format.noEmDash`),
  and every generation prompt instructs against dashes (do not reintroduce
  "use hyphens" guidance).
- **No emojis anywhere**, in the UI, mock data, or generated content. Use words
  or plain typographic glyphs instead. Stripped server-side in
  `backend/modules/base.sanitize`; do not add emojis in components or fixtures.
- Outlet/reporter/contact names are fictional, so unreliable reporting is never
  attributed to a real publication.

## Commands

Backend (run both processes; they talk through `data/save/`):
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py            # Dynasty+ companion: frontend/dist + API at http://127.0.0.1:5050
python run_sim.py        # Simulator (CFB 27 stand-in) at http://127.0.0.1:5070
```
Drive the season in the Simulator (start a season, then "Simulate Week"); Dynasty+
auto-refreshes from the save it writes. With no API key Dynasty+ runs entirely on
mock content. Set `CFBMOD_USE_LLM=true` plus `ANTHROPIC_API_KEY` in `.env` to
enable live generation (the Simulator needs no LLM). The Simulator's season needs
the FBS league seed: `python scripts/build_league_seed.py` (already committed as
`data/league_seed.json`).

Frontend (one project, two entries):
```
cd frontend
npm install
npm run dev              # Vite on 5173: / -> Dynasty+ (/api->5050), /simulator.html -> Simulator (/sim-api->5070)
npm run build            # production build into frontend/dist (both entries; each Flask serves its own)
npm run storybook        # component catalog on 6006
npm run build-storybook  # static Storybook build (use to validate stories)
```

After frontend changes, run `npm run build` so both Flask-served apps reflect
them, and `npm run build-storybook` to confirm the component catalog compiles.

## Adding game vs media data

Game data the game owns (team, roster, staff, recruits, portal, rivals, NIL) lives
in `backend/customization_game.py` + `backend/budget.py` + `backend/sim/`, is
edited in the Simulator, and flows to Dynasty+ through the save. Media-flavor data
the companion owns (reporters, outlets, CFP committee, hot-seat board, awards,
phone contacts) lives in `backend/customization.py` and is read directly by the
modules. Both stores share machinery via `backend/customization_base.Store`.
Dynasty+ modules must read game data from the passed `dynasty` dict (the save),
never from a game store.

## Adding a new generation module

1. Add `backend/modules/<name>.py` exposing
   `generate(dynasty, *, year, week, use_llm, regenerate)` returning JSON, with a
   `_mock(...)` fallback and an LLM prompt path.
2. Register it in `backend/modules/__init__.REGISTRY`.
3. Build its UI as components (per the component rule) and a page in
   `frontend/src/pages/`, wired through `useModule('<name>')`.
