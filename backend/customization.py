"""Media-flavor customization store (owned by the Dynasty+ companion).

Reporters and outlets, recruiting analysts, award voters, the awards tracked,
the CFP committee, the hot-seat board and candidate pool, and the phone
contacts. This is the media-presentation layer the generation modules read
directly; it is never touched by the simulation. The game-data layer (team,
roster, recruits, portal) lives in customization_game.py, owned by the
Simulator and read from the dynasty save file.

Persisted to data/customization.json; a save here invalidates the current
week's module cache so edits show up immediately. Shares all machinery with the
game store via customization_base.Store.
"""
from __future__ import annotations

from typing import Any

from . import config, personality, roster_gen
from .customization_base import (
    BEAT_OPTS, CATEGORY_OPTS, ENTITY_OPTS, TREND_OPTS, Store, field as _f,
)
# Re-exported so existing consumers keep working (phone/inbound reference these).
from .customization_base import (  # noqa: F401
    CLASS_YEARS, CONTACT_CATEGORIES, DEALBREAKERS, ENTITY_KINDS, RECRUIT_STAGES,
    BEATS, TRENDS,
)

_STORE_FILE = config.DATA_DIR / "customization.json"

# =========================================================================
# DEFAULTS - canonical seed data for the media universe.
# =========================================================================
DEFAULTS: dict[str, Any] = {
    # ---- Media: organizations (national + Nebraska local) ----
    "media_orgs_national": [
        {"name": "ESPN", "voice": "the national flagship; sets the weekly agenda", "reliability": 90},
        {"name": "The Athletic", "voice": "subscription longform, deeply sourced and measured", "reliability": 88},
        {"name": "FOX Sports", "voice": "Big Noon broadcast tentpole, big-game framing", "reliability": 84},
        {"name": "Yahoo Sports", "voice": "veteran national columns and reporting", "reliability": 82},
        {"name": "On3", "voice": "recruiting and NIL focused, fast and modern", "reliability": 80},
        {"name": "247Sports", "voice": "recruiting rankings and a team-site network", "reliability": 80},
        {"name": "Rivals", "voice": "recruiting rankings and an insider network", "reliability": 79},
        {"name": "Action Network", "voice": "betting angles and coaching-carousel scoops", "reliability": 78},
    ],
    "media_orgs_local": [
        {"name": "Omaha World-Herald", "voice": "Nebraska's paper of record on the Husker beat", "reliability": 86},
        {"name": "Lincoln Journal Star", "voice": "Lincoln's daily, closest to the program day to day", "reliability": 85},
        {"name": "Huskers Radio Network", "voice": "the official radio home; fan-facing on Sports Nightly", "reliability": 80},
        {"name": "HuskerOnline", "voice": "On3 subscription recruiting and insider site", "reliability": 79},
        {"name": "Corn Nation", "voice": "SB Nation fan blog, opinionated and loyal", "reliability": 70},
        {"name": "Hurrdat Sports", "voice": "local digital media and Husker podcasts", "reliability": 68},
    ],

    # ---- Media: members (real people; bios factual, sliders are simulated) ----
    "reporters": [
        {"name": "Pete Thamel", "outlet": "ESPN", "scope": "national", "beat": "carousel", "reliability": 92, "image": "",
         "bio": "Pete Thamel is ESPN's lead college football insider, a relentless breaker of coaching-carousel and transfer news with a deep web of sources built across Sports Illustrated and Yahoo. When a job opens or a star hits the portal, his phone usually buzzes first.",
         "traits": {"confidence": 80, "competitiveness": 92, "loyalty": 55, "composure": 78, "charisma": 60, "ambition": 88, "ego": 58}},
        {"name": "Heather Dinich", "outlet": "ESPN", "scope": "national", "beat": "national", "reliability": 88, "image": "",
         "bio": "Heather Dinich is ESPN's College Football Playoff reporter, the network's go-to voice on the committee, the bracket math, and the politics of the selection room. Measured and deeply sourced, she explains the why behind the rankings as well as anyone in the sport.",
         "traits": {"confidence": 70, "competitiveness": 72, "loyalty": 62, "composure": 88, "charisma": 64, "ambition": 70, "ego": 45}},
        {"name": "Bruce Feldman", "outlet": "FOX Sports", "scope": "national", "beat": "national", "reliability": 89, "image": "",
         "bio": "Bruce Feldman is a veteran national reporter and author at FOX Sports and The Athletic, known for his Freaks List, his coach relationships, and reliable scoops. He pairs strong sourcing with a genuine feel for scheme and roster building.",
         "traits": {"confidence": 74, "competitiveness": 80, "loyalty": 68, "composure": 80, "charisma": 70, "ambition": 76, "ego": 50}},
        {"name": "Brett McMurphy", "outlet": "Action Network", "scope": "national", "beat": "carousel", "reliability": 84, "image": "",
         "bio": "Brett McMurphy is a coaching-carousel scoop machine at the Action Network, famous for breaking hires and firings, often with his trademark restaurant-receipt sourcing. Aggressive and well-connected, he lives for the silly season.",
         "traits": {"confidence": 82, "competitiveness": 90, "loyalty": 48, "composure": 70, "charisma": 55, "ambition": 85, "ego": 66}},
        {"name": "Paul Finebaum", "outlet": "ESPN", "scope": "national", "beat": "national", "reliability": 72, "image": "",
         "bio": "Paul Finebaum is the most polarizing voice in college football, the radio and TV provocateur whose SEC-tinted takes set the daily conversation. Equal parts lightning rod and ratings magnet, he says what others will not and rarely backs down.",
         "traits": {"confidence": 90, "competitiveness": 75, "loyalty": 40, "composure": 72, "charisma": 85, "ambition": 78, "ego": 88}},
        {"name": "Tom Shatel", "outlet": "Omaha World-Herald", "scope": "local", "beat": "program", "reliability": 84, "image": "",
         "bio": "Tom Shatel is the longtime lead sports columnist for the Omaha World-Herald, a fixture on the Nebraska beat for decades. He writes with perspective and institutional memory, balancing fan passion with the long view of the program's ups and downs.",
         "traits": {"confidence": 70, "competitiveness": 60, "loyalty": 78, "composure": 85, "charisma": 72, "ambition": 50, "ego": 45}},
        {"name": "Sam McKewon", "outlet": "Omaha World-Herald", "scope": "local", "beat": "program", "reliability": 85, "image": "",
         "bio": "Sam McKewon covers Nebraska football for the Omaha World-Herald, blending heavy film study and analytics with a willingness to call it straight. He is among the most plugged-in and prolific voices on the Husker beat.",
         "traits": {"confidence": 74, "competitiveness": 70, "loyalty": 70, "composure": 75, "charisma": 60, "ambition": 62, "ego": 50}},
        {"name": "Parker Gabriel", "outlet": "Lincoln Journal Star", "scope": "local", "beat": "program", "reliability": 82, "image": "",
         "bio": "Parker Gabriel covers Nebraska football for the Lincoln Journal Star, the diligent daily beat writer closest to the program's practices, press conferences, and locker room. Fair and thorough, he reports the day to day that fans live on.",
         "traits": {"confidence": 60, "competitiveness": 64, "loyalty": 66, "composure": 80, "charisma": 58, "ambition": 66, "ego": 38}},
        {"name": "Brett Vanderslice", "outlet": "Huskers Radio Network", "scope": "local", "beat": "program", "reliability": 76, "image": "",
         "bio": "Brett Vanderslice is the sideline reporter and weekday host on the Huskers Radio Network, the fan-facing voice closest to the coaches on game day. He trades in access and atmosphere more than scoops, and his questions tend to come from the heart of the fan base.",
         "traits": {"confidence": 66, "competitiveness": 58, "loyalty": 82, "composure": 74, "charisma": 78, "ambition": 54, "ego": 44}},
        {"name": "Owen Hatcher", "outlet": "HuskerOnline", "scope": "local", "beat": "program", "reliability": 80, "image": "",
         "bio": "Owen Hatcher is the lead insider at HuskerOnline, the subscription site that lives on practice notes, depth-chart movement, and recruiting intel. Plugged in around the program day to day, he presses for specifics and reads the locker room.",
         "traits": {"confidence": 72, "competitiveness": 74, "loyalty": 62, "composure": 70, "charisma": 60, "ambition": 72, "ego": 48}},
    ],
    "recruiting_analysts": [
        {"name": "Steve Wiltfong", "outlet": "On3", "lean": "trusts his crystal-ball record and late-cycle momentum",
         "bio": "Steve Wiltfong is On3's director of recruiting prediction, the industry's most-watched crystal-ball voice after years at 247Sports. When Wiltfong logs a pick, programs and fans pay attention.",
         "traits": {"confidence": 78, "competitiveness": 80, "loyalty": 50, "composure": 78, "charisma": 64, "ambition": 78, "ego": 55}},
        {"name": "Adam Gorney", "outlet": "Rivals", "lean": "film-first, trusts the evaluation over the hype",
         "bio": "Adam Gorney is the national recruiting director at Rivals, a veteran evaluator who has ranked classes for over a decade. He leans on film and projection more than the week-to-week buzz.",
         "traits": {"confidence": 70, "competitiveness": 65, "loyalty": 55, "composure": 80, "charisma": 58, "ambition": 66, "ego": 45}},
        {"name": "Tom Loy", "outlet": "247Sports", "lean": "plugged into Southern pipelines and final-visit timing",
         "bio": "Tom Loy is a national recruiting analyst at 247Sports, well-sourced across the Southern pipelines and known for reading final-visit timing and commitment swings.",
         "traits": {"confidence": 74, "competitiveness": 78, "loyalty": 52, "composure": 72, "charisma": 66, "ambition": 74, "ego": 52}},
    ],
    "award_voters": [
        {"name": "Pat Forde", "outlet": "Yahoo Sports", "lean": "rewards the season-long narrative and the biggest moments",
         "bio": "Pat Forde is a longtime national columnist at Yahoo Sports and a Heisman and AP voter, known for sharp, opinionated columns and a strong sense of the sport's history and storylines.",
         "traits": {"confidence": 76, "competitiveness": 65, "loyalty": 55, "composure": 80, "charisma": 70, "ambition": 64, "ego": 52}},
        {"name": "Stewart Mandel", "outlet": "The Athletic", "lean": "follows the resume and the advanced metrics over reputation",
         "bio": "Stewart Mandel is the editor-in-chief of The Athletic's college football coverage and a longtime national voice, famous for his weekly mailbag and even-handed, big-picture analysis.",
         "traits": {"confidence": 72, "competitiveness": 60, "loyalty": 58, "composure": 85, "charisma": 66, "ambition": 70, "ego": 48}},
        {"name": "Bruce Feldman", "outlet": "FOX Sports", "lean": "trusts the eye test and the people inside the building",
         "bio": "Bruce Feldman doubles as an awards voter, leaning on his coach sources and tape study to separate the contenders from the narratives.",
         "traits": {"confidence": 74, "competitiveness": 80, "loyalty": 68, "composure": 80, "charisma": 70, "ambition": 76, "ego": 50}},
    ],

    # ---- Feed: national online personalities (real people; fixed personas) ----
    # The pundit / talking-head / very-online tier that lives on the social feed,
    # distinct from the byline reporters above. Same every time, fully editable.
    "online_personalities": [
        {"name": "Joel Klatt", "handle": "joelklatt", "outlet": "FOX Sports", "scope": "national", "image": "",
         "lean": "FOX's lead college football analyst. Film-first, confident, big-game framing. Posts measured but strong takes, often with a coach's-eye breakdown, and stands behind them.",
         "bio": "Joel Klatt is FOX Sports' lead college football analyst and a former Colorado quarterback, known for sharp, scheme-literate analysis and a willingness to plant a flag on his rankings and playoff takes.",
         "traits": {"confidence": 82, "competitiveness": 74, "loyalty": 58, "composure": 80, "charisma": 78, "ambition": 76, "ego": 60}},
        {"name": "Kirk Herbstreit", "handle": "KirkHerbstreit", "outlet": "ESPN", "scope": "national", "image": "",
         "lean": "ESPN GameDay's voice of the sport. Measured, respected, balanced; rarely inflammatory. Posts thoughtful reactions and praise, and pushes back gently on overreactions.",
         "bio": "Kirk Herbstreit is the longtime voice of ESPN College GameDay and the network's lead game analyst, a former Ohio State quarterback whose even-handed takes carry weight across the sport.",
         "traits": {"confidence": 74, "competitiveness": 66, "loyalty": 70, "composure": 88, "charisma": 84, "ambition": 64, "ego": 42}},
        {"name": "Josh Pate", "handle": "LateKickJosh", "outlet": "Late Kick", "scope": "national", "image": "",
         "lean": "Very-online pundit and podcaster. Narrative-driven, optimistic-contrarian, leans into storylines and fan psychology. Posts in threads and engages replies constantly.",
         "bio": "Josh Pate hosts Late Kick, a hugely popular college football show built on big-picture narratives, program psychology and a direct line to a passionate online audience.",
         "traits": {"confidence": 80, "competitiveness": 70, "loyalty": 60, "composure": 74, "charisma": 86, "ambition": 82, "ego": 58}},
        {"name": "RJ Young", "handle": "RJ_Young", "outlet": "FOX Sports", "scope": "national", "image": "",
         "lean": "FOX national pundit. Opinionated, energetic, culturally fluent. Posts bold takes and reactions, willing to mix in the human and cultural angle of the sport.",
         "bio": "RJ Young is a FOX Sports national college football analyst and author, an energetic voice who blends bold on-field takes with the broader culture of the game.",
         "traits": {"confidence": 78, "competitiveness": 68, "loyalty": 56, "composure": 72, "charisma": 82, "ambition": 78, "ego": 56}},
        {"name": "David Pollack", "handle": "davidpollack47", "outlet": "See Ball Get Ball", "scope": "national", "image": "",
         "lean": "Blunt, defensive-minded former analyst. Posts unfiltered, high-energy takes; values toughness and the trenches and is not afraid to call a team soft.",
         "bio": "David Pollack is a former Georgia All-American edge rusher and longtime national analyst, an outspoken, defense-first voice who prizes physicality and rarely softens his opinions.",
         "traits": {"confidence": 86, "competitiveness": 88, "loyalty": 62, "composure": 64, "charisma": 74, "ambition": 70, "ego": 66}},
        {"name": "Greg McElroy", "handle": "GregMcElroyESPN", "outlet": "ESPN", "scope": "national", "image": "",
         "lean": "ESPN/SEC Network analyst. QB-centric and detail-oriented. Posts careful, well-reasoned breakdowns and avoids hot-take baiting.",
         "bio": "Greg McElroy is an ESPN analyst and former national champion quarterback at Alabama, known for detailed, quarterback-focused analysis delivered with preparation and care.",
         "traits": {"confidence": 72, "competitiveness": 70, "loyalty": 66, "composure": 82, "charisma": 70, "ambition": 68, "ego": 40}},
        {"name": "Cole Cubelic", "handle": "colecubelic", "outlet": "SEC Network", "scope": "national", "image": "",
         "lean": "SEC Network sideline and studio voice, a former lineman who lives in the trenches. High-energy, fan-engaging, loves the line of scrimmage and a good rivalry.",
         "bio": "Cole Cubelic is an SEC Network analyst and former Auburn center, an energetic, plugged-in voice who champions offensive line play and trades constantly with fans online.",
         "traits": {"confidence": 78, "competitiveness": 80, "loyalty": 64, "composure": 70, "charisma": 84, "ambition": 72, "ego": 54}},
    ],

    # ---- Feed: brand / network accounts (outlets, not people; no personas) ----
    "brand_accounts": [
        {"name": "ESPN College Football", "handle": "ESPNCFB", "image": "",
         "voice": "The national flagship account. Score alerts, milestone callouts, highlight framing, top-25 reveals, and the occasional engagement-bait question. Sets the weekly agenda."},
        {"name": "CFB on FOX", "handle": "CFBONFOX", "image": "",
         "voice": "Big Noon broadcast energy. Bold, punchy posts that frame the biggest games of the week, lean into spectacle and trumpet marquee matchups."},
        {"name": "On3", "handle": "On3sports", "image": "",
         "voice": "Recruiting and NIL focused, fast and modern. Posts commitments, rankings movement, portal news and money angles the moment they break."},
        {"name": "247Sports", "handle": "247Sports", "image": "",
         "voice": "Recruiting rankings and a team-site network. Posts commitment news, class rankings, crystal-ball updates and prospect rankings."},
        {"name": "Bleacher Report CFB", "handle": "BR_CFB", "image": "",
         "voice": "Meme-savvy and engagement-first. Posts highlight framing, list-bait, polls and playful reactions built to be shared and argued about."},
        {"name": "The Athletic CFB", "handle": "TheAthleticCFB", "image": "",
         "voice": "Subscription longform, measured and deeply sourced. Posts story teasers, reported nuggets and thoughtful analysis with restraint."},
        {"name": "CBS Sports CFB", "handle": "CBSSportsCFB", "image": "",
         "voice": "National coverage and rankings. Posts results, poll reactions, bowl and playoff projections in a straightforward news voice."},
    ],

    # ---- Phone ----
    "phone_contacts": [
        {"id": "five_star_target", "name": "Cam Brooks-Lee", "role": "5-star WR target", "avatar": "CB",
         "category": "Recruits", "time": "9:41 AM", "preview": "appreciate the love coach, big visit this weekend",
         "personality": "Confident, loyalty matters, wants to be the guy. Texts in short bursts. Cares about NIL and brand.",
         "status": "Official visit this weekend", "image": "",
         "entity": {"kind": "recruit", "name": "Cam Brooks-Lee"}},
        {"id": "recruit_s", "name": "Antoine Devereaux", "role": "4-star S target", "avatar": "AD",
         "category": "Recruits", "time": "Yesterday", "preview": "took my official to Oregon last weekend, still deciding",
         "personality": "Measured, polite, plays it close to the vest, asks thoughtful questions about development.",
         "status": "Weighing his options", "image": "",
         "entity": {"kind": "recruit", "name": "Antoine Devereaux"}},
        {"id": "oc", "name": "Coach Salomone", "role": "Offensive Coordinator", "avatar": "RS",
         "category": "Staff", "time": "8:12 AM", "preview": "tempo plan is dialed for Saturday. we push the pace early.",
         "personality": "Intense, football-obsessed, clipped sentences, always thinking about the next opponent.",
         "status": "Game-planning", "image": "",
         "entity": {"kind": "staff", "name": ""}},
        {"id": "dc", "name": "Coach Brantley", "role": "Defensive Coordinator", "avatar": "TB",
         "category": "Staff", "time": "Mon", "preview": "edge pressure package is ready. front seven is locked in.",
         "personality": "Gruff, confident, talks in football absolutes, loves his front seven.",
         "status": "Watching film", "image": "",
         "entity": {"kind": "staff", "name": ""}},
        {"id": "ad", "name": "Athletic Director", "role": "Athletic Director", "avatar": "AD",
         "category": "Staff", "time": "Sun", "preview": "the trajectory speaks for itself. lets keep building.",
         "personality": "Diplomatic, big-picture, talks Dynasty Points, budgets and expectations, measured.",
         "status": "In meetings", "image": "",
         "entity": {"kind": "budget", "name": ""}},
        {"id": "star_qb", "name": roster_gen.STAR_QB_NAME, "role": "Starting QB", "avatar": roster_gen.STAR_QB_AVATAR,
         "category": "Players", "time": "7:55 AM", "preview": "all good coach. just focused on the game plan.",
         "personality": "Humble team-first leader, deflects credit, quietly competitive.",
         "status": "Locked in for Saturday", "image": "",
         "entity": {"kind": "player", "name": roster_gen.STAR_QB_NAME}},
        {"id": "rb", "name": roster_gen.STAR_RB_NAME, "role": "Running Back", "avatar": roster_gen.STAR_RB_AVATAR,
         "category": "Players", "time": "Yesterday", "preview": "feeling fresh coach, give me the rock",
         "personality": "High-energy, hungry for carries, playful but driven.",
         "status": "Leads the Big Ten in rushing", "image": "",
         "entity": {"kind": "player", "name": roster_gen.STAR_RB_NAME}},
        {"id": "insider", "name": "Priya Anand", "role": "Carousel insider", "avatar": "PA",
         "category": "Media", "outlet": "Coaching Confidential", "media_scope": "National", "media_type": "personality",
         "time": "10:20 AM", "preview": "hearing things on that job we talked about...",
         "personality": "Cagey, hints at scoops, never fully confirms, fishes for info in return.",
         "status": "Working the phones", "image": "",
         "entity": {"kind": "none", "name": ""}},
        {"id": "beat_writer", "name": "Jenna Whitlock", "role": "Beat writer", "avatar": "JW",
         "category": "Media", "outlet": "Cornhusker Insider", "media_scope": "Local", "media_type": "writer",
         "time": "Tue", "preview": "quick one for the story before deadline?",
         "personality": "Friendly but probing, wants quotes, fair but persistent.",
         "status": "On deadline", "image": "",
         "entity": {"kind": "none", "name": ""}},
    ],

    # ---- Committee ----
    "cfp_committee": [
        {"name": "Hunter Yurachek", "role": "Committee Chair - AD, Arkansas", "affiliation": "SEC", "conference": "SEC",
         "bio": "Arkansas' director of athletics since 2017 and the committee chair, with prior AD stops at Houston and Coastal Carolina.",
         "lens": "As chair, drives the room toward consensus and leans on head-to-head results and quality wins.", "image": ""},
        {"name": "Chris Ault", "role": "Hall of Fame coach, Nevada", "affiliation": "Mountain West", "conference": "Mountain West",
         "bio": "College Football Hall of Fame coach who built Nevada over three stints and invented the Pistol offense; also served as the Wolf Pack's AD.",
         "lens": "An offensive innovator who trusts the eye test and rewards explosive, well-coached teams.", "image": ""},
        {"name": "Troy Dannen", "role": "AD, Nebraska", "affiliation": "Big Ten", "conference": "Big Ten",
         "bio": "Nebraska's athletic director, with prior AD tenures at Washington, Tulane and Northern Iowa across several conferences.",
         "lens": "Weighs strength of schedule and how a team is trending into November.", "image": ""},
        {"name": "Mark Dantonio", "role": "Former HC, Michigan State", "affiliation": "Big Ten", "conference": "Big Ten",
         "bio": "The winningest coach in Michigan State history with three Big Ten titles and a Rose Bowl win; previously head coach at Cincinnati.",
         "lens": "A defensive-minded coach who values physical teams that win the line of scrimmage.", "image": ""},
        {"name": "Mark Harlan", "role": "AD, Utah", "affiliation": "Big 12", "conference": "Big 12",
         "bio": "Utah's athletic director, who joined the committee mid-cycle; previously AD at South Florida and a longtime UCLA administrator.",
         "lens": "Watches the West closely and rewards teams that win true road games.", "image": ""},
        {"name": "Jeff Long", "role": "Former CFP Committee Chair", "affiliation": "Former Chair", "conference": "",
         "bio": "The inaugural chair of the CFP selection committee, with a long career as an AD at Arkansas, Kansas and Pittsburgh.",
         "lens": "Process-driven and a stickler for resume over reputation.", "image": ""},
        {"name": "Ivan Maisel", "role": "Veteran national writer", "affiliation": "Media", "conference": "",
         "bio": "An award-winning college football writer and author with decades covering the sport for national outlets.",
         "lens": "Values the season-long body of work and the way a season is remembered.", "image": ""},
        {"name": "Chris Massaro", "role": "AD, Middle Tennessee", "affiliation": "Conference USA", "conference": "Conference USA",
         "bio": "Middle Tennessee's long-tenured athletic director and a steady advocate for Group of Five programs.",
         "lens": "Makes sure non-power resumes get a fair hearing in the room.", "image": ""},
        {"name": "Mike Riley", "role": "Former HC, Oregon State & Nebraska", "affiliation": "Pac-12", "conference": "Pac-12",
         "bio": "A veteran head coach at Oregon State and Nebraska with NFL experience, known for developing quarterbacks and balanced offenses.",
         "lens": "A players-first coach who rewards balance and complementary football.", "image": ""},
        {"name": "David Sayler", "role": "AD, Miami (Ohio)", "affiliation": "MAC", "conference": "MAC",
         "bio": "Athletic director at Miami (Ohio), bringing a Mid-American Conference perspective to the committee.",
         "lens": "Attentive to scheduling context and how teams control games.", "image": ""},
        {"name": "Wesley Walls", "role": "Former NFL TE, Ole Miss", "affiliation": "SEC", "conference": "SEC",
         "bio": "A five-time Pro Bowl tight end who starred at Ole Miss before a long NFL career, representing the player's viewpoint.",
         "lens": "Rewards NFL-caliber rosters and trench play on both lines.", "image": ""},
        {"name": "Carla Williams", "role": "AD, Virginia", "affiliation": "ACC", "conference": "ACC",
         "bio": "Virginia's athletic director and the first Black woman to lead a Power conference athletic department; a former player and administrator at Georgia.",
         "lens": "Detail-oriented and prizes head-to-head results and strength of record.", "image": ""},
    ],

    # ---- Hot seat ----
    "hot_seat_coaches": [
        {"coach": "Lane Whitmore", "team": "Florida Gators", "record": "6-3", "heat": 88, "trend": "up",
         "note": "Third straight November fade has the donors restless.", "image": ""},
        {"coach": "Greg Tannehill", "team": "USC Trojans", "record": "7-2", "heat": 71, "trend": "up",
         "note": "Defense keeps the seat warm despite a strong offense.", "image": ""},
        {"coach": "Marty Cobb", "team": "Michigan State Spartans", "record": "5-4", "heat": 79, "trend": "flat",
         "note": "Buyout drops sharply in January, a likely move.", "image": ""},
        {"coach": "Dirk Vandersloot", "team": "Maryland Terrapins", "record": "6-3", "heat": 54, "trend": "down",
         "note": "Bowl eligibility cooled an early-season firestorm.", "image": ""},
        {"coach": "Hank Russo", "team": "Rutgers Scarlet Knights", "record": "4-5", "heat": 62, "trend": "up",
         "note": "Needs two wins to save the job.", "image": ""},
    ],
    "candidates": [
        {"name": "Ricky Salomone", "current": "Nebraska OC", "archetype": "Riser coordinator", "fit": 92,
         "why": "Top-15 scoring offense, recruits the region, ready for a CEO job.", "image": ""},
        {"name": "Tobias Frame", "current": "Group of Five HC", "archetype": "Proven G5 winner", "fit": 88,
         "why": "Back-to-back conference titles and an elite portal-evaluation track record.", "image": ""},
        {"name": "Coach Del Marsh", "current": "NFL position coach", "archetype": "NFL retread", "fit": 74,
         "why": "Pro pedigree and player development, but unproven as a recruiter.", "image": ""},
        {"name": "Eddie Province", "current": "Power Four DC", "archetype": "Defensive architect", "fit": 81,
         "why": "Elite defenses everywhere he goes; needs the right offensive hire.", "image": ""},
        {"name": "Sam Whitlow", "current": "Hot mid-major HC", "archetype": "Offensive innovator", "fit": 85,
         "why": "Tempo system travels, and his quarterbacks keep going pro.", "image": ""},
    ],

    # ---- Awards ----
    "awards": [
        {"key": "heisman", "name": "Heisman Trophy", "criteria": "Most outstanding player", "position": ""},
        {"key": "biletnikoff", "name": "Biletnikoff Award", "criteria": "Best receiver", "position": "WR"},
        {"key": "butkus", "name": "Butkus Award", "criteria": "Best linebacker", "position": "LB"},
        {"key": "outland", "name": "Outland Trophy", "criteria": "Best interior lineman", "position": "OT"},
        {"key": "bednarik", "name": "Bednarik Award", "criteria": "Best defensive player", "position": "EDGE"},
    ],
}

