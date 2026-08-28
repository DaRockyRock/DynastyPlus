import { useState } from 'react';
import TeamSelect from './TeamSelect.jsx';

export default {
  title: 'Domain/TeamSelect',
  component: TeamSelect,
};

const TEAMS = [
  { name: 'Clemson Tigers', conference: 'ACC', espn_id: 228, abbreviation: 'CLEM', color: 'f56600' },
  { name: 'Miami Hurricanes', conference: 'ACC', espn_id: 2390, abbreviation: 'MIA', color: 'f47321' },
  { name: 'Ohio State Buckeyes', conference: 'Big Ten', espn_id: 194, abbreviation: 'OSU', color: 'bb0000' },
  { name: 'Nebraska Cornhuskers', conference: 'Big Ten', espn_id: 158, abbreviation: 'NEB', color: 'e41c38' },
  { name: 'Oregon Ducks', conference: 'Big Ten', espn_id: 2483, abbreviation: 'ORE', color: '154733' },
  { name: 'Georgia Bulldogs', conference: 'SEC', espn_id: 61, abbreviation: 'UGA', color: 'ba0c2f' },
  { name: 'Texas Longhorns', conference: 'SEC', espn_id: 251, abbreviation: 'TEX', color: 'bf5700' },
  { name: 'Boise State Broncos', conference: 'Mountain West', espn_id: 68, abbreviation: 'BSU', color: '0033a0' },
];

function Interactive({ initial }) {
  const [value, setValue] = useState(initial);
  return (
    <div style={{ maxWidth: 360 }}>
      <TeamSelect teams={TEAMS} value={value} onChange={setValue} />
      <p style={{ color: 'var(--chalk-3)', fontFamily: 'var(--font-body)', marginTop: 12 }}>
        Selected: {value || '(none)'}
      </p>
    </div>
  );
}

export const Default = () => <Interactive initial="Nebraska Cornhuskers" />;
export const Unselected = () => <Interactive initial="" />;
export const Disabled = () => (
  <div style={{ maxWidth: 360 }}>
    <TeamSelect teams={TEAMS} value="Georgia Bulldogs" onChange={() => {}} disabled />
  </div>
);
