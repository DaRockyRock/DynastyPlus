# The Editorial Engine (v2)

A design for how Dynasty+ turns a week of simulation state into a coherent,
living media universe: news articles, a top-stories slider, social posts, an
in-app phone, press conferences, and the CFP / hot-seat / recruiting / awards
surfaces. The Simulator (and later CFB 27 itself) owns the game; this engine
owns everything the world *says* about it.

It replaces "ask a small model to read the whole save and find the stories"
with an **editorial pipeline that does the thinking in code and leaves the
model only the writing.** Grounded in three bodies of work (sources in
`docs/editorial-engine-research.md`):

- **Newsworthiness & surprise** — journalism news values; surprisal; Elo-style
  expectation models; multi-criteria scoring.
- **Narrative engines** — OOTP's two-engine split; quality-based narrative /
  storylets; Facade beats; FM/2K confidence and directive objects.
- **Small-LLM grounding** — Lost-in-the-Middle; plan-then-write data-to-text;
  envelope-only constrained decoding; per-item generation; post-hoc fact
  validation.

---

## 0. The two ideas

**Idea one: code is the editor, the model is the writer.** A small model is bad
at deciding what matters and holding 280KB of state, but good at writing two
fluent sentences from five facts. All selection, ranking, continuity, and
consistency live in deterministic code; the model receives a tight,
self-contained **brief** per content item and writes prose.

**Idea two: scale the model's influence with its capability.** The pipeline
must produce a coherent universe with a 3B model, a 70B model, a hosted
frontier model, or **no model at all** (template renderer). The deterministic
engine is the floor; whatever intelligence the user's model has is layered on
top in safe, bounded ways (richer prose, bigger cascades, an optional
editorial-review pass). Quality degrades gracefully with model power; the
facts, the storylines, and the structure never do.

---

## 1. Architecture

### 1.1 Persistent stores (the history axis)

Per-dynasty stores carrying state across weeks. The first is derived fresh per
scan; the rest accumulate.

| Store | What it holds | Lives at |
|---|---|---|
| **World State (Qualities)** | Flat bag of numeric/enum facts derived from the save: records, ranks, streaks, seat temp, recruiting interest, week, **mood**. The gating vocabulary for everything. | derived per scan |
| **Entity Canon** | Stable IDs + canonical attributes for every team, coach, player, recruit. The only allowed source of entity facts. | `canon/` |
| **Arc Registry** | Long-lived storylines (open/active/resolved) with their own qualities, ordered beats, **claims** (rumors) and **promises** (commitments the user made). | `arcs/<year>.json` |
| **Continuity Ledger** | Every headline/subject/angle already run, per week, for dedupe and follow-ups. | `ledger/<year>.json` |
| **Expectation Model** | Elo-style power ratings + program-relative baselines; drives surprise, stakes, and the hot seat. | `ratings/<year>.json` |
| **Persona Cards** | Persistent voices: reporters, insiders, fan accounts, phone contacts. Voice exemplars, biases, committed takes, credibility track record. | `personas/` |
| **Rundown Log** | Each week's scored rundown persisted with signals, for debuggability, evals, and the dev "why did this run?" view. | `rundown/<year>_<week>.json` |

Today's `narrative` and `world_events` stores are the seeds of the Arc Registry
and Continuity Ledger; `customization.py` personas seed the Persona Cards.

### 1.2 The weekly tick

```
                save (Simulator / CFB 27)
                          │
  ┌───────────────────────▼────────────────────────┐
  │ 1. EXTRACT    qualities + canon + mood           │ code
  │ 2. RATE       update Elo / expectations          │ code
  │ 3. STAKES     scenario math over the schedule    │ code
  │ 4. DETECT     enumerate story candidates         │ code
  │ 5. SCORE      salience (seeded, deterministic)   │ code
  │ 6. ARCS       open / advance / close; resolve    │ code
  │               rumors; check promises             │
  │ 7. RUNDOWN    budget by model profile; MMR;      │ code
  │               ledger dedupe; evergreen floor;    │
  │               assign the week timeline           │
  │ 8. BRIEF      one self-contained brief per beat  │ code
  │ 9. REALIZE    one LLM call per beat, priority-   │ model
  │               ordered, concurrent, cached prefix │ (or template)
  │10. VALIDATE   facts/claims check; repair; fall   │ code
  │               back to template                   │
  │11. WRITE-BACK arcs, ledger, ratings, personas    │ code
  └──────────────────────────────────────────────────┘
                          │
     news · top stories · social · phone · presser
```

