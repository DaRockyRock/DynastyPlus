"""Recruiting records in a real College Football 27 dynasty save.

The game keeps scholarship totals and active team attention in separate
structures.  A Recruit record owns ``TotalScholarshipOffers`` and the week in
which the prospect committed.  A RecruitTarget record is one CPU school's
active recruiting slot.  It points at both the recruit and that recruit's
ProspectTargetSchool record, which carries the school row and current
influence.

This reader and writer deliberately stay inside the fixed capacities already
present in the save.  Attention corrections reassign an existing target slot
within the same school.  They never append a record or expand an ASTO array.
"""
from __future__ import annotations

import struct
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any


# Launch-build (RL1) ref tags, baselines only: game patches renumber the FrTk
# type table (the 2026-07-16 RL2 patch shifted these), so the parse derives
# each tag from its own array's contents (every array here is homogeneous)
# and falls back to these constants only when an array holds no refs.
RECRUIT_REF = 0x215A
TARGET_REF = 0x2180
TARGET_SCHOOL_REF = 0x2DA0

_TAG_LO, _TAG_HI = 0x2000, 0x4000  # plausible type-tag range (see saveparse.tags)

# Verified against week 1, week 3, rivalry week, and bowl week saves.  The
# offer value grows as the season advances.  The committed week is zero until
# a prospect commits, then carries the game's week number.
TOTAL_OFFERS_BIT = 149
TOTAL_OFFERS_WIDTH = 5
COMMITTED_WEEK_BIT = 144
COMMITTED_WEEK_WIDTH = 5


@dataclass(frozen=True)
class Store:
    name: str
    records_off: int
    stride: int
    count: int
    active: int
    fields: tuple[int, ...]


@dataclass(frozen=True)
class ArrayStore:
    name: str
    cmpc: int
    data_size: int


@dataclass(frozen=True)
class Target:
    row: int
    recruit_row: int
    school_ref: int
    school_row: int
    influence: int


@dataclass
class Prospect:
    row: int
    rank: int
    offers: int
    committed_week: int
    top_schools: dict[int, tuple[int, int]]
    targets: dict[int, Target]

    @property
    def committed(self) -> bool:
        return self.committed_week > 0

    @property
    def attention(self) -> int:
        return len(self.targets)


@dataclass(frozen=True)
class OfferChange:
    recruit_row: int
    rank: int
    before: int
    after: int


@dataclass(frozen=True)
class AttentionTransfer:
    target_row: int
    school_row: int
    from_recruit_row: int
    from_rank: int
    to_recruit_row: int
    to_rank: int
    target_school_ref: int


@dataclass
class RecruitingState:
    recruit_store: Store
    target_store: Store
    target_school_store: Store
    prospects: list[Prospect]
    prospects_by_row: dict[int, Prospect]
    board_count: int
    board_capacity: int
    target_refs: int
    recruit_ref_tag: int = RECRUIT_REF  # this save's Recruit ref tag (derived)


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from(">I", data, off)[0]


def _bits(data: bytes, off: int, width: int) -> int:
    value = 0
    for i in range(width):
        bit = off + i
        value = (value << 1) | ((data[bit >> 3] >> (7 - (bit & 7))) & 1)
    return value


def _set_bits(payload: bytearray, record_off: int, bit_off: int,
              width: int, value: int) -> None:
    if not 0 <= value < (1 << width):
        raise ValueError(f"value {value} does not fit in {width} bits")
    for i in range(width):
        bit = bit_off + i
        absolute = record_off * 8 + bit
        mask = 1 << (7 - (absolute & 7))
        if value & (1 << (width - 1 - i)):
            payload[absolute >> 3] |= mask
        else:
            payload[absolute >> 3] &= ~mask


def _framed_occurrences(payload: bytes, name: bytes) -> list[int]:
    """Occurrences that are the exact type name, not a suffix of UserRecruit."""
    out: list[int] = []
    pos = payload.find(name + b"\x00")
    while pos != -1:
        before = payload[pos - 1] if pos else 0
        if not (65 <= before <= 90 or 97 <= before <= 122 or before == 95):
            out.append(pos)
        pos = payload.find(name + b"\x00", pos + 1)
    return out


