import PollRankRow from './PollRankRow.jsx';
import Card from '../ui/Card.jsx';
import { pollEntries } from '../fixtures.js';

export default {
  title: 'Domain/PollRankRow',
  component: PollRankRow,
  parameters: { layout: 'padded' },
};

export const ReadOnly = {
  render: () => (
    <Card className="panel" style={{ width: 380 }}>
      <PollRankRow entry={pollEntries[0]} />
      <PollRankRow entry={pollEntries[4]} isUser />
    </Card>
  ),
};

export const Editable = {
  render: () => (
    <Card className="panel" style={{ width: 380 }}>
      <PollRankRow entry={pollEntries[1]} editable onMoveDown={() => {}} onRemove={() => {}} />
      <PollRankRow entry={pollEntries[2]} editable onMoveUp={() => {}} onMoveDown={() => {}} onRemove={() => {}} />
    </Card>
  ),
};

export const AlgorithmDelta = {
  render: () => (
    <Card className="panel" style={{ width: 380 }}>
      <PollRankRow entry={{ ...pollEntries[0], delta: 3 }} />
      <PollRankRow entry={{ ...pollEntries[1], delta: -2 }} />
      <PollRankRow entry={{ ...pollEntries[2], delta: 0 }} />
    </Card>
  ),
};
