import Button from './Button.jsx';
import { RefreshIcon } from './icons.jsx';

// Used on every module section to force backend regeneration of that section.
export default function RegenerateButton({ onClick, spinning = false, label = 'Regenerate' }) {
  return (
    <Button variant="regen" icon={<RefreshIcon size={14} />} spinning={spinning} onClick={onClick}>
      {label}
    </Button>
  );
}
