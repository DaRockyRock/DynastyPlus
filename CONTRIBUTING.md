# Contributing to Dynasty+ Tools

Thanks for helping improve Dynasty+ Tools. Bug reports, feature ideas,
documentation updates, and code contributions are welcome.

## Before you start

- Use [GitHub Discussions](https://github.com/DaRockyRock/DynastyPlus/discussions)
  for questions, early ideas, and general conversation.
- Search [existing issues](https://github.com/DaRockyRock/DynastyPlus/issues)
  before opening a bug report or feature request.
- Open an issue before beginning a large change so its scope can be agreed on
  before you invest significant time.

## Local setup

You need Python 3.11 or newer and Node.js 20 or newer.

```bash
git clone https://github.com/YOUR-USERNAME/DynastyPlus.git
cd DynastyPlus

python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt

cd frontend
npm ci
npm run build
cd ..

python run.py
```

On Windows PowerShell, activate the virtual environment with
`.venv\Scripts\Activate.ps1`. Open `http://127.0.0.1:5051`.

On first launch, select or confirm the CFB 27 installation and saves folders.
After the game has written a dynasty save, use **Scan Saves** or
**Import a save**.

## Making a change

1. Fork the repository on GitHub.
2. Create a focused branch from the latest `main` branch.
3. Make your change and add or update tests and documentation.
4. Run the checks below.
5. Push the branch to your fork and open a pull request against `main`.

Keep pull requests focused on one problem. Frontend UI elements should be
reusable components under `frontend/src/components/` with colocated Storybook
stories. Reusable components should be exported from
`frontend/src/components/index.js`.

## Required checks

Run these from the repository root before opening a pull request:

```bash
python -m pytest
python scripts/smoke_test.py

cd frontend
npm run build
npm run build-storybook
```

GitHub Actions runs the same checks for every pull request.

## Pull requests

In the pull request description:

- Explain what changed and why.
- Link the related issue with `Closes #123` when applicable.
- Include screenshots or a short recording for visible UI changes.
- Note anything reviewers should test manually.

A maintainer will review the pull request. Addressed feedback and passing checks
are required before the change can be merged.
