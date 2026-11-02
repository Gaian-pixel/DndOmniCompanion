#dice.py

import re
import random

def roll_dice(formula, is_crit=False):
    """
    Parsing semplice e composto formule tipo '3d6+2', '1d20', '1d20+3 adv', '2d6+1d8+3', '1d8+4 Tagliente'
    Se is_crit=True (es. danno critico 5e), raddoppia il numero di dadi tirati
    mantenendo invariato il modificatore fisso.
    Per i tiri di 1d20, rileva automaticamente Successo Critico (20 naturale)
    e Fallimento Critico (1 naturale).
    """
    formula = formula.strip().lower()
    
    # Rilevamento vantaggio / svantaggio (italiano e inglese) e loro annullamento reciproco (D&D 5e RAW)
    has_adv = False
    has_dis = False

    if re.search(r'\b(adv|vantaggio|advantage)\b', formula):
        has_adv = True
        formula = re.sub(r'\b(adv|vantaggio|advantage)\b', '', formula).strip()

    if re.search(r'\b(dis|svantaggio|disadvantage)\b', formula):
        has_dis = True
        formula = re.sub(r'\b(dis|svantaggio|disadvantage)\b', '', formula).strip()

    # RAW 5e: Se presenti entrambi, vantaggio e svantaggio si annullano a vicenda
    adv = has_adv and not has_dis
    dis = has_dis and not has_adv

    # Normalizza gli spazi intorno agli operatori + e - (es. '1d20 + 5' -> '1d20+5')
    formula = re.sub(r'\s*([+-])\s*', r'\1', formula)

    # Supporto per valore numerico costante (es. '5', '+3')
    if re.match(r'^[+-]?\d+$', formula):
        val = int(formula)
        return {
            "rolls": [val],
            "modifier": val,
            "total": val,
            "type": "Costante",
            "natural_roll": val,
            "is_crit": False,
            "is_fumble": False,
            "is_crit_fail": False,
            "crit_status": "normal"
        }

    # Estrai i singoli termini (es. '2d6', '+1d8', '-2', '+5', '+4 tagliente')
    tokens = re.findall(r'([+-]?[^+-]+)', formula)
    if not tokens:
        raise ValueError(f"Formula non valida: {formula}")

    dice_groups = []
    modifier = 0

    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if re.search(r'\d*d\d+', token):
            m = re.match(r'^([+-]?\d*d\d+)', token)
            if not m:
                continue
            clean_token = m.group(1)
            sign = -1 if clean_token.startswith('-') else 1
            part = clean_token.lstrip('+-')
            parts = part.split('d')
            if len(parts) != 2:
                raise ValueError(f"Termine dado non valido: {token}")
            cnt_str, sides_str = parts
            cnt = int(cnt_str) if cnt_str else 1
            try:
                sides = int(sides_str)
            except ValueError:
                raise ValueError(f"Numero facce non valido: {sides_str}")
            if cnt < 1 or sides < 2:
                raise ValueError("Il numero di dadi deve essere almeno 1 e i lati almeno 2")
            if cnt > 100:
                raise ValueError("Massimo 100 dadi consentiti per singolo gruppo di dadi")
            if sides > 1000:
                raise ValueError("Massimo 1000 facce consentite per dado")
            dice_groups.append({
                "sign": sign,
                "orig_count": cnt,
                "count": cnt * 2 if is_crit else cnt,
                "sides": sides
            })
        else:
            m = re.match(r'^([+-]?\d+)', token)
            if m:
                modifier += int(m.group(1))
            else:
                # Ignora annotazioni descrittive come 'tagliente', 'fuoco'
                continue

    if not dice_groups:
        if modifier != 0:
            return {
                "rolls": [],
                "other_rolls": [],
                "modifier": modifier,
                "total": modifier,
                "type": "Normale",
                "natural_roll": modifier,
                "is_crit": False,
                "is_fumble": False,
                "is_crit_fail": False,
                "crit_status": "normal"
            }
        raise ValueError(f"Formula non valida: {formula}")

    total_dice = sum(dg["count"] for dg in dice_groups)
    if total_dice > 200:
        raise ValueError("Massimo 200 dadi totali consentiti per formula di lancio")

    d20_group_idx = next((i for i, dg in enumerate(dice_groups) if dg["sides"] == 20 and dg["orig_count"] == 1), None)
    is_d20_check = (d20_group_idx is not None) and not is_crit

    if adv or dis:
        if d20_group_idx is not None:
            # D&D 5e RAW: Si tira due volte ESCLUSIVAMENTE il d20; dadi aggiuntivi (es. 1d4 Benedizione) si tirano una volta sola
            d20_dg = dice_groups[d20_group_idx]
            d20_val_1 = random.randint(1, d20_dg["sides"])
            d20_val_2 = random.randint(1, d20_dg["sides"])

            shared_rolls = []
            shared_tot = modifier
            for i, dg in enumerate(dice_groups):
                if i != d20_group_idx:
                    r = [random.randint(1, dg["sides"]) for _ in range(dg["count"])]
                    shared_rolls.extend(r)
                    shared_tot += dg["sign"] * sum(r)

            pick_first = (d20_val_1 >= d20_val_2) if adv else (d20_val_1 <= d20_val_2)
            chosen_d20 = d20_val_1 if pick_first else d20_val_2
            other_d20 = d20_val_2 if pick_first else d20_val_1

            rolls = [chosen_d20] + shared_rolls
            other_rolls = [other_d20] + shared_rolls
            total = shared_tot + d20_dg["sign"] * chosen_d20
            nat_roll = chosen_d20
        else:
            rolls_1 = []
            tot_1 = modifier
            for dg in dice_groups:
                r = [random.randint(1, dg["sides"]) for _ in range(dg["count"])]
                rolls_1.extend(r)
                tot_1 += dg["sign"] * sum(r)

            rolls_2 = []
            tot_2 = modifier
            for dg in dice_groups:
                r = [random.randint(1, dg["sides"]) for _ in range(dg["count"])]
                rolls_2.extend(r)
                tot_2 += dg["sign"] * sum(r)

            pick_first = (tot_1 >= tot_2) if adv else (tot_1 <= tot_2)
            rolls = rolls_1 if pick_first else rolls_2
            other_rolls = rolls_2 if pick_first else rolls_1
            total = tot_1 if pick_first else tot_2
            nat_roll = rolls[0] if rolls else 0

        roll_type = "Vantaggio" if adv else "Svantaggio"
        crit_succ = is_d20_check and (nat_roll == 20)
        crit_fail = is_d20_check and (nat_roll == 1)
        return {
            "rolls": rolls,
            "other_rolls": other_rolls,
            "modifier": modifier,
            "total": total,
            "type": roll_type,
            "natural_roll": nat_roll,
            "is_crit": crit_succ,
            "is_fumble": crit_fail,
            "is_crit_fail": crit_fail,
            "crit_status": "crit_success" if crit_succ else ("crit_fail" if crit_fail else "normal")
        }
    else:
        all_rolls = []
        total = modifier
        d20_val = None
        for i, dg in enumerate(dice_groups):
            r = [random.randint(1, dg["sides"]) for _ in range(dg["count"])]
            if i == d20_group_idx and r:
                d20_val = r[0]
            all_rolls.extend(r)
            total += dg["sign"] * sum(r)

        nat_roll = d20_val if d20_val is not None else (all_rolls[0] if all_rolls else modifier)
        crit_succ = is_d20_check and (nat_roll == 20)
        crit_fail = is_d20_check and (nat_roll == 1)

        return {
            "rolls": all_rolls,
            "modifier": modifier,
            "total": total,
            "type": "Critico" if is_crit else "Normale",
            "natural_roll": nat_roll,
            "is_crit": crit_succ,
            "is_fumble": crit_fail,
            "is_crit_fail": crit_fail,
            "crit_status": "crit_success" if crit_succ else ("crit_fail" if crit_fail else "normal")
        }
