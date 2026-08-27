import Stepper from '../ui/Stepper.jsx';
import { BoltIcon } from '../ui/icons.jsx';

// Top bar of the first-run setup flow: brand mark, title, the step indicator,
// and an optional "skip for now" control. Mirrors the Customize studio header.
export default function OnboardingHeader({ steps = [], current = 0, onSkip, skipLabel = 'Continue on mock content' }) {
  return (
    <header className="onb-header">
      <span className="onb-mark"><BoltIcon /></span>
      <div className="onb-titles">
        <h1>Connect your model</h1>
        <span className="sub">Power the news, committee, recruiting and phone with an AI of your choice</span>
      </div>
      {steps.length > 0 && (
        <div className="onb-steps"><Stepper steps={steps} current={current} /></div>
      )}
      <span className="spacer" />
      {onSkip && (
        <button type="button" className="onb-skip" onClick={onSkip}>{skipLabel}</button>
      )}
    </header>
  );
}
