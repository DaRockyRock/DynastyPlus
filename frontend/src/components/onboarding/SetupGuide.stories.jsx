import SetupGuide from './SetupGuide.jsx';

export default {
  title: 'Onboarding/SetupGuide',
  component: SetupGuide,
  parameters: { layout: 'padded' },
};

export const Anthropic = { render: () => <div style={{ maxWidth: 560 }}><SetupGuide provider="anthropic" /></div> };
export const Local = { render: () => <div style={{ maxWidth: 560 }}><SetupGuide provider="local" /></div> };
