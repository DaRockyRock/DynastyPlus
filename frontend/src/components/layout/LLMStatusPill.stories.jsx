import LLMStatusPill from './LLMStatusPill.jsx';

export default {
  title: 'Layout/LLMStatusPill',
  component: LLMStatusPill,
  parameters: { layout: 'centered' },
};

export const Connected = { args: { status: { ready: true, provider: 'anthropic', model: 'claude-haiku-4-5' }, onClick: () => {} } };
export const Local = { args: { status: { ready: true, provider: 'local', model: 'llama-3.1-70b' }, onClick: () => {} } };
export const Mock = { args: { status: { ready: false, provider: 'anthropic', model: 'claude-haiku-4-5' }, onClick: () => {} } };
