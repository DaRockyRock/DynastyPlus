import GameScreen from './GameScreen.jsx';
import PanelCard from '../ui/PanelCard.jsx';

export default {
  title: 'Layout/GameScreen',
  component: GameScreen,
  parameters: { layout: 'fullscreen' },
};

const MENU = [
  { id: 'rules', label: 'Conference Rules' },
  { id: 'rivals', label: 'Protected Rivals' },
  { id: 'preview', label: 'Schedule Preview' },
];

export const ScheduleTool = {
  render: () => (
    <div style={{ padding: '24px 28px' }}>
      <GameScreen
        week="Week 3, 2026"
        menu={MENU}
        active="rules"
        onSelect={() => {}}
        heroTitle="Schedule Editor"
        heroSub="Configure conference games and protected rivalries."
      >
        <PanelCard title="Big Ten">
          <p style={{ margin: 0 }}>Nine conference games with rivalry week in Week 14.</p>
        </PanelCard>
      </GameScreen>
    </div>
  ),
};
