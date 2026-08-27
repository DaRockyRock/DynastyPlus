import Avatar from '../ui/Avatar.jsx';
import { noEmDash } from '../../lib/format.js';

// An attributed quote (coach / player / analyst) in an article.
export default function QuoteBlock({ quote }) {
  const q = quote;
  return (
    <div className="quote-block">
      <Avatar name={q.speaker} size={44} />
      <div className="q-body">
        <p className="q-text">{noEmDash(q.text)}</p>
        <div className="q-attr"><b>{q.speaker}</b><span>{q.role}</span></div>
      </div>
    </div>
  );
}
