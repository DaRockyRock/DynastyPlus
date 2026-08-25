// 5-star recruit rating.
export default function StarRating({ value = 0 }) {
  const n = Math.max(0, Math.min(5, value));
  return (
    <span className="stars">
      {Array.from({ length: 5 }, (_, i) =>
        i < n ? <span key={i}>★</span> : <span key={i} className="empty">★</span>
      )}
    </span>
  );
}
