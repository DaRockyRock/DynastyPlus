import { useState } from 'react';
import { useBudget } from '../hooks/useBudget.js';
import {
  PageHeader, Skeleton, EmptyState, Modal, SegmentedControl,
  BudgetSummaryBar, DynastyBlueprintCard, RecruitingNilTable, RosterNilTable, NilOfferEditor,
} from '../components/index.js';

const VIEWS = [
  { value: 'blueprint', label: 'Blueprint' },
  { value: 'recruiting', label: 'HS NIL' },
  { value: 'roster', label: 'Roster NIL' },
];

// The Dynasty Blueprint hub, split into tabs: the budget blueprint, the
// recruiting (high-school) NIL board, and the roster NIL retention board.
// All numbers and mutations are backed directly by the tools API.
export default function NilPage() {
  const { snapshot, loading, error, saving, allocate, offer } = useBudget();
  const [view, setView] = useState('blueprint');
  const [editing, setEditing] = useState(null); // { row, kind }

  const submitOffer = async (amount) => {
    if (!editing) return;
    await offer(editing.row.id, editing.kind, amount);
    setEditing(null);
  };

  return (
    <>
      <PageHeader
        title="Dynasty Blueprint"
        sub="Dynasty Points, NIL pools, and the recruiting + roster board"
      />

      {loading ? <Skeleton height={360} />
        : error ? <EmptyState>Could not load the budget: {error}</EmptyState>
        : !snapshot ? <EmptyState />
        : (
          <>
            <BudgetSummaryBar snapshot={snapshot} compact />
            <div style={{ margin: '20px 0' }}>
              <SegmentedControl options={VIEWS} value={view} onChange={setView} />
            </div>

            {view === 'blueprint' && (
              <div style={{ marginTop: 22 }}>
                <DynastyBlueprintCard snapshot={snapshot} onAllocate={allocate} saving={saving} />
              </div>
            )}

            {view === 'recruiting' && (
              <RecruitingNilTable rows={snapshot.recruiting_nil} onOffer={(row) => setEditing({ row, kind: 'recruit' })} />
            )}

            {view === 'roster' && (
              <RosterNilTable rows={snapshot.roster_nil} onOffer={(row) => setEditing({ row, kind: 'player' })} />
            )}
          </>
        )}

      <Modal open={!!editing} onClose={() => setEditing(null)} align="center">
        {editing && (
          <NilOfferEditor
            row={editing.row}
            kind={editing.kind}
            dpPerDollar={snapshot?.dp_per_dollar}
            onSubmit={submitOffer}
            onClose={() => setEditing(null)}
          />
        )}
      </Modal>
    </>
  );
}
