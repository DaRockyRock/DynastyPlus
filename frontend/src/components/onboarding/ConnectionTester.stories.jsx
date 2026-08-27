import ConnectionTester from './ConnectionTester.jsx';

export default {
  title: 'Onboarding/ConnectionTester',
  component: ConnectionTester,
  parameters: { layout: 'padded' },
};

export const Idle = { args: { status: 'idle', onTest: () => {} } };
export const Testing = { args: { status: 'testing', onTest: () => {} } };
export const Ok = { args: { status: 'ok', message: 'Connected to Anthropic (claude-haiku-4-5).', onTest: () => {} } };
export const Error = { args: { status: 'error', message: 'Authentication failed - check the API key.', onTest: () => {} } };
