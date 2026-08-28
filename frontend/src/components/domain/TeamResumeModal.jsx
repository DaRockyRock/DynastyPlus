import { useEffect, useState } from 'react';
import Modal from '../ui/Modal.jsx';
import Button from '../ui/Button.jsx';
import Select from '../ui/Select.jsx';
import Skeleton from '../ui/Skeleton.jsx';
import TeamResumePanel from './TeamResumePanel.jsx';
import TaleOfTheTape from './TaleOfTheTape.jsx';

// The resume overlay opened from a rank card: the team's full resume with a
// built-in comparison flow (pick any ranked team, get the tale of the tape
// for the committee's edge cases). `loadResume(row)` is the page's cached
// fetcher; `entries` (the active poll's ordering) feeds the picker.
export default function TeamResumeModal({
  open, onClose, resume, loading = false, entries = [], loadResume, initialCompareRow = null,
}) {
  const [compareRow, setCompareRow] = useState('');
  const [compareResume, setCompareResume] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);

  // a new subject resets the comparison; a pinned pair starts one immediately
  useEffect(() => {
    setCompareRow(initialCompareRow != null ? String(initialCompareRow) : '');
    setCompareResume(null);
    setCompareLoading(false);
    if (open && initialCompareRow != null && loadResume) {
      let alive = true;
      setCompareLoading(true);
      loadResume(initialCompareRow)
        .then((r) => { if (alive) setCompareResume(r); })
        .catch(() => {})
        .finally(() => { if (alive) setCompareLoading(false); });
      return () => { alive = false; };
    }
    return undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resume?.team?.row, open, initialCompareRow]);

  const startCompare = async (rowValue) => {
    setCompareRow(rowValue);
    if (rowValue === '' || !loadResume) {
      setCompareResume(null);
      return;
    }
    setCompareLoading(true);
    try {
      setCompareResume(await loadResume(Number(rowValue)));
    } catch {
      setCompareResume(null);
    } finally {
      setCompareLoading(false);
    }
  };

  const subjectRow = resume?.team?.row;
  const options = [{ value: '', label: 'Compare with...' }].concat(
    entries
      .filter((e) => e.row !== subjectRow)
      .map((e) => ({ value: String(e.row), label: `${e.rank}. ${e.school} (${e.record})` })),
  );

  return (
    <Modal open={open} onClose={onClose} className="resume-modal-overlay">
      <div className="resume-modal">
        <div className="resume-modal-bar">
          {compareResume || compareLoading ? (
            <Button onClick={() => startCompare('')}>Back to resume</Button>
          ) : (
            <Select value={compareRow} options={options} onValueChange={startCompare} />
          )}
          <Button onClick={onClose}>Close</Button>
        </div>
        <div className="resume-modal-body">
          {loading && <Skeleton height={420} />}
          {!loading && (compareLoading ? <Skeleton height={420} /> : (
            compareResume
              ? <TaleOfTheTape a={resume} b={compareResume} />
              : resume && <TeamResumePanel resume={resume} />
          ))}
        </div>
      </div>
    </Modal>
  );
}