The tick runs in two **phases** matching the existing presser machinery:
`preview` (week advanced, game not played: previews, stakes, buildup) and
`reaction` (result + presser in: recaps, fallout, cascades). Candidates and
beats are phase-tagged; the presser gate already enforces that reaction
content waits for the coach's words.

**Determinism rule:** steps 1-8 are pure functions of (save, stores, seed),
where seed = hash(dynasty_id, year, week, phase). Re-running a week reproduces
the same rundown and the same beat IDs (cache keys and cascade dedup depend on
this); only the prose may differ on regeneration.

### 1.3 Model profiles and the generation budget

A `ModelProfile` is resolved at connect time (the existing llm.json probe) and
refined by a rolling latency average from the call log:

```python
@dataclass
class ModelProfile:
    tier: str            # none | nano (<4B) | small (4-15B) | mid | frontier
    latency_s: float     # rolling average per call, self-measured
    max_brief_facts: int # nano: 5, small: 8, mid: 12, frontier: 16
    creative_liberty: str# nano: "restyle the template" ... frontier: "full color"
    cascade_scale: float # social posts per story tier
    review_pass: bool    # mid+ only: the editorial-review call (7.2)
    budget_s: float      # wall-clock envelope for the week's realization
```

The rundown is realized **top-down within the budget**: the lead story first,
then top stories, program news, texts, national coverage, then the social long
tail. When the envelope is spent, remaining beats render through the template
path. A faster model fills more of the week with prose; a slower one ships the
same stories with plainer wording. The user never waits on a wall of calls:
content streams into the UI in priority order (the cache fills per beat), and
`tier == none` means the entire universe renders from templates instantly.

---

## 2. Data structures

### 2.1 World State (Qualities)

```python
@dataclass
class WorldState:
    year: int; week: int; phase: str          # preview | reaction
    season_open: bool
    # user program
    record: tuple[int, int]; conf_record: tuple[int, int]
    streak: int                                # + wins, - losses
    ap_rank: int | None; cfp_seed: int | None
    seat_temp: int                             # 0..100, program-relative
    expectation_delta: float                   # actual vs projected wins
    mood: str                                  # euphoric | confident | steady |
                                               # anxious | grim  (computed: result
                                               # x expectation x stakes)
    # this-week event flags
    last_result: GameResult | None
    rivalry_this_week: bool
    stakes: list[Stake]                        # from the Stakes Computer (3.2)
    # rolling maps
    recruit_interest: dict[str, int]
    player_form: dict[str, str]
    promises_due: list[Promise]                # commitments now testable (4.4)
    extras: dict[str, Any]
```

`mood` is the cheapest immersion lever in the design: one computed word that
becomes a tone directive in every brief, so a gut-punch loss week *feels*
different across the entire surface (somber beat writers, furious fans, a
careful AD text, a gloating rival) without any extra model calls.

### 2.2 Entity Canon

```python
@dataclass
class Entity:
    id: str                  # "recruit:emory_cromwell"
    kind: str                # team | coach | player | recruit
    name: str
    attrs: dict[str, Any]    # position, stars, ovr, conference, tenure, ...
    aliases: list[str]
```

The canon is the only source of entity attributes. Every brief carries a
**cast list** of canonical records, and the validator rejects output that
contradicts them. This kills the "Cromwell is a CB / WR / QB in three
articles" class of bug structurally.

### 2.3 Story Candidate

```python
@dataclass
class StoryCandidate:
    id: str                       # deterministic hash(year, week, type, subjects)
    type: str                     # catalog in 4.6
    scope: str                    # program | national
    phase: str                    # preview | reaction
    subjects: list[str]           # entity ids
    facts: dict[str, Any]         # the numbers this story is about
    signals: dict[str, float]     # raw salience inputs
    score: float = 0.0
    arc_id: str | None = None
```

