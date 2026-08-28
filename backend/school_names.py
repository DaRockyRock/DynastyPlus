"""Short school names for every FBS program, keyed by espn_id.

Broadcast bracket graphics label each slot with just the school ("Clemson",
"Ohio State"), never the full "School Nickname" pairing the rest of the app
uses. Neither the league seed nor the save carries a school/nickname split, so
this is static reference data (the same shape as school_sites.CAMPUS_SITES).
"""
from __future__ import annotations

SHORT_NAMES: dict[int, str] = {
    # ACC
    228: "Clemson", 52: "Florida State", 2390: "Miami", 97: "Louisville",
    2567: "SMU", 59: "Georgia Tech", 152: "NC State", 221: "Pitt",
    153: "North Carolina", 259: "Virginia Tech", 25: "California", 150: "Duke",
    24: "Stanford", 258: "Virginia", 103: "Boston College", 183: "Syracuse",
    154: "Wake Forest",
    # American
    2655: "Tulane", 349: "Army", 235: "Memphis", 2426: "Navy",
    2429: "Charlotte", 242: "Rice", 2636: "UTSA", 151: "East Carolina",
    249: "North Texas", 5: "UAB", 58: "South Florida", 202: "Tulsa",
    2226: "Florida Atlantic", 218: "Temple",
    # Big 12
    254: "Utah", 2306: "Kansas State", 9: "Arizona State", 252: "BYU",
    66: "Iowa State", 2641: "Texas Tech", 2628: "TCU", 38: "Colorado",
    2305: "Kansas", 239: "Baylor", 197: "Oklahoma State", 2132: "Cincinnati",
    277: "West Virginia", 248: "Houston", 12: "Arizona", 2116: "UCF",
    # Big Ten
    194: "Ohio State", 2483: "Oregon", 130: "Michigan", 213: "Penn State",
    30: "USC", 264: "Washington", 2294: "Iowa", 84: "Indiana",
    275: "Wisconsin", 158: "Nebraska", 127: "Michigan State", 2509: "Purdue",
    356: "Illinois", 135: "Minnesota", 77: "Northwestern", 26: "UCLA",
    120: "Maryland", 164: "Rutgers",
    # Conference USA
    2335: "Liberty", 2348: "Louisiana Tech", 2393: "Middle Tennessee",
    98: "Western Kentucky", 2229: "FIU", 338: "Kennesaw State",
    2534: "Sam Houston", 2623: "Missouri State", 166: "New Mexico State",
    48: "Delaware", 55: "Jacksonville State", 2638: "UTEP",
    # Independents
    87: "Notre Dame", 41: "UConn",
    # MAC
    2006: "Akron", 2050: "Ball State", 195: "Ohio", 2084: "Buffalo",
    2309: "Kent State", 113: "UMass", 193: "Miami (OH)",
    2199: "Eastern Michigan", 2649: "Toledo", 2117: "Central Michigan",
    2459: "Northern Illinois", 2711: "Western Michigan", 189: "Bowling Green",
    # Mountain West
    68: "Boise State", 2439: "UNLV", 278: "Fresno State", 62: "Hawai'i",
    2005: "Air Force", 2751: "Wyoming", 167: "New Mexico", 23: "San Jose State",
    328: "Utah State", 21: "San Diego State", 2440: "Nevada",
    36: "Colorado State", 265: "Washington State", 204: "Oregon State",
    # SEC
    61: "Georgia", 251: "Texas", 333: "Alabama", 99: "LSU",
    2633: "Tennessee", 145: "Ole Miss", 201: "Oklahoma", 245: "Texas A&M",
    142: "Missouri", 57: "Florida", 2579: "South Carolina", 2: "Auburn",
    8: "Arkansas", 96: "Kentucky", 238: "Vanderbilt", 344: "Mississippi State",
    # Sun Belt
    256: "James Madison", 2032: "Arkansas State", 295: "Old Dominion",
    2572: "Southern Miss", 2653: "Troy", 2247: "Georgia State",
    276: "Marshall", 6: "South Alabama", 309: "Louisiana", 2433: "UL Monroe",
    290: "Georgia Southern", 326: "Texas State", 2026: "App State",
    324: "Coastal Carolina",
}


def short_name(espn_id: object, fallback: str | None = None) -> str:
    try:
        name = SHORT_NAMES.get(int(espn_id))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        name = None
    return name or fallback or ""
