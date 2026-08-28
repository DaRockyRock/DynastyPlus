import RecruitingAutomationPanel from './RecruitingAutomationPanel.jsx';

const data = {
  writable: true,
  config: { enabled: false, last_applied: null },
  plan: { offers: 1213, attention: 196 },
  audit: {
    class_size: 4100,
    capacity: { used: 4270, total: 4830 },
    tiers: [
      { tier: 'top10', mean_offers: 27.7, offer_floor: 22, mean_attention: 1, attention_floor: 6, under_offer_floor: 0, under_attention_floor: 10 },
      { tier: 'elite5', mean_offers: 24.5, offer_floor: 20, mean_attention: 1, attention_floor: 5, under_offer_floor: 2, under_attention_floor: 22 },
      { tier: 'high4', mean_offers: 20.4, offer_floor: 16, mean_attention: 1.8, attention_floor: 3, under_offer_floor: 17, under_attention_floor: 94 },
    ],
  },
};

export default {
  title: 'Domain/RecruitingAutomationPanel',
  component: RecruitingAutomationPanel,
  parameters: { layout: 'padded' },
};

export const OffByDefault = { args: { data, onToggle: () => {}, onApply: () => {} } };
export const Enabled = {
  args: { data: { ...data, config: { ...data.config, enabled: true } }, onToggle: () => {}, onApply: () => {} },
};
export const Applying = {
  args: { data: { ...data, config: { ...data.config, enabled: true } }, busy: true, onToggle: () => {}, onApply: () => {} },
};