### 2.4 Storyline Arc

```python
@dataclass
class StorylineArc:
    id: str
    type: str                     # hot_seat | playoff_push | rivalry_week |
                                  # qb_battle | recruiting_battle | cinderella |
                                  # collapse | award_watch | streak | revenge_game |
                                  # portal_saga | rumor
    subjects: list[str]
    status: str                   # open | active | resolved | expired
    arc_qualities: dict[str, float]   # pressure, momentum, trust, ...
    beats: list[BeatRecord]           # what already rendered, by week
    claims: list[Claim]               # live rumors attached to this arc (4.3)
    promises: list[Promise]           # user commitments attached (4.4)
    opened_week: int; last_advanced_week: int
    tension: float
```

Arc types are small classes declaring `open_when / advance_when / close_when`
predicates over `WorldState` plus a `next_beat()` that builds briefs from the
arc's accumulated history.

### 2.5 Beat (storylet)

```python
@dataclass
class Beat:
    id: str
    kind: str               # news_article | social_post | text_message |
                            # press_question | insider_report | debate_take |
                            # feature | ticker_item
    source: str             # candidate id | arc id | evergreen id
    scope: str; phase: str
    salience: float
    day_slot: str           # "Mon AM" ... "Sat postgame" (week timeline, 4.5)
    brief: StoryBrief
    effects: list[Effect]   # quality/arc mutations applied after render
    repeatable: str         # one_shot | weekly | cooldown:N
```

### 2.6 Claims and Promises (the truth machinery)

```python
@dataclass
class Claim:                      # a rumor: attributed, possibly false
    id: str
    text: str                     # "Vickers has told confidants he is leaving"
    source_persona: str           # who is reporting it
    confidence: int               # 0..100, what the reporter believes
    truth: bool                   # ground truth, KNOWN to the engine, hidden
                                  # from the reader until resolution
    status: str                   # live | corroborated | refuted
    resolve_when: str             # predicate; sim events settle it

@dataclass
class Promise:                    # something the USER committed to
    id: str
    contact_id: str               # who it was made to
    text_span: str                # the user's verbatim words (regex-verified)
    kind: str                     # playing_time | nil_amount | role | visit | other
    testable_when: str            # predicate over WorldState
    status: str                   # open | honored | broken
```

Claims let the media be **wrong on purpose** (with the wrongness tracked, the
reporter's credibility on the line, and a vindication/correction beat fired at
resolution). Promises are extracted from the user's own outbound texts (the
existing `world._classify_llm` pass returns a verbatim span; code stores it
only if the span regex-matches the actual message, so a weak classifier cannot
invent commitments). When the sim later contradicts a promise, a
`confrontation` beat fires: *"Coach, you told me I'd start."* The world
remembering what the user said is the single deepest immersion mechanic in the
design.

### 2.7 Persona Card

```python
@dataclass
class PersonaCard:
    id: str; name: str
    role: str                     # beat_writer | national | insider | fan |
                                  # player | recruit | staff | rival_coach
    outlet: str | None
    voice: str                    # 2-3 sentence style description
    exemplars: list[str]          # 2-4 short verbatim samples of their writing;
                                  # few-shot voice anchoring is the most reliable
                                  # way to get a small model to hold a voice
    biases: dict[str, str]        # takes they are committed to, per arc
    credibility: int              # 0..100, moves when their claims resolve
    relationship: int             # -100..100 toward the user's program
```

Personas are the difference between "generated content" and "a media universe."
A columnist who has been pro-extension all season must not flip casually; a
reporter burned on a bad rumor gets dunked on and is hedgy for weeks; the
local beat writer knows the roster cold. The card's exemplars ship in the
brief's cached prefix, so voice costs nothing extra per call.

### 2.8 Story Brief (the packet the model sees)

Laid out for a small model: static voice first (KV-cache prefix + primacy),
delimited fact pack, the task last (recency).

