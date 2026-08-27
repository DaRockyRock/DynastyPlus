import StatTable from './StatTable.jsx';
import { statRows } from '../fixtures.js';

export default { title: 'Domain/StatTable', component: StatTable, parameters: { layout: 'padded' } };

export const Default = { render: () => <div style={{ width: 340 }}><StatTable rows={statRows} /></div> };
