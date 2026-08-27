import { useState, useEffect, useRef } from 'react';
import Chip from '../ui/Chip.jsx';
import StoryWatermark from './StoryWatermark.jsx';
import PersonName from '../people/PersonName.jsx';
import { noEmDash, logoUrl } from '../../lib/format.js';

// Top-stories hero slider with dot + arrow navigation and autoplay.
// `watermarkEspnId` faintly stamps the user team's logo behind the slide.
export default function StorySlider({ stories = [], watermarkEspnId = null, interval = 6500, onOpen }) {
  const [idx, setIdx] = useState(0);
  const timer = useRef(null);
  const n = stories.length;

  const restart = () => {
    clearInterval(timer.current);
    if (n > 1) timer.current = setInterval(() => setIdx((p) => (p + 1) % n), interval);
  };

  useEffect(() => {
    restart();
    return () => clearInterval(timer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [n, interval]);

  if (!n) return null;
  const go = (i) => { setIdx((i + n) % n); restart(); };
  const wm = logoUrl(watermarkEspnId);

  return (
    <div className="slider">
      <div className="slides">
        {stories.map((s, i) => {
          const accent = s.accent || '#64748b';
          // A story with its own team's espn_id shows that team's logo. A program
          // story falls back to the user's watermark; a NATIONAL story does NOT (it
          // would make every slide look like the user's team), so it shows no
          // watermark when no team resolved.
          const isNational = (s.scope || '').toLowerCase() === 'national';
          // Background logos: the story's referenced marks (a matchup, a group, a
          // conference) become the backdrop. With no marks, a program slide falls back
          // to the user's team; a national slide shows nothing.
          const fallbackWm = logoUrl(s.espn_id) || (isNational ? null : wm);
          return (
            <article className={`slide${i === idx ? ' active' : ''}`} key={i}>
              <div
                className="slide-bg"
                style={{ background: `radial-gradient(720px 360px at 78% 0%, ${accent}2e, transparent 62%), linear-gradient(135deg, ${accent}1f, #0b0f16 70%), #0b0f16` }}
              >
                <StoryWatermark marks={s.marks} fallbackUrl={fallbackWm} />
              </div>
              <div
                className="slide-content"
                onClick={onOpen ? () => onOpen(s) : undefined}
                style={onOpen ? { cursor: 'pointer' } : undefined}
              >
                <Chip category={s.category} accent={accent} />
                <h2>{noEmDash(s.headline)}</h2>
                <p className="subhead">{noEmDash(s.subheadline)}</p>
                <p className="lede">{noEmDash(s.lede)}</p>
                <p className="byline">
                  {s.byline
                    ? <><PersonName name={noEmDash(String(s.byline).split(',')[0]).trim()} kind="media" />{String(s.byline).includes(',') ? `, ${noEmDash(String(s.byline).split(',').slice(1).join(',')).trim()}` : ''}</>
                    : null}
                </p>
              </div>
            </article>
          );
        })}
      </div>
      {n > 1 && (
        <div className="slider-nav">
          <button className="slider-arrow" onClick={() => go(idx - 1)} aria-label="Previous story">‹</button>
          <div className="slider-dots">
            {stories.map((_, i) => (
              <button key={i} className={i === idx ? 'active' : ''} onClick={() => go(i)} aria-label={`Story ${i + 1}`} />
            ))}
          </div>
          <button className="slider-arrow" onClick={() => go(idx + 1)} aria-label="Next story">›</button>
        </div>
      )}
    </div>
  );
}
