import MoneyValue from './MoneyValue.jsx';

export default {
  title: 'UI/MoneyValue',
  component: MoneyValue,
  parameters: { layout: 'padded' },
};

export const Scale = {
  render: () => (
    <div style={{ display: 'flex', gap: 22, alignItems: 'baseline', fontSize: 22 }}>
      <MoneyValue value={9500000} />
      <MoneyValue value={250000} suffix="/yr" />
      <MoneyValue value={0} />
    </div>
  ),
};

export const Tones = {
  render: () => (
    <div style={{ display: 'flex', gap: 22, alignItems: 'baseline', fontSize: 22 }}>
      <MoneyValue value={2350000} tone="pos" />
      <MoneyValue value={-180000} tone="neg" />
      <MoneyValue value={5500000} tone="nil" />
    </div>
  ),
};
