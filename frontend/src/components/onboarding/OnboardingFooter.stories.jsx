import OnboardingFooter from './OnboardingFooter.jsx';

export default {
  title: 'Onboarding/OnboardingFooter',
  component: OnboardingFooter,
  parameters: { layout: 'fullscreen' },
};

export const FirstStep = { args: { onPrimary: () => {}, primaryLabel: 'Get started' } };
export const MiddleStep = { args: { onBack: () => {}, onPrimary: () => {}, primaryLabel: 'Save and connect' } };
export const WithHint = {
  args: { onBack: () => {}, onPrimary: () => {}, primaryLabel: 'Save and connect', hint: 'Test passed - ready to go' },
};
