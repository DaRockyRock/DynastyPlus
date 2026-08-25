// Read/write nested object values by a dot path (e.g. "entity.kind"). Used by
// the settings editors so a single field can target a nested key. Returns a new
// object on set (never mutates), so React state updates stay predictable.

export function getPath(obj, path) {
  if (!path) return undefined;
  return String(path).split('.').reduce((acc, key) => (acc == null ? undefined : acc[key]), obj);
}

export function setPath(obj, path, value) {
  const keys = String(path).split('.');
  const next = Array.isArray(obj) ? [...obj] : { ...(obj || {}) };
  let cursor = next;
  for (let i = 0; i < keys.length - 1; i += 1) {
    const k = keys[i];
    cursor[k] = (cursor[k] && typeof cursor[k] === 'object') ? { ...cursor[k] } : {};
    cursor = cursor[k];
  }
  cursor[keys[keys.length - 1]] = value;
  return next;
}
