import { CheckIcon } from './icons.jsx';

// Horizontal step indicator for a wizard. `steps` is a list of labels; `current`
// is the active index. Past steps render a check, the active one is highlighted.
export default function Stepper({ steps = [], current = 0 }) {
  return (
    <ol className="stepper">
      {steps.map((label, i) => {
        const state = i < current ? 'done' : i === current ? 'active' : 'todo';
        return (
          <li key={label} className={`step step-${state}`}>
            <span className="step-dot">{state === 'done' ? <CheckIcon size={13} /> : i + 1}</span>
            <span className="step-label">{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
