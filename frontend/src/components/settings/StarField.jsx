// 1-5 star rating picker. Click a star to set; click the active top star to clear.
export default function StarField({ value = 0, max = 5, onChange }) {
  const v = Number(value) || 0;
  return (
    <div className="star-field">
      {Array.from({ length: max }, (_, i) => {
        const n = i + 1;
        return (
          <button
            key={n}
            type="button"
            className={n <= v ? 'on' : ''}
            onClick={() => onChange(n === v ? 0 : n)}
            aria-label={`${n} star${n > 1 ? 's' : ''}`}
          >
            {n <= v ? '★' : '☆'}
          </button>
        );
      })}
      {v > 0 && <span className="sf-clear">{v}-star</span>}
    </div>
  );
}
