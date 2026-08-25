// Section icons for the Customize nav. One compact glyph per schema `icon`
// name, with a neutral fallback so a new section never renders blank.
function S({ size = 18, children }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {children}
    </svg>
  );
}

const GLYPHS = {
  shield: <path d="M12 2l8 3v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V5z" />,
  whistle: <><circle cx="9" cy="13" r="5" /><path d="M14 11h7l-2 4M9 8V5h4" /></>,
  chart: <><line x1="4" y1="20" x2="20" y2="20" /><rect x="6" y="11" width="3" height="6" /><rect x="11" y="7" width="3" height="10" /><rect x="16" y="13" width="3" height="4" /></>,
  swords: <><path d="M14.5 14.5L21 21l-1.5 1.5L13 16M3 3l6.5 6.5M9.5 9.5L3 16l1.5 1.5L11 11M21 3l-6.5 6.5" /></>,
  clipboard: <><rect x="6" y="4" width="12" height="17" rx="2" /><path d="M9 4h6v3H9zM9 11h6M9 15h4" /></>,
  jersey: <><path d="M8 3l4 2 4-2 4 3-2 3v11H6V9L4 6z" /></>,
  star: <polygon points="12 2 15 9 22 9.5 17 14.5 18.5 21.5 12 18 5.5 21.5 7 14.5 2 9.5 9 9" />,
  target: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" /></>,
};

const FALLBACK = <><circle cx="12" cy="12" r="9" /><line x1="12" y1="8" x2="12" y2="16" /><line x1="8" y1="12" x2="16" y2="12" /></>;

export default function SettingsIcon({ name, size = 18 }) {
  return <S size={size}>{GLYPHS[name] || FALLBACK}</S>;
}