# =========================================================================
# SCHEMA - editor description for the media sections.
# =========================================================================
SCHEMA: list[dict[str, Any]] = [
    # ---------------- Media organizations (national + local tabs) ----------------
    {
        "key": "media_orgs_national", "label": "National Media", "group": "Organizations", "icon": "newspaper",
        "blurb": "National outlets and networks that set the weekly agenda.",
        "kind": "list", "item_kind": "Outlet", "title_field": "name", "subtitle_field": "voice",
        "fields": [
            _f("name", "Outlet name", "text", width="full"),
            _f("voice", "House voice", "textarea", width="full", help="How this outlet writes and what it cares about."),
            _f("reliability", "Reliability", "percent", width="half"),
        ],
    },
    {
        "key": "media_orgs_local", "label": "Local Media", "group": "Organizations", "icon": "newspaper",
        "blurb": "The local Nebraska outlets closest to the program.",
        "kind": "list", "item_kind": "Outlet", "title_field": "name", "subtitle_field": "voice",
        "fields": [
            _f("name", "Outlet name", "text", width="full"),
            _f("voice", "House voice", "textarea", width="full", help="How this outlet writes and what it cares about."),
            _f("reliability", "Reliability", "percent", width="half"),
        ],
    },
    {
        "key": "reporters", "label": "Media Members", "group": "Media", "icon": "mic",
        "blurb": "The reporters and personalities behind the bylines, national and local.",
        "kind": "list", "item_kind": "Media Member", "title_field": "name", "subtitle_field": "outlet", "image_field": "image",
        "fields": [
            _f("image", "Photo", "image", width="full"),
            _f("name", "Name", "text", width="half"),
            _f("outlet", "Outlet", "text", width="half"),
            _f("scope", "Scope", "select", width="half", options=[{"value": "national", "label": "National"}, {"value": "local", "label": "Local"}]),
            _f("beat", "Beat", "select", width="half", options=BEAT_OPTS),
            _f("reliability", "Reliability", "percent", width="half"),
        ],
    },
    {
        "key": "recruiting_analysts", "label": "Recruiting Analysts", "group": "Media", "icon": "binoculars",
        "blurb": "The voices on the recruiting board.",
        "kind": "list", "item_kind": "Analyst", "title_field": "name", "subtitle_field": "outlet",
        "fields": [
            _f("name", "Name", "text", width="half"),
            _f("outlet", "Outlet", "text", width="half"),
            _f("lean", "Lean", "textarea", width="full", help="How this analyst evaluates prospects."),
        ],
    },
    {
        "key": "award_voters", "label": "Award Voters", "group": "Media", "icon": "ballot",
        "blurb": "The panel that votes on the Heisman and position awards.",
        "kind": "list", "item_kind": "Voter", "title_field": "name", "subtitle_field": "outlet",
        "fields": [
            _f("name", "Name", "text", width="half"),
            _f("outlet", "Outlet", "text", width="half"),
            _f("lean", "Lean", "textarea", width="full"),
        ],
    },

    # ---------------- Feed accounts ----------------
    {
        "key": "online_personalities", "label": "Online Personalities", "group": "Feed", "icon": "mic",
        "blurb": "National pundits and TV/online voices who post on the social feed.",
        "kind": "list", "item_kind": "Personality", "title_field": "name", "subtitle_field": "outlet", "image_field": "image",
        "fields": [
            _f("image", "Photo", "image", width="full"),
            _f("name", "Name", "text", width="half"),
            _f("handle", "Handle", "text", width="half", placeholder="joelklatt", help="The @ name, without the @."),
            _f("outlet", "Outlet", "text", width="half"),
            _f("scope", "Scope", "select", width="half", options=[{"value": "national", "label": "National"}, {"value": "local", "label": "Local"}]),
            _f("lean", "Posting style", "textarea", width="full", help="How this personality posts and what they care about."),
        ],
    },
    {
        "key": "brand_accounts", "label": "Brand Accounts", "group": "Feed", "icon": "newspaper",
        "blurb": "Network and outlet accounts (ESPN, FOX, On3) that post on the feed.",
        "kind": "list", "item_kind": "Brand", "title_field": "name", "subtitle_field": "handle", "image_field": "image",
        "fields": [
            _f("image", "Logo", "image", width="full"),
            _f("name", "Name", "text", width="half"),
            _f("handle", "Handle", "text", width="half", placeholder="ESPNCFB", help="The @ name, without the @."),
            _f("voice", "House voice", "textarea", width="full", help="How this account posts and what it cares about."),
        ],
    },

    # ---------------- Phone ----------------
    {
        "key": "phone_contacts", "label": "Phone Contacts", "group": "Phone", "icon": "phone",
        "blurb": "Who the coach can text. Recruits, players and staff can link to the NIL engine.",
        "kind": "list", "item_kind": "Contact", "title_field": "name", "subtitle_field": "role", "image_field": "image",
        "fields": [
            _f("image", "Photo", "image", width="full"),
            _f("name", "Name", "text", width="half"),
            _f("role", "Role", "text", width="half"),
            _f("avatar", "Initials", "text", width="quarter", maxLength=3, help="Fallback when there is no photo."),
            _f("category", "Category", "select", width="quarter", options=CATEGORY_OPTS),
            _f("time", "Last seen", "text", width="half", placeholder="9:41 AM"),
            _f("preview", "Preview text", "textarea", width="full"),
            _f("status", "Status line", "text", width="full"),
            _f("personality", "Personality", "textarea", width="full", help="Drives how this contact texts back."),
            _f("entity.kind", "Links to", "select", width="half", options=ENTITY_OPTS,
               help="Connects the chat to the NIL/budget engine."),
            _f("entity.name", "Linked entity name", "text", width="half",
               help="Match a recruit or player name to enable in-chat NIL offers."),
            _f("id", "Internal id", "slug", width="full", help="Stable identifier. Lowercase, no spaces."),
        ],
    },

    # ---------------- Committee ----------------
    {
        "key": "cfp_committee", "label": "CFP Committee", "group": "Committee", "icon": "gavel",
        "blurb": "The twelve-member selection committee and how each one sees the field.",
        "kind": "list", "item_kind": "Member", "title_field": "name", "subtitle_field": "role", "image_field": "image",
        "fields": [
            _f("image", "Photo", "image", width="full"),
            _f("name", "Name", "text", width="half"),
            _f("role", "Role", "text", width="half"),
            _f("affiliation", "Affiliation", "text", width="half", help="Shown on the badge, e.g. SEC, Media."),
            _f("conference", "Conference", "team_conference", width="half", help="For the affiliation logo. Blank for none."),
            _f("bio", "Biography", "textarea", width="full"),
            _f("lens", "Lens", "textarea", width="full", help="How this member weighs the field."),
        ],
    },

    # ---------------- Hot Seat ----------------
    {
        "key": "hot_seat_coaches", "label": "Hot Seat Board", "group": "Hot Seat", "icon": "fire",
        "blurb": "Coaches around the country feeling the heat.",
        "kind": "list", "item_kind": "Coach", "title_field": "coach", "subtitle_field": "team", "image_field": "image",
        "fields": [
            _f("image", "Photo", "image", width="full"),
            _f("coach", "Coach", "text", width="half"),
            _f("team", "Team", "team", width="half"),
            _f("record", "Record", "text", width="quarter", placeholder="6-3"),
            _f("heat", "Heat", "percent", width="quarter"),
            _f("trend", "Trend", "select", width="half", options=TREND_OPTS),
            _f("note", "Note", "textarea", width="full"),
        ],
    },
    {
        "key": "candidates", "label": "Candidate Pool", "group": "Hot Seat", "icon": "users",
        "blurb": "The names that surface when a job opens.",
        "kind": "list", "item_kind": "Candidate", "title_field": "name", "subtitle_field": "current", "image_field": "image",
        "fields": [
            _f("image", "Photo", "image", width="full"),
            _f("name", "Name", "text", width="half"),
            _f("current", "Current job", "text", width="half"),
            _f("archetype", "Archetype", "text", width="half"),
            _f("fit", "Fit", "percent", width="half"),
            _f("why", "Why", "textarea", width="full"),
        ],
    },

    # ---------------- Awards ----------------
    {
        "key": "awards", "label": "Awards", "group": "Awards", "icon": "trophy",
        "blurb": "The trophies tracked on the awards watch.",
        "kind": "list", "item_kind": "Award", "title_field": "name", "subtitle_field": "criteria",
        "fields": [
            _f("name", "Award name", "text", width="half"),
            _f("key", "Internal key", "slug", width="half", help="Lowercase id, no spaces."),
            _f("criteria", "Criteria", "text", width="full"),
            _f("position", "Position", "text", width="half", help="Blank for all-position awards (e.g. Heisman)."),
        ],
    },
]