def _store(payload: bytes, name: str) -> Store:
    candidates: list[Store] = []
    for at in _framed_occurrences(payload, name.encode("ascii")):
        bsft = payload.find(b"BSFT", at, at + 400)
        if bsft == -1:
            continue
        try:
            words = struct.unpack_from(">6I", payload, bsft + 4)
        except struct.error:
            continue
        total, count, field_words = words[0], words[3], words[4] + 1
        if not (0 < count < 100_000 and 0 < field_words < 512):
            continue
        records_off = bsft + 28 + field_words * 4
        body = total - 28 - field_words * 4
        if body <= 0 or body % count:
            continue
        stride = body // count
        if stride <= 0 or records_off + count * stride > len(payload):
            continue
        table = struct.unpack_from(f">{field_words}I", payload, bsft + 28)
        candidates.append(Store(name, records_off, stride, count,
                                int(table[0]), tuple(int(x) for x in table[1:])))
    if not candidates:
        raise ValueError(f"{name} store was not found")
    return max(candidates, key=lambda s: s.count)


def _array(payload: bytes, name: str) -> ArrayStore:
    candidates: list[ArrayStore] = []
    term = (name + "[]").encode("ascii")
    for at in _framed_occurrences(payload, term):
        cmpc = payload.find(b"CMPC", at, at + 500)
        if cmpc == -1:
            continue
        try:
            data_size = _u32(payload, cmpc + 4)
        except struct.error:
            continue
        if 32 <= data_size and cmpc + data_size <= len(payload):
            candidates.append(ArrayStore(name, cmpc, data_size))
    if not candidates:
        raise ValueError(f"{name} array was not found")
    return max(candidates, key=lambda a: a.data_size)


def _simple_refs(payload: bytes, array: ArrayStore, tag: int) -> list[int]:
    used = _u32(payload, array.cmpc + 32)
    if used > (array.data_size - 36) // 4:
        raise ValueError(f"{array.name} array has an invalid population")
    values = struct.unpack_from(f">{used}I", payload, array.cmpc + 36)
    return [value & 0xFFFF for value in values if value >> 16 == tag]


def _array_ref_tag(payload: bytes, array: ArrayStore, fallback: int) -> int:
    """The array's homogeneous ref tag, measured from its own used values."""
    used = _u32(payload, array.cmpc + 32)
    if used > (array.data_size - 36) // 4:
        return fallback
    c: Counter = Counter()
    for value in struct.unpack_from(f">{used}I", payload, array.cmpc + 36):
        hi = value >> 16
        if value and _TAG_LO <= hi < _TAG_HI:
            c[hi] += 1
    return c.most_common(1)[0][0] if c else fallback


def _grid_ref_tag(payload: bytes, counts: list[int], capacity: int, grid: int,
                  fallback: int) -> int:
    """The dominant ref tag across a fixed-list grid's used slots."""
    c: Counter = Counter()
    for owner, used in enumerate(counts):
        for slot in range(used):
            v = _u32(payload, grid + (owner * capacity + slot) * 4)
            hi = v >> 16
            if v and _TAG_LO <= hi < _TAG_HI:
                c[hi] += 1
    return c.most_common(1)[0][0] if c else fallback


def _fixed_lists(payload: bytes, array: ArrayStore, owners: int) -> tuple[list[int], int, int]:
    """Return the used counts, per owner capacity, and absolute grid offset."""
    if owners <= 0:
        raise ValueError(f"{array.name} has no owners")
    remaining = array.data_size - 32 - owners * 4
    if remaining < 0 or remaining % (owners * 4):
        raise ValueError(f"{array.name} has an invalid fixed list shape")
    capacity = remaining // (owners * 4)
    counts = list(struct.unpack_from(f">{owners}I", payload, array.cmpc + 32))
    if capacity <= 0 or any(value > capacity for value in counts):
        raise ValueError(f"{array.name} has an invalid list capacity")
    return counts, capacity, array.cmpc + 32 + owners * 4


def _prospect_top_schools(payload: bytes, recruit_store: Store,
                          school_store: Store) -> dict[int, dict[int, tuple[int, int]]]:
    array = _array(payload, "ProspectTargetSchool")
    counts, capacity, grid = _fixed_lists(payload, array, recruit_store.count)
    school_tag = _grid_ref_tag(payload, counts, capacity, grid, TARGET_SCHOOL_REF)
    out: dict[int, dict[int, tuple[int, int]]] = {}
    for recruit_row, used in enumerate(counts):
        schools: dict[int, tuple[int, int]] = {}
        for slot in range(used):
            ref = _u32(payload, grid + (recruit_row * capacity + slot) * 4)
            if ref >> 16 != school_tag:
                continue
            school_ref = ref & 0xFFFF
            if school_ref >= school_store.count:
                continue
            raw = _u32(payload, school_store.records_off + school_ref * school_store.stride)
            school_row, influence = raw >> 16, raw & 0xFFFF
            schools.setdefault(school_row, (school_ref, influence))
        out[recruit_row] = schools
    return out


