import PresserBusyOverlay from './PresserBusyOverlay.jsx';

// The busy scrim is absolutely positioned inside .presser-card, so the story
// frames it in a stand-in card to show how it covers the modal.
export default {
  title: 'Domain/PresserBusyOverlay',
  component: PresserBusyOverlay,
  parameters: { layout: 'centered' },
};

const Card = ({ children }) => (
  <div
    className="presser-card"
    style={{ width: 520, height: 320, padding: 22, display: 'flex', flexDirection: 'column', gap: 10 }}
  >
    <div className="presser-kicker">Post-Game Press Conference</div>
    <p style={{ color: 'var(--chalk-2)' }}>
      The transcript and the current question sit under the scrim while the next
      question generates.
    </p>
    {children}
  </div>
);

export const Generating = {
  render: () => (
    <Card>
      <PresserBusyOverlay show />
    </Card>
  ),
};

export const SkipWrapUp = {
  render: () => (
    <Card>
      <PresserBusyOverlay show title="Wrapping up" caption="Finishing the rest of the press conference" />
    </Card>
  ),
};

// Hidden: renders nothing (the overlay is gone once the next question lands).
export const Hidden = {
  render: () => (
    <Card>
      <PresserBusyOverlay show={false} />
    </Card>
  ),
};
