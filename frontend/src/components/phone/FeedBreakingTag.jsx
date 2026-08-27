// A broadcast-style "BREAKING" flag for a feed post the world engine generated in
// reaction to something the coach just said (a reporter breaking the news on the
// timeline). The leading cap + condensed italic caps echo the on-air lower-third
// look used across the app. Renders nothing for ordinary posts.
export default function FeedBreakingTag({ breaking = true }) {
  if (!breaking) return null;
  return (
    <span className="fp-breaking" aria-label="Breaking news">
      <span className="fp-breaking-cap" aria-hidden="true" />
      <span className="fp-breaking-text">Breaking</span>
    </span>
  );
}
