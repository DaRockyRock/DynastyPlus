import { useState } from 'react';
import TextArea from './TextArea.jsx';
import FormField from './FormField.jsx';

export default {
  title: 'UI/TextArea',
  component: TextArea,
};

export const Default = {
  render: function Render() {
    const [value, setValue] = useState('A proud league built around regional rivalries and November football.');
    return (
      <div style={{ width: 420 }}>
        <FormField label="Description" help="Shown on the conference page in Dynasty+.">
          <TextArea value={value} onValueChange={setValue} rows={4} />
        </FormField>
      </div>
    );
  },
};
