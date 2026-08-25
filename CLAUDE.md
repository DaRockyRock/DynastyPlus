# CLAUDE.md

Guidance for working in this repository.

## Product

Dynasty+ Tools is one local web app for a modeled college football dynasty. Its
four surfaces are Season, Customize, NIL, and Recruiting. The app owns the
season state, program data, Dynasty Points budget, NIL offers, recruiting
actions, and an exportable dynasty snapshot.

There is one Python process and one React entry:

- `run.py` launches the Flask app in `simulator/app.py` on port 5050.
- `backend/sim/` owns deterministic season and recruiting simulation.
- `backend/customization_game.py` owns editable program, staff, roster, rival,
  commit, and target data.
- `backend/budget.py` owns Dynasty Points, NIL, and recruiting-action spend.
- `simulator/save_writer.py` exports `data/save/dynasty.json` after state
  changes. `backend/schema.py` documents that snapshot.
- `frontend/src/ToolsApp.jsx` is the only React entry. Shared state is provided
  by `frontend/src/context/ToolsContext.jsx`.

All runtime paths derive from `backend/config.DATA_DIR`. `CFBMOD_DATA_DIR` wins
when set; packaged builds use the platform's per-user data directory; source
checkouts use `./data`.

## Component rule

Every rendered UI element must be a reusable component in
`frontend/src/components/`, and every component must have a colocated Storybook
story.

1. Put primitives in `components/ui/`, feature pieces in `components/domain/`,
   shell components in `components/layout/`, and editor pieces in
   `components/settings/`.
2. Add a `*.stories.jsx` file next to each component. Use
   `src/components/fixtures.js` for shared sample data.
3. Export reusable components from `src/components/index.js`.
4. Compose pages from the component library. Add a component when a page needs
   a new visual shape.
5. Verify the catalog with `npm run build-storybook`.

## Design system

- Tokens and fonts live in `frontend/src/styles/tokens.css`; component styles
  live in `frontend/src/styles/global.css`.
- The visual direction is a Saturday night broadcast HUD using Saira Condensed
  for display type and Saira for body text.
- The active team colors are available as `--team` and `--team-alt`.
- Use real ESPN team logos through `TeamLogo`, with its monogram fallback.
- Do not use emoji.
- Avoid em and en dashes as punctuation in user-facing copy.

## Commands

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

Frontend development:

```bash
cd frontend
npm run dev
npm run build
npm run storybook
npm run build-storybook
```

Vite serves the app at port 5173 and proxies `/api` to port 5050. The Flask
production server serves `frontend/dist/index.html`.

The season simulation requires `data/league_seed.json`. Rebuild it with
`python scripts/build_league_seed.py` if the committed seed changes.

After frontend changes, run both `npm run build` and
`npm run build-storybook`.
