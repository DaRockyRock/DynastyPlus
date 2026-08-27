import PresserReporterHeader from './PresserReporterHeader.jsx';
import { presserReporter } from '../fixtures.js';

export default { title: 'Domain/PresserReporterHeader', component: PresserReporterHeader, parameters: { layout: 'padded' } };

export const Local = { render: () => <div style={{ maxWidth: 520 }}><PresserReporterHeader reporter={presserReporter} index={0} total={5} /></div> };
export const National = {
  render: () => <div style={{ maxWidth: 520 }}><PresserReporterHeader reporter={{ name: 'Pete Thamel', outlet: 'ESPN', scope: 'national' }} index={2} total={5} /></div>,
};
