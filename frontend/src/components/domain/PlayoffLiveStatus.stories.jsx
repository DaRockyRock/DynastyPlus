import PlayoffLiveStatus from './PlayoffLiveStatus.jsx';

export default {
  title: 'Domain/PlayoffLiveStatus',
  component: PlayoffLiveStatus,
};

const wrap = (props) => (
  <div style={{ width: 620, padding: 16 }}>
    <PlayoffLiveStatus {...props} />
  </div>
);

// Quiet by design: nothing renders in normal play.
export const Quiet = { render: () => wrap({}) };
export const NeedsWrite = {
  render: () => wrap({ needsWrite: true, onApply: () => {} }),
};
export const NeedsWriteApplying = {
  render: () => wrap({ needsWrite: true, applying: true, onApply: () => {} }),
};
export const AwaitingReload = { render: () => wrap({ awaitingReload: true }) };
export const InvalidFormat = {
  render: () => wrap({ problems: ['This bye structure does not close into a bracket: the field covers 20 opening slots, which must be a power of two.'] }),
};
