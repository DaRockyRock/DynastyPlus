import HeatRow from './HeatRow.jsx';
import Card from '../ui/Card.jsx';
import { coach } from '../fixtures.js';

export default {
  title: 'Domain/HeatRow',
  component: HeatRow,
  parameters: { layout: 'padded' },
};

export const List = {
  render: () => (
    <Card style={{ padding: '8px 12px', width: 560 }}>
      <HeatRow coach={{ ...coach, coach: 'Garrett Mason', team: 'Nebraska Cornhuskers', abbr: 'NEB', espn_id: 158, record: '8-1', heat: 8, is_user: true, note: 'Job security as high as it has been.' }} />
      <HeatRow coach={coach} />
      <HeatRow coach={{ ...coach, coach: 'Marty Cobb', team: 'Michigan State Spartans', abbr: 'MSU', espn_id: 127, record: '5-4', heat: 79, note: 'Buyout drops sharply in January.' }} />
    </Card>
  ),
};
