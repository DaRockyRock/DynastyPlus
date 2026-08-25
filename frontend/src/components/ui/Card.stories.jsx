import Card from './Card.jsx';

export default {
  title: 'UI/Card',
  component: Card,
  parameters: { layout: 'padded' },
};

export const Basic = {
  render: () => (
    <Card style={{ padding: 18, maxWidth: 360 }}>
      <h3 style={{ margin: '0 0 6px' }}>Card title</h3>
      <p style={{ margin: 0, color: 'var(--text-2)', fontSize: 13 }}>
        The base elevated surface used across the app for grouping content.
      </p>
    </Card>
  ),
};

export const Tile = {
  render: () => (
    <Card className="tile" style={{ maxWidth: 360 }}>
      <h3>Tile variant</h3>
      <div className="muted">Adds consistent internal padding via the tile class.</div>
    </Card>
  ),
};
