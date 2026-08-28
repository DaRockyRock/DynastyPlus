import ModToolsPanel from './ModToolsPanel.jsx';
import { modToolsStatus, modExportResult } from '../fixtures.js';

export default {
  title: 'Domain/ModToolsPanel',
  component: ModToolsPanel,
  parameters: { layout: 'padded' },
};

const wrap = (props) => (
  <div style={{ width: 680 }}>
    <ModToolsPanel onLocate={() => {}} onOpenManager={() => {}} onRefresh={() => {}} {...props} />
  </div>
);

export const ToolsNotFound = {
  render: () => wrap({ status: modToolsStatus.missing }),
};

export const AnticheatSwapPending = {
  render: () => wrap({ status: modToolsStatus.swapPending }),
};

export const Ready = {
  render: () => wrap({ status: modToolsStatus.ready }),
};

export const ReadyWithInstalledMod = {
  render: () => wrap({ status: modToolsStatus.readyInstalled, exportResult: modExportResult }),
};
