import PanelCard from './PanelCard.jsx';

export default {
  title: 'UI/PanelCard',
  component: PanelCard,
};

export const ScheduleSummary = {
  render: () => (
    <div style={{ maxWidth: 620 }}>
      <PanelCard title="Schedule Summary">
        <p style={{ margin: 0 }}>136 teams, 12 regular-season games, 0 conflicts.</p>
      </PanelCard>
    </div>
  ),
};

export const ConferenceRules = {
  render: () => (
    <div style={{ maxWidth: 620 }}>
      <PanelCard title="Big Ten" right={<span className="st-note">18 teams</span>}>
        <p style={{ margin: 0 }}>Nine conference games with two protected rivals.</p>
      </PanelCard>
    </div>
  ),
};

export const Flush = {
  render: () => (
    <div style={{ maxWidth: 620 }}>
      <PanelCard title="Rankings" flush>
        <div style={{ padding: 20, color: 'var(--chalk-3)' }}>table content, no body padding</div>
      </PanelCard>
    </div>
  ),
};
