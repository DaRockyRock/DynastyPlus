// Standard page heading: title, optional subtitle, and right-aligned actions.
export default function PageHeader({ title, sub, actions }) {
  return (
    <div className="view-head">
      <div>
        <h1>{title}</h1>
        {sub && <div className="sub">{sub}</div>}
      </div>
      {actions && <div className="actions">{actions}</div>}
    </div>
  );
}
