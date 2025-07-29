from dice import roll_dice

formule = [
    "1d20",
    "2d6+3",
    "4d8-2",
    "d10+5",
    "3d4",
    "invalid",
]

for f in formule:
    try:
        result = roll_dice(f)
        print(f"Formula: {f} -> Rolls: {result['rolls']}, Modifier: {result['modifier']}, Total: {result['total']}")
    except ValueError as e:
        print(f"Formula: {f} -> Errore: {e}")
