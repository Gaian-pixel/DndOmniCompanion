"""
server/dm_monster_engine.py
Motore completo delle regole e tratti del Manuale dei Mostri (MM D&D 5e):
- Azioni di Tana (Lair Actions) a Iniziativa 20 (perdendo i pareggi) senza ripetizioni consecutive
- Guardie Azioni Leggendarie (blocco se incapacitato) + Risoluzione Resistenza Leggendaria pendente DM
- Tratti Mitici (Mythic Awakening Fase 2 a 0 PF) & Azioni Mitiche
- Effetti Regionali (Regional Effects)
- Parser e Lancio Incantesimi Innati (A volontà / X/giorno) e a Slot dei Mostri
- Tratti MM: Sciame (Swarm), Movimento Incorporeo, Mutaforma (Shapechanger), Trasferimento Danno,
  Esplosione alla Morte (Death Burst), Pietrificazione a 2 stadi, Scalare come Ragno,
  Anfibio / Respirare sott'Acqua, Sensi Acuti (Keen Senses).
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from common.dice import roll_dice
from common.dnd5e_tables import entity_has_keyword
from common.hex_utils import Hex, grid_distance_3d
from common.i18n import is_condition_active
from common.item_modifiers import get_effective_save_bonus_from_dict
from common.network_utils import broadcast, send_message
from common.protocol import make_chat_broadcast, make_error_reply, make_game_state, make_player_stats_update


SWARM_IMMUNE_CONDITIONS = {
    "affascinato", "charmed",
    "spaventato", "frightened",
    "afferrato", "grappled",
    "paralizzato", "paralyzed",
    "pietrificato", "petrified",
    "prono", "prone",
    "trattenuto", "restrained",
    "stordito", "stunned",
}


def _collect_trait_entries(entity: Any) -> List[Dict[str, str]]:
    if not entity:
        return []
    fs = getattr(entity, "full_sheet", None)
    if not isinstance(fs, dict):
        return []
    out: List[Dict[str, str]] = []
    for key in ("special_abilities", "features", "actions", "legendary_actions", "mythic_actions", "lair_actions"):
        val = fs.get(key)
        if isinstance(val, list):
            for entry in val:
                if isinstance(entry, dict):
                    out.append({
                        "section": key,
                        "name": str(entry.get("name", "") or ""),
                        "desc": str(entry.get("desc", entry.get("description", "")) or ""),
                    })
                elif isinstance(entry, str) and entry.strip():
                    parts = entry.split(".", 1)
                    out.append({
                        "section": key,
                        "name": parts[0].strip(),
                        "desc": parts[1].strip() if len(parts) > 1 else entry,
                    })
    return out


# ==============================================================================
# 1. SCIAME, INCORPOREO, MUTAFORMA, ANFIBIO, SPIDER CLIMB, SENSI ACUTI
# ==============================================================================

def is_swarm_entity(entity: Any) -> bool:
    return entity_has_keyword(entity, "sciame", "swarm")


def filter_swarm_condition(entity: Any, cond: str) -> bool:
    """Ritorna False se lo Sciame è immune alla condizione (MM)."""
    if not is_swarm_entity(entity):
        return True
    c_low = str(cond or "").strip().lower()
    return not any(imm in c_low for imm in SWARM_IMMUNE_CONDITIONS)


def get_swarm_damage_divisor(attacker: Any) -> int:
    """MM Sciame: Quando scende a <= metà PF Max, infligge metà danni."""
    if not attacker or not is_swarm_entity(attacker):
        return 1
    hp = int(getattr(attacker, "hp", 1) or 0)
    mx = max(1, int(getattr(attacker, "max_hp", 1) or 1))
    return 2 if hp <= (mx // 2) else 1


def is_incorporeal_entity(entity: Any) -> bool:
    return entity_has_keyword(entity, "movimento incorporeo", "incorporeal movement")


def is_shapechanger_entity(entity: Any) -> bool:
    return entity_has_keyword(entity, "mutaforma", "shapechanger")


def has_spider_climb(entity: Any) -> bool:
    return entity_has_keyword(entity, "scalare come un ragno", "arrampicarsi come un ragno", "spider climb")


def has_water_breathing(entity: Any) -> bool:
    return entity_has_keyword(entity, "anfibio", "amphibious", "respirare sott'acqua", "water breathing")


def has_keen_senses(entity: Any) -> bool:
    return entity_has_keyword(entity, "sensi acuti", "keen senses", "olfatto acuto", "vista acuta", "udito acuto", "keen sight", "keen smell", "keen hearing")


def is_incapacitated_entity(entity: Any) -> bool:
    if not entity or getattr(entity, "hp", 1) <= 0:
        return True
    conds = getattr(entity, "conditions", []) or []
    return any(
        is_condition_active(conds, c)
        for c in (
            "Incapacitato", "Incosciente", "Paralizzato", "Stordito", "Pietrificato", "Morto",
            "Incapacitated", "Unconscious", "Paralyzed", "Stunned", "Petrified", "Dead",
        )
    )


# ==============================================================================
# 2. INCANTESIMI INNATI E A SLOT DEI MOSTRI (PARSER & LANCIO)
# ==============================================================================

def parse_monster_spellcasting(mdata_or_entity: Any) -> Dict[str, Any]:
    """
    Estrae Incantesimi Innati e Slot Incantesimi dallo statblock SRD/MM del mostro.
    Popola `innate_spells`, `spell_slots`, `spellcasting_dc`, `spellcasting_attack`.
    """
    if isinstance(mdata_or_entity, dict):
        fs = mdata_or_entity
        abilities = mdata_or_entity.get("special_abilities") or mdata_or_entity.get("features") or []
    else:
        fs = getattr(mdata_or_entity, "full_sheet", None)
        if not isinstance(fs, dict):
            fs = {}
        abilities = fs.get("special_abilities") or fs.get("features") or []

    text_blocks: List[str] = []
    if isinstance(abilities, list):
        for ab in abilities:
            if isinstance(ab, dict):
                nm = str(ab.get("name", ""))
                ds = str(ab.get("desc", ab.get("description", "")))
                if any(k in (nm + " " + ds).lower() for k in ("spellcasting", "incantesim", "innat")):
                    text_blocks.append(f"{nm}: {ds}")
            elif isinstance(ab, str) and any(k in ab.lower() for k in ("spellcasting", "incantesim", "innat")):
                text_blocks.append(ab)
    elif isinstance(abilities, str) and any(k in abilities.lower() for k in ("spellcasting", "incantesim", "innat")):
        text_blocks.append(abilities)

    combined = "\n".join(text_blocks)
    res: Dict[str, Any] = {
        "dc": 13,
        "attack_bonus": 5,
        "innate": {},   # spell_name -> {"max": 0|N, "current": 0|N}  (max=0 => At will)
        "slots": {},    # "1".."9" -> {"max": n, "current": n, "spells": [...]}
    }
    if not combined:
        return res

    m_dc = re.search(r'(?:spell save dc|cd(?:\s+dei)?\s+ts[^0-9]{0,12})\s*(\d+)', combined, re.IGNORECASE)
    if m_dc:
        res["dc"] = int(m_dc.group(1))
    m_atk = re.search(r'([+-]\d+)\s*(?:to hit with spell|per colpire con attacchi incantesimo)', combined, re.IGNORECASE)
    if m_atk:
        res["attack_bonus"] = int(m_atk.group(1))

    # Innate lines: "At will: ..." / "3/day each: ..." / "1/day: ..."
    m_will = re.search(r'(?:at will|a volontà)\s*:\s*([^\n]+)', combined, re.IGNORECASE)
    if m_will:
        for sp in re.split(r'[,;]', m_will.group(1)):
            s_clean = re.sub(r'\(.*?\)', '', sp).strip(" .")
            if s_clean:
                res["innate"][s_clean] = {"max": 0, "current": 0}

    for m_day in re.finditer(r'(\d+)\s*/\s*(?:day|giorno)(?:\s+each|\s+ciascuno)?\s*:\s*([^\n]+)', combined, re.IGNORECASE):
        uses = int(m_day.group(1))
        for sp in re.split(r'[,;]', m_day.group(2)):
            s_clean = re.sub(r'\(.*?\)', '', sp).strip(" .")
            if s_clean:
                res["innate"][s_clean] = {"max": uses, "current": uses}

    # Slot lines: "1st level (4 slots): ..." / "Cantrips (at will): ..."
    for m_lvl in re.finditer(r'(\d+)\s*(?:st|nd|rd|th|°)?\s*(?:level|livello)\s*\((\d+)\s*slots?\)\s*:\s*([^\n]+)', combined, re.IGNORECASE):
        lvl = str(max(1, min(9, int(m_lvl.group(1)))))
        slots_n = int(m_lvl.group(2))
        sp_list = [re.sub(r'\(.*?\)', '', x).strip(" .") for x in re.split(r'[,;]', m_lvl.group(3)) if x.strip()]
        res["slots"][lvl] = {"max": slots_n, "current": slots_n, "spells": sp_list}

    return res


def sync_monster_spellcasting_to_sheet(entity: Any) -> Dict[str, Any]:
    parsed = parse_monster_spellcasting(entity)
    fs = getattr(entity, "full_sheet", None) if not isinstance(entity, dict) else entity
    if isinstance(fs, dict):
        if parsed["innate"] and not fs.get("innate_spells"):
            fs["innate_spells"] = parsed["innate"]
        if parsed["slots"] and not fs.get("spell_slots"):
            fs["spell_slots"] = {
                k: {"max": v["max"], "current": v["current"], "spells": list(v.get("spells", []))}
                for k, v in parsed["slots"].items()
            }
        if parsed["slots"] or parsed["innate"]:
            fs["spellcasting_dc"] = parsed["dc"]
            fs["spellcasting_attack"] = parsed["attack_bonus"]
    return parsed


def cast_monster_spell(monster: Any, spell_name: str, game_state: Any, slot_level: Optional[int] = None, target_name: Optional[str] = None) -> Tuple[bool, str]:
    fs = getattr(monster, "full_sheet", None)
    if not isinstance(fs, dict):
        fs = {}
        monster.full_sheet = fs
    parsed = sync_monster_spellcasting_to_sheet(monster)
    innate = fs.get("innate_spells") or {}
    slots = fs.get("spell_slots") or {}
    used_desc = ""

    matched_inn = next((k for k in innate.keys() if spell_name.lower() in k.lower() or k.lower() in spell_name.lower()), None)
    if matched_inn:
        info = innate[matched_inn]
        mx = int(info.get("max", 0) or 0)
        if mx > 0:
            cur = int(info.get("current", mx) or 0)
            if cur <= 0:
                return False, f"{monster.name} ha esaurito gli usi giornalieri di {matched_inn}!"
            info["current"] = cur - 1
            used_desc = f"Innato ({info['current']}/{mx} rimasti)"
        else:
            used_desc = "Innato (A volontà)"
    else:
        req_l = int(slot_level or 1)
        if req_l > 0:
            found_l = None
            for lk in sorted([int(k) for k in slots.keys() if str(k).isdigit()]):
                if lk >= req_l and isinstance(slots.get(str(lk)), dict) and int(slots[str(lk)].get("current", 0)) > 0:
                    found_l = lk
                    break
            if found_l is None:
                return False, f"{monster.name} non ha slot incantesimo disponibili di {req_l}° livello o superiore."
            slots[str(found_l)]["current"] -= 1
            used_desc = f"Slot {found_l}° ({slots[str(found_l)]['current']}/{slots[str(found_l)]['max']})"
        else:
            used_desc = "Trucchetto"

    dc = int(fs.get("spellcasting_dc", parsed.get("dc", 13)) or 13)
    atk_b = int(fs.get("spellcasting_attack", parsed.get("attack_bonus", 5)) or 5)
    atk_r = roll_dice(f"1d20{'+' if atk_b >= 0 else ''}{atk_b}")["total"]
    tgt_str = f" su {target_name}" if target_name else ""
    msg = f"✨ [INCANTESIMO MOSTRO] {monster.name} lancia '{spell_name}'{tgt_str} [{used_desc}] (CD {dc} | TxC se richiesto: {atk_r})."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    return True, msg


# ==============================================================================
# 3. AZIONI DI TANA (INITIATIVE 20 LOSING TIES), AZIONI MITICHE, REGIONALI
# ==============================================================================

def trigger_lair_actions_if_crossed(game_state: Any, prev_init: Optional[int], next_init: Optional[int], round_advanced: bool) -> bool:
    """
    MM: Le Azioni di Tana avvengono a Iniziativa 20 (perdendo i pareggi), quindi subito dopo
    eventuali combattenti con iniziativa >= 20 e prima di quelli con iniziativa < 20.
    """
    if not game_state or not getattr(game_state, "combat_active", False):
        return False
    cur_round = int(getattr(game_state, "round_number", 1) or 1)
    if getattr(game_state, "_lair_triggered_round", 0) == cur_round:
        return False

    active_lair_bosses = [
        p for p in getattr(game_state, "players", [])
        if getattr(p, "has_lair_actions", False)
        and getattr(p, "hp", 0) > 0
        and not any(is_condition_active(getattr(p, "conditions", []), c) for c in ("Incapacitato", "Incosciente", "Paralizzato", "Stordito", "Pietrificato", "Morto"))
    ]
    if not active_lair_bosses:
        return False

    crossed = False
    if round_advanced and (next_init is None or next_init < 20):
        crossed = True
    elif prev_init is not None and next_init is not None and prev_init >= 20 and next_init < 20:
        crossed = True
    elif round_advanced and getattr(game_state, "turn_index", 0) == 0:
        crossed = True

    if not crossed:
        return False

    game_state._lair_triggered_round = cur_round
    for boss in active_lair_bosses:
        lair_msg = f"🏰 [AZIONE DI TANA - Init 20 (perdendo pareggi)] Round {cur_round}: La tana di {boss.name} si attiva!"
        broadcast(game_state, make_chat_broadcast("Sistema", lair_msg))
        if hasattr(game_state, "log_dm_message"):
            game_state.log_dm_message(f"[BOSS] {lair_msg}")
    return True


def execute_lair_action(boss: Any, action_name: str, game_state: Any, dc: int = 15, save_stat: str = "DES", damage_formula: str = "3d6", damage_type: str = "Contundente") -> Tuple[bool, str]:
    """Esegue meccanicamente un'Azione di Tana rispettando il divieto di ripetere la stessa 2 round di fila."""
    last = getattr(boss, "lair_last_action", None)
    if last and str(last).strip().lower() == str(action_name).strip().lower():
        return False, f"Regola MM: {boss.name} non può usare '{action_name}' per due round consecutivi!"
    boss.lair_last_action = action_name
    from server.rules.combat import apply_damage
    targets = [
        p for p in getattr(game_state, "players", [])
        if p.name != boss.name
        and getattr(p, "is_party_member", False) != getattr(boss, "is_party_member", False)
        and getattr(p, "hp", 0) > 0
        and getattr(p, "in_combat", True)
    ]
    hit_logs = []
    for t in targets:
        mod = get_effective_save_bonus_from_dict(t, save_stat)
        sv = roll_dice(f"1d20{'+' if mod >= 0 else ''}{mod}")["total"]
        raw = roll_dice(damage_formula)["total"] if damage_formula else 0
        dmg_a = (raw // 2) if (sv >= dc and raw > 0) else raw
        fin, _, _, _ = apply_damage(t, dmg_a, damage_type=damage_type, game_state=game_state) if dmg_a > 0 else (0, "", 0, 0)
        hit_logs.append(f"{t.name}: TS {sv} vs {dc} -> -{fin}")
    msg = f"🏰 [AZIONE DI TANA ESEGUITA - {boss.name}: {action_name}] " + (", ".join(hit_logs) if hit_logs else "nessun bersaglio attivo.")
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    return True, msg


def check_and_trigger_mythic_awakening(target: Any, game_state: Any) -> Tuple[bool, str]:
    """
    MM/MOoT Mythic Trait: Se la creatura mitica scende a 0 PF per la prima volta,
    entra in Fase Mitica (reset PF, azzera condizioni invalidanti, ricarica Azioni Leggendarie).
    """
    if not target or getattr(target, "mythic_phase_active", False):
        return False, ""
    fs = getattr(target, "full_sheet", None) or {}
    is_mythic = bool(
        getattr(target, "is_mythic", False)
        or (isinstance(fs, dict) and (fs.get("is_mythic") or fs.get("mythic_actions")))
        or entity_has_keyword(target, "risveglio mitico", "mythic trait", "tratto mitico")
    )
    if not is_mythic:
        return False, ""

    target.mythic_phase_active = True
    target.mythic_actions_unlocked = True
    mythic_hp = int((fs.get("mythic_hp") if isinstance(fs, dict) else None) or getattr(target, "max_hp", 100) or 100)
    target.hp = max(1, mythic_hp)
    target.legendary_actions_current = getattr(target, "legendary_actions_max", 3) or 3
    if isinstance(getattr(target, "conditions", None), list):
        target.conditions = [c for c in target.conditions if str(c).lower() not in ("morto", "dead", "incosciente", "unconscious", "prono", "prone", "incapacitato", "incapacitated")]
    if isinstance(fs, dict):
        fs["hp_current"] = target.hp
        fs["conditions"] = list(getattr(target, "conditions", []))
        fs["mythic_phase_active"] = True
    msg = f"🌟 [RISVEGLIO MITICO!] {target.name} scende a 0 PF ma scatena la sua **Fase 2 Mitica**: torna a {target.hp} PF e sblocca le Azioni Mitiche!"
    if game_state:
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        if hasattr(game_state, "log_dm_message"):
            game_state.log_dm_message(f"[BOSS] {msg}")
        broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
    return True, msg


def register_regional_effects(boss: Any, effects: Optional[List[str]] = None, game_state: Any = None) -> List[str]:
    fs = getattr(boss, "full_sheet", None) if boss else {}
    eff_list = list(effects or (fs.get("regional_effects") if isinstance(fs, dict) else []) or [])
    if game_state:
        if not hasattr(game_state, "active_regional_effects") or not isinstance(game_state.active_regional_effects, list):
            game_state.active_regional_effects = []
        for eff in eff_list:
            entry = {"boss": boss.name if boss else "Tana", "effect": str(eff)}
            if entry not in game_state.active_regional_effects:
                game_state.active_regional_effects.append(entry)
    return eff_list


# ==============================================================================
# 4. DAMAGE TRANSFER, DEATH BURST, PIETRIFICAZIONE MULTI-STADIO
# ==============================================================================

def apply_damage_transfer(target: Any, raw_dmg: int, damage_type: str, game_state: Any) -> Tuple[int, Optional[str]]:
    """
    MM Trasferimento Danno (Cloaker / Mantello / Roper):
    Se legato a una vittima, metà danno al mostro e metà al bersaglio vincolato.
    """
    if not target or raw_dmg <= 1 or not game_state:
        return raw_dmg, None
    tether_name = getattr(target, "damage_transfer_target", None)
    if not tether_name or not entity_has_keyword(target, "trasferimento del danno", "damage transfer"):
        if not tether_name:
            return raw_dmg, None
    other = game_state.find_player(tether_name)
    if not other or getattr(other, "hp", 0) <= 0:
        return raw_dmg, None
    half = raw_dmg // 2
    rem = raw_dmg - half
    other.hp = max(0, int(other.hp) - half)
    if isinstance(getattr(other, "full_sheet", None), dict):
        other.full_sheet["hp_current"] = other.hp
    note = f"🔗 [TRASFERIMENTO DANNO] {target.name} trasferisce {half} danni {damage_type} a {other.name}!"
    broadcast(game_state, make_chat_broadcast("Sistema", note))
    broadcast(game_state, make_player_stats_update(other.name, other.hp, other.max_hp, other.initiative, other.conditions, getattr(other, "temp_hp", 0)))
    return rem, note


def trigger_death_burst_on_zero_hp(creature: Any, game_state: Any) -> Optional[str]:
    """
    MM Esplosione alla Morte (Magmin, Mephit, Balor):
    Quando scende a 0 PF esplode causando danni in area con TS.
    """
    if not creature or not game_state or getattr(creature, "_death_burst_triggered", False):
        return None
    if not entity_has_keyword(creature, "esplosione alla morte", "death burst", "death throes", "spora mortale"):
        return None
    creature._death_burst_triggered = True

    entries = _collect_trait_entries(creature)
    desc = " ".join(e["desc"] for e in entries if any(k in (e["name"] + " " + e["desc"]).lower() for k in ("death", "esplosion", "mort")))
    m_dc = re.search(r'(?:dc|cd)\s*(\d+)', desc, re.IGNORECASE)
    dc = int(m_dc.group(1)) if m_dc else 11
    m_dice = re.search(r'\((\d+d\d+(?:\s*[+-]\s*\d+)?)\)', desc)
    dmg_formula = m_dice.group(1).replace(" ", "") if m_dice else "2d6"
    m_rad = re.search(r'(\d+)\s*(?:ft|feet|piedi)', desc, re.IGNORECASE)
    rad_hex = max(1, (int(m_rad.group(1)) // 5)) if m_rad else 2
    dmg_type = "Fuoco" if "fire" in desc.lower() or "fuoco" in desc.lower() else ("Acido" if "acid" in desc.lower() else "Forza")

    c_pos = getattr(creature, "position", None)
    g_type = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
    from server.rules.combat import apply_damage
    hit_logs = []
    for p in list(getattr(game_state, "players", [])):
        if p.name == creature.name or getattr(p, "hp", 0) <= 0:
            continue
        if c_pos and getattr(p, "position", None):
            d = grid_distance_3d(Hex(c_pos[0], c_pos[1]), Hex(p.position[0], p.position[1]), getattr(creature, "elevation", 0), getattr(p, "elevation", 0), grid_type=g_type)
            if d > rad_hex:
                continue
        mod = get_effective_save_bonus_from_dict(p, "DES")
        sv = roll_dice(f"1d20{'+' if mod >= 0 else ''}{mod}")["total"]
        raw = roll_dice(dmg_formula)["total"]
        app_d = raw // 2 if sv >= dc else raw
        fin, _, _, _ = apply_damage(p, app_d, damage_type=dmg_type, game_state=game_state)
        hit_logs.append(f"{p.name} (-{fin})")

    msg = f"💥 [ESPLOSIONE ALLA MORTE - {creature.name}] CD {dc} DES ({dmg_formula} {dmg_type}): {', '.join(hit_logs) if hit_logs else 'nessuna creatura nel raggio.'}"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    return msg


def apply_petrification_stage(target: Any, failed_save: bool, game_state: Any) -> str:
    """
    MM Pietrificazione a 2 stadi (Basilisco / Medusa / Gorgone):
    - 1° fallimento: Trattenuto mentre la carne inizia a pietrificarsi (stage=1)
    - 2° fallimento: Pietrificato permanentemente (stage=2)
    - Successo allo stage=1: l'effetto termina e stage torna 0.
    """
    if not target:
        return ""
    if not hasattr(target, "conditions") or not isinstance(target.conditions, list):
        target.conditions = []
    stage = int(getattr(target, "petrification_stage", 0) or 0)
    if failed_save:
        stage += 1
        target.petrification_stage = stage
        if stage == 1:
            if "Trattenuto" not in target.conditions:
                target.conditions.append("Trattenuto")
            msg = f"🪨 [PIETRIFICAZIONE STADIO 1] {target.name} inizia a tramutarsi in pietra (Trattenuto)! Ripeterà il TS a fine turno."
        else:
            if "Trattenuto" in target.conditions:
                target.conditions.remove("Trattenuto")
            if "Pietrificato" not in target.conditions:
                target.conditions.append("Pietrificato")
            msg = f"🗿 [PIETRIFICAZIONE COMPLETA] {target.name} fallisce il 2° TS ed è **PIETRIFICATO**!"
    else:
        target.petrification_stage = 0
        if "Trattenuto" in target.conditions:
            target.conditions.remove("Trattenuto")
        msg = f"✨ [PIETRIFICAZIONE SVENTATA] {target.name} supera il TS e si libera dal processo di pietrificazione!"
    if isinstance(getattr(target, "full_sheet", None), dict):
        target.full_sheet["conditions"] = list(target.conditions)
    if game_state:
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
    return msg


def handle_resolve_legendary_resistance_request(data: dict, player: Any, game_state: Any) -> None:
    """Risolve una scelta DM su PENDING_LEGENDARY_RES_PROMPT (use | decline)."""
    lr_id = str(data.get("pending_id") or data.get("id") or "")
    decision = str(data.get("decision", "use")).lower()
    pend = getattr(game_state, "pending_legendary_resistances", None)
    if not isinstance(pend, dict) or lr_id not in pend:
        return
    info = pend.pop(lr_id)
    target = game_state.find_player(info.get("target"))
    if not target:
        return
    if decision == "use" and getattr(target, "legendary_resistances_current", 0) > 0:
        target.legendary_resistances_current -= 1
        msg = f"👑 [RESISTENZA LEGGENDARIA ATTIVATA] {target.name} spende una Resistenza Leggendaria ({target.legendary_resistances_current}/{getattr(target, 'legendary_resistances_max', 3)} rimaste) e trasforma il TS {info.get('stat')} vs CD {info.get('dc')} ({info.get('source')}) in SUCCESSO!"
    else:
        msg = f"💀 [RESISTENZA NON USATA] {target.name} accetta il fallimento del TS {info.get('stat')} vs CD {info.get('dc')} ({info.get('source')})."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    if hasattr(game_state, "_trigger_gui_update"):
        game_state._trigger_gui_update()


def is_recharge_ability(action_dict: Any) -> bool:
    """Rileva se un'azione/tratto del mostro possiede la clausola Recharge (es. 5-6, 4-6, 6)."""
    if not isinstance(action_dict, dict):
        text = str(action_dict or "").lower()
    else:
        text = f"{action_dict.get('name', '')} {action_dict.get('desc', '')}".lower()
    return bool(re.search(r"(?:recharge|ricarica)\s*[456](?:[-–]6)?", text))


def mark_monster_ability_used(monster: Any, action_obj: Any) -> Tuple[bool, str]:
    """
    Segna un'abilità Recharge del mostro come spesa (`expended=True`) quando viene utilizzata.
    Ritorna (già_spesa, note).
    """
    if not monster or not is_recharge_ability(action_obj):
        return False, ""
    target_name = action_obj.get("name", "") if isinstance(action_obj, dict) else str(action_obj).split(".")[0].strip()
    fs = getattr(monster, "full_sheet", None)
    if not isinstance(fs, dict):
        return False, ""

    matched_item = None
    for list_key in ("actions", "special_abilities", "features"):
        lst = fs.get(list_key)
        if isinstance(lst, list):
            for entry in lst:
                if isinstance(entry, dict) and entry.get("name", "").lower() == target_name.lower():
                    matched_item = entry
                    break
        if matched_item:
            break

    if matched_item is None:
        r_list = getattr(monster, "recharge_abilities", None)
        if not isinstance(r_list, list):
            r_list = []
            monster.recharge_abilities = r_list
        for entry in r_list:
            if isinstance(entry, dict) and entry.get("name", "").lower() == target_name.lower():
                matched_item = entry
                break
        if matched_item is None:
            matched_item = {"name": target_name, "desc": action_obj.get("desc", "") if isinstance(action_obj, dict) else str(action_obj), "expended": False}
            r_list.append(matched_item)

    if matched_item.get("expended", False):
        return True, f"⚠️ '{target_name}' è ancora SCARICA (in attesa di Ricarica a inizio turno)!"

    matched_item["expended"] = True
    if isinstance(action_obj, dict):
        action_obj["expended"] = True
    return False, f"⏳ [RICARICA] '{target_name}' segnata come spesa (tirerà 1d6 all'inizio del prossimo turno)."


def check_swallow_internal_regurgitation(monster: Any, attacker: Any, damage_dealt: int, game_state: Any) -> Optional[str]:
    """
    MM Swallow (Inghiottito): se una creatura nello stomaco del mostro infligge >= soglia danni
    (default 20 o parsato dalla descrizione) in un singolo turno, il mostro tira un TS COS (CD 15 o parsata);
    se fallisce rigurgita tutte le creature ingoiate.
    """
    if not monster or not attacker or damage_dealt <= 0 or getattr(monster, "hp", 0) <= 0:
        return None
    if getattr(attacker, "swallowed_by", None) != monster.name:
        return None

    threshold = 20
    dc = 15
    fs = getattr(monster, "full_sheet", None) or {}
    for list_key in ("actions", "special_abilities", "features"):
        entries = fs.get(list_key) if isinstance(fs, dict) else None
        if isinstance(entries, list):
            for item in entries:
                txt = f"{item.get('name', '')} {item.get('desc', '')}" if isinstance(item, dict) else str(item)
                if "swallow" in txt.lower() or "ingoi" in txt.lower() or "inghiott" in txt.lower():
                    m_thr = re.search(r"(\d+)\s+(?:or\s+more\s+)?damage", txt, re.I) or re.search(r"almeno\s+(\d+)\s+danni", txt, re.I)
                    m_dc = re.search(r"DC\s*(\d+)\s+Constitution|CD\s*(\d+)\s+(?:su\s+)?(?:COS|Costituzione)", txt, re.I)
                    if m_thr:
                        threshold = max(1, int(m_thr.group(1)))
                    if m_dc:
                        dc = max(5, int(m_dc.group(1) or m_dc.group(2)))
                    break

    monster.swallow_damage_taken = int(getattr(monster, "swallow_damage_taken", 0) or 0) + int(damage_dealt)
    if monster.swallow_damage_taken < threshold:
        return None

    from common.item_modifiers import get_effective_save_bonus_from_dict
    from common.dice import roll_dice
    con_save = get_effective_save_bonus_from_dict(monster, "COS")
    sv = roll_dice(f"1d20{'+' if con_save >= 0 else ''}{con_save}")["total"]
    monster.swallow_damage_taken = 0

    if sv >= dc:
        msg = f"🐊 [STOMACO] {monster.name} subisce >= {threshold} danni interni ma supera TS COS ({sv} vs CD {dc}): trattiene le prede!"
        if game_state:
            broadcast(game_state, make_chat_broadcast("Sistema", msg))
        return msg

    if not game_state:
        return None
    reg_names = []
    for sw_v in getattr(game_state, "players", []):
        if getattr(sw_v, "swallowed_by", None) == monster.name:
            sw_v.swallowed_by = None
            if not hasattr(sw_v, "conditions") or not isinstance(sw_v.conditions, list):
                sw_v.conditions = []
            sw_v.conditions = [
                c for c in sw_v.conditions
                if not any(k in str(c).lower() for k in ("ingoi", "inghiott", "swallow", "accecat", "blinded", "trattenut", "restrained"))
            ]
            if "Prono" not in sw_v.conditions:
                sw_v.conditions.append("Prono")
            if getattr(monster, "position", None):
                sw_v.position = list(monster.position)
            reg_names.append(sw_v.name)
            broadcast(game_state, make_player_stats_update(sw_v.name, sw_v.hp, sw_v.max_hp, sw_v.initiative, sw_v.conditions, getattr(sw_v, "temp_hp", 0)))
    msg = f"🤢 [RIGURGITO MM] {monster.name} fallisce TS COS ({sv} vs CD {dc}) per i danni interni (>= {threshold}) e **rigurgita** {', '.join(reg_names) or 'la preda'} (cade Prono a terra)!"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    return msg


# ==============================================================================
# 2. MULTIATTACCO, RISUCCHIO VITA/FORZA, RUGGINE, SGUARDO PIETRIFICANTE & BEHOLDER
# ==============================================================================

_WORD_COUNTS = {
    "one": 1, "a": 1, "an": 1, "uno": 1, "una": 1, "un": 1,
    "two": 2, "due": 2, "twice": 2,
    "three": 3, "tre": 3,
    "four": 4, "quattro": 4,
    "five": 5, "cinque": 5,
    "six": 6, "sei": 6,
}

_ATK_SYNONYMS: Dict[str, Tuple[str, ...]] = {
    "bite": ("bite", "morso"),
    "claw": ("claw", "claws", "artiglio", "artigli"),
    "tail": ("tail", "coda"),
    "slam": ("slam", "schianto"),
    "sting": ("sting", "pungiglione"),
    "tentacle": ("tentacle", "tentacles", "tentacolo", "tentacoli"),
    "greatsword": ("greatsword", "spadone"),
    "longsword": ("longsword", "spada lunga"),
    "shortsword": ("shortsword", "spada corta"),
    "scimitar": ("scimitar", "scimitarra"),
    "greataxe": ("greataxe", "ascia bipenne"),
    "dagger": ("dagger", "pugnale"),
    "longbow": ("longbow", "arco lungo"),
    "javelin": ("javelin", "giavellotto"),
    "horn": ("horn", "horns", "corno", "corna"),
    "gore": ("gore", "incornata"),
    "beak": ("beak", "becco"),
    "hooves": ("hooves", "hoof", "zoccoli", "zoccolo"),
    "fist": ("fist", "fists", "pugno", "pugni"),
    "eye ray": ("eye ray", "eye rays", "raggio oculare", "raggi oculari"),
}


def _extract_action_attack_and_damage(act: Any) -> Tuple[str, Optional[int], Optional[str], str]:
    if isinstance(act, str):
        name = act.split(".")[0].strip()
        desc = act
        atk_b = None
        dmg_d = None
    else:
        name = str(act.get("name", "Attacco") or "Attacco").strip()
        desc = str(act.get("desc", act.get("description", "")) or "")
        atk_b = act.get("attack_bonus")
        dmg_d = act.get("damage_dice")
    if atk_b is None:
        m = re.search(r"([+-]?\d+)\s+(?:to\s+hit|per\s+colpire|al\s+colpo)", desc, re.IGNORECASE)
        if m:
            try:
                atk_b = int(m.group(1))
            except (ValueError, TypeError):
                atk_b = None
    if not dmg_d:
        m_d = re.search(r"\((\d+d\d+(?:\s*[+-]\s*\d+)?)\)", desc)
        if m_d:
            dmg_d = m_d.group(1).replace(" ", "")
    return name, (int(atk_b) if atk_b is not None else None), dmg_d, desc


def parse_monster_multiattack(monster: Any) -> List[Tuple[Dict[str, Any], int]]:
    """Parse Multiattack text into a list of (action_dict, attack_count)."""
    if not monster:
        return []
    fs = getattr(monster, "full_sheet", None) or {}
    actions = fs.get("actions") if isinstance(fs, dict) else None
    if not isinstance(actions, list) or not actions:
        return []

    multi_desc = ""
    candidates: List[Dict[str, Any]] = []
    for a in actions:
        a_dict = a if isinstance(a, dict) else {"name": str(a).split(".")[0].strip(), "desc": str(a)}
        nm = str(a_dict.get("name", "") or "").lower()
        if "multiatt" in nm:
            multi_desc += " " + str(a_dict.get("desc", a_dict.get("description", "")) or "")
        else:
            candidates.append(a_dict)

    if not multi_desc.strip() or not candidates:
        return []

    txt = multi_desc.lower()
    sequence: List[Tuple[Dict[str, Any], int]] = []
    matched_names = set()

    # Match "<count> [with its] <attack_name>" or "<count> <attack_name> attack(s)"
    for cand in candidates:
        c_name = str(cand.get("name", "") or "").strip()
        c_low = c_name.lower()
        aliases = {c_low}
        for k, syns in _ATK_SYNONYMS.items():
            if any(s in c_low for s in syns):
                aliases.update(syns)
        # Try matching count token right before any alias (allowing up to 3 filler words like "with its", "con il")
        found_count = 0
        for alias in sorted(aliases, key=len, reverse=True):
            pat = r"\b(" + "|".join(re.escape(w) for w in _WORD_COUNTS.keys()) + r"|\d+)\b(?:\s+\w+){0,3}\s+" + re.escape(alias) + r"\b"
            for m in re.finditer(pat, txt):
                tok = m.group(1)
                cnt = int(tok) if tok.isdigit() else _WORD_COUNTS.get(tok, 1)
                found_count += max(1, cnt)
            if found_count > 0:
                break
        if found_count > 0 and c_low not in matched_names:
            matched_names.add(c_low)
            sequence.append((cand, found_count))

    if not sequence:
        # Generic Multiattack like "makes two melee attacks" or "esegue tre attacchi"
        m_gen = re.search(
            r"\b(" + "|".join(re.escape(w) for w in _WORD_COUNTS.keys()) + r"|\d+)\b(?:\s+\w+){0,2}\s+(?:attacks?|attacchi?)",
            txt,
        )
        if m_gen:
            tok = m_gen.group(1)
            cnt = int(tok) if tok.isdigit() else _WORD_COUNTS.get(tok, 2)
            # Pick first candidate that looks like a weapon/natural attack
            primary = next(
                (c for c in candidates if _extract_action_attack_and_damage(c)[1] is not None),
                candidates[0],
            )
            sequence.append((primary, max(1, cnt)))

    return sequence


def execute_monster_multiattack(
    monster: Any,
    game_state: Any = None,
    target: Any = None,
) -> Dict[str, Any]:
    """Execute a monster's parsed Multiattack sequence in one click."""
    seq = parse_monster_multiattack(monster)
    if not seq:
        # Check Beholder eye rays fallback if Multiattack isn't physical
        fs = getattr(monster, "full_sheet", None) or {}
        actions_txt = str(fs.get("actions", "") if isinstance(fs, dict) else "").lower()
        if "eye ray" in actions_txt or "raggi oculari" in actions_txt:
            ray_res = roll_beholder_eye_rays(monster, targets=([target] if target else None), game_state=game_state, count=3)
            return {"ok": True, "beholder_rays": ray_res, "rolls": [], "total_damage": ray_res.get("total_damage", 0), "summary": ray_res["summary"]}
        return {"ok": False, "rolls": [], "total_damage": 0, "summary": f"Nessun Multiattacco parsabile per {getattr(monster, 'name', 'Mostro')}."}

    results: List[Dict[str, Any]] = []
    total_dmg = 0
    lines: List[str] = [f"⚔️ **[MULTIATTACCO - {monster.name}]**" + (f" vs {target.name} (CA {getattr(target, 'ac', 10)})" if target else "")]
    target_ac = int(getattr(target, "ac", 10) or 10) if target else None

    for act, count in seq:
        nm, atk_b, dmg_d, desc = _extract_action_attack_and_damage(act)
        for _ in range(count):
            d20_res = roll_dice("1d20")
            nat = int(d20_res["rolls"][0])
            is_crit = (nat == 20)
            atk_tot = nat + int(atk_b or 0) if atk_b is not None else None

            hit = True
            if target_ac is not None and atk_tot is not None:
                hit = is_crit or (nat != 1 and atk_tot >= target_ac)

            dmg_tot = 0
            if dmg_d:
                dr = roll_dice(dmg_d)
                dmg_tot = int(dr["total"])
                if is_crit:
                    # Roll weapon dice twice on critical hit
                    m_dice_only = re.match(r"(\d+d\d+)", dmg_d)
                    if m_dice_only:
                        dmg_tot += int(roll_dice(m_dice_only.group(1))["total"])

            applied = 0
            eff_notes: List[str] = []
            if target and hit and dmg_tot > 0 and game_state is not None:
                from server.rules.combat import apply_damage
                d_type = "Tagliente"
                dl = desc.lower()
                if "necrotic" in dl or "necrot" in dl:
                    d_type = "Necrotico"
                elif "piercing" in dl or "perforan" in dl:
                    d_type = "Perforante"
                elif "bludgeoning" in dl or "contundent" in dl:
                    d_type = "Contundente"
                elif "fire" in dl or "fuoco" in dl:
                    d_type = "Fuoco"
                elif "acid" in dl or "acido" in dl:
                    d_type = "Acido"
                elif "poison" in dl or "veleno" in dl:
                    d_type = "Veleno"
                applied, _, _, dmg_hp = apply_damage(target, dmg_tot, damage_type=d_type, game_state=game_state, is_crit=is_crit, attacker=monster)
                eff_notes = apply_monster_special_hit_effects(monster, target, nm, desc, dmg_hp or applied, game_state=game_state)
                total_dmg += applied
            elif not target:
                total_dmg += dmg_tot

            atk_str = f"TpC {atk_tot} (d20={nat})" if atk_tot is not None else "Effetto"
            hit_lbl = "CRIT!" if is_crit else ("COLPISCE" if hit else "MANCA")
            dmg_str = f"{applied if target else dmg_tot} danni" if dmg_d else ""
            row_txt = f"• {nm}: {atk_str}" + (f" [{hit_lbl}]" if target else "") + (f" -> {dmg_str}" if (dmg_d and hit) else "")
            if eff_notes:
                row_txt += " " + " ".join(eff_notes)
            lines.append(row_txt)
            results.append({"action": nm, "attack_total": atk_tot, "nat": nat, "is_crit": is_crit, "hit": hit, "damage": applied if target else dmg_tot})

    summary = "\n".join(lines)
    if game_state:
        broadcast(game_state, make_chat_broadcast("DM", summary))
        if target:
            broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, getattr(target, "conditions", []), getattr(target, "temp_hp", 0)))
            broadcast(game_state, make_game_state(game_state.get_state_dict()))
    return {"ok": True, "rolls": results, "total_damage": total_dmg, "summary": summary}


BEHOLDER_EYE_RAYS: List[Tuple[int, str, str, str, int, Optional[str], Optional[str], str]] = [
    (1, "Raggio di Charme", "Charm Ray", "SAG", 16, None, None, "Affascinato per 1 ora"),
    (2, "Raggio Paralizzante", "Paralyzing Ray", "COS", 16, None, None, "Paralizzato per 1 minuto"),
    (3, "Raggio di Paura", "Fear Ray", "SAG", 16, None, None, "Spaventato per 1 minuto"),
    (4, "Raggio di Lentezza", "Slowing Ray", "DES", 16, None, None, "Velocità dimezzata, niente reazioni, 1 attacco/turno"),
    (5, "Raggio di Debilitazione", "Enervation Ray", "COS", 16, "8d8", "Necrotico", "Danni Necrotici (metà se supera)"),
    (6, "Raggio Telecinetico", "Telekinetic Ray", "FOR", 16, None, None, "Spostato fino a 9 m e Trattenuto"),
    (7, "Raggio del Sonno", "Sleep Ray", "SAG", 16, None, None, "Addormentato (Incosciente) per 1 minuto"),
    (8, "Raggio di Pietrificazione", "Petrification Ray", "DES", 16, None, None, "Pietrificazione a 2 stadi"),
    (9, "Raggio di Disintegrazione", "Disintegration Ray", "DES", 16, "10d8", "Forza", "Polverizzato se scende a 0 PF"),
    (10, "Raggio della Morte", "Death Ray", "DES", 16, "10d10", "Necrotico", "Muore istantaneamente se scende a 0 PF"),
]


def roll_beholder_eye_rays(
    beholder: Any,
    targets: Optional[List[Any]] = None,
    game_state: Any = None,
    count: int = 3,
    forced_indices: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Roll 3 non-duplicate random Beholder Eye Rays (MM p. 28) and optionally resolve them against targets."""
    import random as _rand_b

    if forced_indices:
        picks = [max(1, min(10, int(x))) for x in forced_indices][:10]
    else:
        picks = _rand_b.sample(range(1, 11), k=max(1, min(10, int(count or 3))))

    b_name = getattr(beholder, "name", "Beholder")
    lines = [f"👁️ **[RAGGI OCULARI DEL BEHOLDER - {b_name}]**"]
    rays_out: List[Dict[str, Any]] = []
    total_dmg = 0

    for idx_pos, ray_num in enumerate(picks):
        _, name_it, name_en, save_stat, dc, dmg_dice, dmg_type, note = BEHOLDER_EYE_RAYS[ray_num - 1]
        tgt = targets[idx_pos % len(targets)] if targets else None
        raw_dmg = roll_dice(dmg_dice)["total"] if dmg_dice else 0
        saved = None
        final_dmg = 0

        if tgt is not None:
            s_mod = get_effective_save_bonus_from_dict(tgt, save_stat)
            s_roll = roll_dice(f"1d20{'+' if s_mod >= 0 else ''}{s_mod}")["total"]
            saved = s_roll >= dc
            if ray_num == 8:
                apply_petrification_stage(tgt, failed_save=(not saved), game_state=game_state)
            elif ray_num in (5, 9, 10):
                eff_raw = (raw_dmg // 2) if (ray_num == 5 and saved) else (0 if saved else raw_dmg)
                if eff_raw > 0 and game_state is not None:
                    from server.rules.combat import apply_damage
                    final_dmg, _, _, _ = apply_damage(tgt, eff_raw, damage_type=dmg_type or "Forza", game_state=game_state, attacker=beholder)
                    total_dmg += final_dmg
                else:
                    final_dmg = eff_raw
            elif not saved:
                cond_map = {1: "Affascinato", 2: "Paralizzato", 3: "Spaventato", 4: "Rallentato", 6: "Trattenuto", 7: "Incosciente"}
                cond = cond_map.get(ray_num)
                if cond:
                    if not hasattr(tgt, "conditions") or not isinstance(tgt.conditions, list):
                        tgt.conditions = []
                    if cond not in tgt.conditions:
                        tgt.conditions.append(cond)
            line = f"• d10={ray_num} **{name_it}** ({name_en}) vs {tgt.name}: TS {save_stat} {s_roll} vs CD {dc} -> {'Superato' if saved else 'FALLITO'}"
            if dmg_dice:
                line += f" ({final_dmg} danni {dmg_type})"
            elif not saved:
                line += f" [{note}]"
        else:
            line = f"• d10={ray_num} **{name_it}** (TS {save_stat} CD {dc}): {note}" + (f" [{dmg_dice} -> {raw_dmg} {dmg_type}]" if dmg_dice else "")
        lines.append(line)
        rays_out.append({"ray_number": ray_num, "name": name_it, "save_stat": save_stat, "dc": dc, "saved": saved, "damage": final_dmg or raw_dmg})

    summary = "\n".join(lines)
    if game_state:
        broadcast(game_state, make_chat_broadcast("DM", summary))
        if targets:
            broadcast(game_state, make_game_state(game_state.get_state_dict()))
    return {"rays": rays_out, "total_damage": total_dmg, "summary": summary}


def toggle_antimagic_cone(
    beholder: Any,
    game_state: Any,
    active: bool = True,
    direction_deg: float = 0.0,
    range_hexes: int = 30,
) -> bool:
    """Activate/update or deactivate a Beholder's 150-ft Antimagic Cone (MM p. 28)."""
    if not game_state or not beholder:
        return False
    if not hasattr(game_state, "antimagic_cones") or not isinstance(game_state.antimagic_cones, dict):
        game_state.antimagic_cones = {}
    if not active:
        game_state.antimagic_cones.pop(beholder.name, None)
        return False
    game_state.antimagic_cones[beholder.name] = {
        "caster": beholder.name,
        "active": True,
        "direction_deg": float(direction_deg) % 360.0,
        "range_hexes": max(1, int(range_hexes or 30)),
    }
    return True


def is_in_beholder_antimagic_cone(entity: Any, game_state: Any) -> bool:
    """Return True if entity stands inside an active Beholder Antimagic Cone."""
    import math

    if not entity or not game_state:
        return False
    cones = getattr(game_state, "antimagic_cones", None)
    if not isinstance(cones, dict) or not cones:
        return False
    epos = getattr(entity, "position", None)
    if not epos or len(epos) < 2:
        return False
    g_type = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")

    for c_name, cone in list(cones.items()):
        if not isinstance(cone, dict) or not cone.get("active", True):
            continue
        caster = game_state.find_player(c_name) if hasattr(game_state, "find_player") else None
        if not caster or getattr(caster, "hp", 0) <= 0 or is_incapacitated_entity(caster):
            continue
        if caster is entity or getattr(entity, "name", None) == caster.name:
            continue
        cpos = getattr(caster, "position", None)
        if not cpos or len(cpos) < 2:
            continue
        dist = grid_distance_3d(Hex(cpos[0], cpos[1]), Hex(epos[0], epos[1]), getattr(caster, "elevation", 0), getattr(entity, "elevation", 0), grid_type=g_type)
        if dist <= 0 or dist > int(cone.get("range_hexes", 30) or 30):
            continue
        # Compute axial/grid vector angle in degrees
        dq = epos[0] - cpos[0]
        dr = epos[1] - cpos[1]
        if g_type == "square":
            vx, vy = float(dq), float(dr)
        else:
            vx = 1.5 * float(dq)
            vy = math.sqrt(3.0) * (float(dr) + float(dq) / 2.0)
        angle = math.degrees(math.atan2(vy, vx)) % 360.0
        cone_dir = float(cone.get("direction_deg", 0.0) or 0.0) % 360.0
        diff = abs((angle - cone_dir + 180.0) % 360.0 - 180.0)
        if diff <= 30.0:
            return True
    return False


def has_petrifying_gaze(entity: Any) -> bool:
    return entity_has_keyword(entity, "sguardo pietrificante", "petrifying gaze")


def check_petrifying_gaze_at_turn_start(creature: Any, game_state: Any, forced_roll: Optional[int] = None) -> Optional[str]:
    """MM Basilisk/Medusa Petrifying Gaze: automatic CON save at start of turn within 30ft unless averting eyes."""
    if not creature or not game_state or getattr(creature, "hp", 0) <= 0:
        return None
    if is_incapacitated_entity(creature):
        return None
    c_pos = getattr(creature, "position", None)
    if not c_pos or len(c_pos) < 2:
        return None
    c_party = bool(getattr(creature, "is_party_member", False) or getattr(creature, "conn", None))
    g_type = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")

    for other in list(getattr(game_state, "players", [])):
        if other.name == creature.name or getattr(other, "hp", 0) <= 0 or is_incapacitated_entity(other):
            continue
        o_party = bool(getattr(other, "is_party_member", False) or getattr(other, "conn", None))
        if o_party == c_party or not has_petrifying_gaze(other):
            continue
        o_pos = getattr(other, "position", None)
        if not o_pos or len(o_pos) < 2:
            continue
        dist = grid_distance_3d(Hex(c_pos[0], c_pos[1]), Hex(o_pos[0], o_pos[1]), getattr(creature, "elevation", 0), getattr(other, "elevation", 0), grid_type=g_type)
        if dist > 6.0:
            continue
        if getattr(creature, "averting_eyes", False):
            note = f"👁️ [SGUARDO PIETRIFICANTE] {creature.name} distoglie lo sguardo da {other.name} e evita il TS!"
            broadcast(game_state, make_chat_broadcast("Sistema", note))
            return note
        # Parse DC from monster trait (default Basilisk 12, Medusa 14)
        dc = 12
        for entry in _collect_trait_entries(other):
            txt = f"{entry['name']} {entry['desc']}"
            if "petrifying gaze" in txt.lower() or "sguardo pietrificante" in txt.lower():
                m_dc = re.search(r"(?:dc|cd)\s*(\d+)", txt, re.I)
                if m_dc:
                    dc = int(m_dc.group(1))
                break
        con_mod = get_effective_save_bonus_from_dict(creature, "COS")
        d20 = int(forced_roll) if forced_roll is not None else roll_dice("1d20")["total"]
        tot = d20 + con_mod
        return apply_petrification_stage(creature, failed_save=(tot < dc), game_state=game_state)
    return None


def _adjust_entity_str(target: Any, delta: int) -> int:
    """Adjust FOR/STR on attributes / full_sheet and return resulting STR score."""
    attrs = getattr(target, "attributes", None)
    if not isinstance(attrs, dict):
        attrs = {}
        target.attributes = attrs
    cur = int(attrs.get("FOR", attrs.get("STR", 10)) or 10)
    fs = getattr(target, "full_sheet", None)
    if isinstance(fs, dict) and isinstance(fs.get("attributes"), dict) and "FOR" not in attrs and "STR" not in attrs:
        cur = int(fs["attributes"].get("FOR", fs["attributes"].get("STR", 10)) or 10)
    new_val = cur + int(delta)
    if "STR" in attrs and "FOR" not in attrs:
        attrs["STR"] = new_val
    else:
        attrs["FOR"] = new_val
    if isinstance(fs, dict):
        fs.setdefault("attributes", {})
        if "STR" in fs["attributes"] and "FOR" not in fs["attributes"]:
            fs["attributes"]["STR"] = new_val
        else:
            fs["attributes"]["FOR"] = new_val
    return new_val


def apply_monster_special_hit_effects(
    attacker: Any,
    target: Any,
    attack_name: str = "",
    attack_desc: str = "",
    damage_dealt: int = 0,
    game_state: Any = None,
    forced_save_roll: Optional[int] = None,
    forced_drain_roll: Optional[int] = None,
) -> List[str]:
    """Apply MM Life Drain, Strength Drain, and Rust/Corrode Metal on monster attack hit."""
    if not attacker or not target:
        return []
    combined = f"{attack_name} {attack_desc}".lower()
    notes: List[str] = []

    # 1. Life Drain (Risucchio di Vita): CON save or max_hp reduced by damage dealt
    if "life drain" in combined or "risucchio di vita" in combined:
        m_dc = re.search(r"(?:dc|cd)\s*(\d+)", combined, re.I)
        dc = int(m_dc.group(1)) if m_dc else 13
        con_mod = get_effective_save_bonus_from_dict(target, "COS")
        d20 = int(forced_save_roll) if forced_save_roll is not None else roll_dice("1d20")["total"]
        tot = d20 + con_mod
        if tot < dc and damage_dealt > 0:
            red = int(damage_dealt)
            target.life_drain_reduction = int(getattr(target, "life_drain_reduction", 0) or 0) + red
            target.max_hp = max(0, int(getattr(target, "max_hp", 1) or 0) - red)
            target.hp = min(int(getattr(target, "hp", 0) or 0), target.max_hp)
            if isinstance(getattr(target, "full_sheet", None), dict):
                target.full_sheet["max_hp"] = target.max_hp
                target.full_sheet["hp_max"] = target.max_hp
                target.full_sheet["hp_current"] = target.hp
            if target.max_hp <= 0:
                if not hasattr(target, "conditions") or not isinstance(target.conditions, list):
                    target.conditions = []
                if "Morto" not in target.conditions:
                    target.conditions.append("Morto")
                notes.append(f"💀 [RISUCCHIO DI VITA] {target.name} fallisce TS COS ({tot} vs CD {dc}): PF Max -> 0, MUORE!")
            else:
                notes.append(f"🩸 [RISUCCHIO DI VITA] {target.name} fallisce TS COS ({tot} vs CD {dc}): -{red} PF Max (ora {target.max_hp})")
        else:
            notes.append(f"🛡️ [Risucchio di Vita] {target.name} supera TS COS ({tot} vs CD {dc}).")

    # 2. Strength Drain (Risucchio di Forza): Shadow -1d4 STR; dies at STR <= 0
    if "strength drain" in combined or "risucchio di forza" in combined:
        m_d = re.search(r"(\d+d\d+)", combined)
        formula = m_d.group(1) if m_d else "1d4"
        drain = int(forced_drain_roll) if forced_drain_roll is not None else roll_dice(formula)["total"]
        new_str = _adjust_entity_str(target, -drain)
        target.strength_drain_penalty = int(getattr(target, "strength_drain_penalty", 0) or 0) + drain
        if new_str <= 0:
            target.hp = 0
            if not hasattr(target, "conditions") or not isinstance(target.conditions, list):
                target.conditions = []
            if "Morto" not in target.conditions:
                target.conditions.append("Morto")
            notes.append(f"👤 [RISUCCHIO DI FORZA] {target.name} perde -{drain} FOR (FOR -> {new_str} <= 0): MUORE e rinascerà come Ombra!")
        else:
            notes.append(f"👤 [RISUCCHIO DI FORZA] {target.name} perde -{drain} FOR (ora {new_str})")

    # 3. Corrode / Rust Armor on monster hit (Rust Monster Antennae / Black Pudding Pseudopod)
    has_rust_trait = entity_has_keyword(attacker, "corrode metal", "rust metal", "corrodere il metallo", "arrugginire il metallo")
    if any(k in combined for k in ("corrod", "ruggine", "rust", "antennae", "antenne")) or (has_rust_trait and "pseudopod" in combined):
        cur_pen = int(getattr(target, "rust_ac_penalty", 0) or 0) + 1
        target.rust_ac_penalty = cur_pen
        target.ac = max(10, int(getattr(target, "ac", 10) or 10) - 1)
        if cur_pen >= 5:
            notes.append(f"🦀 [CORROSIONE ARMATURA] L'armatura metallica di {target.name} si sbriciola (-{cur_pen} cumulativo, distrutta! CA {target.ac})")
        else:
            notes.append(f"🦀 [CORROSIONE ARMATURA] Armatura di {target.name} corrosa (-1 CA permanente, ora CA {target.ac})")

    if notes and game_state and isinstance(getattr(target, "full_sheet", None), dict):
        target.full_sheet["conditions"] = list(getattr(target, "conditions", []) or [])
    return notes


def apply_rust_metal_melee_retaliation(
    attacker: Any,
    target: Any,
    is_ranged: bool = False,
    is_magical: bool = False,
    is_spell: bool = False,
) -> Optional[str]:
    """MM Rust Metal / Corrosive Form: nonmagical metal melee weapon suffers cumulative -1 damage penalty, destroyed at -5."""
    if not attacker or not target or is_ranged or is_magical or is_spell:
        return None
    if not entity_has_keyword(target, "rust metal", "corrode metal", "corrosive form", "arrugginire il metallo", "forma corrosiva"):
        return None
    pen = int(getattr(attacker, "rust_weapon_penalty", 0) or 0) + 1
    attacker.rust_weapon_penalty = pen
    if pen >= 5:
        return f"🦀 [METALLO CORROSO] L'arma non magica di {attacker.name} raggiunge -{pen} ai danni e si DISTRUGGE!"
    return f"🦀 [METALLO CORROSO] L'arma non magica di {attacker.name} subisce -1 cumulativo ai danni (-{pen} totale)."


def restore_drain_penalties(player: Any, rest_type: str = "long") -> None:
    """Restore MM Strength Drain (short/long rest) and Life Drain Max HP (long rest)."""
    if not player:
        return
    s_pen = int(getattr(player, "strength_drain_penalty", 0) or 0)
    if s_pen > 0:
        _adjust_entity_str(player, s_pen)
        player.strength_drain_penalty = 0
    if str(rest_type).lower() == "long":
        hp_red = int(getattr(player, "life_drain_reduction", 0) or 0)
        if hp_red > 0:
            player.max_hp = int(getattr(player, "max_hp", 0) or 0) + hp_red
            player.hp = min(player.max_hp, int(getattr(player, "hp", 0) or 0) + hp_red)
            player.life_drain_reduction = 0
            if isinstance(getattr(player, "full_sheet", None), dict):
                player.full_sheet["max_hp"] = player.max_hp
                player.full_sheet["hp_max"] = player.max_hp
                player.full_sheet["hp_current"] = player.hp
