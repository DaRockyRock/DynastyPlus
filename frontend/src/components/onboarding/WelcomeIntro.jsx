// The wizard's opening panel: what a connected model powers. Setup is required,
// so this sets expectations rather than offering an opt-out. Pure copy; the page
// wires the nav.
const USES = [
  'Top stories and the national news feed',
  'The twelve-member CFP committee and its ballots',
  'Recruiting intel, the transfer portal, and the hot seat',
  'In-character texts with recruits, staff, players and media',
];

export default function WelcomeIntro({ uses = USES }) {
  return (
    <div className="onb-welcome">
      <h2 className="onb-h2">Bring your dynasty to life</h2>
      <p className="onb-lede">
        Dynasty+ uses an AI model to write a living media universe around your season - rankings,
        storylines, scoops and conversations that build week over week. Connect one to get started.
      </p>
      <ul className="onb-uses">
        {uses.map((u) => <li key={u}>{u}</li>)}
      </ul>
    </div>
  );
}
