import GameScoreHeader from './GameScoreHeader.jsx';
import { gameCenter } from '../fixtures.js';

export default { title: 'Domain/GameScoreHeader', component: GameScoreHeader, parameters: { layout: 'padded' } };

export const Final = { render: () => <div style={{ maxWidth: 560 }}><GameScoreHeader game={gameCenter} /></div> };
// With the league coaching directory: each team shows its head coach under the abbr.
export const WithCoaches = {
  render: () => (
    <div style={{ maxWidth: 560 }}>
      <GameScoreHeader
        game={gameCenter}
        coaches={{
          [gameCenter.away.name]: { name: 'Vance Calhoun' },
          [gameCenter.home.name]: { name: 'Marcus Larkin' },
        }}
      />
    </div>
  ),
};
export const Overtime = {
  render: () => <div style={{ maxWidth: 560 }}><GameScoreHeader game={{ ...gameCenter, overtime: true, final: { ...gameCenter.final, overtime: true } }} /></div>,
};
