# CFB 27 save: schedule / results / postseason structures

Research log for `backend/saveparse/schedule.py` (2026-07-07). Method: four
saves of one Nebraska dynasty (preseason, rivalry week, bowl week 1, bowl
week 2) block-diffed and bit-mined against ground truth (the in-game
top-stories screenshot: #5 Oregon 12-2 at #4 Texas A&M 10-2 on Jan 1; Nebraska
5-6; known CFP first-round and conference-championship winners inferred from
bracket slot movement between saves).

## SeasonGameStore

One SPBF block per season, 983 records x 100 bytes (this dynasty; the count is
in the block header, do not hardcode). Two blocks carry the name; the first is
`PracticeSeasonGameStore` (33 records), the real one is the occurrence not
preceded by `Practice`. Full field layout: `backend/saveparse/schedule.py`
docstring.

Verified findings worth restating:

- **Scores** are bit-packed at bytes 76/77 (home bits 609..615, away
  617..623). Validated by reconstructing full W/L logs: Nebraska 5-6,
  Oregon 12-2 (with the 45-22 Ohio State loss, the 31-29 CCG loss, the 34-17
  first-round win), Texas A&M 10-2.
- **The engine pre-sims a week when the week begins.** The bowl-week-2 save
  already holds final scores for the quarterfinals (Texas A&M 28, Oregon 21)
  flagged unofficial (byte 97 = 0x10). Byte 97 gains 0x01 when the user
  advances past the game. Consequence: anything the companion surfaces must
  filter on the official bit, or it spoils results; and a matchup patch to a
  locked week must clear the pre-sim state (`clear_engine_state`).
- **Bracket lifecycle.** From rivalry week the playoff records already hold
  the engine's PROJECTED matchups. They are re-written at selection (entering
  bowl week 1), and each later round's slots are filled when the week that
  plays them begins. The national-championship record does not exist up
  front: records after the last CCG are a free chain (+0 = next free index),
  and the engine allocates the NCG record when the semifinals complete.
- **Record identity** (this dynasty): regular season 0..923 (891 scheduled in
  preseason), bowls 369..401 (33 records with BowlInfo refs at +16),
  CFP R1 924..927, QF 928..931, SF 932..933, CCGs 934..943, free 944+.
  Ranges are located structurally (bowl refs, free chain), never hardcoded.

## The week slate and the lock (2026-07-08, from the 128-team live run)

- **`SeasonGameRequest`** (SPBF store, 68-byte records): the engine's queue
  for the CURRENT week, two request rows per game, each with a game-record
  ref (`0x3174|row`) at +32. Allocated at the week-ADVANCE boundary, so the
  queue is present even in the arrival autosave, BEFORE the engine locks the
  week. `schedule.week_slate` reads it; it is the authority on which records
  the engine will sim or offer for play this week (verified: 56 rows = the
  exact 28 records later locked at bowl week 1).
- **The arrival autosave is PRE-lock.** The lock (pending/participation
  allocation + CPU pre-sims) happens in-session after the boundary; the game
  then autosaves again (e.g. on dynasty exit). Pre-lock, a slate record also
  carries a boundary marker in bytes 98/99 (0x1c01 bowls / 0x1c02 CFP rounds;
  dormant unplayed records show 0x1d2d). Writers must not stamp the unplayed
  pattern over those markers.
- **The lock's participation is frozen by TEAM, not by record.** Patching a
  locked record's team refs changes what the schedule screens show, but the
  engine still runs the lock-time participants: a matchup written into a
  locked week for a team the engine had on a bye reads as a bye on the
  dynasty home screen and cannot be played (observed in-game: #1 South
  Carolina given a first-round game post-lock). The participation lives in
  opaque pending objects (`TeamStats` rows referenced at +12/+40 are stat
  blobs with no team field), so it is not patchable byte-wise. The seam
  instead: patch matchups into a PRE-lock save and let the engine lock them.
