import { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../lib/api.js';
import { useApp } from '../context/AppContext.jsx';
import {
  SettingsHeader, SettingsNav, SettingsPanel, ObjectForm, EntityList, SettingsMetaProvider,
} from '../components/index.js';

const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// The Customize studio: a full-screen, schema-driven editor for every named
// entity in the dynasty. Fetches the schema + current values once, holds an
// in-memory working draft, and saves one section at a time. Closing the studio
// pulls saved edits back into the running app (handled in AppContext).
export default function SettingsPage() {
  const { closeSettings, toast } = useApp();
  const [schema, setSchema] = useState(null);
  const [saved, setSaved] = useState({});
  const [draft, setDraft] = useState({});
  const [active, setActive] = useState(null);
  const [modified, setModified] = useState(() => new Set());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [traitDefs, setTraitDefs] = useState([]);

  useEffect(() => {
    let alive = true;
    api.customization()
      .then((state) => {
        if (!alive) return;
        setSchema(state.schema);
        setSaved(state.values);
        setDraft(JSON.parse(JSON.stringify(state.values)));
        setModified(new Set(state.modified || []));
        setTraitDefs(state.options?.personality_traits || []);
        setActive(state.schema[0]?.key || null);
      })
      .catch((e) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, []);

  const meta = useMemo(
    () => ({ traitDefs, generatePerson: (key, seed) => api.generatePerson(key, seed) }),
    [traitDefs],
  );

  const section = useMemo(
    () => (schema || []).find((s) => s.key === active) || null,
    [schema, active],
  );

  const counts = useMemo(() => {
    const out = {};
    (schema || []).forEach((s) => {
      if (s.kind === 'list' && Array.isArray(draft[s.key])) out[s.key] = draft[s.key].length;
    });
    return out;
  }, [schema, draft]);

  const dirty = section ? !eq(draft[section.key], saved[section.key]) : false;

  const onChangeSection = useCallback((key, value) => {
    setDraft((d) => ({ ...d, [key]: value }));
  }, []);

  const save = useCallback(async () => {
    if (!section) return;
    setSaving(true);
    try {
      const res = await api.saveCustomization(section.key, draft[section.key]);
      setSaved((s) => ({ ...s, [section.key]: res.value }));
      setDraft((d) => ({ ...d, [section.key]: res.value }));
      setModified((m) => new Set(m).add(section.key));
      toast(`Saved ${section.label}`);
    } catch (e) {
      toast('Save failed: ' + e.message);
    } finally {
      setSaving(false);
    }
  }, [section, draft, toast]);

  const reset = useCallback(async () => {
    if (!section) return;
    try {
      const res = await api.resetCustomization(section.key);
      setSaved((s) => ({ ...s, [section.key]: res.value }));
      setDraft((d) => ({ ...d, [section.key]: res.value }));
      setModified((m) => { const n = new Set(m); n.delete(section.key); return n; });
      toast(`Reset ${section.label} to default`);
    } catch (e) {
      toast('Reset failed: ' + e.message);
    }
  }, [section, toast]);

  return (
    <SettingsMetaProvider value={meta}>
    <div className="settings">
      <SettingsHeader onClose={closeSettings} />
      <div className="set-layout">
        {schema && (
          <SettingsNav
            schema={schema}
            active={active}
            onSelect={setActive}
            counts={counts}
            modified={modified}
          />
        )}
        <div className="set-content">
          {error ? (
            <div className="set-content-inner"><div className="empty-state">Could not load customization: {error}</div></div>
          ) : !section ? (
            <div className="set-content-inner"><div className="empty-state">Loading customization...</div></div>
          ) : (
            <SettingsPanel section={section} dirty={dirty} saving={saving} onSave={save} onReset={reset}>
              {section.kind === 'object' ? (
                <ObjectForm
                  section={section}
                  value={draft[section.key]}
                  onChange={(v) => onChangeSection(section.key, v)}
                />
              ) : (
                <EntityList
                  key={section.key}
                  section={section}
                  items={draft[section.key] || []}
                  onChange={(v) => onChangeSection(section.key, v)}
                />
              )}
            </SettingsPanel>
          )}
        </div>
      </div>
    </div>
    </SettingsMetaProvider>
  );
}