def _active_targets(payload: bytes, target_store: Store, school_store: Store,
                    recruit_tag: int = RECRUIT_REF) -> tuple[list[Target], int, int, int]:
    board_store = _store(payload, "RecruitingBoard")
    array = _array(payload, "RecruitTarget")
    counts, capacity, grid = _fixed_lists(payload, array, board_store.count)
    target_tag = _grid_ref_tag(payload, counts, capacity, grid, TARGET_REF)
    targets: list[Target] = []
    seen: set[int] = set()
    for board, used in enumerate(counts):
        for slot in range(used):
            ref = _u32(payload, grid + (board * capacity + slot) * 4)
            if ref >> 16 != target_tag:
                continue
            row = ref & 0xFFFF
            if row >= target_store.count or row in seen:
                continue
            seen.add(row)
            off = target_store.records_off + row * target_store.stride
            recruit_ref = _u32(payload, off + 4)
            if recruit_ref >> 16 != recruit_tag:
                continue
            # The board index is the team row.  The third word is an auxiliary
            # target handle, not a ProspectTargetSchool handle.  It stays with
            # the team slot when attention is reassigned.
            auxiliary_ref = _u32(payload, off + 8) & 0xFFFF
            targets.append(Target(row=row, recruit_row=recruit_ref & 0xFFFF,
                                  school_ref=auxiliary_ref, school_row=board,
                                  influence=0))
    return targets, board_store.count, capacity, len(seen)


def parse(payload: bytes) -> RecruitingState:
    recruit_store = _store(payload, "Recruit")
    target_store = _store(payload, "RecruitTarget")
    school_store = _store(payload, "ProspectTargetSchool")
    if recruit_store.stride < 24 or target_store.stride < 12 or school_store.stride != 4:
        raise ValueError("recruiting record sizes do not match the CFB 27 layout")

    recruit_array = _array(payload, "Recruit")
    recruit_tag = _array_ref_tag(payload, recruit_array, RECRUIT_REF)
    class_rows = _simple_refs(payload, recruit_array, recruit_tag)
    if not class_rows or len(class_rows) > recruit_store.count:
        raise ValueError("the active recruiting class is not readable")
    # National rank is duplicated in the record.  Checking a spread of rows
    # guards the offer writer against a coincidental or shifted array match.
    for rank in (1, min(32, len(class_rows)), min(600, len(class_rows)), len(class_rows)):
        row = class_rows[rank - 1]
        rec = payload[recruit_store.records_off + row * recruit_store.stride:
                      recruit_store.records_off + (row + 1) * recruit_store.stride]
        if _bits(rec, 68, 13) != rank:
            raise ValueError("the active recruiting class rank layout did not validate")

    top_schools = _prospect_top_schools(payload, recruit_store, school_store)
    targets, boards, capacity, target_refs = _active_targets(
        payload, target_store, school_store, recruit_tag)
    targets_by_recruit: dict[int, dict[int, Target]] = defaultdict(dict)
    for target in targets:
        targets_by_recruit[target.recruit_row].setdefault(target.school_row, target)

    prospects: list[Prospect] = []
    for rank, row in enumerate(class_rows, start=1):
        if row >= recruit_store.count:
            raise ValueError("the recruiting class points outside RecruitStore")
        rec = payload[recruit_store.records_off + row * recruit_store.stride:
                      recruit_store.records_off + (row + 1) * recruit_store.stride]
        prospects.append(Prospect(
            row=row,
            rank=rank,
            offers=_bits(rec, TOTAL_OFFERS_BIT, TOTAL_OFFERS_WIDTH),
            committed_week=_bits(rec, COMMITTED_WEEK_BIT, COMMITTED_WEEK_WIDTH),
            top_schools=top_schools.get(row, {}),
            targets=dict(targets_by_recruit.get(row, {})),
        ))
    return RecruitingState(
        recruit_store=recruit_store,
        target_store=target_store,
        target_school_store=school_store,
        prospects=prospects,
        prospects_by_row={p.row: p for p in prospects},
        board_count=boards,
        board_capacity=capacity,
        target_refs=target_refs,
        recruit_ref_tag=recruit_tag,
    )


