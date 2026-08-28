import Callout from './Callout.jsx';

export default {
  title: 'UI/Callout',
  component: Callout,
  parameters: { layout: 'padded' },
};

export const Info = {
  render: () => (
    <div style={{ maxWidth: 520 }}>
      <Callout tone="info" title="Close the dynasty before writing">
        Return to the CFB 27 main menu before applying changes to the save.
      </Callout>
    </div>
  ),
};

export const Warn = {
  render: () => (
    <div style={{ maxWidth: 520 }}>
      <Callout tone="warn" title="Week 1 is already locked">
        Use a preseason save to rebuild the entire schedule, including the opening week.
      </Callout>
    </div>
  ),
};

export const Success = {
  render: () => (
    <div style={{ maxWidth: 520 }}>
      <Callout tone="success" title="Save updated">Reload the dynasty in CFB 27 to use the new schedule.</Callout>
    </div>
  ),
};
