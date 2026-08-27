import Button from '../ui/Button.jsx';
import StatusDot from '../ui/StatusDot.jsx';
import { BoltIcon } from '../ui/icons.jsx';

// "Test connection" control plus its live result line. Presentational: the
// parent owns the request and feeds back `status` + `message`.
//
//   status  - 'idle' | 'testing' | 'ok' | 'error'
//   message - result text shown beside the dot
//   onTest  - run the test
const DOT = { idle: 'off', testing: 'idle', ok: 'live', error: 'error' };

export default function ConnectionTester({ status = 'idle', message = '', onTest, disabled = false }) {
  const testing = status === 'testing';
  return (
    <div className="conn-tester">
      <Button
        variant="action"
        icon={<BoltIcon />}
        spinning={testing}
        disabled={disabled || testing}
        onClick={onTest}
      >
        {testing ? 'Testing...' : 'Test connection'}
      </Button>
      {status !== 'idle' && (
        <span className={`conn-result conn-${status}`}>
          <StatusDot tone={DOT[status]} pulse={status === 'ok'} />
          <span className="conn-msg">{message || (testing ? 'Reaching the model...' : '')}</span>
        </span>
      )}
    </div>
  );
}
