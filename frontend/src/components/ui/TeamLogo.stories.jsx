import TeamLogo from './TeamLogo.jsx';

export default {
  title: 'UI/TeamLogo',
  component: TeamLogo,
  parameters: { layout: 'centered' },
  argTypes: { size: { control: { type: 'range', min: 16, max: 120, step: 4 } } },
};

// Real ESPN logos (Nebraska, Ohio State, Oregon, Texas).
export const Nebraska = { args: { espnId: 158, abbr: 'NEB', name: 'Nebraska Cornhuskers', size: 64 } };
export const OhioState = { args: { espnId: 194, abbr: 'OSU', name: 'Ohio State Buckeyes', size: 64 } };

export const Sizes = {
  render: () => (
    <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
      {[24, 32, 46, 64, 88].map((s) => (
        <TeamLogo key={s} espnId={158} abbr="NEB" name="Nebraska" size={s} />
      ))}
    </div>
  ),
};

// Monogram fallback when the logo cannot load (unknown espnId).
export const MonogramFallback = {
  args: { espnId: null, abbr: 'NEB', name: 'Nebraska Cornhuskers', color: '#e41c38', size: 64 },
};

export const Row = {
  render: () => (
    <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
      {[[158, 'NEB'], [194, 'OSU'], [2483, 'ORE'], [251, 'TEX'], [61, 'UGA'], [333, 'ALA']].map(([id, ab]) => (
        <TeamLogo key={id} espnId={id} abbr={ab} size={40} />
      ))}
    </div>
  ),
};
