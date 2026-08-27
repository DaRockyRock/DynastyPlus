# Editorial Engine — research sources

The design in `editorial-engine.md` is grounded in the work below. Grouped by the
three pillars, with the load-bearing sources first.

## A. Newsworthiness, surprise, and scoring

- **News values taxonomies** — Harcup & O'Neill, "What is News? News values
  revisited (again)" (2017): https://eprints.hud.ac.uk/id/eprint/27268/1/What%20is%20news.pdf
  · list: https://owenspencer-thomas.com/journalism/newsvalues/harcup-and-oneill-2016/
  · Galtung & Ruge factors: https://en.wikipedia.org/wiki/News_values
- **Surprisal / self-information** (the upset measure, `-log2 p`):
  https://en.wikipedia.org/wiki/Information_content ·
  https://en.wikipedia.org/wiki/Entropy_(information_theory)
- **Elo win probability + margin-of-victory update** (FiveThirtyEight NFL model code,
  K=20, HFA=65, MOV multiplier):
  https://github.com/fivethirtyeight/nfl-elo-game/blob/master/forecast.py ·
  https://en.wikipedia.org/wiki/Elo_rating_system
- **Power ratings -> spread -> win prob** (SP+ concept; spread to probability,
  sigma ~= 13.5 CFB): https://thepowerrank.com/guide-cfb-rankings/ ·
  https://blog.collegefootballdata.com/talking-tech-elo-ratings/ ·
  https://arxiv.org/pdf/2212.08116
- **Multi-criteria scoring** — normalization choice matters:
  https://link.springer.com/chapter/10.1007/978-3-319-31165-4_26 · weights as
  trade-off ratios: https://www.1000minds.com/decision-making/what-is-mcdm-mcda ·
  softmax temperature: https://medium.com/@harshit158/softmax-temperature-5492e4007f71
  · exponential recency decay: https://arxiv.org/pdf/2008.11432

## B. Narrative / storyline engines

- **Quality-Based vs Salience-Based Narrative** (Emily Short) — qualities +
  storylets, salience selection:
  https://emshort.blog/2016/04/12/beyond-branching-quality-based-and-salience-based-narrative-structures/
- **Storylets design space** (Kreminski & Wardrip-Fruin, ICIDS 2018) — content +
  precondition + state-change; four design dimensions:
  https://mkremins.github.io/publications/Storylets_SketchingAMap.pdf
- **Facade beats + drama manager** (Mateas & Stern) — beat = preconditions, weights,
  priorities, story-value/tension effects; select beat whose tension fits the arc:
  https://users.soe.ucsc.edu/~michaelm/publications/mateas-tidse2003.pdf
- **Declarative Optimization-Based Drama Management** (Nelson et al.) — score
  trajectories against an author objective; causer/denier/hint actions:
  https://eis.ucsc.edu/papers/Nelson_etal_-_DODM_-_IEEE-CGA06.pdf
- **OOTP storyline engine** (two-engine split; storyline = condition set + ordered
  articles + effects, authored as data; eligibility + significance gates):
  https://en.wikipedia.org/wiki/Out_of_the_Park_Baseball ·
  https://github.com/jfox015/OOTP-Storylines
- **Job-security / directive objects** — FM Confidence:
  https://www.fmscout.com/confidence.htm · NBA 2K MyGM directives:
  https://nba.2k.com/2k26/courtside-report/mynba/ · CFB program-relative
  expectations: https://www.ea.com/games/ea-sports-college-football/college-football-27/news/college-football-27-dynasty

## C. Small-LLM grounded generation

- **Lost in the Middle** (U-shaped position bias; shorter context = higher accuracy)
  — Liu et al., TACL 2024: https://arxiv.org/abs/2307.03172
- **Plan-then-write / content selection + planning** (data-to-text faithfulness) —
  Puduppully et al. 2018: https://ar5iv.labs.arxiv.org/html/1809.00582 ·
  Step-by-Step (symbolic planner is provably faithful), Moryossef et al. 2019:
  https://ar5iv.labs.arxiv.org/html/1904.03396
- **Constrain the envelope, not the prose** — GBNF grammars:
  https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md · "Let Me
  Speak Freely?" (JSON-mode constraint degrades reasoning), Tam et al. EMNLP 2024:
  https://arxiv.org/html/2408.02442v1
- **Faithfulness / hallucination mitigation** — RotoWire fact-grounding:
  https://aclanthology.org/W19-8639/ · NLG hallucination survey:
  https://arxiv.org/html/2202.03629v6 · Chain-of-Verification (decoupled fact
  check), Dhuliawala et al. 2023: https://arxiv.org/abs/2309.11495
- **Per-item over batched for small models** (batching drops accuracy, worst on small
  models) — BatchPrompt, ICLR 2024: https://arxiv.org/html/2309.00384v3
- **Robust JSON repair** — json_repair: https://github.com/mangiucugna/json_repair
- **Template + LLM hybrid** ("fact pack -> prose", template high-stakes lines):
  https://arxiv.org/html/2512.05498v1
