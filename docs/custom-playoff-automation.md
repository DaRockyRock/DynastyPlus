# Custom playoff: in-game automation design

> STATUS (2026-07-07): built. `backend/playoff_live.py` owns the runtime
> (projection -> selection -> weekly writes -> history); the saves-folder
> watcher auto-starts with Dynasty+ Tools and `/api/playoff/live` (polled by the
> Playoff Bracket tab) is the fallback heartbeat. Save knowledge that landed
> after this design: rankings are per-team fields in TeamStore (+674 main,
> +694/+699 variant polls, `saveparse/polls.py`); game records carry no week
> field, so rounds map onto the engine's stock postseason records via their
> BowlGame refs and rivalry week is derived from play order; venues are
> written through the record's +4 stadium handle.

Goal: with Dynasty+ Tools open in the background, the user's custom
playoff format drives the REAL game: matchups are written into the CFB 27
save, the game plays/sims them (its own top-stories panel picks them up), the
bracket advances automatically each week, bowls regenerate around the custom
field, and the finished playoff lands in the dynasty's history. Worst case the
app asks the user to reload their dynasty in game; there is no manual data
entry.

## The write seam

`backend/saveparse/schedule.py` reads and patches the `SeasonGameStore` (983
game records; see docs/cfb27-schedule-format.md). Writes go through the
conference editor's proven flow: backup-once, patch the payload in place,
verify by re-parsing, `container.encode`, overwrite the save file. The game
re-reads the save when the user loads (or reloads) the dynasty.

## Timing model (the engine's own loop)

Observed engine behavior, which the automation must ride:

1. Entering a week LOCKS that week's games (allocates pending/participation/
   result structures) and PRE-SIMS their results (unofficial until advance).
2. Playoff records exist from preseason; the engine writes its OWN 12-team
   projections into them from rivalry week, finalizes at selection (entering
   bowl week 1), and fills each later round's slots at the week boundary.
3. Bowl matchups are written once at selection and never touched again.

So the companion's write windows are the week boundaries: every time a new
autosave appears with the week advanced, the app immediately rewrites the
NEW current week's postseason matchups per the custom bracket (clearing the
engine's pre-sim state for records it changes), plus every future round it
already knows. If the user has the dynasty loaded when the write happens,
the app shows "reload your dynasty in game" (the at-worst UX); if the write
lands before they load the week (the common case, since the autosave appears
at advance), reloading is unnecessary... whether the game re-reads the save
between advance and play is part of the in-game verification below.

## Bracket engine

`backend/playoff_live.py` (new) owns the runtime bracket per dynasty:

- `data/dynasties/<id>/playoff/state.json`: season year, status
  (projected | selected | in_progress | complete), the frozen field + seeds,
  per-game state (slot mapping into save records, results), notes.
- Projection phase (regular season): `playoff.build_bracket` fed with REAL
  save data: poll order (saveparse polls), real records/standings
  (saveparse results), real rivalry-week outcomes for every team (schedule +
  calendar), conference champions once CCGs are official.
- Selection (CCGs official): freeze the field per the custom format
  (auto-bids, disqualifiers incl. rivalry-week losses computed from real
  results, conference limits, Notre Dame rule, byes), seed it, and map
  bracket games onto save records (below). Regenerate the non-playoff bowls
  from the remaining eligible teams. Write everything.
- Advancement: on each save change, read official results for mapped records,
  fill winners into the bracket, write next-round matchups, update state.
  Rounds beyond the game's stock bracket depth advance the same way; only the
  record inventory differs.
- Completion: NCG official -> champion recorded; append the season's bracket
  (matchups, scores, sites, champion) to `playoff/history.json` and surface it
  in the dynasty archive.

## Save-record inventory (custom formats vs the stock 11 slots)

The stock season has 11 playoff records (4+4+2+1, NCG allocated late), 33
bowl records, 10 CCGs, and a free-record chain. Custom formats map rounds
onto weeks and games onto records:

- <= 12 teams: use the stock playoff records; byes shrink early rounds
  (unused records are cleared to empty bowls or left teamless).
- Larger fields: rounds still map one-per-bowl-week; a round's games draw
  records from (in order) the stock playoff slots for that week, then bowl
  records (their BowlInfo ref re-pointed for branding/site), then the free
  chain (pending in-game verification that a free record activated by the
  companion is playable).
