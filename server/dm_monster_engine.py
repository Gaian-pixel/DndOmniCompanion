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
