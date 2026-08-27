import { noEmDash } from '../../lib/format.js';

// Large editorial pull quote with a team-color rule.
export default function PullQuote({ children }) {
  const content = typeof children === 'string' ? noEmDash(children) : children;
  return <blockquote className="pull-quote">{content}</blockquote>;
}
