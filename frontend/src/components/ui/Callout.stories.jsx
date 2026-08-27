import Callout from './Callout.jsx';

export default {
  title: 'UI/Callout',
  component: Callout,
  parameters: { layout: 'padded' },
};

export const Info = {
  render: () => (
    <div style={{ maxWidth: 520 }}>
      <Callout tone="info" title="Runs on mock content until connected">
        Every section works without a model. Connect one to generate live, persistent media.
      </Callout>
    </div>
  ),
};

export const Warn = {
  render: () => (
    <div style={{ maxWidth: 520 }}>
      <Callout tone="warn" title="Key stays on this machine">
        Your API key is saved locally in data/llm.json and is never sent anywhere but Anthropic.
      </Callout>
    </div>
  ),
};

export const Success = {
  render: () => (
    <div style={{ maxWidth: 520 }}>
      <Callout tone="success" title="Connected">Generating with Claude Haiku 4.5.</Callout>
    </div>
  ),
};
