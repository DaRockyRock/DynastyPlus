// The ranking-algorithm picker: one selectable card per computer rating
// system (Colley Matrix, Massey, Elo, ...), with the plain-language blurb
// and a tag of what each system counts. Pure presentational radio list.
export default function PollAlgorithmPicker({ algorithms = [], value, onChange }) {
  return (
    <div className="algo-picker" role="radiogroup">
      {algorithms.map((a) => (
        <button
          key={a.id}
          type="button"
          role="radio"
          aria-checked={a.id === value}
          className={`algo-card${a.id === value ? ' active' : ''}`}
          onClick={() => onChange?.(a.id)}
        >
          <span className="algo-card-head">
            <span className="algo-card-name">{a.name}</span>
            {a.uses && <span className="algo-card-uses">{a.uses}</span>}
          </span>
          <span className="algo-card-blurb">{a.blurb}</span>
        </button>
      ))}
    </div>
  );
}
