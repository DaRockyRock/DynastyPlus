import { useState, useRef, useEffect } from 'react';
import Modal from '../ui/Modal.jsx';
import PhoneFrame from './PhoneFrame.jsx';
import PhoneTabs from './PhoneTabs.jsx';
import ContactRow from './ContactRow.jsx';
import PhoneThread from './PhoneThread.jsx';
import RecruitBudgetStrip from './RecruitBudgetStrip.jsx';
import FeedScreen from './FeedScreen.jsx';
import PhoneBottomNav from './PhoneBottomNav.jsx';
import { api } from '../../lib/api.js';
import { offerText } from '../../lib/format.js';
import { useApp } from '../../context/AppContext.jsx';

// Connected phone. Hosts two apps inside the device frame, switched by the bottom
// nav: Messages (texting anyone in the dynasty, NIL offers, budget talk) and the
// social Feed. Contacts, threads, the active conversation and the feed all live in
// AppContext, so an NIL offer made on the NIL page (or a name hovered anywhere)
// lands in the right chat, and tapping a feed author opens that same chat.
export default function PhoneApp() {
  const {
    closePhone, phoneOpen, phoneContacts, phoneCategories, phoneThreads, appendThread,
    budget, setBudget, activeChatId, setActiveChat, unreadByContact, unreadTotal,
    markThreadRead, feedUnseen,
  } = useApp();
  const [tab, setTab] = useState('All');
  // Which of the phone's two apps is showing (the bottom nav switches it).
  const [app, setApp] = useState('messages');
  // Which contacts are currently composing a reply.
  // Keyed by contact id so the typing indicator follows the conversation into the
  // list, and survives the coach leaving the chat or closing the phone.
  const [pending, setPending] = useState({});
  const startPending = (id) => setPending((p) => ({ ...p, [id]: true }));
  const stopPending = (id) => setPending((p) => {
    if (!(id in p)) return p;
    const next = { ...p };
    delete next[id];
    return next;
  });

  const active = phoneContacts.find((c) => c.id === activeChatId);
  const tabs = ['All', ...phoneCategories];

  // The last message of a thread (most recent bubble carrying text) and its
  // recency, both read from the live threads so the list preview always matches
  // the open conversation and sorts like a real Messages app.
  const lastText = (id) => {
    const items = phoneThreads[id] || [];
    for (let i = items.length - 1; i >= 0; i -= 1) {
      if (items[i] && items[i].text) return items[i].text;
    }
    return null;
  };
  const recency = (id) => {
    const items = phoneThreads[id] || [];
    if (!items.length) return 0;
    let ts = 0;
    for (const it of items) if (it && it.ts && it.ts > ts) ts = it.ts;
    return ts || 1; // a thread with messages always outranks an empty one
  };

  // Sorted by most recent message; conversations with no history keep their roster
  // order below. Reading a text does not change recency, so it stays put.
  const visible = (tab === 'All' ? phoneContacts : phoneContacts.filter((c) => c.category === tab))
    .slice()
    .sort((a, b) => recency(b.id) - recency(a.id));

  // Reading a conversation (opening it while the phone is up) marks its incoming
  // texts read. Gated on phoneOpen so a reply that lands while the phone is closed
  // stays a notification.
  useEffect(() => {
    if (phoneOpen && activeChatId && (unreadByContact[activeChatId] || 0) > 0) markThreadRead(activeChatId);
  }, [phoneOpen, activeChatId, unreadByContact, markThreadRead]);

  // Track whether the coach is actually looking at a given conversation right now,
  // so a reply that arrives while he is elsewhere becomes an unread notification.
  const activeRef = useRef(activeChatId);
  const phoneOpenRef = useRef(phoneOpen);
  useEffect(() => { activeRef.current = activeChatId; }, [activeChatId]);
  useEffect(() => { phoneOpenRef.current = phoneOpen; }, [phoneOpen]);

  // Deliver reply bubbles one at a time with a typing pause scaled to length, so
  // a multi-message reply reads like real texting instead of arriving at once. A
  // bubble that lands while the coach is not viewing that conversation is marked
  // unread, so it shows up as a notification he needs to read.
  const streamReplies = async (chatId, texts) => {
    for (const text of texts) {
      const delay = Math.min(1500, 450 + String(text).length * 24);
      await new Promise((r) => setTimeout(r, delay));
      const viewing = phoneOpenRef.current && activeRef.current === chatId;
      appendThread(chatId, [{ from: 'them', text, ...(viewing ? {} : { unread: true }) }]);
    }
    // If the reply finished arriving while the coach was elsewhere, persist it as
    // unread so the notification survives a reload or week advance.
    if (texts.length && !(phoneOpenRef.current && activeRef.current === chatId)) {
      api.phoneMarkUnread(chatId).catch(() => {});
    }
  };

  // Derive the chat marker for a contact from the live snapshot (mirrors
  // budget.marker_for on the backend).
  const markerFor = (contact) => {
    const e = contact && contact.entity;
    if (!e || !budget) return null;
    if (e.kind === 'recruit') {
      const row = (budget.recruiting_nil || []).find((r) => r.name === e.name);
      return row && { kind: 'recruit', ...row, hours_remaining: budget.recruiting_hours.remaining, hours_total: budget.recruiting_hours.total };
    }
    if (e.kind === 'player') {
      const row = (budget.roster_nil || []).find((r) => r.name === e.name);
      return row && { kind: 'player', ...row };
    }
    if (e.kind === 'budget') {
      return {
        kind: 'budget',
        available_dp: budget.dynasty_points.available,
        total_dp: budget.dynasty_points.total,
        recruiting_available: budget.nil.recruiting.available,
        roster_available: budget.nil.roster.available,
        hours_remaining: budget.recruiting_hours.remaining,
      };
    }
    if (e.kind === 'staff') {
      return { kind: 'staff', hours_remaining: budget.recruiting_hours.remaining, hours_total: budget.recruiting_hours.total };
    }
    return null;
  };

  const send = async (text) => {
    const chatId = activeChatId;
    appendThread(chatId, [{ from: 'me', text }]);
    startPending(chatId);
    try {
      const res = await api.phoneMessage(chatId, text);
      await streamReplies(chatId, (res.messages || []).map((m) => m.text));
    } catch (e) {
      appendThread(chatId, [{ from: 'them', text: `(no reply - ${e.message})` }]);
    } finally {
      stopPending(chatId);
    }
  };

  // Apply an NIL offer / recruiting action / budget ask. For offers we first
  // drop the coach's outgoing text explaining the offer, then the receipt and
  // the in-character reply, and refresh the live budget snapshot.
  const sendAction = async (action, meText) => {
    const chatId = activeChatId;
    if (meText) appendThread(chatId, [{ from: 'me', text: meText }]);
    startPending(chatId);
    try {
      const res = await api.phoneMessage(chatId, meText || '', action);
      if (res.effect) appendThread(chatId, [{ from: 'me', kind: 'receipt', effect: res.effect }]);
      if (res.budget) setBudget(res.budget);
      await streamReplies(chatId, (res.messages || []).map((m) => m.text));
    } catch (e) {
      appendThread(chatId, [{ from: 'them', text: `(no reply - ${e.message})` }]);
    } finally {
      stopPending(chatId);
    }
  };

  const marker = active ? markerFor(active) : null;

  const onOffer = (amount) => {
    const prev = marker && marker.kind === 'player' ? marker.current_nil : (marker && marker.offer) || 0;
    const meText = offerText(amount, prev, marker && marker.kind);
    sendAction({ type: 'nil_offer', entity_id: marker && marker.id, kind: marker && marker.kind, amount }, meText);
  };

  // In a DM (a thread is open) the bottom nav hides, like iOS inside a conversation.
  let body;
  if (active) {
    body = (
      <PhoneThread
        contact={active}
        messages={phoneThreads[activeChatId] || []}
        typing={!!pending[activeChatId]}
        onSend={send}
        onBack={() => setActiveChat(null)}
        marker={marker}
        actions={(budget && budget.actions) || []}
        hoursRemaining={(budget && budget.recruiting_hours && budget.recruiting_hours.remaining) || 0}
        dpPerDollar={budget && budget.dp_per_dollar}
        onOffer={onOffer}
        onRecruitingAction={(actionKey) => sendAction({ type: 'recruiting_action', entity_id: marker && marker.id, action_key: actionKey })}
        onBudgetRequest={() => sendAction({ type: 'budget_request' })}
      />
    );
  } else if (app === 'feed') {
    body = <FeedScreen />;
  } else {
    body = (
      <div className="msg-screen">
        <div className="msg-titlebar">
          <span className="msg-title">Messages</span>
          <button className="msg-edit" onClick={closePhone}>Done</button>
        </div>
        <div className="msg-search">Search</div>
        <PhoneTabs tabs={tabs} active={tab} onSelect={setTab} />
        {tab === 'Recruits' && <RecruitBudgetStrip snapshot={budget} />}
        <div className="contact-list">
          {visible.map((c) => (
            <ContactRow
              key={c.id}
              contact={c}
              preview={lastText(c.id) ?? undefined}
              unread={unreadByContact[c.id] || 0}
              typing={!!pending[c.id]}
              onClick={() => setActiveChat(c.id)}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <Modal open={phoneOpen} onClose={closePhone} align="right">
      <PhoneFrame>
        {body}
        {!active && (
          <PhoneBottomNav
            active={app}
            onSelect={setApp}
            unreadMessages={unreadTotal}
            unseenFeed={feedUnseen}
          />
        )}
      </PhoneFrame>
    </Modal>
  );
}
