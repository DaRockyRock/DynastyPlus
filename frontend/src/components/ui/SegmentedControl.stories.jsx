import { useState } from 'react';
import SegmentedControl from './SegmentedControl.jsx';

export default {
  title: 'UI/SegmentedControl',
  component: SegmentedControl,
  parameters: { layout: 'centered' },
};

export const Interactive = {
  render: () => {
    function Demo() {
      const [value, setValue] = useState('blueprint');
      return (
        <SegmentedControl
          options={[
            { value: 'blueprint', label: 'Blueprint' },
            { value: 'recruiting', label: 'HS NIL' },
            { value: 'roster', label: 'Roster NIL' },
          ]}
          value={value}
          onChange={setValue}
        />
      );
    }
    return <Demo />;
  },
};
