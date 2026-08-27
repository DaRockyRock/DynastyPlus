import { useState } from 'react';
import { useModule } from '../hooks/useModule.js';
import { noEmDash } from '../lib/format.js';
import {
  PageHeader, SectionTitle, SourcePill, RegenerateButton, Skeleton, EmptyState, Card,
  BracketImage, CommitteeMemberCard, CommitteeBallotModal,
} from '../components/index.js';

export default function CFPPage() {
  const { data, loading, error, regenerate, regenerating } = useModule('cfp_committee');
  const [selected, setSelected] = useState(null);

  const bracket = data?.bracket || {};
  const seeds = {};
  (bracket.byes || []).forEach((s) => { seeds[s.seed] = s; });
  (bracket.first_round || []).forEach((m) => { seeds[m.home.seed] = m.home; seeds[m.away.seed] = m.away; });
  // Before the committee convenes (see cfp_committee._REVEAL_WEEK) there is no seeded
  // bracket: show the synthesis as a projection note instead of an empty bracket image.
  const hasBracket = Object.keys(seeds).length > 0;

  return (
    <>
      <PageHeader
        title="CFP Committee"
        sub="Twelve real selection-committee members, each ranking the dynasty field"
        actions={<>
          <SourcePill source={data?.source} />
          <RegenerateButton onClick={regenerate} spinning={regenerating} />
        </>}
      />
      {loading ? <Skeleton height={400} />
        : error ? <EmptyState>Could not load the committee: {error}</EmptyState>
        : (
          <>
            <Card style={{ padding: 20, marginBottom: 22 }}>
              <SectionTitle>{hasBracket ? 'Projected Bracket and Committee Synthesis' : 'Committee Outlook'}</SectionTitle>
              <p style={{ color: 'var(--chalk-2)', fontSize: 13.5, lineHeight: 1.6, margin: '0 0 14px' }}>
                {noEmDash(data.synthesis || '')}
              </p>
              {hasBracket && <BracketImage seeds={seeds} />}
            </Card>
            <SectionTitle>Committee Ballots</SectionTitle>
            <p style={{ color: 'var(--chalk-3)', fontSize: 12.5, margin: '-8px 0 16px' }}>
              Click a member to view their full top 25.
            </p>
            <div className="committee-grid">
              {(data.ballots || []).map((b, i) => (
                <CommitteeMemberCard key={i} member={b} onClick={() => setSelected(b)} />
              ))}
            </div>
          </>
        )}

      <CommitteeBallotModal member={selected} onClose={() => setSelected(null)} />
    </>
  );
}
