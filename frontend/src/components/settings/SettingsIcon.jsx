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
  newspaper: <><path d="M4 5h13v15H4zM17 9h3v9a2 2 0 01-2 2M7 9h7M7 13h7M7 17h5" /></>,
  mic: <><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0014 0M12 18v3" /></>,
  binoculars: <><path d="M6 3h3v3M15 3h3v3" /><rect x="4" y="6" width="6" height="13" rx="3" /><rect x="14" y="6" width="6" height="13" rx="3" /><path d="M10 11h4" /></>,
  ballot: <><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M8 10l2 2 4-4" /><line x1="8" y1="16" x2="16" y2="16" /></>,
  phone: <><rect x="7" y="2" width="10" height="20" rx="2.5" /><line x1="11" y1="18" x2="13" y2="18" /></>,
  gavel: <><path d="M14 3l7 7-3 3-7-7zM10.5 6.5L3 14l3 3 7.5-7.5M4 21h9" /></>,
  fire: <path d="M12 2c1 3-1 4-1 6 0 2 2 2 2 4M12 22c-4 0-7-2.5-7-7 0-3 2-5 3-7 .5 2 2 3 3 3 0-3 1-5 3-6-1 4 3 5 3 10 0 4.5-3 7-8 7z" />,
  users: <><circle cx="9" cy="8" r="3" /><path d="M3 20c0-3 3-5 6-5s6 2 6 5M16 6a3 3 0 010 6M15 15c3 0 6 2 6 5" /></>,
  trophy: <><path d="M8 4h8v5a4 4 0 01-8 0zM8 6H5v2a3 3 0 003 3M16 6h3v2a3 3 0 01-3 3M10 15h4v3h-4zM8 21h8" /></>,
  'arrow-in': <><path d="M3 12h12M11 8l4 4-4 4" /><path d="M19 4v16" /></>,
  'arrow-out': <><path d="M21 12H9M13 8l-4 4 4 4" /><path d="M5 4v16" /></>,
};

const FALLBACK = <><circle cx="12" cy="12" r="9" /><line x1="12" y1="8" x2="12" y2="16" /><line x1="8" y1="12" x2="16" y2="12" /></>;

export default function SettingsIcon({ name, size = 18 }) {
  return <S size={size}>{GLYPHS[name] || FALLBACK}</S>;
}
