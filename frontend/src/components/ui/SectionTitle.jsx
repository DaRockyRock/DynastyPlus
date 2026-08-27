// Uppercase section header with a team-color tick. `right` renders at the end
// of the row (e.g., a SourcePill + RegenerateButton); `note` is a small muted
// caption that renders before it (e.g., how a board is ranked).
export default function SectionTitle({ children, right, note, style }) {
  return (
    <div className="section-title" style={style}>
      <h2 className="st-text">{children}</h2>
      {(right != null || note != null) && (
        <div className="st-right">
          {note != null && <span className="st-note">{note}</span>}
          {right}
        </div>
      )}
    </div>
  );
}
