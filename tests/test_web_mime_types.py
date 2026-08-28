"""The frontend bundle must be served with correct web MIME types.

Regression guard for the blank/green boot screen: on Windows, Python's
mimetypes map is seeded from the registry, and on many machines ".js" is
pointed at "text/plain". Flask then serves the Vite build's entry module as
text/plain, Chromium refuses to run it under its strict module MIME check, and
the app hangs on the boot screen. backend.app.pin_web_mime_types() must make
our own value win regardless of what the machine's registry (or a stale map)
says."""
import mimetypes

from backend import app as backend_app


def test_js_is_pinned_to_javascript():
    assert mimetypes.guess_type("bundle.js")[0] == "text/javascript"
    assert mimetypes.guess_type("bundle.mjs")[0] == "text/javascript"
    assert mimetypes.guess_type("styles.css")[0] == "text/css"


def test_pin_overrides_a_corrupted_registry_value():
    # Simulate the broken machine: something set ".js" to text/plain.
    mimetypes.add_type("text/plain", ".js")
    assert mimetypes.guess_type("x.js")[0] == "text/plain"  # sanity: corruption took

    backend_app.pin_web_mime_types()  # our hardening re-asserts the right value
    assert mimetypes.guess_type("x.js")[0] == "text/javascript"
