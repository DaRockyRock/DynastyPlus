import { useState } from 'react';
import PollAlgorithmPicker from './PollAlgorithmPicker.jsx';
import Card from '../ui/Card.jsx';
import { pollAlgorithms } from '../fixtures.js';

export default {
  title: 'Domain/PollAlgorithmPicker',
  component: PollAlgorithmPicker,
  parameters: { layout: 'padded' },
};

function Live() {
  const [value, setValue] = useState('colley');
  return (
    <Card className="panel" style={{ width: 360 }}>
      <PollAlgorithmPicker algorithms={pollAlgorithms} value={value} onChange={setValue} />
    </Card>
  );
}

export const Interactive = { render: () => <Live /> };
