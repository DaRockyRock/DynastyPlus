import GuideStep from './GuideStep.jsx';
import CodeSnippet from '../ui/CodeSnippet.jsx';

export default {
  title: 'Onboarding/GuideStep',
  component: GuideStep,
  parameters: { layout: 'padded' },
};

export const Steps = {
  render: () => (
    <ol className="guide-list" style={{ maxWidth: 560 }}>
      <GuideStep n={1} title="Open the Anthropic Console">
        Sign in (or create a free account) and add billing.
      </GuideStep>
      <GuideStep n={2} title="Create an API key">
        Copy the key that starts with sk-ant-.
      </GuideStep>
      <GuideStep n={3} title="Paste it below">
        <CodeSnippet>sk-ant-api03-...</CodeSnippet>
      </GuideStep>
    </ol>
  ),
};