- More rounds/games than the stock slots: ROUND CYCLING (built 2026-07-07,
  the NCAA-14-mod pattern). The current week's postseason records are reused
  in waves: the app writes a wave of matchups, the engine sims/plays them
  (pre-simming on dynasty load), the app captures the results, including
  unofficial pre-sims (they are the only result those games will ever get),
  clears the records, and writes the next wave; the user reloads the dynasty
  between waves. The save's own season record-keeping is knowingly wrong for
  cycled games; the app's bracket state and playoff history are the source
  of truth. Proven in simulation up to the full 128-team / 127-game bracket
  (14 waves on a 12-record week). The one engine behavior it depends on,
  re-simming a cleared+rewritten record on dynasty load without a week
  advance, is exactly what the DYNASTY-PTEST2 experiment verifies.

  GAME LABELS: a bowl record repurposed for a playoff game is relabeled in
  place (bowls.set_display_name rewrites the BowlGame display string, 31-char
  cap) to the round name ("CFP First Round", "CFP Quarterfinal", ...) so the
  in-game schedule reads as playoff games, not leftover bowl names; the
  internal key is left alone so logos/assets still resolve.

  USER GAME RULE: in cycling, CPU games advance the bracket off the engine
  pre-sim, but the USER's own game advances ONLY when official (played AND
  week advanced), and the user's live game record is never recycled until
  official. So a pre-sim never decides the user's game before they play it,
  their real result is never clobbered by a record reuse, and their own game
  claims a scarce slot first so they never sit on a bye while their bracket
  game waits.

  BYE FEEDER RULE (2026-07-14): when the user has entered a round on a bye but
  their opponent slot still says winner of an earlier game, that entire
  unfinished feeder subtree claims wave records before later sibling branches
  on the user's title path. A 96-team field has 32 first-round games but only
  28 hosts in the observed bowl-week slate. Without this separate immediate
  priority, USC's R1G16 feeder was the lone opening game left unplayed while
  unrelated later branches advanced. The direct feeder now runs in wave one
  for every bye position.

  SINGLE USER DESTINATION RULE (2026-07-14): once the user's custom matchup
  is staged, the user must appear in exactly one unofficial postseason game.
  Retaining the user's original engine bowl is not merely cosmetic. In the
  96-team USC run, Tulsa at USC was correctly written and user-marked, but the
  original USC at Ole Miss bowl still made the dynasty hub report a bye. The
  repair preserves that original game and its opponent, but replaces USC's
  side with an unused non-field substitute. Format 10 prefers an unused FBS
  program: an FCS substitute worked in USC's ordinary bowl but crashed a new
  Penn State dynasty when placed in its native CFP record. This keeps the
  engine's bowl references valid while making the custom game the user's only
  postseason destination.

  USER ROUTE RULE (corrected 2026-07-15): a directly written matchup can appear
  as Play Game even when CFB 27 originally assigned the user to an ordinary
  bowl, but CFB silently discards its postgame result on a native CFP record.
  Dynasty+ maps early user games into Bowl Week 1 and uses the native final-16
  handoff only when the selection boundary put that program on CFB's own CFP
  path. Otherwise every remaining user round stays on the saveable bowl-record
  cycle. No ownership or coach workflow is used.

  PRE-LOCK BASE WAVES (rebuilt 2026-07-08; supersedes both the capacity
  limit and in-place cycling). The decisive discovery from the South
  Carolina 128-team live run: the engine's week LOCK freezes participation
  by TEAM in opaque pending objects, so patching a locked save can only
  change what the schedule screens display. A user matchup added post-lock
  reads as a BYE on the dynasty home screen and cannot be played (observed
  in-game: #1 seed South Carolina, engine bye, patched first-round game).
  The arrival autosave, however, is PRE-lock: the week's slate is already
  queued (SeasonGameRequest, two rows per game; schedule.week_slate) but
  nothing is locked, so matchups patched THERE are adopted by the engine at
  lock as its own pending objects and pre-sims. The direct matchup is visible
  on the home screen once its schedule cache is current. The
  loop:

  1. At selection (the arrival autosave at the playoff week, pre-lock) the
     app snapshots the save byte-for-byte (playoff/cycle_base.sav) and reads
     the week slate from it (state.slate_records; 28 records in the SC run).
     THE ANCHOR REFUSES A LOCKED WORLD (`_week_locked`: any slate record
     pre-simmed / with a result / official; added 2026-07-12): a user who
     loads into bowl week before the app's first sync leaves a POST-lock
     newest autosave, and a base taken from it is a dead end, because the
     engine never re-locks a week it already locked, so the wave's cleared
     records come up detached and are NEVER simmed (reported live: a 9-game
     first round stuck at "0 of 9 recorded"; the save showed the wave's
     matchups in the dormant 0x1d2d shape beside the engine's untouched
     pre-sims of its ORIGINAL slate). When the anchor candidate is locked,
     the guide walks the user to play or sim the week, advance, and exit;
     the anchor is taken at the next (pre-lock) arrival world instead. A run
     already anchored on a locked base by an older build (state.base_locked)
     self-heals the same way: the doomed base is dropped and the whole cycle
     re-anchors on the next pre-lock arrival (unfinished games unmapped,
     slate/base keys recomputed; finished results keep).
  2. Every WAVE is written onto the fresh base world (never in place): as
     many decided bracket games as the slate holds, teams + venue only
     (pristine writes; the pre-lock boundary markers at bytes 98/99 must
     survive), BowlGame display names relabeled to the round. The user's own
     game claims a slot first, preferring the record whose base matchup
     involves their team so the engine's own pairing is consumed, and the
     game's SeasonGameRequest pair is retyped to the user-participation
     variant with its +40 pointed at the request ID for the user's side
     (schedule.set_user_pending): the type keeps the lock from pre-simming
     the game, that matching RequestId makes the dynasty hub offer it for play (both
     halves proved necessary in separate live runs). The engine's own game
     for the user is NEVER blanked: nulling the teams of the user's own
     scheduled game crashed the game on load (Missouri run); a leftover
     engine game for the user in a future week is accepted as cosmetic noise
     instead. While the user's game is live in the current wave, the plan is
     frozen and no rewrite happens (newly decided games wait). The patched
     base replaces the save file; the user reloads and the engine locks the
     wave itself.
  3. The user plays their game (if they have one) and/or sims, then advances
     or just exits; results reach autosaves (CPU pre-sims included, they are
     the only result a cycled CPU game gets) and the app captures them. The
     user's own game only ever advances the bracket off an OFFICIAL result,
     so a pre-sim never decides it and their real result is never clobbered.
  4. When every mapped game is finished and games remain, the next wave is
     due (needs_write -> the Update button): the app writes base + next wave
     and the user reloads, back at the playoff week. A wave is never written
     while the user's own game holds a played-but-not-advanced result (it
     would be rolled away), and a mid-wave world is never disturbed
     (_wave_staged).
  5. When the championship is captured, the snapshot is deleted and the
     season proceeds from wherever the user is; the engine's own leftover
     CFP may still schedule games (a note warns they are cosmetic).

  Self-healing: a mapped game whose record went official with a FOREIGN
  matchup or without a result (the write was clobbered because the user did
  not reload) is unmapped and rescheduled in the next wave, so nothing
  stalls.

  Verified in faithful emulation against the real SC save (every wave played
  to official, capture, rewrite): 128 teams / 127 games = 9 waves on a 28-slot
  week, champion crowned and archived, labels correct every wave, and the
  user's team held a PLAYABLE home-screen game in all 7 of its rounds with
  its real played results. In-game verification of wave 1 (the user's
  first-round game appearing playable after reload) is the current
  checkpoint.

