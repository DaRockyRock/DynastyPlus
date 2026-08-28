import { useCallback, useEffect, useState } from 'react';
import { api } from '../lib/api.js';

export function useRecruitingTool() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const next = await api.recruitingTool();
      setData(next);
      setError(null);
      return next;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const setEnabled = useCallback(async (enabled) => {
    setBusy(true);
    try {
      await api.saveRecruitingTool({ enabled });
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }, [load]);

  const apply = useCallback(async () => {
    setBusy(true);
    try {
      await api.applyRecruiting();
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }, [load]);

  return { data, loading, busy, error, reload: load, setEnabled, apply };
}
