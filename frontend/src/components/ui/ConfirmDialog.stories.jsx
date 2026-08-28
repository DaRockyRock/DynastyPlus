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
    <Demo title="Remove from library?" confirmLabel="Remove" danger>
      This removes the card from Dynasty+ Tools. The original CFB 27 save stays untouched.
    </Demo>
  ),
};

export const Busy = {
  render: () => (
    <Demo title="Remove from library?" confirmLabel="Removing" danger busy>
      Removing this dynasty card.
    </Demo>
  ),
};
