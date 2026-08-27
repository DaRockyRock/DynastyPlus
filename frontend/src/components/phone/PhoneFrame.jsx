// iOS-style phone device shell: rounded frame + status bar. Compose a Messages
// list or a conversation inside it.
export default function PhoneFrame({ time = '9:41', children }) {
  return (
    <div className="phone-frame">
      <div className="ios-statusbar">
        <span>{time}</span>
        <span className="sb-right">
          <span className="sb-bars">
            <i style={{ height: 5 }} /><i style={{ height: 7 }} /><i style={{ height: 9 }} /><i style={{ height: 11 }} />
          </span>
          <span className="ios-battery"><i /></span>
        </span>
      </div>
      {children}
    </div>
  );
}
