import FormField from '../ui/FormField.jsx';
import TextInput from '../ui/TextInput.jsx';
import PasswordInput from '../ui/PasswordInput.jsx';
import Select from '../ui/Select.jsx';

// Provider-specific connection fields. Controlled by the parent via `value`
// ({ model, apiKey, baseUrl }) and `onField(name, value)`.
//
//   provider    - 'anthropic' | 'local'
//   models      - [{ id, label }] for the Anthropic model dropdown
//   hasSavedKey - true when a key is already stored (so the field can say
//                 "leave blank to keep it" instead of looking empty/required)
export default function ConnectionForm({ provider, value, onField, models = [], hasSavedKey = false }) {
  const { model = '', apiKey = '', baseUrl = '' } = value || {};
  const keyPlaceholder = hasSavedKey ? 'Saved - leave blank to keep it' : 'sk-ant-...';

  if (provider === 'local') {
    return (
      <div className="set-grid">
        <FormField label="Server base URL" width="full"
          help="Your local server's address. Include /v1 if your tool uses it.">
          <TextInput value={baseUrl} onValueChange={(v) => onField('baseUrl', v)}
            placeholder="http://localhost:11434/v1" inputMode="url" spellCheck={false} />
        </FormField>
        <FormField label="Model" width="half"
          help="The model you are running locally.">
          <TextInput value={model} onValueChange={(v) => onField('model', v)}
            placeholder="llama3.1" spellCheck={false} />
        </FormField>
        <FormField label="API key (optional)" width="half"
          help="Only if your local server requires one.">
          <PasswordInput value={apiKey} onValueChange={(v) => onField('apiKey', v)}
            placeholder={hasSavedKey ? 'Saved - leave blank to keep it' : 'Leave blank if not needed'} />
        </FormField>
      </div>
    );
  }

  const modelOpts = models.map((m) => ({ value: m.id, label: m.label }));
  return (
    <div className="set-grid">
      <FormField label="Model" width="half"
        help="Haiku is fastest and cheapest - a great default for weekly generation.">
        <Select options={modelOpts} value={model} onValueChange={(v) => onField('model', v)} />
      </FormField>
      <FormField label="Anthropic API key" width="half"
        help="Stored locally on this machine. Used only to reach Anthropic.">
        <PasswordInput value={apiKey} onValueChange={(v) => onField('apiKey', v)} placeholder={keyPlaceholder} />
      </FormField>
    </div>
  );
}
