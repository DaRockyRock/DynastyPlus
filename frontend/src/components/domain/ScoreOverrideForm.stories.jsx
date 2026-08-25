import { useState } from 'react';
import ScoreOverrideForm from './ScoreOverrideForm.jsx';
import { simUserGame } from '../fixtures.js';

export default {
  title: 'Domain/ScoreOverrideForm',
  component: ScoreOverrideForm,
  parameters: { layout: 'padded' },
};

function Demo({ startEnabled }) {
  const [enabled, setEnabled] = useState(startEnabled);
  const [value, setValue] = useState({ user_score: '31', opp_score: '24' });
  return (
    <div style={{ width: 420 }}>
      <ScoreOverrideForm
        team={simUserGame.team} opponent={simUserGame.opponent}
        home={simUserGame.home} week={simUserGame.week}
        enabled={enabled} value={value} onToggle={setEnabled} onChange={setValue}
      />
    </div>
  );
}

export const Enabled = { render: () => <Demo startEnabled /> };
export const Disabled = { render: () => <Demo startEnabled={false} /> };
