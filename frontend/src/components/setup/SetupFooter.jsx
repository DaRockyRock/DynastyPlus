import Button from '../ui/Button.jsx';
import { ChevronLeft, ChevronRight } from '../ui/icons.jsx';

export default function SetupFooter({
  onBack,
  backLabel = 'Back',
  onPrimary,
  primaryLabel = 'Continue',
  primaryIcon,
  primaryDisabled = false,
  primarySpinning = false,
  hint,
}) {
  return (
    <footer className="setup-footer">
      {onBack ? (
        <Button variant="action" icon={<ChevronLeft />} onClick={onBack}>{backLabel}</Button>
      ) : <span />}
      {hint && <span className="setup-hint">{hint}</span>}
      {onPrimary && (
        <Button
          variant="accent"
          icon={primaryIcon !== undefined ? primaryIcon : <ChevronRight />}
          spinning={primarySpinning}
          disabled={primaryDisabled || primarySpinning}
          onClick={onPrimary}
        >
          {primaryLabel}
        </Button>
      )}
    </footer>
  );
}
