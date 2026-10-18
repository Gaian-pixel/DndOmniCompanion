#dice.py

import re
import random

def roll_dice(formula, is_crit=False):
    """
    Parsing semplice formule tipo '3d6+2', '1d20', '1d20+3 adv'
    Se is_crit=True (es. danno critico 5e), raddoppia il numero di dadi tirati
    mantenendo invariato il modificatore fisso.
    Per i tiri di 1d20, rileva automaticamente Successo Critico (20 naturale)
    e Fallimento Critico (1 naturale).
    """
    formula = formula.strip().lower()
    
    adv = False
    dis = False
    if formula.endswith(' adv') or formula.endswith('adv'):
        adv = True
        formula = re.sub(r'\s*adv$', '', formula).strip()
    elif formula.endswith(' dis') or formula.endswith('dis'):
        dis = True
        formula = re.sub(r'\s*dis$', '', formula).strip()

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
        
    pattern = r'^(\d*)d(\d+)([+-]\d+)?$'
    match = re.match(pattern, formula)
    if not match and " " in formula:
        match = re.match(pattern, formula.split()[0])
    if not match:
        raise ValueError(f"Formula non valida: {formula}")

    # Estrai gruppi
    count_str, sides_str, modifier_str = match.groups()
    orig_count = int(count_str) if count_str else 1
    sides = int(sides_str)
    modifier = int(modifier_str) if modifier_str else 0

    if orig_count < 1 or sides < 2:
        raise ValueError("Il numero di dadi deve essere almeno 1 e i lati almeno 2")

    count = orig_count * 2 if is_crit else orig_count
    is_d20_check = (orig_count == 1 and sides == 20 and not is_crit)

    if adv or dis:
        rolls_1 = [random.randint(1, sides) for _ in range(count)]
        rolls_2 = [random.randint(1, sides) for _ in range(count)]
        total_1 = sum(rolls_1) + modifier
        total_2 = sum(rolls_2) + modifier
        
        if adv:
            if total_1 >= total_2:
                rolls = rolls_1
                total = total_1
                other_rolls = rolls_2
            else:
                rolls = rolls_2
                total = total_2
                other_rolls = rolls_1
            roll_type = "Vantaggio"
        else:
            if total_1 <= total_2:
                rolls = rolls_1
                total = total_1
                other_rolls = rolls_2
            else:
                rolls = rolls_2
                total = total_2
                other_rolls = rolls_1
            roll_type = "Svantaggio"
            
        nat_roll = rolls[0] if rolls else 0
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
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + modifier
        nat_roll = rolls[0] if rolls else 0
        crit_succ = is_d20_check and (nat_roll == 20)
        crit_fail = is_d20_check and (nat_roll == 1)

        return {
            "rolls": rolls,
            "modifier": modifier,
            "total": total,
            "type": "Critico" if is_crit else "Normale",
            "natural_roll": nat_roll,
            "is_crit": crit_succ,
            "is_fumble": crit_fail,
            "is_crit_fail": crit_fail,
            "crit_status": "crit_success" if crit_succ else ("crit_fail" if crit_fail else "normal")
        }
