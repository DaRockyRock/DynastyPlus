import MoveRow from './MoveRow.jsx';
import Card from '../ui/Card.jsx';

export default {
  title: 'Domain/MoveRow',
  component: MoveRow,
  parameters: { layout: 'padded' },
};

export const Incoming = {
  render: () => (
    <Card className="panel" style={{ width: 420 }}>
      <MoveRow kind="in" player={{ name: 'Reggie Stallworth', position: 'WR', from: 'Arizona State Sun Devils', grade: 'B+' }} />
      <MoveRow kind="in" player={{ name: 'Mike Okafor', position: 'DT', from: 'Cincinnati Bearcats', grade: 'B' }} />
    </Card>
  ),
};

// Outgoing rows now carry the satisfaction-driven reason the player left (the
// Simulator owns this), shown on the right when no grade is present.
export const Outgoing = {
  render: () => (
    <Card className="panel" style={{ width: 420 }}>
      <MoveRow kind="out" player={{ name: 'Drew Lindqvist', position: 'QB', to: 'Miami Hurricanes', reason: 'Buried on the depth chart and itching for snaps.' }} />
      <MoveRow kind="out" player={{ name: 'Tre Robinson', position: 'WR', to: 'Undecided', reason: 'Frustrated with the way the season is going.' }} />
    </Card>
  ),
};

export const Targets = {
  render: () => (
    <Card className="panel" style={{ width: 420 }}>
      <MoveRow kind="target" player={{ name: 'Gavin Vermeer', position: 'RB', from: 'Baylor Bears', lean: 'Top 3' }} />
      <MoveRow kind="target" player={{ name: 'Rasheed Goodson', position: 'WR', from: 'Utah State Aggies', lean: 'On the board' }} />
    </Card>
  ),
};
