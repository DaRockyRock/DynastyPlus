import { noEmDash } from '../../lib/format.js';

// The exchanges so far (or the full record once complete): each reporter's
// question with the coach's answer, plus any follow-up. Auto-filled answers
// (after a skip) carry a subtle tag.
export default function PresserTranscript({ turns = [], coachName = 'Coach' }) {
  if (!turns.length) return null;
  return (
    <div className="presser-transcript">
      {turns.map((t, i) => (
        <div className="presser-turn" key={i}>
          <div className="presser-turn-q">
            <span className="presser-turn-who">{t.reporter_name}</span>
            <span className="presser-turn-text">{noEmDash(t.question)}</span>
          </div>
          {t.answer && (
            <div className="presser-turn-a">
              <span className="presser-turn-who">{coachName}{t.auto ? ' (statement)' : ''}</span>
              <span className="presser-turn-text">{noEmDash(t.answer)}</span>
            </div>
          )}
          {t.follow_up_question && (
            <>
              <div className="presser-turn-q is-followup">
                <span className="presser-turn-who">{t.reporter_name}</span>
                <span className="presser-turn-text">{noEmDash(t.follow_up_question)}</span>
              </div>
              {t.follow_up_answer && (
                <div className="presser-turn-a">
                  <span className="presser-turn-who">{coachName}{t.auto ? ' (statement)' : ''}</span>
                  <span className="presser-turn-text">{noEmDash(t.follow_up_answer)}</span>
                </div>
              )}
            </>
          )}
        </div>
      ))}
    </div>
  );
}
