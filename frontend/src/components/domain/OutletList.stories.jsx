import OutletList from './OutletList.jsx';

const outlets = [
  { name: 'The Press Box', voice: 'national flagship, measured', reliability: 92 },
  { name: 'Saturday Authority', voice: 'analytics-forward, contrarian', reliability: 88 },
  { name: 'Coaching Confidential', voice: 'carousel rumor mill', reliability: 66 },
  { name: 'The Portal Report', voice: 'transfer scoops, fast and loose', reliability: 71 },
];

export default {
  title: 'Domain/OutletList',
  component: OutletList,
  parameters: { layout: 'padded' },
};

export const Default = { render: () => <div style={{ width: 380 }}><OutletList outlets={outlets} /></div> };
