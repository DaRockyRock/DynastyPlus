"""Tests for the TeamStore poll reader/writer (`backend.saveparse.polls`)
against a synthetic TeamStore blob laid out exactly like the real one."""
import struct

import pytest

from backend.saveparse import polls as savepolls

COUNT = 6           # 5 ranked teams + 1 unranked placeholder row
STRIDE = 720
FIELDS = 1


def build_payload(cfp=(1, 2, 3, 4, 5, 0), ap=(2, 1, 3, 4, 5, 0)) -> bytearray:
    """A minimal payload carrying only the TeamStore in the real shape:
    anchor, BSFT header (data size / count / field count), field table,
    fixed-stride records with the rank fields at their verified offsets."""
    data_size = 28 + FIELDS * 4 + COUNT * STRIDE
    buf = bytearray()
    buf += b"\x00\x09TeamStore\x00"
    bsft = len(buf)
    buf += b"BSFT"
    buf += struct.pack(">6I", data_size, 0, 0, COUNT, FIELDS - 1, 0)
    buf += b"\x00" * (FIELDS * 4)
    assert len(buf) == bsft + 4 + 24 + FIELDS * 4
    for row in range(COUNT):
        rec = bytearray(STRIDE)
        rec[savepolls.CFP_RANK_OFF] = cfp[row]
        rec[savepolls.CFP_ALIAS_OFF] = cfp[row]
        struct.pack_into(">H", rec, savepolls.AP_RANK_OFF, ap[row])
        buf += rec
    return buf


def test_parse_reads_both_polls():
    ranks = savepolls.parse(bytes(build_payload()))
    assert [t.rank for t in ranks] == [1, 2, 3, 4, 5, 0]
    assert [t.ap_rank for t in ranks] == [2, 1, 3, 4, 5, 0]
    assert savepolls.poll_order(bytes(build_payload()), "cfp") == [0, 1, 2, 3, 4]
    assert savepolls.poll_order(bytes(build_payload()), "ap") == [1, 0, 2, 3, 4]


def test_set_poll_order_cfp_writes_rank_and_alias():
    payload = build_payload()
    report = savepolls.set_poll_order(payload, [4, 3, 2, 1, 0], "cfp")
    assert report and "cfp" in report[0]
    assert savepolls.poll_order(bytes(payload), "cfp") == [4, 3, 2, 1, 0]
    # the +694 alias mirrors +699 byte for byte
    rec0, stride, count = savepolls._store(bytes(payload))
    for row in range(count):
        assert payload[rec0 + row * stride + savepolls.CFP_RANK_OFF] == \
            payload[rec0 + row * stride + savepolls.CFP_ALIAS_OFF]
    # the AP poll and the unranked row are untouched
    assert savepolls.poll_order(bytes(payload), "ap") == [1, 0, 2, 3, 4]
    assert savepolls.parse(bytes(payload))[5].rank == 0


def test_set_poll_order_ap():
    payload = build_payload()
    savepolls.set_poll_order(payload, [0, 1, 2, 3, 4], "ap")
    assert savepolls.poll_order(bytes(payload), "ap") == [0, 1, 2, 3, 4]
    assert savepolls.poll_order(bytes(payload), "cfp") == [0, 1, 2, 3, 4]
    assert savepolls.parse(bytes(payload))[5].ap_rank == 0


def test_set_poll_order_must_be_a_permutation():
    payload = build_payload()
    with pytest.raises(ValueError):
        savepolls.set_poll_order(payload, [0, 1, 2, 3], "cfp")       # missing a row
    with pytest.raises(ValueError):
        savepolls.set_poll_order(payload, [0, 1, 2, 3, 5], "cfp")    # unranked row
    with pytest.raises(ValueError):
        savepolls.set_poll_order(payload, [0, 1, 2, 3, 3], "cfp")    # duplicate
    with pytest.raises(ValueError):
        savepolls.set_poll_order(payload, [0, 1, 2, 3, 4], "coaches")  # unknown poll
    # nothing was written by the failed attempts
    assert savepolls.poll_order(bytes(payload), "cfp") == [0, 1, 2, 3, 4]


def test_swap_committee_rank_roundtrip():
    payload = build_payload()
    savepolls.swap_committee_rank(payload, 0, 4)
    assert savepolls.poll_order(bytes(payload), "cfp") == [4, 1, 2, 3, 0]
    savepolls.swap_committee_rank(payload, 0, 4)
    assert savepolls.poll_order(bytes(payload), "cfp") == [0, 1, 2, 3, 4]
