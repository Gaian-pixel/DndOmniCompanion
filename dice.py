import re
import random

def roll_dice(formula):
    """
    Parsing semplice formule tipo '3d6+2', '1d20', '2d10-1'
    Restituisce un dict con rolls, modifier e total
    """
    pattern = r'^(\d*)d(\d+)([+-]\d+)?$'
    match = re.match(pattern, formula.strip())
    if not match:
        raise ValueError(f"Formula non valida: {formula}")

    # Estrai gruppi
    count_str, sides_str, modifier_str = match.groups()
    count = int(count_str) if count_str else 1
    sides = int(sides_str)
    modifier = int(modifier_str) if modifier_str else 0

    if count < 1 or sides < 2:
        raise ValueError("Il numero di dadi deve essere almeno 1 e i lati almeno 2")

    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier

    return {
        "rolls": rolls,
        "modifier": modifier,
        "total": total
    }
