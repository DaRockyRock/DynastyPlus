// Neutral "nothing here" placeholder inside a card.
export default function EmptyState({ children = 'Nothing here yet.' }) {
  return <div className="card empty-state">{children}</div>;
}