# Personas: which sections describe people and how their personalities are made.
PERSONA_SECTIONS: dict[str, tuple[str, str]] = {
    "cfp_committee": ("fixed", "committee member"),
    "reporters": ("fixed", "reporter"),
    "recruiting_analysts": ("fixed", "recruiting analyst"),
    "award_voters": ("fixed", "award voter"),
    "online_personalities": ("fixed", "media personality"),
    "phone_contacts": ("generated", "contact"),
    "candidates": ("generated", "coaching candidate"),
    "hot_seat_coaches": ("generated", "head coach"),
}

# Researched personality sliders for the real CFP committee (fixed personas).
_COMMITTEE_TRAITS = {
    "Hunter Yurachek": {"confidence": 72, "competitiveness": 60, "loyalty": 70, "composure": 84, "charisma": 70, "ambition": 66, "ego": 48},
    "Chris Ault": {"confidence": 88, "competitiveness": 86, "loyalty": 60, "composure": 70, "charisma": 66, "ambition": 82, "ego": 70},
    "Troy Dannen": {"confidence": 64, "competitiveness": 58, "loyalty": 62, "composure": 82, "charisma": 60, "ambition": 64, "ego": 44},
    "Mark Dantonio": {"confidence": 70, "competitiveness": 88, "loyalty": 80, "composure": 90, "charisma": 38, "ambition": 60, "ego": 46},
    "Mark Harlan": {"confidence": 66, "competitiveness": 62, "loyalty": 58, "composure": 76, "charisma": 58, "ambition": 66, "ego": 50},
    "Jeff Long": {"confidence": 68, "competitiveness": 55, "loyalty": 70, "composure": 86, "charisma": 56, "ambition": 58, "ego": 40},
    "Ivan Maisel": {"confidence": 66, "competitiveness": 45, "loyalty": 64, "composure": 84, "charisma": 82, "ambition": 55, "ego": 35},
    "Chris Massaro": {"confidence": 60, "competitiveness": 58, "loyalty": 78, "composure": 80, "charisma": 60, "ambition": 58, "ego": 40},
    "Mike Riley": {"confidence": 64, "competitiveness": 60, "loyalty": 82, "composure": 88, "charisma": 80, "ambition": 52, "ego": 32},
    "David Sayler": {"confidence": 60, "competitiveness": 56, "loyalty": 64, "composure": 78, "charisma": 58, "ambition": 60, "ego": 42},
    "Wesley Walls": {"confidence": 82, "competitiveness": 84, "loyalty": 58, "composure": 70, "charisma": 64, "ambition": 66, "ego": 64},
    "Carla Williams": {"confidence": 74, "competitiveness": 72, "loyalty": 66, "composure": 86, "charisma": 64, "ambition": 78, "ego": 46},
}
for _m in DEFAULTS["cfp_committee"]:
    _m.setdefault("traits", _COMMITTEE_TRAITS.get(_m["name"], personality.default_traits()))


