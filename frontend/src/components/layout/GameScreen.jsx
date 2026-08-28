import MenuRailItem from './MenuRailItem.jsx';

// The game's screen skeleton: the big "WEEK 3, 2026" hero week title, a left
// rail of menu buttons, and the content pane with an optional centered hero
// title ("WEEKLY SCHEDULES") + subtitle or a custom hero slot (event banner).
//
//   <GameScreen week="Week 3, 2026" menu={items} active={id} onSelect={fn}
//               heroTitle="Weekly Schedules" heroSub="View the national schedule here.">
//     {panels}
//   </GameScreen>
//
// `menu` = [{ id, label, sub?, icon?, check? (true|false|undefined), right? }].
// Omit `menu` for full-width content pages.
export default function GameScreen({
  week, menu = null, active, onSelect,
  heroTitle, heroSub, hero = null, children,
}) {
  return (
    <div className={`gamescreen${menu ? '' : ' no-rail'}`}>
      {week && <h1 className="gs-week">{week}</h1>}
      {menu && (
        <nav className="gs-rail menu-rail">
          {menu.map((item) => (
            <MenuRailItem
              key={item.id}
              {...item}
              active={item.id === active}
              onClick={onSelect ? () => onSelect(item.id) : item.onClick}
            />
          ))}
        </nav>
      )}
      <div className="gs-content">
        {hero}
        {(heroTitle || heroSub) && (
          <header className="gs-hero">
            {heroTitle && <h2 className="gs-hero-title">{heroTitle}</h2>}
            {heroSub && <p className="gs-hero-sub">{heroSub}</p>}
          </header>
        )}
        {children}
      </div>
    </div>
  );
}