## In-game verification protocol (user in the loop)

The app cannot prove engine behavior; patched test saves + a checklist can.
Each experiment writes a copy of a real save with one variable changed; the
user loads it and reports. Sequence:

1. Clean-slot matchup: write teams into an untouched future slot (e.g. the
   semifinal records at bowl week 2). Expect: bracket UI + top stories show
   them; the week plays them.
2. Locked-slot rewrite: change a pre-simmed matchup + clear engine state.
   Expect: engine re-locks/re-sims the new matchup on advance.
3. Engine-fill fight: pre-fill a slot the engine fills at the next boundary.
   Expect: engine overwrites it (design assumes so) - confirms the "re-patch
   after every advance" loop.
4. Bowl-record repurpose + neutral-site repoint (BowlInfo ref swap).
5. Free-chain activation (only if 4 fails to cover large fields).

## Surfaces

- Live view: `GET /api/playoff/live` returns the current
  bracket JSON (projection or live states; `BracketGame` already renders
  winners/scores). Page: reuse `PlayoffBracket` with a status header
  (Projected field / Selection done / Round N in progress / Final).
- The walkthrough guide (2026-07-08): the live payload carries `guide`
  (`playoff_live._build_guide`), one phase box per stage (reach the playoff,
  each round, completion) with ordered steps and a cursor at the user's
  current step (update / load / play vs OPP / advance / repeat), derived
  from the sync state so it tracks the save. Rendered by `PlayoffGuide`
  above the bracket; the page polls every 10s and the saves watcher keeps
  the state fresh between polls.
- The watcher uses watchdog on the saves folder and auto-starts while a
  dynasty is selected.
- Neutral sites: the format editor's neutral mode becomes a picker over the
  save's real stadium list (saveparse stadiums + ScheduleNeutralStadium
  eligibility), and the writer repoints the game's site accordingly.

## Results are only EVER the engine's (2026-07-08; the fabrication fix)

The app cannot simulate a game; only the loaded engine can. So a wave record
must be RESULT-LESS when written, and the bracket may advance a game only off
a result the engine freshly produced. The bug: a base snapshot can be
POST-lock (the arrival autosave already carries the engine's poll-order
pre-sims, b97=0x10 on every slate record), and the pristine writes did not
clear them, so every wave reused the same frozen scores and the engine never
re-ran (identical scores each round, and the user could "advance" the whole
CPU bracket without ever loading CFB 27; caught on an 80-team Oklahoma run).
Fix: pristine base writes `clear_engine_state` any post-lock record (zeroing
its pending refs to reproduce the engine's own PRE-lock arrival shape, the
one Kentucky verified re-sims fresh on load) so the written wave is
result-less. Consequences, all correct-by-construction: the bracket advances
only after the user loads (engine sims the wave) and comes back; pressing
Update without loading finds no results and does nothing; every round's
scores are distinct. The user MUST load each batch, which is the intended
loop. (The in-place calendar-tail path still uses `reset_result_keep_pending`
- keep pending refs - which is the Illinois-verified re-sim-on-advance shape.)
Faithful emulation (engine only produces results on an emulated load, each
distinct): Oklahoma 80-team and Kentucky 128-team both showed zero
fabrication and 100% distinct final scores.

## The freeze waits for BOWL week, not one CCG (2026-07-08)

The field freezes (and the cycle anchors) only once the user has ADVANCED
PAST conference-championship week. A single official CCG - the user playing
and winning their own CCG while still AT ccg week - must not trigger it: the
other CCGs are not final and the current slate still holds CCG records, so an
anchor there snapshots the wrong week. Observed: a #1-seed Miami froze the
instant its CCG went official, mis-anchored its bye as a later-week game, and
stuck on "load your dynasty." Gate: `_ccg_week(payload, store)` (CCG records
in the current slate) forces projection/prepare regardless of a partial CCG
count; a premature freeze already recorded (older build or a save rolled back
to CCG week) is undone and re-projected, dropping its snapshot.

