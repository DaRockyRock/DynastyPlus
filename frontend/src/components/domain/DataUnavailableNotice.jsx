import { Card } from '../index.js';
import { AlertIcon } from '../ui/icons.jsx';

// Honest placeholder for a screen whose data the CFB 27 save does not expose
// yet. Dynasty+ reads everything from the real game save and never invents game
// data, so a section with nothing real to show says so plainly rather than
// filling in mock content. `data` is a module payload with `unavailable: true`
// and a `reason`; pass a `title` for the section it stands in for.
export default function DataUnavailableNotice({
  data,
  title = 'Not available yet',
  hint = 'Dynasty+ reads this straight from your CFB 27 save. It will appear here once the save exposes it.',
}) {
  const reason = data?.reason || 'This data is not in the CFB 27 save yet.';
  return (
    <Card className="data-unavailable" style={{ padding: 28, textAlign: 'center' }}>
      <span className="data-unavailable-ico" aria-hidden="true">
        <AlertIcon size={26} />
      </span>
      <h3 className="data-unavailable-title">{title}</h3>
      <p className="data-unavailable-reason">{reason}</p>
      <p className="data-unavailable-hint">{hint}</p>
    </Card>
  );
}
