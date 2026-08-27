import MilestoneRow from './MilestoneRow.jsx';
import { milestone } from '../fixtures.js';

export default { title: 'Domain/MilestoneRow', component: MilestoneRow, parameters: { layout: 'padded' } };

export const Default = { render: () => <div style={{ width: 480 }}><MilestoneRow milestone={milestone} /></div> };