## The PREPARE write + the ANCHOR WEEK (2026-07-08; user playability)

Fabricated queue wiring proved insufficient, and so did a planted committee
rank: the boundary RECOMPUTES the ranking from results, so a 4-8 team
planted at #8 snapped straight back to #115 (Kansas run). Only a game the
ENGINE's own selection scheduled for the user is playable from the dynasty
hub, and only RESULTS survive the boundary (they are the recompute's
input). The design:

- At CHAMPIONSHIP WEEK (the week queue holds the CCGs), when the user is in
  the custom field but the engine would snub them (rank outside the top 12
  AND fewer than 9 official wins), `needs_write` fires and the apply
  performs the PREPARE: the user's most recent losses are score-flipped
  (schedule.swap_result_scores) until the season reads 9 wins, recorded in
  state (result_flips). The boundary then gives the user a bowl natively.
  Top-12 teams and 9+ win teams need nothing: the engine schedules them a
  CFP game or a bowl on its own. The guide reflects this: the "Championship
  week: update" step appears ONLY when the flip is due or done; a team the
  engine already takes goes straight to "Advance into bowl week" as the
  current step (showing the step unconditionally stranded strong seeds with
  a buttonless update task, fixed 2026-07-08, Oklahoma rank 6).
- THE ANCHOR + RE-ANCHOR (rebuilt 2026-07-08, Oklahoma 80-team run): the
  cycle snapshots the arrival save IMMEDIATELY and waves begin at once for
  every game that does not need the user. `_user_engine_week` classifies
  the user's engine game: "here" (in the anchor slate: their games write
  onto it from wave 1, the Kentucky shape), "later" (an engine bye's
  quarterfinal or a week-2/3 bowl: their games are DEFERRED, never mapped
  onto ordinary records; once the waves here are exhausted and their next
  matchup is decided, the guide shows "Reach your matchup week", and on
  arrival the cycle RE-ANCHORS: the snapshot is replaced with that week's
  arrival save, slate/tail/user keys recomputed, and their natively wired
  record hosts their games from then on), or "none" (no engine game:
  everything maps and sims, user_native=false). Blocking all waves until
  the user reached their week (the original design) stranded an engine-bye
  Oklahoma at week 1 with rounds 1-3 unswum.
- Tail caps are anchor-aware: a cycle re-anchored at bowl week 2 hands only
  the semifinals and championship to the calendar (the quarterfinal stock
  records are wave territory in its own slate).
