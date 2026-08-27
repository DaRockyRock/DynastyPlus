import CoachingTreeCard from './CoachingTreeCard.jsx';
import { coachingTree } from '../fixtures.js';

export default { title: 'Domain/CoachingTreeCard', component: CoachingTreeCard, parameters: { layout: 'padded' } };

export const Default = { render: () => <div style={{ width: 380 }}><CoachingTreeCard tree={coachingTree} /></div> };
