import WelcomeIntro from './WelcomeIntro.jsx';

export default {
  title: 'Onboarding/WelcomeIntro',
  component: WelcomeIntro,
  parameters: { layout: 'padded' },
};

export const Default = { render: () => <div style={{ maxWidth: 640 }}><WelcomeIntro /></div> };