- The first wave write restores the REAL flipped scores in the written
  world (only the boundary ever sees the adjusted season). The engine's
  post-boundary ranking was computed from the flipped season; that
  distortion is accepted (it only softens the user's custom seed).
- The user's custom game is pinned to their engine record every round (the
  assigner reserves user-involving base records for the user while they are
  alive). On IN-PLACE targets (stock mode, records the lock already froze)
  only the OPPONENT and venue change (the Illinois-verified seam) and the
  user's engine SIDE is preserved, with the custom host's campus pinned via
  an explicit stadium handle. PRISTINE (pre-lock base) wave writes honor the
  bracket's real orientation instead (revised 2026-07-11): the lock adopts
  the record wholesale on load and the user request row is game-scoped, not
  side-scoped, so an away game presents the user as the visitor (reported:
  Florida "hosting" at SMU's stadium, their band/logos/menu framing all home).
  The orientation actually written is persisted on the game as `_disk`.
  Waves prioritize the user's bracket subtree so their next opponent is
  always decided.
- RESEEDING (2026-07-11, format option `reseed`): after every round the
  surviving teams re-pair by ORIGINAL seed, best remaining against worst
  remaining (the NFL model), instead of following the fixed bracket tree.
  Works with every field size and bye structure: each seed carries the round
  it enters (`entry_round`), later rounds are built as labeled placeholder
  slots (type "reseed"), and playoff.fill_reseeded_rounds pairs a round's
  entrants (previous round's winners + seeds whose bye ends there) once the
  previous round is fully final. The sync calls it after every result fill;
  wave priority in reseed mode gates the user's next matchup on the WHOLE
  earliest unfinished round (_reseed_gate_games) since any survivor could be
  their opponent. Campus (higher-seed) sites re-resolve to the new host.
  Loop-tested: 8-team win/elim and 24-team byes+reseed complete with every
  round's entrants and pairings verified.
- THE SELECTION WINDOW (2026-07-11): from the freeze until the FIRST final
  result, the bracket re-seeds on every sync whenever the committee ranking
  or the format changes (the sync reads the save's live week through
  pipeline.load_live_dynasty, never the app pointer, which lags in the Tools
  app and froze fields from an archived pre-CCG snapshot: stale seeds, stale
  records, and projected champions instead of the real CCG winners). The
  poll editor's committee hold lifts during this window, so hand-editing the
  CFP ranking at bowl week is the supported way to shape the final field;
  the first recorded result locks the bracket for good.
- THE CALENDAR TAIL (2026-07-08): the trailing rounds that fit the stock
  postseason ride the REAL calendar instead of anchor-week waves: the
  quarterfinals (up to 4 games) on bowl week 2's stock records, semifinals
  (2) on week 3, the championship (1) on championship week with its own
  presentation (_calendar_rounds; verified in emulation: SF on records
  932/933, NCG on the championship record). Wave writes and the staged
  check exclude those rounds; the tail writes them stock-mode style
  (in-place, re-patched after every advance) once every bigger round is
  final. Gated on the user being able to follow: eliminated, outside the
  field, or on the engine's own CFP path (state.user_cfp_path, i.e. their
  anchor record is a stock CFP record; the engine then advances them with
  native wiring week by week). A bowl-route user still alive keeps the
  anchor-week loop instead (their playable wiring is bowl-record-bound),
  and the tail begins if and when they are eliminated. The selection prepare
  temporarily flips every regular-season loss so CFB sees an undefeated team,
  then the first playoff write restores every real score. If CFB still omits the
  program, the run safely remains on the bowl-record cycle.
- IN-GAME CONFIRMED (Kentucky run): the user played custom first- and
  second-round games on their engine bowl record. Post-run fixes: on a wave
  where the user's next game is undecided, the reservation yields to their
  PATH games (else the engine's original pairing survives as a playable
  phantom, observed: Kentucky offered its old Navy matchup), with the queue
  row downgraded for that world only; `user_live` protects the record only
  while it holds the MAPPED matchup. Field branding keys off the bowl
  IDENTITY (+16), not the display name, so the user's record is repointed
  each wave (the displaced row goes to the partner record). Known cosmetic:
  the Heisman ceremony replays on each rewound load (watched-flag hunt open).
- THE ORANGE FIELD (2026-07-09): a CFP-round identity only carries field art
  for its NATIVE venues - the first round is campus-only, the QF/SF live at
  the New Year's Six stadiums (the engine picks which bowl's art by matching
  the record's +4 against the PlayoffBowlsInfo stadium handles), and the
  title game's art travels with whatever venue is written. Writing a neutral
  or bowl site onto a record that keeps a CFP identity leaves the engine with
  no art to compose, and it renders a blank ORANGE field (observed in-game on
  neutral- and bowl-sited custom games). The unused Generic Bowl row also has
  no field-art package, confirmed by SMU versus South Carolina on 2026-07-14.
  A playable user game at an ordinary neutral site therefore keeps the custom
  SeasonGame stadium handle and keeps a native CFP BowlGame identity. The
  BowlGame identity's own stadium is paired to that same selected venue. The
  SMU versus Iowa State test proved that pairing alone did not select a valid
  surface, so the separate `Stadium.STADIUM_FIELDRECIPENAME` override is also
  set to the installed recipe for whichever team is actually the home side.
  That changes the painted field only. The stadium model, crowd, scoreboards,
  and location still come from the custom venue. Named bowls retain their bowl
  identity, stadium, field, and presentation, and QF/SF games at a New Year's
  Six stadium retain the native round identity.
  The same swap discipline applies, no identity is ever duplicated. IN-PLACE
  writes (stock mode, the calendar tail)
  target the ENGINE's own CFP records, whose identity cannot be repointed
  safely, so there the VENUE yields instead (`_venue_safe_for_record`): a
  site the record's identity has no art for is refused, the record keeps a
  native venue (and a venue broken by an earlier build is repaired to one).
  `_WAVE_FORMAT` 15 rewrites an already-staged playable wave once with the
  field-recipe treatment. Format 13 accidentally changed the stadium to the
  home team's campus. Format 14 kept the selected stadium and paired the
  BowlGame presentation venue, but the Iowa State test showed that it could
  still render orange. Format 15 keeps both of those handles and changes only
  the Stadium field recipe, then restores its previous value after the game.

## Two apps, one dynasty (2026-07-08, incident)

Dynasty+ Tools auto-starts the playoff watcher, so a user
and Tools side by side gets two processes syncing the same dynasty. Their
concurrent live.json read-modify-writes were observed corrupting state
(wave_format/base_wave keys vanished, the plan diverged from the save), and
a mid-race state reset re-froze selection and OVERWROTE cycle_base.sav with
a played-out world. Fixes: `sync()` now takes a cross-process file lock
(playoff/sync.lock, msvcrt on Windows / fcntl elsewhere), and selection
never overwrites an existing snapshot (only the season-change reset deletes
it). Recovery from a corrupted mid-cycle state: restore cycle_base.sav over
the save, delete live.json, re-apply; selection re-freezes from the pristine
base (note the re-frozen bracket may differ from the lost one, since
selection inputs include unofficial results).

## Session robustness (2026-07-08)

- The game holds the loaded week IN MEMORY: every app write becomes visible
  only when the user reloads the dynasty. `awaiting_reload` (set on each
  write, cleared once the engine visibly runs a mapped record) drives a
  persistent "Reload your dynasty" action banner on the bracket page. An
  in-game BYE WEEK right after reaching the playoff week simply means the
  wave landed after the game loaded the week: reload, and the matchups
  (already verified on disk) appear.
- PROFILE-COLLEGE only retains rows for recently touched sessions, so live
  dynasties used to vanish from the app (and scan PRUNED them). Now: scan
  keeps and refreshes registry entries whose save file still exists (reading
  the save with the registry's school hint; season position derived from the
  schedule store when the profile row is gone), and the current dynasty is
  resolved through the registry rather than falling back to a different
  dynasty's save.

## The pending-list rule + the update button (2026-07-08, in-game verified)

The Illinois live run revealed the first engine rule: the refs at
+0/+12/+24/+32/+40/+44 of a game record tie it into the engine's week
sim/play list. Zeroing them DETACHES the game - the engine never sims it,
play/force-win ignore it, and at advance it ages into official-with-NO-result.
The South Carolina run then revealed the second: even KEEPING those refs
(`schedule.reset_result_keep_pending`) only keeps the record simmable for the
lock-time participants; the lock freezes participation by TEAM, so a post-lock
rewrite cannot give the USER a game the engine did not schedule them into
(home screen shows a bye). Cycle-mode waves therefore write PRE-lock base
worlds only (see above); reset_result_keep_pending remains for stock-mode
repatches of records the engine already locked. Games whose record went
official-without-result are unmapped and rescheduled into the next wave.
Venue writes verified live (first round at the higher seed's campus per the
format).

Write flow: polling and the saves watcher are CAPTURE-ONLY (results advance
the bracket the moment an autosave lands); the save is only ever written by
POST /api/playoff/apply - the bracket page's "Update dynasty file" button,
pressed while the dynasty is closed at CFB 27's main menu. Capture syncs
report `needs_write` (a dry-run probe, including due rewinds) driving the
banner: needs_write -> the button; awaiting_reload -> "load the dynasty,
you're good to go"; otherwise silent.

## Anchoring, elimination, and the pin (2026-07-09)

The user plays the custom matchup written into a real postseason game record:

- **Anchoring.** Legacy pure-cycle runs route forward to the user's first
  engine-scheduled postseason game. HYBRID always anchors its early phase on
  the bowl week 1 arrival because the final-16 bridge must reuse that week's
  first-round records. There is no record-flip prepare step: the engine seeds
  its postseason by committee rank, so changing a win-loss record cannot create
  a trustworthy route.
- **Three execution modes (revised 2026-07-13).** The exact 12-team CFP shape
  runs in STOCK mode. Any custom bracket of 16 teams or fewer runs in NATIVE
  mode on the game's postseason calendar. A bracket larger than 16 runs in
  HYBRID mode: only the rounds needed to reduce the field to 16 cycle on the
  bowl week 1 arrival save, then the round of 16 through the championship run
  natively on successive game-owned postseason weeks. `classify_mode` exposes
  this distinction to the format editor.
- **NATIVE mode (2026-07-13, the balla14-style forward calendar).** Every
  bracket of 16 or fewer teams now plays through CFB 27 on its OWN bowl-week
  calendar, moving forward with no rewinds and recording every game in-game,
  the flow balla14's playoff tool proved (see the [[balla14-playoff-tool-findings]]
  memory). `native_mode_fits`/`classify_mode` select it below stock and above
  cycle. Each round maps onto the stock postseason records walking back from
  the title game (championship 401, semifinal 932-933, quarterfinal 928-931,
  first round 924-927), and a first round bigger than 4 games BORROWS regular
  bowl records from bowl week 1's slate (`_native_borrow`, up to
  `_NATIVE_FR_BORROW`=4, so a 16-team opening round of 8 games fits: the
  balla14 borrowed-bowl trick, and it picks the same four in practice: Cure,
  Boca Raton, New Orleans, Gasparilla). The current round is written at its
  PRE-LOCK arrival (`_native_ready_rounds` gates to records in the current
  slate), using the same `_apply_to_save(pristine=..., only_rounds=...)` shape
  as a cycle wave so the engine locks the matchup and `set_user_pending`
  exposes Play Game. The crucial second write happens BEFORE the week advance:
  once the current results decide every participant in the next round,
  `_native_prestage_rounds` writes both teams into those future records. CFB
  allocates one participant request per team at the boundary. Waiting until
  arrival left every native quarterfinal with only its bye seed's request; the matchup
  displayed and launched, but CFB discarded the completed game because the
  opponent had no participant request. This timing matches the working 16-team
  reference tool, which writes its quarterfinals while Bowl Week 1 is still
  current. The user exits after the game, updates, reloads the same week, and
  only then advances. Two record-hygiene rules keep the engine from freezing on
  advance: `neutralize` refills a ready round's UNCLAIMED stock records (the
  engine's own leftover pairing there) with FCS filler, and `blank_records`
  clears FUTURE-round stock records that are not yet the fully decided next
  round. A decided next round is never blanked because it must cross the
  boundary with both participants already present. A shorter
  bracket (2/4/8 teams) starts on a LATER bowl week (its rounds map to the
  trailing kinds), so the user advances through the earlier weeks playing the
  engine's own throwaway CFP, which does not count. No snapshot, no
  completion-restore, no engrave: the save already holds the real playoff on
  its real records. Loop-tested (tests/test_playoff_live_loop.py, native
  cases) for 2/4/8/16 teams, win-it-all + every elimination round + spectator
  (user outside the field, the "watch it play through" case), verifying no
  team is ever double-booked within a single week's slate (the freeze
  condition). The emulator's week-advance boundary now allocates participant
  requests per team, so a late-written second team reproduces the real
  half-pair failure and every native regression proves the pre-stage occurred.
