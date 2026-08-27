import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api.js';
import { useApp } from '../context/AppContext.jsx';

// Fetches a single generation module for the current week. Returns the data,
// loading/error state, and a regenerate() that forces backend regeneration.
export function useModule(moduleKey) {
  const { pointer, reloadKey, toast } = useApp();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [regenerating, setRegenerating] = useState(false);

  const load = useCallback(async (regenerate = false) => {
    setLoading(!regenerate);
    setRegenerating(regenerate);
    setError(null);
    try {
      const res = await api.module(moduleKey, { ...pointer, regenerate });
      setData(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
      setRegenerating(false);
    }
  }, [moduleKey, pointer]);

  useEffect(() => { load(false); }, [load, reloadKey]);

  const regenerate = useCallback(async () => {
    await load(true);
    toast('Regenerated ' + moduleKey.replace(/_/g, ' '));
  }, [load, moduleKey, toast]);

  return { data, loading, error, regenerating, regenerate };
}
