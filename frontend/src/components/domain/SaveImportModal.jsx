import { useState } from 'react';
import Modal from '../ui/Modal.jsx';
import Button from '../ui/Button.jsx';
import TeamSelect from './TeamSelect.jsx';
import SaveFileRow from './SaveFileRow.jsx';

// The "Import a save" overlay. Scan only sees saves whose
// PROFILE-COLLEGE row is still live, so a dynasty whose row rotated away (or a
// manual save that never had one) never appears in the library. This lists
// every save file on disk and imports the one the user picks; when the save has
// no profile row the game does not name the user's program, so the user chooses
// it from the save's own team list before importing.
export default function SaveImportModal({
  open, onClose, saves = [], loading = false, onImport, loadTeams,
}) {
  const [picking, setPicking] = useState(null); // save awaiting a team choice
  const [teams, setTeams] = useState([]);
  const [teamsLoading, setTeamsLoading] = useState(false);
  const [picked, setPicked] = useState('');
  const [busyPath, setBusyPath] = useState(null);

  const reset = () => { setPicking(null); setTeams([]); setPicked(''); };
  const close = () => { reset(); onClose?.(); };

  async function doImport(path, school) {
    setBusyPath(path);
    try {
      const entry = await onImport?.(path, school);
      if (entry) reset();
      return entry;
    } finally {
      setBusyPath(null);
    }
  }

  // The picker's value is the team's full name; the backend resolves the user's
  // program by school, so hand it the chosen team's school.
  function confirmPick() {
    const team = teams.find((t) => t.name === picked);
    doImport(picking.save_path, team ? team.school : picked);
  }

  async function openPicker(save) {
    setPicking(save);
    setPicked('');
    setTeams([]);
    setTeamsLoading(true);
    try {
      const list = await loadTeams?.(save.save_path);
      setTeams(list || []);
    } finally {
      setTeamsLoading(false);
    }
  }

  async function onRowImport(save) {
    if (save.school) {
      const entry = await doImport(save.save_path, save.school);
      if (entry) return;
      // the profile row named a program the save's team table does not match
      // (seen with the FCS-to-FBS movers): fall back to the picker so the
      // user chooses their team instead of the import silently going nowhere
    }
    await openPicker(save);
  }

  return (
    <Modal open={open} onClose={close} align="center">
      {open && (
        <div className="modal-card" style={{
          width: 'min(620px, 92vw)', maxHeight: '82vh', display: 'flex', flexDirection: 'column',
          background: 'var(--panel, #0c121e)', border: '1px solid var(--line, rgba(255,255,255,0.1))',
          borderRadius: 14, overflow: 'hidden',
        }}>
          <div style={{
            display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
            gap: 12, padding: '18px 20px 14px',
            borderBottom: '1px solid var(--line, rgba(255,255,255,0.08))',
          }}>
            <div>
              <div style={{
                font: '800 20px "Saira Condensed", sans-serif', letterSpacing: '0.02em',
                textTransform: 'uppercase', color: 'var(--text-1, #e9eef5)',
              }}>
                Import a save
              </div>
              <div style={{ fontSize: 12.5, color: 'var(--text-2, #9aa6b2)', marginTop: 3, maxWidth: 460 }}>
                Every dynasty save on disk. Bring in one Scan missed, older saves the
                game no longer lists on its load screen show up here too.
              </div>
            </div>
            <button className="bm-close" onClick={close} aria-label="Close">&times;</button>
          </div>

          <div style={{ padding: 16, overflowY: 'auto' }}>
            {picking ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div style={{ fontSize: 13.5, color: 'var(--text-1, #e9eef5)' }}>
                  This save has no program on record. Pick the team you coach in{' '}
                  <strong>{picking.save_name.replace(/^DYNASTY-/i, '')}</strong>.
                </div>
                {teamsLoading ? (
                  <div style={{ fontSize: 13, color: 'var(--text-2, #9aa6b2)' }}>Reading the save's teams...</div>
                ) : (
                  <TeamSelect teams={teams} value={picked} onChange={setPicked} placeholder="Select your program" />
                )}
                <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
                  <Button
                    variant="accent"
                    disabled={!picked || busyPath === picking.save_path}
                    spinning={busyPath === picking.save_path}
                    onClick={confirmPick}
                  >
                    {busyPath === picking.save_path ? 'Importing...' : 'Import dynasty'}
                  </Button>
                  <Button variant="action" onClick={reset} disabled={busyPath === picking.save_path}>
                    Back
                  </Button>
                </div>
              </div>
            ) : loading ? (
              <div style={{ padding: '24px 4px', fontSize: 13.5, color: 'var(--text-2, #9aa6b2)' }}>
                Reading your saves folder...
              </div>
            ) : saves.length === 0 ? (
              <div style={{ padding: '24px 4px', fontSize: 13.5, color: 'var(--text-2, #9aa6b2)' }}>
                No save files found in your CFB 27 saves folder.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {saves.map((s) => (
                  <SaveFileRow
                    key={s.save_path}
                    save={s}
                    onImport={onRowImport}
                    busy={busyPath === s.save_path}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}
