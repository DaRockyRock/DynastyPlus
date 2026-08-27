// A loading scrim shown OVER the press conference card while the next question
// (or, on skip, the auto-answered remainder) is generated in the background.
// Without it the modal looks frozen on the question the coach just answered, since
// the model can take several seconds to come back with the next prompt. Rendered
// inside .presser-card (which is position: relative), so it covers only the modal.
export default function PresserBusyOverlay({
  show = false,
  title = 'Working the room',
  caption = 'The next reporter is lining up a question',
}) {
  if (!show) return null;
  return (
    <div className="presser-busy" role="status" aria-live="polite">
      <div className="presser-busy-spinner" aria-hidden="true" />
      <p className="presser-busy-title">{title}</p>
      <p className="presser-busy-caption">{caption}</p>
    </div>
  );
}
