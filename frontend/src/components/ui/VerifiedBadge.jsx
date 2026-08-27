import { CheckIcon } from './icons.jsx';

// The blue verified check shown next to notable feed accounts (media, brands,
// personalities). Renders nothing for unverified accounts (fans).
export default function VerifiedBadge({ verified = true, size = 14 }) {
  if (!verified) return null;
  return (
    <span className="verified-badge" style={{ width: size, height: size }} aria-label="Verified">
      <CheckIcon size={Math.round(size * 0.66)} />
    </span>
  );
}
