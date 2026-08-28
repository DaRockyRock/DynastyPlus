import { BoltIcon } from '../ui/icons.jsx';
import SetupFooter from './SetupFooter.jsx';

// Full-screen chrome for selecting the local game and save folders.
export default function SetupScreen({
  title = 'Set up Dynasty+',
  subtitle,
  onSkip,
  skipLabel = 'Skip for now',
  onPrimary,
  primaryLabel = 'Continue',
  primaryDisabled = false,
  primarySpinning = false,
  footerHint,
  children,
}) {
  return (
    <div className="setup-root setup-screen">
      <header className="setup-header">
        <span className="setup-mark"><BoltIcon /></span>
        <div className="setup-titles">
          <h1>{title}</h1>
          {subtitle && <span className="sub">{subtitle}</span>}
        </div>
        <span className="spacer" />
        {onSkip && (
          <button type="button" className="setup-skip" onClick={onSkip}>{skipLabel}</button>
        )}
      </header>

      <div className="setup-scroll">
        <div className="setup-inner setup-body">{children}</div>
      </div>

      {onPrimary && (
        <SetupFooter
          onPrimary={onPrimary}
          primaryLabel={primaryLabel}
          primaryDisabled={primaryDisabled}
          primarySpinning={primarySpinning}
          hint={footerHint}
        />
      )}
    </div>
  );
}
