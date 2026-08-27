import { noEmDash } from '../../lib/format.js';

// The reporter's question, set like a quote at the podium. `followUp` flags it as
// a rare press for a vague answer.
export default function PresserQuestion({ question, followUp = false }) {
  if (!question) return null;
  return (
    <div className={`presser-q${followUp ? ' is-followup' : ''}`}>
      {followUp && <span className="presser-q-tag">Follow-up</span>}
      <p className="presser-q-text">{noEmDash(question)}</p>
    </div>
  );
}