- **HYBRID handoff (2026-07-13).** Once every pre-tail game is final, the 16
  survivors are known. The round of 16 is written by rewinding one last time
  to the clean pre-lock bowl week 1 snapshot. Completed cycle assignments do
  not reserve records in that clean world, and quarantined records are never
  borrowed. Four stock first-round records, the user's live engine record when
  applicable, and enough healthy regular bowls host all eight games. After that
  write, `state.handoff` is permanent. The snapshot stays recovery-only through
  completion and is never used for another forward round. Quarterfinal,
  semifinal, and championship syncs use only the current forward-moving save.
  This differs from the retired calendar-tail experiment, which wrote
  unresolved future CFP records. The supported handoff writes a current round
  on arrival and its fully decided successor immediately before the boundary.
  Custom bowls and neutral sites remain part of each bracket game and are
  applied to these native records, including a bowl-selected championship.
- **Native handoff requires an engine CFP route (corrected 2026-07-15).** The
  separate CFB27 playoff tool's direct `SeasonGame` write is sufficient for CPU
  teams. For a user program omitted from the engine CFP, it is only visually
  playable: Actions launches the game, postgame runs, then CFB returns to the
  hub with the game unplayed. That tool refreshes the hidden team schedule cache
  through an owner transfer plus retire and rehire after inserted rounds.
  Dynasty+ does not require that workflow. Before selection it temporarily
  presents a custom-field user as undefeated so CFB creates the native route
  organically, then restores the real scores. The final-16 handoff runs only
  when that route is present. A snubbed or already-started ordinary-bowl user
  remains on the proven bowl-record cycle through elimination or the title.
