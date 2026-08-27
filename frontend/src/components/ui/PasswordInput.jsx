import { useState } from 'react';
import { EyeIcon, EyeOffIcon } from './icons.jsx';

// A secret input (API keys) with a show/hide toggle. Masked by default. Styled
// to the design system; the eye button sits inside the field.
export default function PasswordInput({
  value = '',
  onValueChange,
  placeholder = '',
  autoComplete = 'off',
  ...rest
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="pass-field">
      <input
        className="set-input"
        type={show ? 'text' : 'password'}
        value={value}
        placeholder={placeholder}
        autoComplete={autoComplete}
        spellCheck={false}
        onChange={(e) => onValueChange?.(e.target.value)}
        {...rest}
      />
      <button
        type="button"
        className="pass-toggle"
        onClick={() => setShow((s) => !s)}
        aria-label={show ? 'Hide' : 'Show'}
        title={show ? 'Hide' : 'Show'}
      >
        {show ? <EyeOffIcon size={16} /> : <EyeIcon size={16} />}
      </button>
    </div>
  );
}
