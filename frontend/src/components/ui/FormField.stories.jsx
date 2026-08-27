import FormField from './FormField.jsx';

export default {
  title: 'UI/FormField',
  component: FormField,
  parameters: { layout: 'padded' },
};

export const Text = {
  render: () => (
    <div className="set-grid">
      <FormField label="Anthropic API key" help="Starts with sk-ant-. Stored locally, never shared.">
        <input className="set-input" placeholder="sk-ant-..." />
      </FormField>
    </div>
  ),
};

export const TwoUp = {
  render: () => (
    <div className="set-grid">
      <FormField label="Base URL" width="half" help="Your local server.">
        <input className="set-input" placeholder="http://127.0.0.1:8787" />
      </FormField>
      <FormField label="Model" width="half">
        <input className="set-input" placeholder="claude-haiku-4-5" />
      </FormField>
    </div>
  ),
};
