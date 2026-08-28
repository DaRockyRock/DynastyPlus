// The game's content panel: translucent charcoal surface with a white
// condensed header over a full-width hairline. `title` optional (bare panel),
// `right` is the header's right slot, `flush` removes body padding (tables).
export default function PanelCard({ title, right = null, flush = false, className = '', children, ...rest }) {
  return (
    <section className={`gpanel${flush ? ' flush' : ''}${className ? ` ${className}` : ''}`} {...rest}>
      {(title || right) && (
        <header className="gpanel-head">
          {title && <h3 className="gpanel-title">{title}</h3>}
          {right && <span className="gpanel-right">{right}</span>}
        </header>
      )}
      <div className="gpanel-body">{children}</div>
    </section>
  );
}
