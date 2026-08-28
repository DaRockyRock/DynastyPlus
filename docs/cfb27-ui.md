# Dynasty+ Tools UI guide

Dynasty+ Tools is a local save editor for EA Sports College Football 27. Its
interface is organized around seven editors: Conferences, Schedule, Playoff
Format, Playoff Bracket, Bowl Games, Rankings, and Recruiting Tool.

## Screen structure

- `App.jsx` owns the seven top-level tabs.
- Each editor uses `GameScreen` and the shared components exported from
  `frontend/src/components/index.js`.
- `TopBar` shows the selected dynasty, current season, and save-sync controls.
- `LandingPage` scans and imports CFB 27 dynasty save files.
- `SetupPage` locates the game and saves folders and extracts local game art.

## Shared components

- `PanelCard` contains editor controls and data.
- `TeamLogo`, `TeamHelmet`, and `ConferenceLogo` show locally extracted art.
- `Button`, `ConfirmDialog`, `Callout`, `EmptyState`, and `Skeleton` provide
  shared interaction and feedback states.
- `HintBar` and `WeekSyncModal` communicate save and synchronization status.

## Styling

- Shared tokens are in `frontend/src/styles/tokens.css`.
- Shared component styles are in `frontend/src/styles/global.css`.
- Editor-specific styles are in the matching `screens-*.css` file.
- Preserve existing class names when a component is reused by more than one
  editor, and add or update Storybook stories for reusable UI changes.

Game art is extracted from the user's own installed copy and stored locally.
It is ignored by Git and is not distributed with the repository.
