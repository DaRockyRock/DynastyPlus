import PanelCard from '../ui/PanelCard.jsx';
import Badge from '../ui/Badge.jsx';
import FormField from '../ui/FormField.jsx';
import TextInput from '../ui/TextInput.jsx';
import TextArea from '../ui/TextArea.jsx';
import ImageUpload from '../settings/ImageUpload.jsx';
import ConferenceLogoPicker from './ConferenceLogoPicker.jsx';

// The identity editor for one conference: logo, display name, abbreviation,
// championship game name, and description. The name and championship fields
// are fixed-size in the game save, so each shows its character budget; the
// logo, abbreviation, and description are companion-side flavor. The logo can
// be a custom upload or one of the game's own classic marks (historicLogos);
// either shows across Dynasty+ and, with the MMC Modding Tools, in game.
// Presentational: the page owns the draft; edits arrive as `onChange(patch)`.
// `onUpload` lets Storybook stub the image uploader.
const ABBR_MAX = 8;

function BudgetLabel({ label, value, max }) {
  const len = (value || '').length;
  return (
    <span className="cs-field-label">
      {label}
      <span className={`cs-budget${len >= max ? ' warn' : ''}`}>{len} / {max}</span>
    </span>
  );
}

export default function ConferenceIdentityCard({ conf, onChange, onUpload, historicLogos = [] }) {
  if (!conf) return null;
  const patch = (p) => onChange?.({ ...conf, ...p });

  return (
    <PanelCard
      className="cs-identity"
      title="Conference Identity"
      right={
        <span className="cs-identity-tags">
          {conf.key && <Badge label="Save key" value={conf.key} />}
          <Badge value="In game" />
        </span>
      }
    >
      <div className="cs-identity-body">
        <div className="cs-identity-logo">
          <ImageUpload
            value={conf.logo || ''}
            onChange={(url) => patch({ logo: url || null })}
            onUpload={onUpload}
            hint="Conference mark shown across Dynasty+. A square PNG with transparency works best. To show it inside CFB 27, set up the MMC Modding Tools (panel above)."
          />
          <ConferenceLogoPicker
            logos={historicLogos}
            value={conf.logo || ''}
            onSelect={(url) => patch({ logo: url || null })}
          />
        </div>
        <div className="cs-identity-fields">
          <div className="cs-field-row">
            <FormField label={<BudgetLabel label="Display Name" value={conf.name} max={20} />}>
              <TextInput
                value={conf.name || ''}
                maxLength={20}
                onValueChange={(v) => patch({ name: v })}
              />
            </FormField>
            <FormField label={<BudgetLabel label="Abbreviation" value={conf.abbr} max={ABBR_MAX} />}>
              <TextInput
                value={conf.abbr || ''}
                maxLength={ABBR_MAX}
                onValueChange={(v) => patch({ abbr: v.toUpperCase() })}
              />
            </FormField>
          </div>
          {!conf.independents && (
            <FormField label={<BudgetLabel label="Championship Game" value={conf.champ_game} max={27} />}>
              <TextInput
                value={conf.champ_game || ''}
                maxLength={27}
                onValueChange={(v) => patch({ champ_game: v })}
              />
            </FormField>
          )}
          <FormField
            label="Description"
            help="Companion-side flavor. Names and championship titles above write into the game; the logo shows across Dynasty+ and, with the MMC Modding Tools, in the game."
          >
            <TextArea
              value={conf.description || ''}
              rows={2}
              onValueChange={(v) => patch({ description: v })}
            />
          </FormField>
        </div>
      </div>
    </PanelCard>
  );
}
