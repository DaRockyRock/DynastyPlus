import { useState } from 'react';
import SimControlPanel from './SimControlPanel.jsx';
import { simUserGame } from '../fixtures.js';

export default {
  title: 'Domain/SimControlPanel',
  component: SimControlPanel,
  parameters: { layout: 'padded' },
};

function Demo({ busy = false, withGame = true }) {
  const [override, setOverride] = useState({ enabled: false, value: { user_score: '', opp_score: '' } });
  return (
    <div style={{ width: 520 }}>
      <SimControlPanel
        week={simUserGame.week}
        userGame={withGame ? simUserGame : null}
        override={override}
        onToggleOverride={(e) => setOverride((o) => ({ ...o, enabled: e }))}
        onChangeOverride={(value) => setOverride((o) => ({ ...o, value }))}
        onAdvance={() => {}}
        busy={busy}
      />
    </div>
  );
}

export const Idle = { render: () => <Demo /> };
export const Simulating = { render: () => <Demo busy /> };
export const ByeWeek = { render: () => <Demo withGame={false} /> };
