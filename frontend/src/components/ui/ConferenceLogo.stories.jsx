import ConferenceLogo from './ConferenceLogo.jsx';
import { CONFERENCES } from '../../lib/conferences.js';

export default {
  title: 'UI/ConferenceLogo',
  component: ConferenceLogo,
  parameters: { layout: 'centered' },
};

export const Single = { args: { name: 'Big Ten', size: 40 } };

export const AllConferences = {
  render: () => (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 18, maxWidth: 460, alignItems: 'center' }}>
      {Object.keys(CONFERENCES).map((name) => (
        <div key={name} style={{ textAlign: 'center', width: 70, fontSize: 10, color: 'var(--chalk-3)' }}>
          <ConferenceLogo name={name} size={40} />
          <div style={{ marginTop: 6 }}>{name}</div>
        </div>
      ))}
    </div>
  ),
};
