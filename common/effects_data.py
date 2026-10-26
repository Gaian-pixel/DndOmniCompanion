# effects_data.py
"""
D&D 5e Timed Effects & Save-Ends Presets and Utilities.
Provides standard 5e spells, conditions with durations, and saving throw ending mechanics.
"""

from typing import Dict, Any, List, Optional
from common.i18n import get_language

# 5e Standard Presets Library
EFFECT_PRESETS: Dict[str, Dict[str, Any]] = {
    "bless": {
        "key": "bless",
        "name_it": "Benedizione",
        "name_en": "Bless",
        "icon": "✨",
        "duration_rounds": 10,
        "decrement_timing": "round_end",
        "concentration": True,
        "save_ends": None,
        "condition": None,
        "description_it": "+1d4 ai tiri per colpire e ai tiri salvezza.",
        "description_en": "+1d4 to attack rolls and saving throws."
    },
    "bane": {
        "key": "bane",
        "name_it": "Anatema",
        "name_en": "Bane",
        "icon": "🔮",
        "duration_rounds": 10,
        "decrement_timing": "round_end",
        "concentration": True,
        "save_ends": {"stat": "CAR", "dc": 13, "timing": "end_of_turn"},
        "condition": None,
        "description_it": "-1d4 ai tiri per colpire e ai tiri salvezza. TS Carisma.",
        "description_en": "-1d4 to attack rolls and saving throws. Charisma save."
    },
    "rage": {
        "key": "rage",
        "name_it": "Ira",
        "name_en": "Rage",
        "icon": "🔥",
        "duration_rounds": 10,
        "decrement_timing": "round_end",
        "concentration": False,
        "save_ends": None,
        "condition": "Ira",
        "description_it": "Resistenza a danni contundenti, perforanti e taglienti; vantaggio prove Forza.",
        "description_en": "Resistance to bludgeoning, piercing, and slashing; advantage on Strength checks."
    },
    "shield": {
        "key": "shield",
        "name_it": "Scudo",
        "name_en": "Shield",
        "icon": "🛡️",
        "duration_rounds": 1,
        "decrement_timing": "start_of_turn",
        "concentration": False,
        "save_ends": None,
        "condition": "Scudo",
        "description_it": "+5 alla Classe Armatura fino all'inizio del tuo prossimo turno.",
        "description_en": "+5 to AC until the start of your next turn."
    },
    "haste": {
        "key": "haste",
        "name_it": "Velocità",
        "name_en": "Haste",
        "icon": "⚡",
        "duration_rounds": 10,
        "decrement_timing": "round_end",
        "concentration": True,
        "save_ends": None,
        "condition": None,
        "description_it": "Velocità raddoppiata, +2 CA, vantaggio TS Destrezza, azione extra.",
        "description_en": "Speed doubled, +2 AC, advantage on Dex saves, extra action."
    },
    "hold_person": {
        "key": "hold_person",
        "name_it": "Blocca Persone",
        "name_en": "Hold Person",
        "icon": "🧊",
        "duration_rounds": 10,
        "decrement_timing": "round_end",
        "concentration": True,
        "save_ends": {"stat": "SAG", "dc": 14, "timing": "end_of_turn"},
        "condition": "Paralizzato",
        "description_it": "Bersaglio Paralizzato. Può effettuare un TS Saggezza a fine turno per liberarsi.",
        "description_en": "Target is Paralyzed. Can make a Wisdom save at the end of each turn to end the spell."
    },
    "blindness": {
        "key": "blindness",
        "name_it": "Cecità",
        "name_en": "Blindness",
        "icon": "🙈",
        "duration_rounds": 10,
        "decrement_timing": "round_end",
        "concentration": False,
        "save_ends": {"stat": "COS", "dc": 13, "timing": "end_of_turn"},
        "condition": "Accecato",
        "description_it": "Bersaglio Accecato. Può effettuare un TS Costituzione a fine turno per liberarsi.",
        "description_en": "Target is Blinded. Can make a Constitution save at the end of each turn to end."
    },
    "tasha_laughter": {
        "key": "tasha_laughter",
        "name_it": "Risata di Tasha",
        "name_en": "Tasha's Laughter",
        "icon": "🤣",
        "duration_rounds": 10,
        "decrement_timing": "round_end",
        "concentration": True,
        "save_ends": {"stat": "SAG", "dc": 13, "timing": "end_of_turn"},
        "condition": "Incapacitato",
        "description_it": "Bersaglio Prono e Incapacitato dal riso. TS Saggezza a fine turno per liberarsi.",
        "description_en": "Target is Prone and Incapacitated with laughter. Wisdom save at end of turn."
    },
    "slow": {
        "key": "slow",
        "name_it": "Lentezza",
        "name_en": "Slow",
        "icon": "🐌",
        "duration_rounds": 10,
        "decrement_timing": "round_end",
        "concentration": True,
        "save_ends": {"stat": "SAG", "dc": 14, "timing": "end_of_turn"},
        "condition": None,
        "description_it": "Velocità dimezzata, -2 CA, nessuna reazione. TS Saggezza a fine turno.",
        "description_en": "Half speed, -2 AC, no reactions. Wisdom save at end of turn."
    },
    "fear": {
        "key": "fear",
        "name_it": "Paura",
        "name_en": "Fear",
        "icon": "😱",
        "duration_rounds": 10,
        "decrement_timing": "round_end",
        "concentration": True,
        "save_ends": {"stat": "SAG", "dc": 14, "timing": "end_of_turn"},
        "condition": "Spaventato",
        "description_it": "Bersaglio Spaventato e costretto alla fuga. TS Saggezza se fuori dalla linea di vista.",
        "description_en": "Target is Frightened and must flee. Wisdom save when out of line of sight."
    },
    "poisoned_save": {
        "key": "poisoned_save",
        "name_it": "Avvelenato (TS)",
        "name_en": "Poisoned (Save)",
        "icon": "🟢",
        "duration_rounds": 3,
        "decrement_timing": "round_end",
        "concentration": False,
        "save_ends": {"stat": "COS", "dc": 12, "timing": "end_of_turn"},
        "condition": "Avvelenato",
        "description_it": "Svantaggio ai tiri per colpire e alle prove. TS Costituzione a fine turno per guarire.",
        "description_en": "Disadvantage on attack rolls and ability checks. Constitution save at end of turn."
    },
    "dodge": {
        "key": "dodge",
        "name_it": "Schivata",
        "name_en": "Dodge",
        "icon": "🛡️",
        "duration_rounds": 1,
        "decrement_timing": "start_of_turn",
        "concentration": False,
        "save_ends": None,
        "condition": "Schivata",
        "description_it": "Attacchi contro di te hanno svantaggio e hai vantaggio ai TS su DES.",
        "description_en": "Attacks against you have disadvantage and you have advantage on DEX saves."
    },
    "invisibility": {
        "key": "invisibility",
        "name_it": "Invisibilità",
        "name_en": "Invisibility",
        "icon": "👻",
        "duration_rounds": 10,
        "decrement_timing": "round_end",
        "concentration": True,
        "save_ends": None,
        "condition": "Invisibile",
        "description_it": "Invisibile a vista normale finché non attacca o lancia un incantesimo.",
        "description_en": "Invisible to normal sight until attacking or casting a spell."
    }
}

