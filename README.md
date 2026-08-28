# Dynasty+ Tools

Dynasty+ Tools is the source code for the Dynasty+ Tools desktop application for
EA Sports College Football 27. It reads real CFB 27 dynasty saves and provides
focused editors for the parts of a dynasty the game does not expose directly.

## Included tools

- **Conferences**: customize membership, divisions, names, rivalries, and marks.
- **Schedule**: configure conference rules and protected rivals, generate a
  schedule, preview it, and apply it to the active dynasty save.
- **Playoff Format**: customize field size, byes, access rules, seeding, round
  sites, and conference limits.
- **Playoff Bracket**: manage the live custom postseason and write pending
  matchups to the dynasty save.
- **Bowl Games**: assign and apply the non-playoff bowl slate.
- **Rankings**: inspect team resumes and manage poll behavior.
- **Recruiting Tool**: audit and correct recruiting competition in the save.

The app scans the game's own save folder. You can also import a specific dynasty
save manually.

## Quick start

You need Python 3.11 or newer and Node.js 20 or newer.

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

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Open `http://127.0.0.1:5051`. On first launch, the Setup screen detects the CFB
27 installation and saves folder. After playing a dynasty so the game has
written a save, click **Scan Saves**, then **Continue**. If a save does not appear
in the library, use **Import a save**.

Game art is extracted from the user's local CFB 27 installation and is never
included in this repository or a distributed installer.

## Configuration

Copy `.env.example` to `.env` only when you need to override a default:

| Variable | Purpose |
| --- | --- |
| `CFBMOD_SAVE_PATH` | CFB 27 saves folder or one dynasty save. |
| `CFBMOD_GAME_ROOT` | CFB 27 installation folder used for local art extraction. |
| `CFBMOD_HOST` / `CFBMOD_PORT` | Local bind address. The default port is `5051`. |
| `CFBMOD_DATA_DIR` | Optional runtime-data location override. |
| `CFBMOD_PLAYOFF_AUTOSYNC` | Set `false` to require manual bracket updates. |

## Desktop build

The Windows installer packages the Python backend, the Tools frontend, and an
Electron shell. Users do not need Python or Node after installation.

```bash
pip install -r requirements-build.txt
python scripts/build_app.py
```

The installer is written beneath `dist-app/tools/`. Trademarked game art is
still read from each user's own installation at runtime.

## Development

```bash
cd frontend
npm run dev
npm run build
npm run storybook
npm run build-storybook
```

The Flask API is in `backend/app.py`. Real save parsing and writing lives under
`backend/saveparse/` and the editor engines are in modules such as
`backend/confsetup.py`, `backend/schedrules.py`, `backend/playoff.py`,
`backend/playoff_live.py`, `backend/polledit.py`, and `backend/recruiting_fix.py`.

## Safety

- Close the dynasty in CFB 27 before applying changes.
- Editor operations validate their planned changes before writing.
- Follow the on-screen backup and reload guidance for each tool.
- Do not commit `.env`, runtime data, save files, extracted game art, or build
  outputs.

## Contributing

Questions and early ideas belong in [GitHub Discussions](https://github.com/DaRockyRock/DynastyPlus/discussions).
Use [GitHub Issues](https://github.com/DaRockyRock/DynastyPlus/issues) for bugs
and scoped feature requests. Code contributions are made by forking the
repository and opening a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md)
for the setup, testing, and review workflow.
