import { useState } from 'react';
import ByeTierEditor from './ByeTierEditor.jsx';

export default {
  title: 'Domain/ByeTierEditor',
  component: ByeTierEditor,
};

function Demo({ initial }) {
  const [tiers, setTiers] = useState(initial);
  return (
    <div style={{ width: 360 }}>
      <ByeTierEditor tiers={tiers} onChange={setTiers} maxTeams={24} />
      <pre style={{ color: 'var(--chalk-3)', fontSize: 11, marginTop: 12 }}>{JSON.stringify(tiers)}</pre>
    </div>
  );
}

export const StandardCfp = { render: () => <Demo initial={[{ rounds: 1, teams: 4 }]} /> };
export const MultiTier = { render: () => <Demo initial={[{ rounds: 2, teams: 1 }, { rounds: 1, teams: 2 }]} /> };
export const NoByes = { render: () => <Demo initial={[]} /> };