- **User-ness is a typed request row, not derived from teams.** Each queued
  game has two SeasonGameRequest rows; the game the user plays carries a
  user-participation variant on the pair's SECOND row (+16 = 0x21DA|member,
  +28 = 0, +48 = no-result sentinel, +56 = 0x01 vs CPU's +16 = 0,
  +28 = scheduler handle, +48 = pending handle, +56 = 0x09). The lock trusts
  it blindly: a pre-lock matchup patch WITHOUT retyping the row gets
  pre-simmed like a CPU game even with the user's team in it (observed
  in-game: Minnesota, hidden 30-27 result, home screen bye).
- **Fabricated user wiring is NOT sufficient.** A queue row retyped to the
  user variant with +40 = the record's away result-slot ref (== +52), byte
  identical to an organic playable game (Maryland diff), still reads as a
  BYE on the dynasty hub (North Carolina run, the third in-game test). The
  typed row does half the job (the lock leaves the game un-simmed and
  allocates its slots) but the hub's play-your-game gate lives in the
  boundary's opaque object graph (0x80xxxxxx handles), which cannot be
  fabricated byte-wise. The only wiring that plays is the wiring the ENGINE
  builds when ITS OWN selection schedules the user (bowl or CFP), after
  which opponent/venue rewrites keep it playable (Illinois-verified).
- **The committee ranking is writable and drives the engine's field**, but
  it RECOMPUTES at every week boundary. The recompute is prior-rank
  anchored: across the CCG->bowl boundary the median move was 1 spot, only
  2 of 143 teams moved more than 6, and every 5-12 team stayed within 3. So
  a rank planted at 8 during championship week survives into the engine's
  first-round window (5..12) with high probability; the failure mode is a
  base without a user game, detected and degraded honestly.
- **Never blank the user's own scheduled game.** Nulling both team refs of
  the engine's own matchup for the user (their bowl in a later week) crashed
  the game on load (observed in-game: Missouri run; the engine keeps its own
  references to the user's next game). Leave leftover engine games for the
  user alone.

## The week field (2026-07-11)

Regular-season records DO carry their week: bits 5..8 of the big-endian u16 at
record offset +94 (`(u16 >> 5) & 0xF`), 0-based. Week 0 is the kickoff week the
profile labels "Week 1" (11 games in the reference dynasty), week 13 is rivalry
week, week 14 is the Army-Navy week (one game); the profile's week is always
`field + 1`. Verified across six saves of three dynasties: official results are
exactly weeks 0..N-1, the pre-simmed set and the SeasonGameRequest queue are
exactly week N, and no FBS team appears twice in one week (only the five FCS
placeholder team rows, 30..34, repeat within a week). Engine-created
postseason records (CCGs, bowls, CFP) leave the field 0, so it is only
meaningful after excluding those structurally. Parsed as `Game.sched_week`.

The u16 at +68 (top half of the attendance-packed u32) is a per-record
day/time slot code (constant per record from preseason on; a handful of
distinct values per week, the bulk sharing the Saturday default). Not fully
decoded; the schedule editor treats it as opaque and leaves it with the
record, so a rewritten matchup inherits its slot's kickoff day/time.

Other stores surveyed on the way (2026-07-11): `ScheduleKnownGame` (16-byte
records: two team refs + a packed year/date word) is the game's list of
real-world FUTURE contracted series feeding its scheduler, not the current
season; `ScheduleProtectedOpponent` (8-byte: team ref + 0x296E rivalry ref)
is the game's own protected-rivalry table; `ScheduleStructureEntry[Exact]` /
`ScheduleStructureYear[Exact]` describe future-year scheduling structure.
None of them are needed for current-season matchup rewrites.

## Open items (in-game verification pending)

- After `clear_engine_state` on a locked/pre-simmed game, does the engine
  re-lock and re-sim the new matchup on advance (orphaned pending /
  participation / result records tolerated)? (Moot for the playoff runtime,
  which now writes pre-lock worlds only.)
- Does the engine's own bracket-advance overwrite slots the companion filled
  (it fills next-round slots from ITS bracket at week start), i.e. does the
  companion need to re-patch after every advance? (Design assumes yes.)

Related stores decoded separately: BowlInfo[] / PlayoffBowlsInfo[] (bowl
identity + playoff round tie-ins), ScheduleKnownGame[] weekly calendars,
Stadium[] + ScheduleNeutralStadium[] (venues), polls/standings. See their
parsers under `backend/saveparse/` as they land.
