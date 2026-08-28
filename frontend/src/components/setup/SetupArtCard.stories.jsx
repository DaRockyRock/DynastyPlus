import SetupArtCard from './SetupArtCard.jsx';

export default {
  title: 'Setup/SetupArtCard',
  component: SetupArtCard,
};

export const NotInstalled = {
  args: { installFound: true, present: false, onExtract: () => {} },
};

export const Extracting = {
  args: {
    installFound: true,
    extracting: true,
    stage: 'teams',
    done: 0,
    total: 7,
    onExtract: () => {},
  },
};

export const Installed = {
  args: {
    installFound: true,
    present: true,
    onExtract: () => {},
  },
};

export const GameMissing = {
  args: { installFound: false, present: false, onExtract: () => {} },
};
