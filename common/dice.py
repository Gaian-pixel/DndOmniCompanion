#dice.py

import re
import random

def roll_dice(formula):
    """
    Parsing semplice formule tipo '3d6+2', '1d20', '1d20+3 adv'
    Restituisce un dict con rolls, modifier e total
    """
    formula = formula.strip().lower()
    
    adv = False
    dis = False
    if formula.endswith(' adv'):
        adv = True
        formula = formula[:-4].strip()
    elif formula.endswith(' dis'):
        dis = True
        formula = formula[:-4].strip()
        
    pattern = r'^(\d*)d(\d+)([+-]\d+)?$'
    match = re.match(pattern, formula)
    if not match:
        raise ValueError(f"Formula non valida: {formula}")

    # Estrai gruppi
    count_str, sides_str, modifier_str = match.groups()
    count = int(count_str) if count_str else 1
    sides = int(sides_str)
    modifier = int(modifier_str) if modifier_str else 0

    if count < 1 or sides < 2:
        raise ValueError("Il numero di dadi deve essere almeno 1 e i lati almeno 2")

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
            
        return {
            "rolls": rolls,
            "other_rolls": other_rolls,
            "modifier": modifier,
            "total": total,
            "type": roll_type
        }
    else:
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + modifier

        return {
            "rolls": rolls,
            "modifier": modifier,
            "total": total,
            "type": "Normale"
        }
