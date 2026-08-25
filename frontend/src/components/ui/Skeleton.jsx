// Shimmer placeholder shown while a module's content loads.
export default function Skeleton({ height = 420, className = '' }) {
  return <div className={['skeleton', className].filter(Boolean).join(' ')} style={{ height }} />;
}