```python
@dataclass
class StoryBrief:
    persona: PersonaCard          # rendered as the cached prefix
    mood: str                     # tone directive, persona-mapped
    cast: list[CastEntry]         # the closed entity list (with policies, 6.1)
    facts: list[str]              # 4-N atomic facts, week-tagged, PRE-FORMATTED
                                  # strings ("won 28-24", "No. 5"); the model
                                  # never does arithmetic
    claims: list[Claim]           # rumor content, must be attributed + hedged
    stakes: list[str]             # forward-looking lines from the Stakes Computer
    callback: str                 # the one best historical hook ("first road win
                                  # over a ranked team since 2019"), or ""
    continuity_note: str          # "their third straight loss" (ledger)
    constraints: str              # no-dash, no-emoji, season-open guards, length
    task: str                     # the concrete directive, LAST
    schema: dict                  # JSON envelope (envelope constrained, prose free)
```

---

## 3. The salience scorer

### 3.1 Signals (news values made computable)

| Signal | Computed from | News value |
|---|---|---|
| `surprise` | surprisal of result vs expectation (3.3) | Surprise |
| `magnitude` | WP swing, margin, poll-rank delta | Magnitude |
| `stakes` | Stakes Computer output (3.2) | Drama / Magnitude |
| `conflict` | rivalry, controversy, injury, blowout-loss | Conflict / Bad news |
| `eliteness` | poll rank + star rating of subjects | Power elite / Celebrity |
| `proximity` | own team 1.0 > rival > conference > national | Relevance |
| `follow_up` | advances an open arc / ledger recency | Continuity |
| `goodness` | streaks, records, milestones | Good news |

### 3.2 The Stakes Computer (anticipation, pure math)

Real sports media is mostly *forward-looking*. Stakes are deterministic
scenario analysis over the remaining schedule, computed every tick:

