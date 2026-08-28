import SaveProgressOverlay from './SaveProgressOverlay.jsx';

export default {
  title: 'Domain/SaveProgressOverlay',
  component: SaveProgressOverlay,
  parameters: { layout: 'fullscreen' },
};

export const ApplyingSave = {
  render: () => (
    <SaveProgressOverlay
      open
      steps={[
        { label: 'Writing changes into your dynasty save', status: 'active' },
        { label: 'Building the logo mod', note: 'First run mirrors your game files (about a minute)', status: 'pending' },
      ]}
    />
  ),
};

export const BuildingMod = {
  render: () => (
    <SaveProgressOverlay
      open
      steps={[
        { label: 'Writing changes into your dynasty save', status: 'done' },
        { label: 'Building the logo mod', note: 'First run mirrors your game files (about a minute)', status: 'active' },
      ]}
    />
  ),
};

export const NamesOnly = {
  render: () => (
    <SaveProgressOverlay
      open
      steps={[{ label: 'Writing changes into your dynasty save', status: 'active' }]}
    />
  ),
};

// The save succeeded but the optional logo mod could not be built (e.g. the
// image tools are unavailable in this build). The save shows done; the logo
// step shows skipped, not a hard failure.
export const LogoModSkipped = {
  render: () => (
    <SaveProgressOverlay
      open
      steps={[
        { label: 'Writing changes into your dynasty save', status: 'done' },
        { label: 'Building the logo mod', note: 'Skipped: the image tools are unavailable in this build', status: 'skipped' },
      ]}
    />
  ),
};
