// Transient bottom-center notification. Presentational: visibility is driven
// by whether `message` is set. Manages its own enter/exit animation state so
// the exit plays before the element is removed from the DOM.
import { useState, useEffect, useRef } from 'react';

const EXIT_MS = 240;

export default function Toast({ message }) {
  const [text, setText] = useState(null);
  const [phase, setPhase] = useState('out'); // 'in' | 'out'
  const exitTimer = useRef(null);

  useEffect(() => {
    if (message) {
      clearTimeout(exitTimer.current);
      setText(message);
      setPhase('in');
    } else {
      setPhase('out');
      exitTimer.current = setTimeout(() => setText(null), EXIT_MS);
    }
    return () => clearTimeout(exitTimer.current);
  }, [message]);

  if (!text) return null;
  return (
    <div className={`toast toast--${phase}`}>{text}</div>
  );
}
