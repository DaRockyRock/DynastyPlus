// Previous / advance week stepper used in the top bar.
export default function WeekNav({ week, minWeek = 1, onPrev, onNext }) {
  return (
    <div className="week-nav">
      <button disabled={week <= minWeek} onClick={onPrev} title="Previous week" aria-label="Previous week">‹</button>
      <button onClick={onNext} title="Advance week" aria-label="Advance week">›</button>
    </div>
  );
}
