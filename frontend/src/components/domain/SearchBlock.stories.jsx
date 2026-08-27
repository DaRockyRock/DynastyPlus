import SearchBlock from './SearchBlock.jsx';

export default {
  title: 'Domain/SearchBlock',
  component: SearchBlock,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => (
    <div style={{ width: 620 }}>
      <SearchBlock search={{
        open_team: 'Florida Gators',
        narrative: 'The Florida job is open, and it is one of the more attractive openings of the cycle. The collective wants a closer who can win the region.',
        frontrunner: 'Tobias Frame',
      }} />
    </div>
  ),
};
