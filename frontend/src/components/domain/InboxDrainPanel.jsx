import Card from '../ui/Card.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import MoneyValue from '../ui/MoneyValue.jsx';
import EmptyState from '../ui/EmptyState.jsx';

const humanize = (slug) => String(slug || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

function describe(a) {
  if (a.kind === 'nil_offer') {
    return { who: humanize(a.entity_id), what: 'NIL offer', amount: a.amount };
  }
  if (a.kind === 'recruiting_action') {
    return { who: humanize(a.entity_id), what: humanize(a.action_key) || 'Recruiting action' };
  }
  if (a.kind === 'allocate') {
    return { who: 'Dynasty Points', what: 'Reallocation' };
  }
  return { who: humanize(a.entity_id), what: a.kind };
}

// The coach actions the companion has queued in the inbox, waiting to be applied
// on the next advance. Shown on the Simulator side so the user sees what the
// companion sent before simulating the week.
export default function InboxDrainPanel({ actions = [], title = 'Queued from Dynasty+' }) {
  const pending = actions.filter((a) => !a.applied);
  return (
    <Card style={{ padding: 16 }}>
      <SectionTitle>{title}</SectionTitle>
      {pending.length === 0 ? (
        <EmptyState>No coach actions queued. Make an NIL offer in Dynasty+ and it lands here.</EmptyState>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10 }}>
          {pending.map((a, i) => {
            const d = describe(a);
            return (
              <div key={a.id || i} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
                padding: '8px 12px', borderRadius: 8,
                background: 'var(--surface-2, rgba(255,255,255,0.04))',
                border: '1px solid var(--border, rgba(255,255,255,0.08))',
              }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span style={{ font: '700 13px "Saira Condensed", sans-serif', letterSpacing: '0.03em', textTransform: 'uppercase' }}>
                    {d.who}
                  </span>
                  <span style={{ fontSize: 12, color: 'var(--text-2, #9aa6b2)' }}>
                    {d.what}{a.week != null ? ` (Week ${a.week})` : ''}
                  </span>
                </div>
                {d.amount != null && <MoneyValue value={d.amount} />}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
