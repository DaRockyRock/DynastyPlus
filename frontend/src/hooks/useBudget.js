import { useState, useCallback } from 'react';
import { api } from '../lib/api.js';
import { offerText } from '../lib/format.js';
import { useApp } from '../context/AppContext.jsx';

// NIL / Dynasty Points budget + mutators (allocate / offer / recruiting action).
// The snapshot itself is the app-wide one in AppContext (so the persistent
// budget bar and every surface stay in sync); each mutator folds its fresh
// snapshot back in via setBudget.
export function useBudget() {
  const { app, pointer, toast, contactForName, appendThread, budget, setBudget, reloadBudget } = useApp();
  const snapshot = budget;
  const loading = budget === null;
  const error = null;
  const [saving, setSaving] = useState(false);
  const setSnapshot = setBudget;

  // The Simulator owns the budget store, so its actions mutate it directly. In
  // the Dynasty+ companion the same actions become queued intents in the inbox;
  // the Simulator drains + applies them and the authoritative numbers arrive on
  // the next save refresh. The phone-offer convenience always queues server-side.
  const isSim = app === 'simulator';

  const allocate = useCallback(async (allocations) => {
    setSaving(true);
    try {
      const res = isSim
        ? await api.allocateBudget(allocations, pointer)
        : await api.queueAllocate(allocations, pointer);
      if (res.snapshot) setSnapshot(res.snapshot);
      toast(isSim
        ? (res?.effect?.over_budget ? 'Blueprint saved (over budget)' : 'Blueprint saved')
        : 'Blueprint change queued for the Simulator');
      return res;
    } finally {
      setSaving(false);
    }
  }, [isSim, pointer, toast]);

  // Make/adjust an NIL offer. If the recruit/player has a phone contact, route
  // it through their chat so the coach's offer text + the in-character reply land
  // in Messages; otherwise offer from the NIL board.
  const offer = useCallback(async (entityId, kind, amount, name, prevAmount = 0) => {
    const contact = name ? contactForName(name) : null;
    if (contact) {
      const meText = offerText(amount, prevAmount, kind);
      appendThread(contact.id, [{ from: 'me', text: meText }]);
      const res = await api.phoneMessage(contact.id, meText, { type: 'nil_offer', entity_id: entityId, kind, amount });
      const items = [];
      if (res.effect) items.push({ from: 'me', kind: 'receipt', effect: res.effect });
      (res.messages || []).forEach((m) => items.push({ from: 'them', text: m.text }));
      appendThread(contact.id, items);
      if (res.budget) setSnapshot(res.budget);
      if (res?.effect?.message) toast(res.effect.message + ' (texted ' + (name || '').split(' ')[0] + ')');
      return res;
    }
    const res = isSim
      ? await api.nilOffer({ entity_id: entityId, kind, amount }, pointer)
      : await api.queueNilOffer({ entity_id: entityId, kind, amount }, pointer);
    if (res.snapshot) setSnapshot(res.snapshot);
    if (res?.effect?.message) toast(res.effect.message + (isSim ? '' : ' (queued)'));
    return res;
  }, [isSim, pointer, toast, contactForName, appendThread]);

  const recruitingAction = useCallback(async (entityId, actionKey) => {
    const res = isSim
      ? await api.recruitingAction({ entity_id: entityId, action_key: actionKey }, pointer)
      : await api.queueRecruitingAction({ entity_id: entityId, action_key: actionKey }, pointer);
    if (res.snapshot) setSnapshot(res.snapshot);
    if (res?.effect?.message) toast(res.effect.message + (isSim ? '' : ' (queued)'));
    return res;
  }, [isSim, pointer, toast]);

  return { snapshot, loading, error, saving, reload: reloadBudget, allocate, offer, recruitingAction };
}
