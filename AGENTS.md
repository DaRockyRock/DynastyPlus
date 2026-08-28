# Dynasty+ Tools contributor guide

## Scope

This repository contains one application: Dynasty+ Tools. It reads and edits real
EA Sports College Football 27 dynasty saves. Keep changes focused on the editor
workflows listed below.

The shipped tools are conference customization, schedule generation, playoff
format and live bracket editing, bowl assignments, rankings/polls, recruiting
correction, and local game-art extraction.

## Architecture

- `backend/app.py` exposes the local Flask API.
- `backend/saveparse/` reads and writes CFB 27 save containers.
- `backend/confsetup.py`, `schedrules.py`, `playoff.py`,
  `playoff_live.py`, `bowl_editor.py`, `polledit.py`, and
  `recruiting_fix.py` implement the editors.
- `frontend/src/App.jsx` is the Tools shell.
- `frontend/src/pages/` contains one page per tool.
- `frontend/src/components/` contains reusable UI and colocated Storybook
  stories.
- `electron/`, `packaging/`, and `scripts/build_app.py` build the desktop
  application.

## Local development

Use Python 3.11+ and Node.js 20+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt

cd frontend
npm ci
npm run build
cd ..

python run.py
```

The app runs at `http://127.0.0.1:5051`. For frontend hot reload, run
`npm run dev` inside `frontend/` while the Python backend is running.

## Verification

Before submitting a change, run:

```bash
python -m pytest
python scripts/smoke_test.py

cd frontend
npm run build
npm run build-storybook
```

Never commit local `.env` files, CFB 27 saves, runtime data, extracted game
art, build outputs, credentials, or personal paths.
