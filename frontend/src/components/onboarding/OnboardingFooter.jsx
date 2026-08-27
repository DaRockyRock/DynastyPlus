import Button from '../ui/Button.jsx';
import { ChevronLeft, ChevronRight } from '../ui/icons.jsx';

// Sticky footer nav for the wizard. Back on the left, the primary action on the
// right. All actions are optional so each step can show only what it needs.
export default function OnboardingFooter({
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
    <footer className="onb-footer">
      {onBack ? (
        <Button variant="action" icon={<ChevronLeft />} onClick={onBack}>{backLabel}</Button>
      ) : <span />}
      {hint && <span className="onb-hint">{hint}</span>}
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
