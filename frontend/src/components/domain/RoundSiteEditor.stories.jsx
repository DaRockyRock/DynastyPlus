import { useState } from 'react';
import RoundSiteEditor from './RoundSiteEditor.jsx';
import { playoffBracket12, saveStadiums } from '../fixtures.js';

const bowls = [
  { key: 'peach', name: 'Peach Bowl' },
  { key: 'rose', name: 'Rose Bowl' },
  { key: 'fiesta', name: 'Fiesta Bowl' },
  { key: 'sugar', name: 'Sugar Bowl' },
  { key: 'cotton', name: 'Cotton Bowl' },
  { key: 'orange', name: 'Orange Bowl' },
  { key: 'alamo', name: 'Alamo Bowl' },
];

export default {
  title: 'Domain/RoundSiteEditor',
  component: RoundSiteEditor,
};

function Demo({ initial, round, stadiums = [] }) {
  const [config, setConfig] = useState(initial);
  return (
    <div style={{ width: 420 }}>
      <RoundSiteEditor
        name={round.name}
        games={round.games}
        config={config}
        bowls={bowls}
        stadiums={stadiums}
        onChange={setConfig}
      />
    </div>
  );
}

export const CampusRound = { render: () => <Demo round={playoffBracket12.rounds[0]} initial={{ mode: 'higher_seed' }} /> };
export const BowlRound = { render: () => <Demo round={playoffBracket12.rounds[1]} initial={{ mode: 'bowls', bowls: ['peach', 'rose', 'fiesta', 'sugar'] }} /> };
export const NeutralRound = { render: () => <Demo round={playoffBracket12.rounds[2]} initial={{ mode: 'neutral', venue: 'Wembley Stadium', city: 'London, UK' }} /> };
export const NeutralRoundWithGameStadiums = { render: () => <Demo round={playoffBracket12.rounds[2]} stadiums={saveStadiums} initial={{ mode: 'neutral', stadium: 112, venue: 'Mercedes-Benz Stadium', city: 'Atlanta, GA' }} /> };
