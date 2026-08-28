import { useCallback, useState } from 'react';
import { useApp } from '../context/AppContext.jsx';
import { APP_NAME, APP_TAGLINE } from '../lib/app.js';
import {
  PageHeader, Button, EmptyState, DynastyCard, SectionTitle, Icons,
  SaveImportModal, ConfirmDialog,
} from '../components/index.js';

// The landing screen: a library of dynasties scanned from the
// CFB 27 saves folder. The app is passive here, nothing generates. The coach
// plays CFB 27, clicks Scan to read the saves, then Continue to enter a dynasty.
// Scan only sees saves the game still lists, so "Import a save" reaches every
// save file on disk (older dynasties, manual saves) that Scan cannot.
export default function LandingPage() {
  const {
    dynastyLib, scanning, scan, selectDynasty, openSetup,
    browseSaves, loadSaveTeams, importSave, removeDynasty,
  } = useApp();
  const list = dynastyLib?.dynasties || [];

  const [importOpen, setImportOpen] = useState(false);
  const [saves, setSaves] = useState([]);
  const [savesLoading, setSavesLoading] = useState(false);
  const [removeTarget, setRemoveTarget] = useState(null);
  const [removeBusy, setRemoveBusy] = useState(false);

  const openImport = useCallback(async () => {
    setImportOpen(true);
    setSavesLoading(true);
    try { setSaves(await browseSaves()); }
    finally { setSavesLoading(false); }
  }, [browseSaves]);

  // After an import, refresh the browser list so the row flips to "In library".
  const handleImport = useCallback(async (path, school) => {
    const entry = await importSave(path, school);
    if (entry) setSaves(await browseSaves());
    return entry;
  }, [importSave, browseSaves]);

  const confirmRemove = useCallback(async () => {
    if (!removeTarget) return;
    setRemoveBusy(true);
    try {
      if (await removeDynasty(removeTarget.id)) setRemoveTarget(null);
    } finally {
      setRemoveBusy(false);
    }
  }, [removeDynasty, removeTarget]);
  // A newer save is on disk than what we last scanned (a new program, or a
  // newer week/state), so a rescan would pick it up.
  const updateWaiting = dynastyLib?.save_present && dynastyLib?.save_hash
    && dynastyLib.save_hash !== dynastyLib.current_hash;

  return (
    <div className="view" style={{ maxWidth: 760, margin: '0 auto' }}>
      <PageHeader
        title={APP_NAME}
        sub={`${APP_TAGLINE} Pick a dynasty to continue, or scan your CFB 27 saves.`}
        actions={(
          <>
            <Button variant="action" icon={<Icons.ImageIcon />} onClick={openSetup}>
              Game art &amp; folders
            </Button>
            <Button variant="action" icon={<Icons.UploadIcon />} onClick={openImport}>
              Import a save
            </Button>
            <Button variant="accent" icon={<Icons.RefreshIcon />} onClick={scan} spinning={scanning} disabled={scanning}>
              {scanning ? 'Scanning...' : 'Scan Saves'}
            </Button>
          </>
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
          A newer dynasty save is on disk. Click <strong>Scan Saves</strong> to bring it in.
        </div>
      )}

      <SectionTitle>Your dynasties</SectionTitle>
      {list.length === 0 ? (
        <EmptyState>
          No dynasties found. Play a dynasty in EA Sports College Football 27
          (so the game writes a save), then click Scan Saves to bring it in here.
        </EmptyState>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
          {list.map((d) => (
            <DynastyCard
              key={d.id}
              dynasty={d}
              onContinue={selectDynasty}
              onRemove={setRemoveTarget}
              busy={scanning}
            />
          ))}
        </div>
      )}

      <SaveImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        saves={saves}
        loading={savesLoading}
        onImport={handleImport}
        loadTeams={loadSaveTeams}
      />
      <ConfirmDialog
        open={!!removeTarget}
        title="Remove this dynasty?"
        confirmLabel="Remove from library"
        danger
        busy={removeBusy}
        onConfirm={confirmRemove}
        onClose={() => setRemoveTarget(null)}
      >
        This removes {removeTarget?.team_name} from Dynasty+ only. The CFB 27 save file
        and its companion data stay untouched. You can bring it back later with Import a save.
      </ConfirmDialog>
    </div>
  );
}
