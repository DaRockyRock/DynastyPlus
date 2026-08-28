import Modal from './Modal.jsx';
import Button from './Button.jsx';

// Confirmation overlay for destructive or irreversible actions. Composes the
// generic Modal into a titled card with a message body and Cancel / Confirm
// actions. `danger` paints the confirm button in the loss color; `busy` disables
// the controls and spins the confirm button while the action runs.
export default function ConfirmDialog({
  open,
  title = 'Are you sure?',
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  danger = false,
  busy = false,
  onConfirm,
  onClose,
  children,
}) {
  return (
    <Modal open={open} onClose={busy ? undefined : onClose} align="center">
      {open && (
        <div className="confirm-dialog modal-card" role="alertdialog" aria-modal="true">
          <div className="confirm-head">
            <div className="confirm-title">{title}</div>
            <button className="bm-close" onClick={onClose} disabled={busy} aria-label="Close">
              &times;
            </button>
          </div>
          {children && <div className="confirm-body">{children}</div>}
          <div className="confirm-actions">
            <Button onClick={onClose} disabled={busy}>{cancelLabel}</Button>
            <Button
              variant="accent"
              className={danger ? 'danger' : ''}
              spinning={busy}
              disabled={busy}
              onClick={onConfirm}
            >
              {confirmLabel}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