- **User games require no ownership changes.** The writer sets the matchup and
  the correct home-side or away-side user request together. Unsafe native
  insertion is never used for a live ordinary-bowl user, so no transfer,
  retirement, or rehire workflow is needed.
- **Locked native user record (format 16, 2026-07-14).** After SMU beat Iowa
  State, the quarterfinal save correctly contained SMU versus Michigan in
  record 928, but the engine's locked user-typed `SeasonGameRequest` still
  opened record 931, which the custom plan had reassigned to Texas Tech versus
  Miami. Actions therefore offered Texas Tech even though the schedule record
  was correct. Native pinning now reads the typed request directly, treats that
  record as authoritative, and swaps plan assignments when a sibling already
  owns it. The custom opponent rewrite then lands on the engine's organic
  Play Game wiring instead of trying to fabricate that wiring elsewhere.
  `awaiting_reload` is never accepted as evidence by itself: the current save
  must still match the repaired plan. This prevents an older successful-write
  flag from hiding a newly required record swap and trapping the guide on Load.
- **SMU quarterfinal participant-request failure and recovery (format 18,
  2026-07-14).** SMU versus Michigan displayed correctly in SeasonGame 931 and
  launched from Actions, but finishing returned to the dynasty menu with the
  game unplayed. The 468_2 schema identifies +52 and +60 as `AwayRequestId`
  and `HomeRequestId`, not transferable result-object references. CFB had
  crossed the Bowl Week 1 boundary while each future quarterfinal still held
  only its native bye seed, then Dynasty+ added the custom opponent after the
  engine issued requests. Copying numeric IDs from ordinary bowls made the
  matchup launch but did not create the corresponding backing requests, so CFB
  still discarded the postgame result. That transplant repair is removed. The
  permanent fix stages the next round before the advance and saves that exact
  pre-boundary world as `native_boundary_base.sav`. If a one-sided request is
  ever detected, Dynasty+ restores the immediately prior bowl week, keeps all
  completed games, stages both participants, and lets CFB issue both requests
  itself on the repeated advance. A malformed forward world is retained as
  `native_boundary_failed.sav` for safety.
- **Complete requests are not enough for an externally inserted user
  (2026-07-15).** A second SMU versus Michigan replay had both engine-issued
  participant request IDs, one correct user Actions row, and a structurally
  healthy `SeasonGame`, yet the 13-12 result was still discarded. The only
  postgame save delta was the queue's launch marker. This proves the missing
  object is CFB's internal team postseason route, not another field in the game
  record. Native handoff is now gated by the user's engine-selected CFP path;
  an ordinary-bowl user stays on the cycle instead.
- **Duplicate native Actions rows (format 18, 2026-07-15).** After the repaired
  SMU boundary produced a healthy two-sided Michigan matchup, CFB tagged both
  `SeasonGameRequest` participant rows as the same dynasty member. The hub
  consequently displayed two Play Game entries that opened the same
  SeasonGame. Healthy decoded queues use the first row for a home user and the
  second row for an away user, with +40 equal to that side's participant request
  ID. Native sync detects a count greater than one, prompts one Update, keeps the
  side-matching row, and restores the other duplicate to the observed CPU
  request shape. The SeasonGame and its engine-issued `AwayRequestId` and
  `HomeRequestId` are not changed.
- **Native-CFP bye placeholder (format 10, 2026-07-14).** When a user has a
  custom bye but CFB 27 gave them a native first-round CFP game, the cycle must
  keep that user-owned record valid without double-booking its original
  opponent. An FCS throwaway made the save structurally parseable but crashed
  CFB 27 on load in a fresh Penn State run. Format 10 rewrites every staged
  format 9 wave once and uses an unused non-field FBS program instead. The
  placeholder is not part of the custom bracket and the user must not play it.
