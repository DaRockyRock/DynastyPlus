import QuoteBlock from './QuoteBlock.jsx';
import { quote } from '../fixtures.js';

export default { title: 'Domain/QuoteBlock', component: QuoteBlock, parameters: { layout: 'padded' } };

export const Coach = { render: () => <div style={{ width: 560 }}><QuoteBlock quote={quote} /></div> };
export const Player = {
  render: () => (
    <div style={{ width: 560 }}>
      <QuoteBlock quote={{ speaker: 'Marcus Whitfield', role: 'QB, Nebraska', text: '"I just try to take care of the ball and let the offense operate."' }} />
    </div>
  ),
};
