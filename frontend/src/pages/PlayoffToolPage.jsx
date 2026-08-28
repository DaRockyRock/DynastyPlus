import { useApp } from '../context/AppContext.jsx';
import { PlayoffFormatEditor } from '../components/index.js';

// Dynasty+ Tools' Playoff tab: the playoff format customizer plus its live
// bracket preview, edge to edge. The embedded PlayoffFormatEditor renders its own header (with the
// Reset/Save actions), the controls, the preview bracket, and the selection
// summary, all driven by /api/playoff/*. The page is rendered full
// bleed (App.jsx gives the main view a `view-bleed` modifier for this tab) so
// the bracket gets the whole width instead of being clipped by the column.
//
// The preview builds the current field into the draft format. On a real CFB 27
// save the rankings are not parsed yet, so the editor shows a "cannot be built
// yet" note next to the controls; the format itself still saves.
export default function PlayoffToolPage() {
  const { pointer, toast } = useApp();
  return (
    <div className="playoff-tool">
      <PlayoffFormatEditor embedded toast={toast} pointer={pointer} />
    </div>
  );
}
