import StoryWatermark from './StoryWatermark.jsx';
import { logoUrl } from '../../lib/format.js';
import { matchupMarks, groupMarks, groupSixMarks, conferenceMarks, teamMarks } from '../fixtures.js';

// The watermark sits inside a slide's background, beneath the legibility gradient,
// so preview it in a slide-sized box with the same gradient + overlay and some
// sample copy on top to show it reads as a backdrop.
const accent = '#3b82f6';
const Slide = ({ children }) => (
  <div style={{ position: 'relative', width: 760, height: 360, borderRadius: 12, overflow: 'hidden' }}>
    <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(720px 360px at 78% 0%, ${accent}2e, transparent 62%), linear-gradient(135deg, ${accent}1f, #0b0f16 70%), #0b0f16` }}>
      {children}
      <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, rgba(7,10,16,.12) 0%, rgba(7,10,16,.5) 52%, rgba(7,10,16,.94) 100%)' }} />
    </div>
    <div style={{ position: 'absolute', left: 34, bottom: 30, maxWidth: 420, color: '#fff' }}>
      <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 34, lineHeight: 1.04, margin: 0, fontWeight: 700 }}>
        Headline rides over the backdrop
      </h2>
    </div>
  </div>
);

export default {
  title: 'Domain/StoryWatermark',
  component: StoryWatermark,
  parameters: { layout: 'padded' },
};

export const Matchup = { render: () => <Slide><StoryWatermark marks={matchupMarks} /></Slide> };
export const Group = { render: () => <Slide><StoryWatermark marks={groupMarks} /></Slide> };
export const GroupOfSix = { render: () => <Slide><StoryWatermark marks={groupSixMarks} /></Slide> };
export const Conference = { render: () => <Slide><StoryWatermark marks={conferenceMarks} /></Slide> };
export const SingleTeam = { render: () => <Slide><StoryWatermark marks={teamMarks} /></Slide> };
export const FallbackUserTeam = {
  render: () => <Slide><StoryWatermark marks={{ kind: null, teams: [] }} fallbackUrl={logoUrl(158)} /></Slide>,
};