def _invalidate_cache() -> None:
    """Drop the current week's cached module output so edits show up immediately.
    Past weeks keep their generated content so the dynasty archive is preserved."""
    try:
        from . import cache
        cache.clear_current_week()
    except Exception:
        pass


_store = Store(store_file=_STORE_FILE, defaults=DEFAULTS, schema=SCHEMA,
               persona_sections=PERSONA_SECTIONS, on_change=_invalidate_cache)

# Module-level delegating API (kept stable for the modules + the Dynasty+ app).
section = _store.section
load = _store.load
get_state = _store.get_state
generate_person = _store.generate_person
set_section = _store.set_section
reset_section = _store.reset_section
reset_all = _store.reset_all


def apply_local_media(team_name: str) -> dict[str, Any]:
    """Swap the local media to the named program's real local outlets + beat
    writers, keeping the national media untouched.

    The national reporters (scope != "local") are preserved exactly, including
    any user edits; only the local-scope reporters and the local-outlet list are
    replaced with the team's researched data (backend/local_media). A no-op for a
    program that has no researched local media, so the current local set survives
    rather than being wiped. Called by pipeline.scan when the save names a new
    program; the cache invalidation rides on set_section's on_change."""
    from . import local_media
    orgs = local_media.orgs_for(team_name)
    locals_ = local_media.reporters_for(team_name)
    if orgs:
        set_section("media_orgs_local", orgs)
    if locals_:
        national = [r for r in section("reporters")
                    if (r.get("scope") or "national").lower() != "local"]
        set_section("reporters", national + locals_)
    return {"orgs": len(orgs), "writers": len(locals_)}
