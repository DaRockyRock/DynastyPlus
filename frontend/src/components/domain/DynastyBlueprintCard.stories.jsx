import DynastyBlueprintCard from './DynastyBlueprintCard.jsx';
import { budgetSnapshot } from '../fixtures.js';

export default {
  title: 'Domain/DynastyBlueprintCard',
  component: DynastyBlueprintCard,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => <div style={{ width: 520 }}><DynastyBlueprintCard snapshot={budgetSnapshot} onAllocate={() => {}} /></div>,
};
