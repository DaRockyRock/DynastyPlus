import { useState } from 'react';
import Modal from './Modal.jsx';
import Button from './Button.jsx';
import Card from './Card.jsx';

export default {
  title: 'UI/Modal',
  component: Modal,
  parameters: { layout: 'fullscreen' },
};

function Demo({ align }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ padding: 40 }}>
      <Button variant="accent" onClick={() => setOpen(true)}>Open {align} modal</Button>
      <Modal open={open} onClose={() => setOpen(false)} align={align}>
        <Card className="modal-card" style={{ padding: 28, maxWidth: 420 }}>
          <h3 style={{ marginTop: 0 }}>Modal title</h3>
          <p style={{ color: 'var(--text-2)', fontSize: 13 }}>
            Click the backdrop or press Escape to close.
          </p>
          <Button onClick={() => setOpen(false)}>Close</Button>
        </Card>
      </Modal>
    </div>
  );
}

export const Centered = { render: () => <Demo align="center" /> };
export const RightAligned = { render: () => <Demo align="right" /> };
