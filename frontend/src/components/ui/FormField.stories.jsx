import FormField from './FormField.jsx';

export default {
  title: 'UI/FormField',
  component: FormField,
  parameters: { layout: 'padded' },
};

export const Text = {
  render: () => (
    <div className="set-grid">
      <FormField label="Coach name" help="Shown in program customization.">
        <input className="set-input" placeholder="Garrett Mason" />
      </FormField>
    </div>
  ),
};

export const TwoUp = {
  render: () => (
    <div className="set-grid">
      <FormField label="School" width="half">
        <input className="set-input" placeholder="Nebraska" />
      </FormField>
      <FormField label="Nickname" width="half">
        <input className="set-input" placeholder="Cornhuskers" />
      </FormField>
    </div>
  ),
};
