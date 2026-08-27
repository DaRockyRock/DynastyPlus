import { useState } from 'react';
import ConfirmDialog from './ConfirmDialog.jsx';
import Button from './Button.jsx';

export default {
  title: 'UI/ConfirmDialog',
  component: ConfirmDialog,
  parameters: { layout: 'fullscreen' },
};

function Demo({ danger, confirmLabel, title, busy, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ padding: 40 }}>
      <Button variant="accent" onClick={() => setOpen(true)}>Open dialog</Button>
      <ConfirmDialog
        open={open}
        title={title}
        confirmLabel={confirmLabel}
        danger={danger}
        busy={busy}
        onClose={() => setOpen(false)}
        onConfirm={() => setOpen(false)}
      >
        {children}
      </ConfirmDialog>
    </div>
  );
}

export const Default = {
  render: () => <Demo title="Leave without saving?">Your unsaved edits will be lost.</Demo>,
};

export const Danger = {
  render: () => (
    <Demo title="Delete Dynasty" confirmLabel="Delete Everything" danger>
      This permanently wipes every simulated season, all generated media, archives,
      budget, and phone, feed, and news state, plus your team customization. Both
      apps start completely from scratch. This cannot be undone.
    </Demo>
  ),
};

export const Busy = {
  render: () => (
    <Demo title="Delete Dynasty" confirmLabel="Delete Everything" danger busy>
      Wiping every season and all generated content.
    </Demo>
  ),
};
