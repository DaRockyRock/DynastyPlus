import BudgetMeter from './BudgetMeter.jsx';
import { formatMoney } from '../../lib/format.js';

export default {
  title: 'UI/BudgetMeter',
  component: BudgetMeter,
  parameters: { layout: 'padded' },
};

export const Pools = {
  render: () => (
    <div style={{ width: 360, display: 'flex', flexDirection: 'column', gap: 18 }}>
      <BudgetMeter label="Recruiting NIL" value={900000} max={5500000} tone="nil"
        caption={`${formatMoney(4600000)} of ${formatMoney(5500000)} left`} />
      <BudgetMeter label="Roster NIL" value={2650000} max={5000000} tone="recruiting"
        caption={`${formatMoney(2350000)} of ${formatMoney(5000000)} left`} />
      <BudgetMeter label="Recruiting Hours" value={600} max={1500} tone="cfp" caption="900 of 1500 left" />
      <BudgetMeter label="Over budget" value={6200000} max={5500000} tone="nil" caption="over the pool" />
    </div>
  ),
};
