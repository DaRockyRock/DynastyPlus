import PlayoffOffState from './PlayoffOffState.jsx';

export default {
  title: 'Domain/PlayoffOffState',
  component: PlayoffOffState,
};

export const Default = {
  args: {},
};

export const Busy = {
  args: { busy: true },
};
