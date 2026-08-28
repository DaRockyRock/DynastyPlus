import { useState } from 'react';
import PollSwitch from './PollSwitch.jsx';

export default {
  title: 'Domain/PollSwitch',
  component: PollSwitch,
};

const LABELS = { cfp: 'CFP Committee Rankings', ap: 'AP Top 25' };

export const Default = {
  render: () => {
    const [poll, setPoll] = useState('cfp');
    return <PollSwitch value={poll} onChange={setPoll} labels={LABELS} />;
  },
};
