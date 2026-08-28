import PanelCard from '../ui/PanelCard.jsx';
import HudChip from '../ui/HudChip.jsx';
import ToggleSwitch from '../ui/ToggleSwitch.jsx';
import Button from '../ui/Button.jsx';

export default function RecruitingAutomationPanel({ data, busy = false, onToggle, onApply }) {
  const audit = data?.audit;
  const config = data?.config || {};
  const plan = data?.plan || {};
  const capacity = audit?.capacity || {};
  return (
    <PanelCard
      title="Recruiting Competition"
      className="rec-auto"
      right={(
        <ToggleSwitch
          checked={!!config.enabled}
          onChange={onToggle}
          label="Correct offers and CPU attention after each CFB 27 autosave"
        />
      )}
    >
      <div className="rec-auto-summary">
        <div className="rec-auto-chips">
          <HudChip label="Recruit class" value={audit?.class_size ?? 'None'} accent="var(--recruiting)" />
          <HudChip label="Offer fixes" value={plan.offers ?? 0} accent="var(--accent-orange)" />
          <HudChip label="Attention moves" value={plan.attention ?? 0} accent="var(--cfp)" />
          <HudChip label="CPU board use" value={capacity.total ? `${capacity.used}/${capacity.total}` : 'None'} />
        </div>
        <p>
          The correction reads CFB 27 scholarship totals and CPU recruiting boards directly.
          It raises low offer counts and moves existing CPU attention toward under-attended top
          prospects without expanding the game&apos;s fixed board capacity or changing your board.
        </p>
      </div>

      <div className="rec-auto-note">
        <strong>{config.enabled ? 'Automatic recruiting changes are on.' : 'Automatic recruiting changes are off.'}</strong>
        {config.enabled ? (
          <span>
            After CFB 27 advances, Dynasty+ patches the completed autosave. Return to the main
            menu and reload the dynasty when prompted. You do not need to close either app.
          </span>
        ) : (
          <span>
            This tab remains a read-only audit. Dynasty+ will not change any recruiting data
            unless you turn on the switch above.
          </span>
        )}
      </div>

      {(audit?.tiers || []).length > 0 && (
        <div className="rec-auto-table-wrap">
          <table className="rec-auto-table">
            <thead>
              <tr>
                <th>Tier</th>
                <th>Offers</th>
                <th>Offer floor</th>
                <th>Active teams</th>
                <th>Attention floor</th>
                <th>Needs work</th>
              </tr>
            </thead>
            <tbody>
              {audit.tiers.map((tier) => (
                <tr key={tier.tier}>
                  <td>{tier.tier}</td>
                  <td>{tier.mean_offers}</td>
                  <td>{tier.offer_floor}</td>
                  <td>{tier.mean_attention}</td>
                  <td>{tier.attention_floor}</td>
                  <td>{tier.under_offer_floor + tier.under_attention_floor}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="rec-auto-actions">
        <span>
          {config.last_applied
            ? `Last updated ${config.last_applied.save}, ${config.last_applied.offers} offers and ${config.last_applied.attention} attention moves`
            : 'No recruiting correction has been written for this dynasty.'}
        </span>
        <Button variant="accent" onClick={onApply} disabled={busy || !data?.writable || !config.enabled}>
          {busy ? 'Updating dynasty file' : config.enabled ? 'Apply now' : 'Turn on to apply'}
        </Button>
      </div>
    </PanelCard>
  );
}
