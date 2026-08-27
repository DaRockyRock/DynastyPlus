import { useState } from 'react';
import { useBudget } from '../hooks/useBudget.js';
import { useModule } from '../hooks/useModule.js';
import { noEmDash } from '../lib/format.js';
import {
  PageHeader, SourcePill, RegenerateButton, Skeleton, EmptyState, NilCallout, Modal, SegmentedControl,
  BudgetSummaryBar, DynastyBlueprintCard, RecruitingNilTable, RosterNilTable, NilOfferEditor,
} from '../components/index.js';

const VIEWS = [
  { value: 'blueprint', label: 'Blueprint' },
  { value: 'recruiting', label: 'HS NIL' },
  { value: 'roster', label: 'Roster NIL' },
];

// The Dynasty Blueprint hub, split into tabs: the budget blueprint, the
// recruiting (high-school) NIL board, and the roster NIL retention board.
// Numbers are live from /api/budget; the prose comes from the nil_budget module.
export default function NilPage() {
  const { snapshot, loading, error, saving, allocate, offer } = useBudget();
  const prose = useModule('nil_budget');
  const [view, setView] = useState('blueprint');
  const [editing, setEditing] = useState(null); // { row, kind }

  const submitOffer = async (amount) => {
    if (!editing) return;
    const prev = editing.kind === 'player' ? editing.row.current_nil : editing.row.offer;
    await offer(editing.row.id, editing.kind, amount, editing.row.name, prev || 0);
    setEditing(null);
  };

  return (
    <>
      <PageHeader
        title="Dynasty Blueprint"
        sub="Dynasty Points, NIL pools, and the recruiting + roster board"
        actions={<>
          <SourcePill source={prose.data?.source} />
          <RegenerateButton onClick={prose.regenerate} spinning={prose.regenerating} />
        </>}
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
              <>
                {prose.data?.summary && (
                  <NilCallout>
                    {noEmDash(prose.data.summary)}
                    {prose.data.blueprint_strategy ? ' ' + noEmDash(prose.data.blueprint_strategy) : ''}
                  </NilCallout>
                )}
                <div style={{ marginTop: 22 }}>
                  <DynastyBlueprintCard snapshot={snapshot} onAllocate={allocate} saving={saving} />
                </div>
              </>
            )}

            {view === 'recruiting' && (
              <>
                <RecruitingNilTable rows={snapshot.recruiting_nil} onOffer={(row) => setEditing({ row, kind: 'recruit' })} />
                {prose.data?.recruiting_analysis && (
                  <div style={{ marginTop: 12 }}><NilCallout>{noEmDash(prose.data.recruiting_analysis)}</NilCallout></div>
                )}
              </>
            )}

            {view === 'roster' && (
              <>
                <RosterNilTable rows={snapshot.roster_nil} onOffer={(row) => setEditing({ row, kind: 'player' })} />
                {prose.data?.roster_analysis && (
                  <div style={{ marginTop: 12 }}><NilCallout>{noEmDash(prose.data.roster_analysis)}</NilCallout></div>
                )}
              </>
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
