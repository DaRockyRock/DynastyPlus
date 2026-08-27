import DecadeCard from './DecadeCard.jsx';

export default { title: 'Domain/DecadeCard', component: DecadeCard, parameters: { layout: 'padded' } };

export const Default = {
  render: () => (
    <div style={{ width: 560 }}>
      <DecadeCard decade={{ decade: '2027-2036', summary: 'A decade defined by the rebuild, the breakthrough, and a return to national relevance.' }} />
    </div>
  ),
};