- bowl-eligibility countdown ("one win from bowl eligibility"; "a loss
  Saturday eliminates them"),
- playoff/division clinching and elimination conditions,
- ranked-matchup and rivalry implications ("winner controls the division"),
- record chases and milestones within reach ("two TDs from the school record"),
- the hot-seat line ("a loss drops him below the program baseline").

Each stake is emitted as a ready-to-quote string + a numeric weight feeding
the `stakes` signal. This is the highest-leverage immersion feature per line
of code in the design: "what Saturday means" is what real coverage leads with,
and it is pure arithmetic.

### 3.3 Surprise

```
elo_diff = R_home - R_away + HFA            # HFA ~= 55 Elo
p_home   = 1 / (1 + 10 ** (-elo_diff / 400))
surprise = -log2(p_of_actual_outcome)       # bits; additive across sub-events
```

Ratings update post-game with a margin-of-victory multiplier; rating shifts
feed `expectation_delta` and the program baselines.

### 3.4 Combine and select (seeded, deterministic)

```
# z-score normalize each signal across this week's pool, clip, map to [0,1]
# ONE representative per correlated cluster (never surprise AND is_upset)
base  = Σ w_i * norm(signal_i)
score = base * 2 ** (-age_weeks / HALF_LIFE)
```

Selection is **greedy + Maximal Marginal Relevance** (pick the top, penalize
near-duplicates of what is already chosen) with any tie-break jitter drawn
from the week seed. Same week, same save → same slate, always. MMR is the
structural fix for "three Cromwell-visit stories"; the seed is what keeps
beat IDs, cascade dedup keys, and re-scans stable.

Calibration: weights are tuned against hand-labeled "golden weeks" (section 9),
not vibes; normalization choice changes rankings, so it is validated there too.

---

## 4. The arc engine (continuity, rumors, memory)

### 4.1 The tick, in detail

```
refresh WorldState (incl. mood, stakes, promises_due)
update Expectation Model
detect candidates (phase-tagged)
score candidates (seeded)
for arc in active:    close_when(state)  -> resolved/expired (archive it)
for arc_type:         open_when(state)   -> open new arc
for arc in active:    update arc_qualities; resolve due claims; test due promises
emit beats:
    candidates -> one-off beats
    arcs       -> next_beat() where advance_when(state)   # tension-fit selection
    rumors     -> resolution beats (vindication / correction)
    promises   -> confrontation / trust beats
build rundown (budget by ModelProfile, MMR, ledger dedupe, evergreen floor)
assign day slots (the week timeline)
```

### 4.2 The rundown (editorial budget)

Slots are allocated within the model profile's wall-clock envelope, weighted
by what actually happened (rivalry week → more rivalry; signing day → more
recruiting). Per-surface *minimums* guarantee a whole universe even on the
slowest model (templates absorb the overflow): the lead story, 2+ program
articles, 2+ national articles, the presser questions, and any due
confrontation/resolution beats always ship.

### 4.3 Rumor lifecycle

1. An insider arc emits a `Claim` (the engine rolls its hidden `truth` against
   the reporter's credibility — good reporters are usually right).
2. The claim renders as insider-report + social beats, always attributed and
   hedged ("sources tell...", confidence shown as today).
3. Sim events eventually satisfy `resolve_when`; the engine fires a resolution
   beat: vindication ("as first reported by...") or correction/dunking.
4. The persona's credibility moves; future briefs inherit the new track record.

This makes reliability *visible over time*, which is what makes an insider
ecosystem feel real rather than decorative.

### 4.4 Promise tracking (conversation memory)

User outbound texts already pass through a classify step; it additionally
extracts candidate commitments with a verbatim span. Code keeps only
span-verified extractions, attaches them to the relevant arc/contact, and
tests them when `testable_when` fires (depth chart posted, NIL offer recorded,
visit week arrives). Honored → trust bump, warmer texts. Broken → a
confrontation beat and a colder recruit/player. The phone stops being a
one-shot text generator and becomes a relationship with memory.

### 4.5 The week timeline (diegetic time)

Every beat gets a `day_slot` so the feed reads like a week that unfolded, not
a single dump: Monday presser quotes, Wednesday injury/depth-chart notes and
features, Thursday recruiting items, Friday previews and predictions, Saturday
the game and its cascade, Sunday columns and poll reaction. Pure scheduling,
zero model cost, and it makes timestamps meaningful instead of cosmetic.

### 4.6 Catalog

**Candidates (one-off):** `upset, ranked_clash, blowout, rivalry_result,
comeback, poll_jump, poll_fall, new_number_one, streak_extended, streak_broken,
bowl_clinched, eliminated, record_set, milestone, commit, decommit, flip,
top_target_visit, portal_in, portal_out, injury, coach_fired, coach_hired,
award_threshold, user_action` (presser answers, NIL moves, text leaks — the
user's own choices are first-class news sources).

**Arcs (multi-week):** `hot_seat, playoff_push, rivalry_week (buildup →
result → aftermath), qb_battle, recruiting_battle, cinderella, collapse,
award_watch, win_streak/skid, revenge_game, portal_saga, rumor`.

**Evergreens (the off-week floor):** position-group features, player
spotlights, coordinator profiles, walk-on stories, historical retrospectives,
outlet power rankings (computed from Elo with per-outlet bias jitter),
player-of-the-week awards, mailbags. Gated by qualities + a "never ran this"
ledger check and drawn only when the rundown falls below its floor — bye weeks
get texture instead of silence or repetition.

**Debate takes:** when an arc is genuinely contested (fire/extend, start the
freshman, go for two), two personas with opposing committed `biases` each get
a `debate_take` beat on the same story. Disagreement between recognizable
voices is one of the strongest "this is a real media world" signals available.

---

## 5. Surfaces

All surfaces draw from the **same rundown**, so the slider, the feed, the
phone, and the presser never disagree about what the week's biggest story is.

- **News articles** — top beats per scope → article briefs. Closed cast list +
  claims machinery; marquee lead may escalate to the strongest available model.
- **Top stories** — the highest-scored beats rendered as slider cards from the
  same briefs; no separate generation pass.
- **Social feed** — per chosen story, a cascade sized by tier × profile
  `cascade_scale`: the breaking post (the persona who owns the story), media
  reaction, fan accounts (mood-mapped), debate takes. One call per post;
  ticker items and score lines are pure template.
- **Phone** — `text_message` beats from program arcs/candidates only. Framing
  comes from the arc (recruiting battle → the recruit; injury → the AD), tone
  from mood × relationship. Promises make threads remember. A hot-seat arc
  about the user's own coach never emits "are you leaving?" (the user IS the
  coach); its personal beats are support/pressure framing, and preseason
  speculation stays below the cascade bar. Replies brief = conversation so far
  + persona card + the relevant qualities; a reply can be a leak, which is a
  `user_action` candidate next tick.
- **Press conference** — questions are `press_question` beats from the top of
  the rundown: after an upset loss the room asks about the loss, the line that
  gave up six sacks, and the rival next week — not generic filler. Answers
  write back as on-the-record facts and possible candidates.
- **CFP committee** — stays a structured computation from ratings, gated to
  reveal week; its movement feeds `poll_*` candidates; a "committee debate"
  beat may fire once convened.
- **Hot seat** — board computed from ratings + program-relative baselines;
  stories come from `hot_seat` arcs and the rumor machinery.
- **Recruiting / portal** — boards read from canon; stories/texts from
  candidates and `recruiting_battle` arcs; positions/stars can only come from
  the canon.
- **Awards** — `award_watch` arcs over stat thresholds; preseason shows
  candidates, never invented stat lines.

---

## 6. Validation and write-back

### 6.1 Cast policies (no false rejections)

Naive "reject any name not in the brief" would also reject legitimate color
(a fictional analyst quote) — and on a slow model, regeneration loops are the
last thing the latency budget can afford. Cast entries carry a policy:

```
must_use        # the story is about them; absence is a failure
may_mention     # allowed, attributes must match canon
may_invent      # class-level license, e.g. "a fictional analyst may be quoted
                # BY NAME as long as the name collides with no canon entity"
```

### 6.2 The validation chain (deterministic first)

1. JSON envelope: constrained decode where the server supports it; else parse
   → `_repair_json` → one capped retry.
2. **Fact check:** extract numbers and proper nouns; every number must appear
   in `facts ∪ claims`; every name must satisfy a cast policy; claims must be
   attributed in the text (hedge phrases present).
3. Canon consistency for any mentioned attribute.
4. Structural guards (already shipped): self-matchup headlines, season-open
   scores, dashes, emojis.
5. Ledger dedupe.
6. Optional CoVe-lite on the lead story only (mid+ tiers): "list every name
   and number; is each in FACTS?"
7. On failure: regenerate the single item once → else **render its template**.
   The template path is always available because the brief contains everything
   needed (this is the same renderer that serves `tier == none`).

### 6.3 Write-back

Advance/close arcs; resolve claims and move persona credibility; record
promise outcomes; append to the ledger; refresh ratings; persist the rundown
log; archive resolved arcs as the season's story so far (which becomes the
dynasty archive's narrative spine and next year's preseason callbacks).

---

## 7. Running on any model

### 7.1 The tier ladder

| Tier | Realization behavior |
|---|---|
| **none** | Full universe from templates. Same stories, same stakes, same arcs — drier prose. |
| **nano (<4B)** | Template-adjacent realization ("restyle this draft, keep every number"), 4-6 fact briefs, small cascades, full validation. |
| **small (4-15B)** | Free prose from briefs, moderate cascades, debate takes. |
| **mid (local 30-70B)** | Richer briefs, larger cascades, CoVe-lite on the lead, editorial review pass. |
| **frontier (hosted)** | Everything above + full-color features; optional batching of trivial items; biggest social long tail. |

Two invariants across the ladder: **facts never degrade** (they are decided in
code) and **the rundown is identical** (selection is deterministic). The model
only changes how vividly the same true universe is narrated.

### 7.2 The editorial-review pass (mid+ tiers)

One bounded call that lets a capable model add taste without breaking
determinism: it sees the scored rundown and may (a) reorder within the top
band, (b) sharpen `angle` strings, (c) promote ONE candidate from just below
the cutoff. Code applies only those whitelisted changes. The deterministic
slate is the floor; editorial taste is the ceiling.

### 7.3 Progressive fill

Realization streams in priority order (lead → top stories → program → phone →
national → social tail), each beat cached as it lands, so the user opening the
app seconds after Scan sees the most important content first while the long
tail fills behind them. The existing single-flight and per-module locks remain
the concurrency guards.

---

## 8. Mapping onto the current code

New package `backend/editorial/`:

```
editorial/
  state.py        # WorldState extraction, mood, qualities
  canon.py        # Entity Canon build + lookups
  ratings.py      # Elo, baselines, win prob, surprisal
  stakes.py       # the Stakes Computer
  candidates.py   # detectors (catalog 4.6)
  scorer.py       # signals, normalization, MMR, seeding
  arcs.py         # arc types, registry, claims, promises
  rundown.py      # budget, timeline, evergreen floor
  briefs.py       # StoryBrief assembly, persona prefixes
  realize.py      # per-beat LLM calls + template renderer
  validate.py     # the chain in 6.2
  writeback.py    # ledger, personas, archive
```

| Today | Becomes |
|---|---|
| `base.build_context` (trimmed save dump) | `briefs.py` per-item packets |
| `base.flashpoints` / `national_brief` / `grounding_facts` | `state.py` + `stakes.py` + scorer output |
| `world._assess_story` | `scorer.py` |
| `world.react_to_coverage` / `_compose_llm` / `_react_inbound` | arc/beat engine emitting social + phone beats |
| `narrative` store | Continuity Ledger + Arc Registry |
| `world_events` | beat render log (role unchanged) |
| `customization` personas | Persona Cards (superset, user-editable as today) |
| per-module `generate()` | thin renderers over the rundown |
| `interview._ask_question` | `press_question` beats |
| `_mock()` functions per module | ONE template renderer over the same briefs |

The Simulator and the save boundary are untouched. When CFB 27 ships and the
real save replaces the Simulator, the engine doesn't change — richer save data
just means more candidates and better facts.

### What we deliberately do NOT do

- **No agent simulation of the media ecosystem** (LLM agents with goals):
  latency-prohibitive locally, non-deterministic, and the storylet pattern
  achieves the same surface behavior.
- **No embeddings / vector retrieval**: the state is structured; keyed lookups
  and the Callback Finder's deterministic queries are more precise and
  debuggable.
- **No fine-tuning requirement**: voice comes from persona exemplars; facts
  come from briefs. Works with any stock model the user connects.

---

## 9. Evals and telemetry

- **Golden weeks:** a small library of recorded saves with hand-labeled
  expectations ("this upset obviously leads", "bye week draws evergreens").
  CI replays them through steps 1-8 and asserts rundown stability and label
  agreement. This is how scorer weights get tuned, per the MCDA guidance.
- **Per-beat telemetry** (extends `data/llm.log`): brief size, latency,
  validation outcome, regen count, template fallbacks. Feeds the rolling
  `ModelProfile` and surfaces "your model is struggling, consider X" in the
  in-app LLM setup.
- **The rundown log** doubles as the dev view: every story shows its signals
  and score ("why did this run?"), which makes weight tuning and modding
  transparent.

---

## 10. Build plan (each step ships value)

1. **Foundations:** ModelProfile + budget; seeded selection; Elo/expectations;
   Stakes Computer; candidate detector + scorer feeding the EXISTING news
   prompts as grounding. (Pure code; biggest immediate quality jump.)
2. **Truth layer:** Entity Canon + cast policies + the validation chain +
   pre-formatted numbers rule.
3. **The rundown:** per-beat realization (progressive, concurrent, cached
   prefix), the unified template renderer (replaces per-module mocks), week
   timeline, MMR + ledger dedupe.
4. **Voices:** Persona Cards with exemplars; mood; debate takes; cascades
   driven by the rundown.
5. **Memory:** Arc Registry (hot_seat, recruiting_battle, playoff_push first);
   claims/rumor lifecycle; promise tracking; evergreen floor.
6. **Polish:** presser unification; editorial-review pass; CoVe-lite; golden
   weeks + telemetry tuning.

Step 1 is mostly a reorganization of logic that already exists
(`_assess_story`, `flashpoints`, `national_brief`) and closes the realism gap
fastest.
