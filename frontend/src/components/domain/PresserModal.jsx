import Modal from '../ui/Modal.jsx';
import Button from '../ui/Button.jsx';
import PresserReporterHeader from './PresserReporterHeader.jsx';
import PresserQuestion from './PresserQuestion.jsx';
import PresserAnswerInput from './PresserAnswerInput.jsx';
import PresserTranscript from './PresserTranscript.jsx';
import PresserBusyOverlay from './PresserBusyOverlay.jsx';

// The post-game press conference overlay. Five local reporters ask one question
// each; the coach answers (or skips the rest). Composes only library pieces.
// While in progress it cannot be dismissed by backdrop/escape (answer or skip);
// once complete it shows the public transcript with a Continue button.
export default function PresserModal({ presser, coachName = 'Coach', busy = false, onAnswer, onSkip, onClose }) {
  if (!presser) return null;
  const complete = presser.status === 'complete';
  const prompt = presser.prompt;
  return (
    <Modal open onClose={complete ? onClose : undefined} align="center" className="presser-overlay">
      <div className="presser-card">
        <PresserBusyOverlay show={busy} />
        <div className="presser-head">
          <span className="presser-kicker">Post-Game Press Conference</span>
          <span className="presser-result">{presser.result_line}</span>
        </div>

        {complete ? (
          <>
            <div className="presser-body">
              <PresserTranscript turns={presser.turns} coachName={coachName} />
            </div>
            <div className="presser-foot">
              <span className="presser-note">These remarks are on the record. Reporters may quote them all week.</span>
              <Button variant="accent" onClick={onClose}>Continue</Button>
            </div>
          </>
        ) : (
          <>
            {presser.turns?.length > 0 && (
              <div className="presser-body presser-prior">
                <PresserTranscript turns={presser.turns} coachName={coachName} />
              </div>
            )}
            {prompt && (
              <div className="presser-now">
                <PresserReporterHeader reporter={prompt.reporter} index={prompt.index} total={prompt.total} />
                <PresserQuestion question={prompt.question} followUp={prompt.kind === 'follow_up'} />
                <PresserAnswerInput onSend={onAnswer} onSkip={onSkip} busy={busy} />
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}
