"""
common/encounter_calc.py
Calcolatore Ufficiale della Difficoltà degli Incontri secondo le regole di D&D 5e (DMG p. 82 & 2024).
Fornisce il calcolo delle soglie di XP del gruppo (Facile, Medio, Difficile, Mortale),
il moltiplicatore per il numero di mostri e la valutazione del grado di sfida dell'incontro.
"""

# Soglie di XP per livello di personaggio (DMG p. 82)
XP_THRESHOLDS_5E = {
    1:  {"easy": 25,   "medium": 50,   "hard": 75,   "deadly": 100},
    2:  {"easy": 50,   "medium": 100,  "hard": 150,  "deadly": 200},
    3:  {"easy": 75,   "medium": 150,  "hard": 225,  "deadly": 400},
    4:  {"easy": 125,  "medium": 250,  "hard": 375,  "deadly": 500},
    5:  {"easy": 250,  "medium": 500,  "hard": 750,  "deadly": 1100},
    6:  {"easy": 300,  "medium": 600,  "hard": 900,  "deadly": 1400},
    7:  {"easy": 350,  "medium": 750,  "hard": 1100, "deadly": 1700},
    8:  {"easy": 450,  "medium": 900,  "hard": 1400, "deadly": 2100},
    9:  {"easy": 550,  "medium": 1100, "hard": 1600, "deadly": 2400},
    10: {"easy": 600,  "medium": 1200, "hard": 1900, "deadly": 2800},
    11: {"easy": 800,  "medium": 1600, "hard": 2400, "deadly": 3600},
    12: {"easy": 1000, "medium": 2000, "hard": 3000, "deadly": 4500},
    13: {"easy": 1100, "medium": 2200, "hard": 3400, "deadly": 5100},
    14: {"easy": 1250, "medium": 2500, "hard": 3800, "deadly": 5700},
    15: {"easy": 1400, "medium": 2800, "hard": 4300, "deadly": 6400},
    16: {"easy": 1600, "medium": 3200, "hard": 4800, "deadly": 7200},
    17: {"easy": 2000, "medium": 3900, "hard": 5900, "deadly": 8800},
    18: {"easy": 2100, "medium": 4200, "hard": 6300, "deadly": 9500},
    19: {"easy": 2400, "medium": 4900, "hard": 7300, "deadly": 10900},
    20: {"easy": 2800, "medium": 5700, "hard": 8500, "deadly": 12700},
}

# Tabella XP corrispondente al Grado Sfida (CR / GS)
CR_TO_XP = {
    "0": 10, "1/8": 25, "1/4": 50, "1/2": 100,
    "1": 200, "2": 450, "3": 700, "4": 1100, "5": 1800,
    "6": 2300, "7": 2900, "8": 3900, "9": 5000, "10": 5900,
    "11": 7200, "12": 8400, "13": 10000, "14": 11500, "15": 13000,
    "16": 15000, "17": 18000, "18": 20000, "19": 22000, "20": 25000,
    "21": 33000, "22": 41000, "23": 50000, "24": 62000, "30": 155000
}


def get_monster_count_multiplier(num_monsters: int, party_size: int = 4) -> float:
    """Restituisce il moltiplicatore XP in base al numero di mostri e alla dimensione del party."""
    if num_monsters <= 0:
        return 1.0
    elif num_monsters == 1:
        base = 1.0
    elif num_monsters == 2:
        base = 1.5
    elif 3 <= num_monsters <= 6:
        base = 2.0
    elif 7 <= num_monsters <= 10:
        base = 2.5
    elif 11 <= num_monsters <= 14:
        base = 3.0
    else:
        base = 4.0

    # Aggiustamento 5e per party piccoli (<3 PG) o grandi (>5 PG)
    if party_size < 3:
        if base == 1.0: base = 1.5
        elif base == 1.5: base = 2.0
        elif base == 2.0: base = 2.5
        elif base == 2.5: base = 3.0
        elif base == 3.0: base = 4.0
        else: base = 5.0
    elif party_size > 5:
        if base == 1.5: base = 1.0
        elif base == 2.0: base = 1.5
        elif base == 2.5: base = 2.0
        elif base == 3.0: base = 2.5
        elif base == 4.0: base = 3.0
    return base


def calculate_encounter_difficulty(party_levels: list[int], monster_xps: list) -> dict:
    """
    Calcola la difficoltà dell'incontro per un dato gruppo di livelli e mostri (XP o CR).
    Accetta lista di XP (int), CR ("1/4", 1, 2), o dizionari monster.
    Ritorna un dizionario con:
    - difficulty: 'Banale', 'Facile', 'Medio', 'Difficile', 'Mortale'
    - total_raw_xp / raw_xp: somma XP base dei mostri
    - adjusted_xp: XP modificati dal moltiplicatore
    - multiplier: moltiplicatore mostri
    - thresholds: soglie del gruppo {'easy': X, 'medium': Y, 'hard': Z, 'deadly': W}
    """
    if not party_levels:
        party_levels = [1]
        
    thresholds = {"easy": 0, "medium": 0, "hard": 0, "deadly": 0}
    for lvl in party_levels:
        clamped_lvl = max(1, min(20, int(lvl)))
        t = XP_THRESHOLDS_5E.get(clamped_lvl, XP_THRESHOLDS_5E[1])
        for k in thresholds:
            thresholds[k] += t[k]
            
    parsed_xps = []
    for m in monster_xps:
        if isinstance(m, dict):
            xp = m.get("xp")
            if xp is None and "cr" in m:
                xp = CR_TO_XP.get(m["cr"], CR_TO_XP.get(str(m["cr"]), 0))
            parsed_xps.append(int(xp or 0))
        elif isinstance(m, str):
            if m in CR_TO_XP:
                parsed_xps.append(CR_TO_XP[m])
            else:
                try: parsed_xps.append(int(m))
                except ValueError: parsed_xps.append(0)
        elif isinstance(m, (int, float)):
            if m in CR_TO_XP and m <= 30:
                parsed_xps.append(CR_TO_XP[m])
            else:
                parsed_xps.append(int(m))
        else:
            parsed_xps.append(0)

    num_monsters = len(parsed_xps)
    total_raw_xp = sum(parsed_xps)
    multiplier = get_monster_count_multiplier(num_monsters, party_size=len(party_levels))
    adjusted_xp = int(total_raw_xp * multiplier)
    
    if adjusted_xp < thresholds["easy"]:
        diff = "Banale"
    elif adjusted_xp < thresholds["medium"]:
        diff = "Facile"
    elif adjusted_xp < thresholds["hard"]:
        diff = "Medio"
    elif adjusted_xp < thresholds["deadly"]:
        diff = "Difficile"
    else:
        diff = "Mortale"
        
    return {
        "difficulty": diff,
        "total_raw_xp": total_raw_xp,
        "raw_xp": total_raw_xp,
        "adjusted_xp": adjusted_xp,
        "multiplier": multiplier,
        "thresholds": thresholds,
        "party_size": len(party_levels),
        "monster_count": num_monsters
    }
