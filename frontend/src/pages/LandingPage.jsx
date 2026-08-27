import { useApp } from '../context/AppContext.jsx';
import {
  PageHeader, Button, EmptyState, DynastyCard, SectionTitle, Icons,
} from '../components/index.js';

// The companion's landing screen: a library of dynasties scanned from the
// Simulator. The app is passive here, nothing generates. The coach creates a
// dynasty in the Simulator, clicks Scan to import it, then Continue to enter.
export default function LandingPage() {
  const { dynastyLib, scanning, scan, selectDynasty } = useApp();
  const list = dynastyLib?.dynasties || [];
  // A new/updated save is sitting in the Simulator drop spot, not yet imported
  // (a brand-new program, or a newer week/state than what we last scanned).
  const updateWaiting = dynastyLib?.save_present && dynastyLib?.save_hash
    && dynastyLib.save_hash !== dynastyLib.current_hash;

  return (
    <div className="view" style={{ maxWidth: 760, margin: '0 auto' }}>
      <PageHeader
        title="Dynasty+ Tools"
        sub="Pick a dynasty to continue, or scan one in from the Simulator."
        actions={(
          <Button variant="accent" icon={<Icons.RefreshIcon />} onClick={scan} spinning={scanning} disabled={scanning}>
            {scanning ? 'Scanning...' : 'Scan from Simulator'}
          </Button>
        )}
      />

      {updateWaiting && (
        <div
          style={{
            margin: '4px 0 20px', padding: '12px 16px', borderRadius: 10,
            background: 'color-mix(in srgb, var(--team) 16%, transparent)',
            border: '1px solid color-mix(in srgb, var(--team) 45%, transparent)',
            color: 'var(--text-1, #e9eef5)', fontSize: 13.5,
          }}
        >
          A dynasty save is waiting in the Simulator. Click <strong>Scan from Simulator</strong> to import it.
        </div>
      )}

      <SectionTitle>Your dynasties</SectionTitle>
      {list.length === 0 ? (
        <EmptyState>
          No dynasties yet. Open the Simulator (http://127.0.0.1:5070), start a season,
          then click Scan from Simulator to bring it in here.
        </EmptyState>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
          {list.map((d) => (
            <DynastyCard key={d.id} dynasty={d} onContinue={selectDynasty} busy={scanning} />
          ))}
        </div>
      )}

    </div>
  );
}
