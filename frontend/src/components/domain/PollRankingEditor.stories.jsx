import { useState } from 'react';
import PollRankingEditor from './PollRankingEditor.jsx';
import Card from '../ui/Card.jsx';
import { pollEntries } from '../fixtures.js';

export default {
  title: 'Domain/PollRankingEditor',
  component: PollRankingEditor,
  parameters: { layout: 'padded' },
};

function Live() {
  const [entries, setEntries] = useState(pollEntries.slice(0, 8));
  return (
    <Card className="panel" style={{ width: 420 }}>
      <PollRankingEditor
        entries={entries}
        onChange={setEntries}
        userTeam="Nebraska Cornhuskers"
        addOptions={pollEntries.filter((e) => !entries.some((d) => d.team === e.team))}
      />
    </Card>
  );
}

export const Interactive = { render: () => <Live /> };
