// Insider-report status: developing / corroborated / disputed.
export default function StatusTag({ status = 'developing' }) {
  const s = (status || 'developing').toLowerCase();
  return <span className={`status-tag ${s}`}>{status}</span>;
}
