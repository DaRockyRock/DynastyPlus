import OnboardingHeader from './OnboardingHeader.jsx';

const STEPS = ['Welcome', 'Connect', 'Confirm'];

export default {
  title: 'Onboarding/OnboardingHeader',
  component: OnboardingHeader,
  parameters: { layout: 'fullscreen' },
};

export const Default = { args: { steps: STEPS, current: 1, onSkip: () => {} } };
export const NoSkip = { args: { steps: STEPS, current: 0 } };
