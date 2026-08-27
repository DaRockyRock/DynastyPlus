import Callout from './Callout.jsx';

export default {
  title: 'UI/Callout',
  component: Callout,
  parameters: { layout: 'padded' },
};

export const Info = {
  render: () => (
    <div style={{ maxWidth: 520 }}>
      <Callout tone="info" title="No save loaded">
        Scan a dynasty save to populate every available Tools view.
      </Callout>
    </div>
  ),
};

export const Warn = {
  render: () => (
    <div style={{ maxWidth: 520 }}>
      <Callout tone="warn" title="Save not found">
        Check the configured save path, then scan again.
      </Callout>
    </div>
  ),
};

export const Success = {
  render: () => (
    <div style={{ maxWidth: 520 }}>
      <Callout tone="success" title="Save imported">The dynasty is ready to inspect.</Callout>
    </div>
  ),
};
