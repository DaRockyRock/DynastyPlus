import { useState, useEffect } from 'react';
import Card from '../ui/Card.jsx';
import Button from '../ui/Button.jsx';
import PointsValue from '../ui/PointsValue.jsx';
import AllocationBar from '../ui/AllocationBar.jsx';

// Editable Dynasty Points allocation across the three blueprint categories.
// Sliders preview against the live bar; "Save Blueprint" commits via onAllocate.
const ROWS = [
  ['coaching_staff', 'Coaching Staff'],
  ['facilities', 'Facilities'],
  ['nil', 'NIL'],
];

export default function DynastyBlueprintCard({ snapshot, onAllocate, saving = false }) {
  const total = snapshot?.dynasty_points?.total || 0;
  const [alloc, setAlloc] = useState(snapshot?.dynasty_points?.allocations || {});

  useEffect(() => { setAlloc(snapshot?.dynasty_points?.allocations || {}); }, [snapshot]);

  const used = ROWS.reduce((sum, [k]) => sum + (alloc[k] || 0), 0);
  const free = total - used;
  const set = (k, v) => setAlloc((a) => ({ ...a, [k]: Math.max(0, v) }));

  return (
    <Card className="blueprint">
      <div className="bp-head">
        <h3>Dynasty Blueprint</h3>
        <span className="bp-total">Budget <PointsValue value={total} /></span>
      </div>
      <AllocationBar total={total} allocations={alloc} showLegend={false} />
      <div className="bp-rows">
        {ROWS.map(([k, label]) => (
          <div className="bp-row" key={k}>
            <span className="bp-name">{label}</span>
            <input
              type="range" min="0" max={total} step="100" value={alloc[k] || 0}
              onChange={(e) => set(k, +e.target.value)}
            />
            <span className="bp-amt"><PointsValue value={alloc[k] || 0} /></span>
          </div>
        ))}
      </div>
      <div className="bp-foot">
        <span className="bp-open">Open <PointsValue value={free} tone={free < 0 ? 'neg' : 'pos'} /></span>
        <Button variant="accent" spinning={saving} disabled={free < 0 || saving} onClick={() => onAllocate?.(alloc)}>
          Save Blueprint
        </Button>
      </div>
    </Card>
  );
}
