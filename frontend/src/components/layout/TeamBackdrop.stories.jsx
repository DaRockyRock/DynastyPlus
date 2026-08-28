import TeamBackdrop from './TeamBackdrop.jsx';

export default {
  title: 'Layout/TeamBackdrop',
  component: TeamBackdrop,
};

// The fixed stadium layer needs some foreground to show it is behind content.
const Foreground = () => (
  <div style={{ position: 'relative', minHeight: 420, padding: 40 }}>
    <h1 style={{ fontFamily: 'var(--font-hero)', fontStyle: 'italic', color: '#fff' }}>
      WEEK 3, 2026
    </h1>
    <p style={{ color: 'var(--chalk-2)', maxWidth: 480 }}>
      Panels render over the team&apos;s extracted hub background. The dark wash
      keeps text readable at any art brightness.
    </p>
  </div>
);

export const BallState = () => (
  <>
    <TeamBackdrop espnId={2050} />
    <Foreground />
  </>
);

export const MissingArt = () => (
  <>
    <TeamBackdrop espnId={999999} />
    <Foreground />
  </>
);