def correction_plan(state: RecruitingState, *, offer_floor,
                    attention_floor, user_team_row: int | None = None
                    ) -> tuple[list[OfferChange], list[AttentionTransfer]]:
    """Build a fixed capacity correction plan without changing ``state``."""
    offers = [
        OfferChange(p.row, p.rank, p.offers, min(31, offer_floor(p.rank)))
        for p in state.prospects
        if not p.committed and p.offers < min(31, offer_floor(p.rank))
    ]

    attention = Counter({p.row: p.attention for p in state.prospects})
    school_targets: dict[int, list[Target]] = defaultdict(list)
    for prospect in state.prospects:
        for target in prospect.targets.values():
            school_targets[target.school_row].append(target)
    for rows in school_targets.values():
        rows.sort(key=lambda t: state.prospects_by_row.get(
            t.recruit_row, Prospect(t.recruit_row, 0, 0, 0, {}, {})).rank,
                  reverse=True)

    claimed: set[int] = set()
    transfers: list[AttentionTransfer] = []
    recipients = [p for p in state.prospects
                  if not p.committed and attention_floor(p.rank) > p.attention]
    for recipient in recipients:
        needed = attention_floor(recipient.rank) - attention[recipient.row]
        schools = sorted(recipient.top_schools.items(),
                         key=lambda item: item[1][1], reverse=True)
        current_schools = set(recipient.targets)
        for school_row, (school_ref, _influence) in schools:
            if needed <= 0:
                break
            if school_row == user_team_row or school_row in current_schools:
                continue
            donor = None
            for candidate in school_targets.get(school_row, []):
                if candidate.row in claimed:
                    continue
                source = state.prospects_by_row.get(candidate.recruit_row)
                if source is None or source.committed or source.rank <= 600:
                    continue
                # Keep at least one active team on every donor.  The game is at
                # fixed capacity, so a transfer must come from genuine surplus.
                if attention[source.row] <= 1:
                    continue
                donor = (candidate, source)
                break
            if donor is None:
                continue
            target, source = donor
            claimed.add(target.row)
            attention[source.row] -= 1
            attention[recipient.row] += 1
            current_schools.add(school_row)
            transfers.append(AttentionTransfer(
                target_row=target.row,
                school_row=school_row,
                from_recruit_row=source.row,
                from_rank=source.rank,
                to_recruit_row=recipient.row,
                to_rank=recipient.rank,
                target_school_ref=school_ref,
            ))
            needed -= 1
    return offers, transfers


def apply_plan(payload: bytearray, state: RecruitingState,
               offer_changes: list[OfferChange],
               transfers: list[AttentionTransfer]) -> None:
    for change in offer_changes:
        off = state.recruit_store.records_off + change.recruit_row * state.recruit_store.stride
        _set_bits(payload, off, TOTAL_OFFERS_BIT, TOTAL_OFFERS_WIDTH, change.after)
    for transfer in transfers:
        off = state.target_store.records_off + transfer.target_row * state.target_store.stride
        struct.pack_into(">I", payload, off + 4,
                         (state.recruit_ref_tag << 16) | transfer.to_recruit_row)


def summary(state: RecruitingState, *, tiers: list[Any], offer_floor,
            attention_floor) -> dict[str, Any]:
    tier_rows: list[dict[str, Any]] = []
    under_offers = 0
    under_attention = 0
    for tier in tiers:
        rows = [p for p in state.prospects if tier.rank_lo <= p.rank <= tier.rank_hi]
        if not rows:
            continue
        open_rows = [p for p in rows if not p.committed]
        offer_low = [p for p in open_rows if p.offers < offer_floor(p.rank)]
        attention_low = [p for p in open_rows if p.attention < attention_floor(p.rank)]
        under_offers += len(offer_low)
        under_attention += len(attention_low)
        tier_rows.append({
            "tier": tier.key,
            "rank_range": [tier.rank_lo, min(tier.rank_hi, len(state.prospects))],
            "sample": len(rows),
            "offer_floor": offer_floor(rows[0].rank),
            "attention_floor": attention_floor(rows[0].rank),
            "mean_offers": round(sum(p.offers for p in rows) / len(rows), 1),
            "mean_attention": round(sum(p.attention for p in rows) / len(rows), 1),
            "under_offer_floor": len(offer_low),
            "under_attention_floor": len(attention_low),
        })
    return {
        "class_size": len(state.prospects),
        "committed": sum(p.committed for p in state.prospects),
        "under_offer_floor": under_offers,
        "under_attention_floor": under_attention,
        "tiers": tier_rows,
        "capacity": {
            "teams": state.board_count,
            "per_team": state.board_capacity,
            "total": state.board_count * state.board_capacity,
            "used": state.target_refs,
        },
    }