- **Elimination.** Once the user is out (a loss) or done (champion), their
  record is dropped from the wave pool so no CPU game overwrites it, and their
  real last game is PINNED: its exact played bytes are captured and restored
  onto the record on every rewind (`schedule.read_record`/`write_record`,
  `state.user_frozen`). The rest of the bracket sims around them. A user with
  no engine postseason game uses the same direct write and conditional
  schedule-cache refresh path.
- **Completion restore (crash fix).** Cycling fills the save's bowl/CFP records
  with custom matchups, relabeled bowls, and DOUBLE-BOOKED teams (a team placed
  in a custom game while still in its engine-original bowl). The engine FREEZES
  trying to advance past that. So when a pure-cycle playoff completes,
  `_restore_base_to_save()` writes the pre-lock base snapshot back over the
  save, handing the engine its own untouched postseason; the user advances the
  real bowl weeks normally and the custom results live in Playoff History. The
  base snapshot is kept until this restore runs (pressing Update triggers it),
  and the completion guide walks it explicitly (update -> reload -> finish the
  season); it never says "continue as normal" while the restore is pending.
  A calendar-tail run rode the real weeks already and is left alone. CFB clears
  `SeasonGameRequest` immediately after the championship advance, so completion
  also recognizes an official mapped title result with an empty week slate.
  That terminal result is captured before the stale-save gate runs, and a
  completed bracket is exempt from every same-season projection reset.
- **The engrave (playoff run on the season schedule).** After the restore, the
  engine sims its own throwaway postseason for the remaining bowl weeks, so the
  season's schedule page would show those cosmetic results. Once the user has
  advanced past their last cosmetic game, one more Update runs
  `_engrave_user_games()`: the OFFICIAL postseason records that hold the user
  (their bowl, or their CFP path: 1 to 4 slots) are rewritten IN PLACE with the
  custom run's matchups, venues, and scores, latest games first (the finale
  always lands). Only records already containing the user are touched, so no
  bracket slot is double-booked and no pending game is disturbed; the season is
  already past every postseason boundary. Known limit: the save holds at most
  as many games as the engine gave the user, and box scores keep the cosmetic
  sim's stats. A hybrid needs no completion restore because its final four
  rounds used the native calendar. If the user was eliminated during its early
  cycle, the final explicit Update engraves their now-official ordinary bowl
  directly when the championship completes.
- **No base rebase, ever (FIFTH ENGINE RULE, learned in-game 2026-07-09).**
  A rebase (adopting a post-load autosave as the cycle base, tried as a
  Heisman-ceremony fix) shipped for a few hours and broke a live run: a
  mid-session autosave is POST-lock, and the engine does NOT re-lock a week
  it already locked, so wave records cleared to the scheduled-unplayed shape
  on such a base come up DETACHED on reload; the CPU games are never simmed
  (observed: a whole second round sat unsimmed; only the user's own game,
  kept alive by the per-team user wiring, was playable). Only the pre-lock
  ARRIVAL autosave re-locks and re-sims on load, so the anchor snapshot is
  the one and only wave base. The Heisman ceremony therefore still replays
  on every rewound load (cosmetic; the watched-flag byte hunt is the only
  real fix and remains open). `_WAVE_FORMAT` 6 forces rebased worlds to
  rewrite from the true base; `restore_base.sav` copies left by the retired
  rebase are preferred by the completion restore (guaranteed pristine).
  CAUTION: the test emulator models every load as PRE-lock, so it cannot
  catch this class of bug; in-game verification is mandatory for any change
  to the base's shape.

## Testing the whole loop

`tests/cfb27_playoff_engine.py` is a faithful CFB27 engine emulator: given a
real bowl-week-1 base save it models a LOAD (lock the SeasonGameRequest slate,
pre-sim every result-less scheduled record with distinct scores, apply the
user's chosen win/loss) and a harness that redirects everything `sync()` reads
at a throwaway copy of that save plus a synthetic dynasty, touching no real
data. `tests/test_playoff_live_loop.py` drives the entire wave loop and asserts
the bracket always reaches one champion, the user plays exactly as many games
as their finish implies (champion iff they win them all), the eliminated
user's record is never CPU-overwritten and their last result is pinned, and
CPU scores are distinct wave-to-wave.

Verified across sizes 2/4/8/16/32/64/128 at every applicable elimination round
plus a title run, the 24-, 80-, and 96-team bye brackets, a not-in-field bowl
team, an engine-CFP user that completes the native handoff, and an ordinary-bowl
user that safely cycles through the title. Fast coverage also constructs every standard
field size from 1 through 128, while the bracket engine exhausts all 52,307
valid single-, double-, and triple-bye shapes exposed by the editor. These are
`@slow` and skip unless `CFBMOD_TEST_BASE_SAVE` points at a base save:

```
CFBMOD_TEST_BASE_SAVE=/path/to/cycle_base.sav pytest tests/test_playoff_live_loop.py
```

The stock path (the native 12-team shape only) follows CFB27's native CFP flow.
Custom brackets of 16 or fewer use native mode when the user's program is on
CFB's CFP route, including the borrowed-bowl opening for 16 teams. Larger
brackets cycle their preliminary rounds and then use the native final-16 flow
under the same route guard. An ordinary-bowl user stays on the cycle instead.
