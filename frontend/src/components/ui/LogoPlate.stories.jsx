import LogoPlate from './LogoPlate.jsx';
import TeamLogo from './TeamLogo.jsx';
import ConferenceLogo from './ConferenceLogo.jsx';

export default {
  title: 'UI/LogoPlate',
  component: LogoPlate,
  parameters: { layout: 'centered' },
};

// The reason the plate exists: Ohio State's near-black block O is illegible bare
// on the dark field (left), and reads clearly on the plate (right).
export const TeamMarks = {
  render: () => (
    <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
      <TeamLogo espnId={194} abbr="OSU" name="Ohio State Buckeyes" size={56} plate={false} />
      <TeamLogo espnId={194} abbr="OSU" name="Ohio State Buckeyes" size={56} />
      <TeamLogo espnId={61} abbr="UGA" name="Georgia Bulldogs" size={56} />
      <TeamLogo espnId={158} abbr="NEB" name="Nebraska Cornhuskers" size={56} />
    </div>
  ),
};

// Conference marks get the same treatment in card contexts.
export const ConferenceMarks = {
  render: () => (
    <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
      <ConferenceLogo name="Big Ten" size={40} plate />
      <ConferenceLogo name="SEC" size={40} plate />
    </div>
  ),
};

// Sizes used across the app.
export const Sizes = {
  render: () => (
    <div style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
      {[18, 26, 40, 56, 70].map((s) => (
        <TeamLogo key={s} espnId={194} abbr="OSU" name="Ohio State Buckeyes" size={s} />
      ))}
    </div>
  ),
};
