import FormField from './FormField.jsx';

export default {
  title: 'UI/FormField',
  component: FormField,
  parameters: { layout: 'padded' },
};

export const Text = {
  render: () => (
    <div className="set-grid">
      <FormField label="Dynasty save" help="Choose the save file to inspect.">
        <input className="set-input" placeholder="dynasty.json" />
      </FormField>
    </div>
  ),
};

export const TwoUp = {
  render: () => (
    <div className="set-grid">
      <FormField label="Season" width="half" help="The season represented by the save.">
        <input className="set-input" placeholder="2026" />
      </FormField>
      <FormField label="Week" width="half">
        <input className="set-input" placeholder="10" />
      </FormField>
    </div>
  ),
};
