import { useState } from 'react';
import Button from '../ui/Button.jsx';

// The coach's answer box: a growing textarea plus Respond and Skip. Enter sends
// (Shift+Enter for a newline). Skip declines the rest of the presser.
export default function PresserAnswerInput({ onSend, onSkip, busy = false, disabled = false }) {
  const [text, setText] = useState('');
  const send = () => {
    const v = text.trim();
    if (!v || busy || disabled) return;
    setText('');
    onSend?.(v);
  };
  return (
    <div className="presser-input">
      <textarea
        className="presser-textarea"
        rows={3}
        placeholder="Answer the question..."
        value={text}
        disabled={busy || disabled}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
      />
      <div className="presser-input-actions">
        <Button variant="action" onClick={onSkip} disabled={busy}>Skip the rest</Button>
        <Button variant="accent" onClick={send} spinning={busy} disabled={busy || !text.trim()}>Respond</Button>
      </div>
    </div>
  );
}
