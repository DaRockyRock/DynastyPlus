"""Tests for the real CFB 27 recruiting correction planner and bit writer."""
from backend import recruiting_fix
from backend.saveparse import recruiting


def _store(name, off, stride, count=1000):
    return recruiting.Store(name, off, stride, count, 0, ())


def _prospect(row, rank, *, offers=0, committed=0, schools=None, targets=None):
    return recruiting.Prospect(
        row=row, rank=rank, offers=offers, committed_week=committed,
        top_schools=schools or {}, targets=targets or {},
    )


def _state(prospects):
    return recruiting.RecruitingState(
        recruit_store=_store("Recruit", 0, 24),
        target_store=_store("RecruitTarget", 400, 28),
        target_school_store=_store("ProspectTargetSchool", 800, 4),
        prospects=prospects,
        prospects_by_row={p.row: p for p in prospects},
        board_count=138,
        board_capacity=35,
        target_refs=sum(p.attention for p in prospects),
    )


def test_attention_plan_preserves_capacity_and_user_board():
    existing = recruiting.Target(10, 1, 0, 1, 0)
    donor_two = recruiting.Target(20, 700, 0, 2, 0)
    donor_three = recruiting.Target(21, 700, 0, 3, 0)
    recipient = _prospect(
        1, 1, offers=25,
        schools={1: (101, 100), 2: (102, 90), 3: (103, 80)},
        targets={1: existing},
    )
    donor = _prospect(700, 700, offers=8, targets={2: donor_two, 3: donor_three})
    state = _state([recipient, donor])

    offers, transfers = recruiting.correction_plan(
        state,
        offer_floor=recruiting_fix.real_offer_floor,
        attention_floor=lambda rank: 3 if rank == 1 else 0,
        user_team_row=2,
    )

    assert offers == []
    assert len(transfers) == 1
    assert transfers[0].school_row == 3
    assert transfers[0].from_recruit_row == 700
    assert transfers[0].to_recruit_row == 1
    assert state.target_refs == 3


def test_offer_plan_skips_committed_prospects():
    open_prospect = _prospect(10, 12, offers=3)
    committed = _prospect(11, 13, offers=2, committed=7)
    state = _state([open_prospect, committed])
    offers, transfers = recruiting.correction_plan(
        state,
        offer_floor=recruiting_fix.real_offer_floor,
        attention_floor=lambda rank: 0,
    )
    assert transfers == []
    assert [(change.recruit_row, change.after) for change in offers] == [(10, 20)]


def test_apply_plan_changes_only_offer_bits_and_recruit_ref():
    state = _state([])
    payload = bytearray(1200)
    offer = recruiting.OfferChange(2, 12, 3, 20)
    transfer = recruiting.AttentionTransfer(4, 3, 700, 700, 1, 1, 103)
    recruiting.apply_plan(payload, state, [offer], [transfer])

    recruit_off = state.recruit_store.records_off + 2 * state.recruit_store.stride
    assert recruiting._bits(payload[recruit_off:recruit_off + 24],
                            recruiting.TOTAL_OFFERS_BIT,
                            recruiting.TOTAL_OFFERS_WIDTH) == 20
    target_off = state.target_store.records_off + 4 * state.target_store.stride
    assert int.from_bytes(payload[target_off + 4:target_off + 8], "big") \
        == (recruiting.RECRUIT_REF << 16) | 1
    assert payload[target_off + 8:target_off + 12] == b"\x00\x00\x00\x00"


def test_attention_floors_fit_the_real_board_capacity():
    required = sum(recruiting_fix.attention_floor_for(rank)
                   for rank in range(1, 4101))
    assert required == 1154
    assert required < 138 * 35
