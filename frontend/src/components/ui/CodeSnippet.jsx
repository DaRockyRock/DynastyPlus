import { useState } from 'react';
import { CopyIcon, CheckIcon } from './icons.jsx';

// A monospace command/snippet block with a copy button. Used in the setup guide
// to show terminal commands and URLs the user can copy in one click.
export default function CodeSnippet({ children, label }) {
  const [copied, setCopied] = useState(false);
  const text = typeof children === 'string' ? children : String(children ?? '');

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch { /* clipboard blocked; no-op */ }
  };

  return (
    <div className="code-snip">
      {label && <span className="code-snip-label">{label}</span>}
      <code className="code-snip-text">{text}</code>
      <button type="button" className="code-snip-copy" onClick={copy} aria-label="Copy" title="Copy">
        {copied ? <CheckIcon size={15} /> : <CopyIcon size={15} />}
      </button>
    </div>
  );
}
