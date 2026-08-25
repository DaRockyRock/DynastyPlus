import { useState, useCallback } from 'react';
import { api } from '../lib/api.js';
import { useTools } from '../context/ToolsContext.jsx';

// NIL / Dynasty Points budget + mutators (allocate / offer / recruiting action).
// The snapshot is shared across the tools app; each mutation folds its fresh
// result back into context.
export function useBudget() {
  const { pointer, toast, budget, setBudget, reloadBudget } = useTools();
  const snapshot = budget;
  const loading = budget === null;
  const error = null;
  const [saving, setSaving] = useState(false);
  const setSnapshot = setBudget;

  const allocate = useCallback(async (allocations) => {
    setSaving(true);
    try {
      const res = await api.allocateBudget(allocations, pointer);
      if (res.snapshot) setSnapshot(res.snapshot);
      toast(res?.effect?.over_budget ? 'Blueprint saved (over budget)' : 'Blueprint saved');
      return res;
    } finally {
      setSaving(false);
    }
  }, [pointer, toast]);

  const offer = useCallback(async (entityId, kind, amount) => {
    const res = await api.nilOffer({ entity_id: entityId, kind, amount }, pointer);
    if (res.snapshot) setSnapshot(res.snapshot);
    if (res?.effect?.message) toast(res.effect.message);
    return res;
  }, [pointer, toast]);

  const recruitingAction = useCallback(async (entityId, actionKey) => {
    const res = await api.recruitingAction({ entity_id: entityId, action_key: actionKey }, pointer);
    if (res.snapshot) setSnapshot(res.snapshot);
    if (res?.effect?.message) toast(res.effect.message);
    return res;
  }, [pointer, toast]);

  return { snapshot, loading, error, saving, reload: reloadBudget, allocate, offer, recruitingAction };
}
