import { useState, useEffect, Fragment } from 'react';
import { api } from '../../lib/api.js';
import { useApp } from '../../context/AppContext.jsx';
import { noEmDash, stripQuoteFromSections } from '../../lib/format.js';
import Card from '../ui/Card.jsx';
import Chip from '../ui/Chip.jsx';
import Skeleton from '../ui/Skeleton.jsx';
import EmptyState from '../ui/EmptyState.jsx';
import PullQuote from '../ui/PullQuote.jsx';
import QuoteBlock from './QuoteBlock.jsx';
import StatTable from './StatTable.jsx';
import BettingCard from './BettingCard.jsx';
import { ChevronLeft } from '../ui/icons.jsx';

// Full article page. Fetches the expanded detail (sections + a varied mix of
// quotes / stats / betting) for the clicked article and lays it out as a
// reader with a right rail.
export default function ArticleReader({ article, onBack }) {
  const { pointer } = useApp();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let live = true;
    // Full articles are pre-generated during the weekly run and ride along on the
    // card as `detail`, so the reader opens instantly. Only fetch (generating on
    // demand) when no pre-generated detail is present.
    if (article.detail) {
      setData(article.detail);
      setLoading(false);
      setError(null);
      return undefined;
    }
    setLoading(true);
    setError(null);
    api.article(article, pointer)
      .then((d) => { if (live) { setData(d); setLoading(false); } })
      .catch((e) => { if (live) { setError(e.message); setLoading(false); } });
    return () => { live = false; };
  }, [article, pointer]);

  const accent = data?.accent || article.accent || '#64748b';
  const pullQuote = data?.pull_quote || '';
  // The pull quote is pulled verbatim from the body, so drop the echoed sentence
  // from the paragraphs to avoid showing the same line twice.
  const sections = stripQuoteFromSections(data?.sections || [], pullQuote);
  const quotes = data?.quotes || [];

  // Quotes belong inside the article, not in a trailing "what they are saying"
  // list, so place each one after a body paragraph (starting after the lede, with
  // any extras stacking after the last paragraph). The quotes are still the
  // backend-verified ones, so the head coach is never fabricated.
  const quotesByPara = {};
  if (sections.length) {
    const start = sections.length > 1 ? 1 : 0;
    quotes.forEach((q, j) => {
      const idx = Math.min(sections.length - 1, start + j);
      (quotesByPara[idx] = quotesByPara[idx] || []).push(q);
    });
  }

  return (
    <div className="article-reader">
      <button className="reader-back" onClick={onBack}><ChevronLeft size={16} /> Back to feed</button>

      {loading ? (
        <div style={{ marginTop: 18 }}><Skeleton height={520} /></div>
      ) : error ? (
        <EmptyState>Could not load the article: {error}</EmptyState>
      ) : (
        <article>
          <div className="reader-head" style={{ '--accent': accent }}>
            <Chip category={data.category} accent={accent} />
            <h1 className="reader-title">{noEmDash(data.title)}</h1>
            {data.dek && <p className="reader-dek">{noEmDash(data.dek)}</p>}
            <div className="reader-byline">
              {data.outlet && <span className="outlet">{data.outlet}</span>}
              {data.outlet && data.reporter && <span className="sep">/</span>}
              {data.reporter && <span className="by-name">{data.reporter}</span>}
              {data.timestamp && <span className="ts">{data.timestamp}</span>}
            </div>
          </div>

          <div className="reader-grid">
            <div className="reader-main">
              {sections.map((p, i) => (
                <Fragment key={i}>
                  <p>{noEmDash(p)}</p>
                  {i === 0 && pullQuote && <PullQuote>{pullQuote}</PullQuote>}
                  {(quotesByPara[i] || []).map((q, k) => <QuoteBlock key={`q${i}-${k}`} quote={q} />)}
                </Fragment>
              ))}
              {sections.length === 0 && pullQuote && <PullQuote>{pullQuote}</PullQuote>}
              {sections.length === 0 && quotes.map((q, i) => <QuoteBlock key={i} quote={q} />)}
            </div>

            <aside className="reader-rail">
              {(data.stats || []).length > 0 && <StatTable rows={data.stats} />}
              {data.betting && <BettingCard betting={data.betting} />}
              {(data.stats || []).length === 0 && !data.betting && (
                <Card className="tile"><div className="muted">More coverage to come this week.</div></Card>
              )}
            </aside>
          </div>
        </article>
      )}
    </div>
  );
}
