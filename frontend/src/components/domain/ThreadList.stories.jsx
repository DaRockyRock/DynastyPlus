import ThreadList from './ThreadList.jsx';

const threads = [
  { week: 4, category: 'Transfer portal', summary: 'Drew Lindqvist rumored to be weighing the portal.' },
  { week: 9, category: 'CFP watch', summary: 'Nebraska pushing for a playoff bid at 8-1.' },
  { week: 10, category: 'Recruiting', summary: 'Five-star Cam Brooks-Lee set an official visit for Week 10.' },
];

export default { title: 'Domain/ThreadList', component: ThreadList, parameters: { layout: 'padded' } };

export const Default = { render: () => <div style={{ width: 420 }}><ThreadList threads={threads} /></div> };
export const Empty = { render: () => <div style={{ width: 420 }}><ThreadList threads={[]} /></div> };