def get_effect_presets(lang: Optional[str] = None) -> List[Dict[str, Any]]:
    """Restituisce la lista di tutti i preset formattati e localizzati."""
    cur_lang = (lang or get_language() or "it").lower()
    is_en = cur_lang.startswith("en")
    
    presets = []
    for key, p in EFFECT_PRESETS.items():
        name = p["name_en"] if is_en else p["name_it"]
        desc = p["description_en"] if is_en else p["description_it"]
        presets.append({
            "key": key,
            "name": name,
            "icon": p["icon"],
            "duration_rounds": p["duration_rounds"],
            "decrement_timing": p["decrement_timing"],
            "concentration": p["concentration"],
            "save_ends": p["save_ends"],
            "condition": p["condition"],
            "description": desc
        })
    return presets

def create_effect_instance(
    preset_or_name: str,
    source: str = "",
    dc: Optional[int] = None,
    stat: Optional[str] = None,
    duration_rounds: Optional[int] = None,
    concentration_caster: Optional[str] = None,
    condition: Optional[str] = None,
    icon: Optional[str] = None,
    decrement_timing: str = "round_end"
) -> Dict[str, Any]:
    """Crea una nuova istanza di un effetto attivo pronta per essere assegnata ad una creatura."""
    preset = EFFECT_PRESETS.get(preset_or_name.lower())
    
    cur_lang = get_language() or "it"
    is_en = cur_lang.lower().startswith("en")
    
    if preset:
        name = preset["name_en"] if is_en else preset["name_it"]
        eff_icon = icon or preset["icon"]
        eff_dur = duration_rounds if duration_rounds is not None else preset["duration_rounds"]
        eff_timing = preset["decrement_timing"] or decrement_timing
        eff_cond = condition or preset["condition"]
        
        save_ends = None
        if preset["save_ends"]:
            save_ends = dict(preset["save_ends"])
            if dc is not None:
                save_ends["dc"] = int(dc)
            if stat:
                save_ends["stat"] = stat.upper()
        elif stat and dc:
            save_ends = {"stat": stat.upper(), "dc": int(dc), "timing": "end_of_turn"}
            
        is_conc = preset["concentration"]
        caster = concentration_caster if (is_conc or concentration_caster) else None
        if is_conc and not caster and source:
            caster = source
    else:
        name = preset_or_name
        eff_icon = icon or "✨"
        eff_dur = duration_rounds if duration_rounds is not None else 10
        eff_timing = decrement_timing
        eff_cond = condition
        save_ends = None
        if stat and dc:
            save_ends = {"stat": stat.upper(), "dc": int(dc), "timing": "end_of_turn"}
        caster = concentration_caster
        
    import uuid
    eff_id = f"fx_{uuid.uuid4().hex[:8]}"
    
    return {
        "id": eff_id,
        "name": name,
        "icon": eff_icon,
        "source": source,
        "duration_rounds": eff_dur,
        "decrement_timing": eff_timing,
        "save_ends": save_ends,
        "concentration_caster": caster,
        "condition": eff_cond
    }

