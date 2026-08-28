import FormField from './FormField.jsx';

export default {
  title: 'UI/FormField',
  component: FormField,
  parameters: { layout: 'padded' },
};

export const Text = {
  render: () => (
    <div className="set-grid">
      <FormField label="Conference name" help="The name shown throughout the editor.">
        <input className="set-input" placeholder="Big Ten" />
      </FormField>
    </div>
  ),
};

export const TwoUp = {
  render: () => (
    <div className="set-grid">
      <FormField label="Abbreviation" width="half" help="Up to four characters.">
        <input className="set-input" placeholder="B1G" />
      </FormField>
      <FormField label="Championship game" width="half">
        <input className="set-input" placeholder="Big Ten Championship" />
      </FormField>
    </div>
  ),
};
