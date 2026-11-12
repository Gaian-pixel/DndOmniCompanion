"""
server/rules/class_abilities.py - Privilegi di Classe attivi, Talenti, Incantesimi speciali,
Tratti Mostri MM e Regole Opzionali DMG (D&D 5e RAW).
"""

import random
import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

from common.protocol import (
    make_chat_broadcast, make_error_reply, make_player_stats_update,
    make_game_state, make_prompt_save
)
from common.hex_utils import Hex, hex_distance, grid_distance
from common.network_utils import send_message, broadcast
from common.i18n import is_condition_active
from common.dice import roll_dice
from common.item_modifiers import get_effective_attribute_from_dict, get_effective_save_bonus_from_dict
from common.dnd5e_tables import (
    entity_has_keyword, entity_get_class_level, entity_get_total_level,
    entity_get_attr_mod, entity_find_resource, entity_spend_resource,
    roll_system_shock, roll_lingering_injury, roll_madness,
    DMG_POISONS, DMG_DISEASES, roll_chase_complication, get_max_free_dashes,
    get_breath_hold_rounds, get_suffocation_rounds
)


def _sync_sheet_conditions(player):
    """Sincronizza condizioni su player.full_sheet se presente."""
    if isinstance(getattr(player, "full_sheet", None), dict):
        player.full_sheet["conditions"] = list(getattr(player, "conditions", []))
        player.full_sheet["hp_current"] = getattr(player, "hp", 10)
        player.full_sheet["temp_hp"] = getattr(player, "temp_hp", 0)
        player.full_sheet["exhaustion_level"] = getattr(player, "exhaustion_level", 0)


def _is_dm(player) -> bool:
    return player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None


def _get_target_or_self(data, player, game_state):
    target_name = data.get("target_name") or data.get("player_name")
    if target_name and game_state:
        return game_state.find_player(target_name)
    return player


def _check_surprised_block(player, game_state, action_label="agire") -> bool:
    """PHB p. 189: Se Sorpreso nel Round 1, blocca movimento/azioni."""
    if not player:
        return False
    is_surp = getattr(player, "surprised", False) or any(
        str(c).lower() in ("sorpreso", "surprised") for c in getattr(player, "conditions", [])
    )
    if is_surp and getattr(game_state, "combat_active", False):
        msg = f"😱 {player.name} è SORPRESO al 1° turno e non può {action_label} fino alla fine del turno (PHB p. 189)!"
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(msg))
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        return True
    return False


# ==============================================================================
# PALADIN: AURA OF COURAGE & LAY ON HANDS
# ==============================================================================

def is_immune_to_frightened_by_aura(entity, game_state) -> Tuple[bool, Optional[str]]:
    """
    PHB p. 85 (Aura di Coraggio - Paladino Lv 10+):
    Tu e gli alleati amichevoli entro 10 ft (2 celle; 30 ft / 6 celle al 18°) non potete essere Spaventati
    finché il Paladino è cosciente.
    """
    if not entity or not game_state:
        return False, None
    if entity_has_keyword(entity, "aura di coraggio", "aura of courage", "immune spaventato", "immune to frightened"):
        pal_lvl = entity_get_class_level(entity, "paladino", "paladin")
        if pal_lvl == 0 or pal_lvl >= 10:
            if getattr(entity, "hp", 0) > 0:
                return True, getattr(entity, "name", "Aura di Coraggio")

    pos_e = getattr(entity, "position", None)
    if not pos_e:
        return False, None
    hex_e = Hex(pos_e[0], pos_e[1])
    is_party = getattr(entity, "is_party_member", False) or getattr(entity, "is_companion", False)
    grid_type = game_state.current_map.get("grid_type", "hex") if getattr(game_state, "current_map", None) else "hex"

    for p in getattr(game_state, "players", []):
        if getattr(p, "hp", 0) <= 0:
            continue
        p_party = getattr(p, "is_party_member", False) or getattr(p, "is_companion", False)
        if p_party != is_party:
            continue
        pal_lvl = entity_get_class_level(p, "paladino", "paladin")
        has_feat_courage = pal_lvl >= 10 or entity_has_keyword(p, "aura di coraggio", "aura of courage")
        if not has_feat_courage:
            continue
        conds = [str(c).lower() for c in getattr(p, "conditions", [])]
        if any(c in ("incosciente", "unconscious", "incapacitato", "incapacitated", "morto", "dead") for c in conds):
            continue
        pos_p = getattr(p, "position", None)
        if not pos_p:
            continue
        max_hexes = 6 if pal_lvl >= 18 else 2
        if grid_distance(Hex(pos_p[0], pos_p[1]), hex_e, grid_type) <= max_hexes:
            return True, p.name
    return False, None


def handle_lay_on_hands_request(data, player, game_state):
    """Paladino - Imposizione delle Mani (PHB p. 84): cura X PF esatti o spende 5 PF per curare Malattia/Veleno."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    if _check_surprised_block(actor, game_state, "usare Imposizione delle Mani"):
        return
    target = _get_target_or_self(data, actor, game_state) or actor
    mode = data.get("mode", "heal")  # "heal" | "cure"
    res = entity_find_resource(actor, "mani curative", "lay on hands", "imposizione")
    if not res:
        pal_lvl = entity_get_class_level(actor, "paladino", "paladin")
        if pal_lvl <= 0:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Imposizione delle Mani richiede livelli da Paladino."))
            return
        pool_max = pal_lvl * 5
        res = {"name": "Mani Curative (Lay on Hands)", "current": pool_max, "max": pool_max, "reset_on": "long"}
        if isinstance(getattr(actor, "full_sheet", None), dict):
            actor.full_sheet.setdefault("custom_resources", []).append(res)

    cur_pool = int(res.get("current", 0) or 0)
    if mode == "cure":
        cost = 5
        if cur_pool < cost:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply(f"Pool Mani Curative insufficiente ({cur_pool}/5 richiesti)."))
            return
        ok, new_cur, mx = entity_spend_resource(actor, ("mani curative", "lay on hands", "imposizione"), cost)
        if not ok:
            return
        removed = []
        if hasattr(target, "conditions") and isinstance(target.conditions, list):
            for c in list(target.conditions):
                if any(k in str(c).lower() for k in ("avvelenat", "poison", "malatt", "diseas")):
                    target.conditions.remove(c)
                    removed.append(c)
        if hasattr(target, "diseases") and isinstance(target.diseases, list) and target.diseases:
            removed.extend(target.diseases)
            target.diseases = []
        _sync_sheet_conditions(target)
        msg = f"🙏 [IMPOSIZIONE DELLE MANI] {actor.name} spende 5 PF dal pool ({new_cur}/{mx} rimasti) su {target.name} per neutralizzare Veleno/Malattia ({', '.join(removed) if removed else 'purificato'})!"
    else:
        t_fs_lh = getattr(target, "full_sheet", None) or {}
        t_type_lh = (str(t_fs_lh.get("type", "")) + " " + str(target.name)).lower()
        if getattr(target, "is_object", False) or any(k in t_type_lh for k in ("costrutto", "construct", "non morto", "non-morto", "undead", "golem", "scheletro", "skeleton", "zombie")):
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Imposizione delle Mani non ha effetto su Non Morti o Costrutti (PHB p. 84)."))
            return
        amount = max(1, int(data.get("amount", 5) or 5))
        if cur_pool < amount:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply(f"Pool Mani Curative insufficiente ({cur_pool}/{amount} richiesti)."))
            return
        ok, new_cur, mx = entity_spend_resource(actor, ("mani curative", "lay on hands", "imposizione"), amount)
        if not ok:
            return
        old_hp = target.hp
        target.hp = min(target.max_hp, target.hp + amount)
        healed = target.hp - old_hp
        if old_hp == 0 and target.hp > 0:
            target.conditions = [c for c in getattr(target, "conditions", []) if c not in ("Incosciente", "Stabilizzato")]
        _sync_sheet_conditions(target)
        msg = f"✨ [IMPOSIZIONE DELLE MANI] {actor.name} cura {target.name} di {healed} PF (PV: {target.hp}/{target.max_hp} | Pool: {new_cur}/{mx})."

    actor.has_acted_this_turn = True
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(msg)
    game_state._trigger_gui_update()


# ==============================================================================
# BARBARIAN: RECKLESS ATTACK & RELENTLESS RAGE
# ==============================================================================

def handle_reckless_attack_request(data, player, game_state):
    """Barbaro Lv 2+ - Attacco Irruento (PHB p. 48): Vantaggio ai TxC in mischia FOR, nemici hanno Vantaggio contro il Barbaro fino al prossimo turno."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    if _check_surprised_block(actor, game_state, "usare Attacco Irruento"):
        return
    barb_lvl = entity_get_class_level(actor, "barbar", "barbarian")
    if barb_lvl < 2 and not entity_has_keyword(actor, "attacco irruento", "reckless attack"):
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply("Attacco Irruento richiede Barbaro Lv 2+."))
        return
    active_flag = bool(data.get("active", True))
    actor.reckless_attack_active = active_flag
    if not hasattr(actor, "conditions"):
        actor.conditions = []
    if active_flag and "Attacco Irruento" not in actor.conditions:
        actor.conditions.append("Attacco Irruento")
    elif not active_flag:
        actor.conditions = [c for c in actor.conditions if c not in ("Attacco Irruento", "Reckless Attack")]
    _sync_sheet_conditions(actor)
    msg = (
        f"🪓 [ATTACCO IRRUENTO] {actor.name} attacca con furia cieca: Vantaggio agli attacchi in mischia FOR in questo turno, ma gli attacchi contro {actor.name} hanno Vantaggio fino al suo prossimo turno!"
        if active_flag else f"🪓 {actor.name} disattiva Attacco Irruento."
    )
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(actor.name, actor.hp, actor.max_hp, actor.initiative, actor.conditions, getattr(actor, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(msg)


# ==============================================================================
# BARD: BARDIC INSPIRATION & SONG OF REST
# ==============================================================================

def get_bardic_inspiration_die(bard_level: int) -> str:
    if bard_level >= 15:
        return "d12"
    if bard_level >= 10:
        return "d10"
    if bard_level >= 5:
        return "d8"
    return "d6"


def handle_bardic_inspiration_request(data, player, game_state):
    """
    Bardo - Ispirazione Bardica (PHB p. 53):
    - action='grant': spende Azione Bonus + 1 uso risorsa e assegna dado d6/d8/d10/d12 al bersaglio alleato.
    - action='spend': il bersaglio spende il dado ricevuto e ottiene il tiro extra da aggiungere al proprio check/attacco/TS.
    """
    action = data.get("action", "grant")
    if str(action).lower() in ("spend", "use", "usa"):
        actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
        if not actor:
            return
        die = getattr(actor, "bardic_inspiration_die", None)
        if not die:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Non possiedi alcun dado di Ispirazione Bardica attivo."))
            return
        roll_res = roll_dice(f"1{die}")
        bonus_val = roll_res["total"]
        actor.bardic_inspiration_die = None
        if hasattr(actor, "conditions"):
            actor.conditions = [c for c in actor.conditions if not str(c).startswith("Ispirazione Bardica")]
        _sync_sheet_conditions(actor)
        msg = f"🎵 [ISPIRAZIONE BARDICA SPESA] {actor.name} consuma il dado [{die}] e aggiunge +{bonus_val} al tiro!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_player_stats_update(actor.name, actor.hp, actor.max_hp, actor.initiative, actor.conditions, getattr(actor, "temp_hp", 0)))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    if _check_surprised_block(actor, game_state, "concedere Ispirazione Bardica"):
        return
    target = _get_target_or_self(data, actor, game_state)
    if not target or target.name == actor.name:
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply("Devi selezionare un alleato diverso da te per l'Ispirazione Bardica."))
        return
    bard_lvl = entity_get_class_level(actor, "bardo", "bard")
    if bard_lvl <= 0 and not entity_has_keyword(actor, "ispirazione bardica", "bardic inspiration"):
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply("Ispirazione Bardica richiede livelli da Bardo."))
        return
    ok, new_cur, mx = entity_spend_resource(actor, ("ispirazione bardica", "bardic inspiration"), 1)
    if not ok:
        if entity_find_resource(actor, "ispirazione bardica", "bardic inspiration") is None:
            cha_mod = max(1, entity_get_attr_mod(actor, "CAR"))
            res = {"name": "Ispirazione Bardica", "current": max(0, cha_mod - 1), "max": cha_mod, "reset_on": "short" if bard_lvl >= 5 else "long"}
            if isinstance(getattr(actor, "full_sheet", None), dict):
                actor.full_sheet.setdefault("custom_resources", []).append(res)
            new_cur, mx = res["current"], res["max"]
        else:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Usi di Ispirazione Bardica esauriti!"))
            return
    die = get_bardic_inspiration_die(max(1, bard_lvl))
    target.bardic_inspiration_die = die
    if not hasattr(target, "conditions"):
        target.conditions = []
    target.conditions = [c for c in target.conditions if not str(c).startswith("Ispirazione Bardica")]
    target.conditions.append(f"Ispirazione Bardica ({die})")
    actor.bonus_action_used_this_turn = True
    _sync_sheet_conditions(target)
    msg = f"🎶 [ISPIRAZIONE BARDICA] {actor.name} (Azione Bonus) concede un dado {die} a {target.name}! ({new_cur}/{mx} usi rimasti)"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(msg)


# ==============================================================================
# CLERIC: TURN / DESTROY UNDEAD & DIVINE INTERVENTION
# ==============================================================================

def get_destroy_undead_cr_threshold(cleric_level: int) -> float:
    """PHB p. 59: Distruggere Non Morti per livello Chierico."""
    if cleric_level >= 17:
        return 4.0
    if cleric_level >= 14:
        return 3.0
    if cleric_level >= 11:
        return 2.0
    if cleric_level >= 8:
        return 1.0
    if cleric_level >= 5:
        return 0.5
    return 0.0


def _parse_cr_float(cr_val: Any) -> float:
    s = str(cr_val or "0").strip()
    if "/" in s:
        parts = s.split("/")
        try:
            return float(parts[0]) / max(1.0, float(parts[1]))
        except Exception:
            return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


def handle_turn_undead_request(data, player, game_state):
    """Chierico Lv 2+ - Scacciare/Distruggere Non Morti (PHB p. 59): 30 ft (6 celle), TS Saggezza."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    if _check_surprised_block(actor, game_state, "usare Scacciare Non Morti"):
        return
    cleric_lvl = entity_get_class_level(actor, "chierico", "cleric")
    if cleric_lvl < 2 and not entity_has_keyword(actor, "scacciare non morti", "turn undead"):
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply("Scacciare Non Morti richiede Chierico Lv 2+."))
        return
    ok, new_cur, mx = entity_spend_resource(actor, ("canale di divinit", "incanala divinit", "channel divinity", "incanalare"), 1)
    if not ok:
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply("Usi di Canale di Divinità esauriti!"))
        return

    wis_mod = entity_get_attr_mod(actor, "SAG")
    pb = ((entity_get_total_level(actor) - 1) // 4) + 2
    dc = int(data.get("dc") or (8 + pb + wis_mod))
    destroy_cr = get_destroy_undead_cr_threshold(max(2, cleric_lvl))

    pos_a = getattr(actor, "position", None) or [0, 0]
    hex_a = Hex(pos_a[0], pos_a[1])
    grid_type = game_state.current_map.get("grid_type", "hex") if getattr(game_state, "current_map", None) else "hex"

    affected = []
    for p in getattr(game_state, "players", []):
        if p.name == actor.name or getattr(p, "hp", 0) <= 0:
            continue
        fs_p = getattr(p, "full_sheet", None) or {}
        type_str = f"{getattr(p, 'race', '')} {fs_p.get('type', '')} {fs_p.get('creature_type', '')} {p.name}".lower()
        is_undead = any(u in type_str for u in ("non morto", "non-morto", "undead", "scheletro", "skeleton", "zombi", "zombie", "vampiro", "vampire", "lich", "ghoul", "wight", "fantasma", "ghost", "spettro", "mummia"))
        if not is_undead:
            continue
        pos_p = getattr(p, "position", None)
        if pos_p and grid_distance(hex_a, Hex(pos_p[0], pos_p[1]), grid_type) <= 6:
            save_mod = get_effective_save_bonus_from_dict(p, "SAG")
            roll_tot = roll_dice(f"1d20{'+' if save_mod >= 0 else ''}{save_mod}")["total"]
            if roll_tot >= dc:
                affected.append(f"{p.name}: TS SAG {roll_tot} >= {dc} (Resiste)")
            else:
                cr_num = _parse_cr_float(fs_p.get("cr", 0))
                if destroy_cr > 0 and cr_num <= destroy_cr and cr_num > 0 or (destroy_cr > 0 and fs_p.get("cr") is not None and cr_num <= destroy_cr):
                    p.hp = 0
                    if "Morto" not in p.conditions:
                        p.conditions.append("Morto")
                    _sync_sheet_conditions(p)
                    affected.append(f"{p.name}: TS {roll_tot} < {dc} -> 💀 DISTRUTTO (GS {cr_num} <= {destroy_cr})!")
                else:
                    if "Scacciato" not in p.conditions:
                        p.conditions.append("Scacciato")
                    if "Spaventato" not in p.conditions:
                        p.conditions.append("Spaventato")
                    p.condition_durations["Scacciato"] = 10
                    _sync_sheet_conditions(p)
                    affected.append(f"{p.name}: TS {roll_tot} < {dc} -> 🏃 SCACCIATO (1 min)!")
                broadcast(game_state, make_player_stats_update(p.name, p.hp, p.max_hp, p.initiative, p.conditions, getattr(p, "temp_hp", 0)))

    actor.has_acted_this_turn = True
    summary = " | ".join(affected) if affected else "Nessun non-morto ostile entro 9 m (30 ft)."
    msg = f"☀️ [SCACCIARE NON MORTI] {actor.name} (CD {dc} | {new_cur}/{mx} Canali): {summary}"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(msg)


def handle_divine_intervention_request(data, player, game_state):
    """Chierico Lv 10+ - Intervento Divino (PHB p. 59): 1d100 <= Livello Chierico (automatico al 20°)."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    cleric_lvl = entity_get_class_level(actor, "chierico", "cleric")
    if cleric_lvl < 10 and not entity_has_keyword(actor, "intervento divino", "divine intervention"):
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply("Intervento Divino richiede Chierico Lv 10+."))
        return
    eff_lvl = max(10, cleric_lvl)
    forced_roll = data.get("forced_roll")
    d100 = int(forced_roll) if forced_roll is not None else random.randint(1, 100)
    success = (eff_lvl >= 20) or (d100 <= eff_lvl)
    actor.has_acted_this_turn = True
    if success:
        msg = f"🌟 [INTERVENTO DIVINO RIUSCITO!] {actor.name} invoca la propria divinità (d100: {d100} <= {eff_lvl})! La divinità interviene direttamente (Cooldown: 7 giorni)."
    else:
        msg = f"🙏 [INTERVENTO DIVINO FALLITO] {actor.name} tira d100: {d100} (serviva <= {eff_lvl}). La divinità resta in silenzio (riprovabile dopo Riposo Lungo)."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    game_state.log_dm_message(msg)


# ==============================================================================
# FIGHTER: INDOMITABLE & BATTLE MASTER MANEUVERS
# ==============================================================================

def handle_indomitable_request(data, player, game_state):
    """Guerriero Lv 9+ - Indomito (PHB p. 72): Ritira un Tiro Salvezza fallito (1/2/3 per Riposo Lungo)."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    stat = data.get("stat", "COS")
    dc = int(data.get("dc", 10) or 10)
    f_lvl = entity_get_class_level(actor, "guerriero", "fighter")
    if f_lvl < 9 and not entity_has_keyword(actor, "indomito", "indomitable"):
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply("Indomito richiede Guerriero Lv 9+."))
        return
    ok, new_cur, mx = entity_spend_resource(actor, ("indomito", "indomitable"), 1)
    if not ok:
        if entity_find_resource(actor, "indomito", "indomitable") is None:
            ind_max = 1 if f_lvl < 13 else (2 if f_lvl < 17 else 3)
            res = {"name": "Indomito (Indomitable)", "current": max(0, ind_max - 1), "max": ind_max, "reset_on": "long"}
            if isinstance(getattr(actor, "full_sheet", None), dict):
                actor.full_sheet.setdefault("custom_resources", []).append(res)
            new_cur, mx = res["current"], res["max"]
        else:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Usi di Indomito esauriti (recuperati al Riposo Lungo)!"))
            return
    mod = get_effective_save_bonus_from_dict(actor, stat)
    r = roll_dice(f"1d20{'+' if mod >= 0 else ''}{mod}")
    tot = r["total"]
    status = "✅ SUPERATO" if tot >= dc else "❌ ANCORA FALLITO"
    msg = f"🛡️ [INDOMITO] {actor.name} ritira il TS su {stat} (CD {dc}): {tot} [{status}] ({new_cur}/{mx} rimasti)."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(msg)


def handle_maneuver_request(data, player, game_state):
    """
    Maestro della Battaglia - Manovre di Combattimento (PHB p. 73-74):
    Supporta: Sbilanciare (Trip), Attacco Preciso (Precision), Attacco Minaccioso (Menacing),
    Attacco Disarmante (Disarming), Risposta (Riposte).
    """
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    maneuver = str(data.get("maneuver", "trip")).strip().lower()
    target = _get_target_or_self(data, actor, game_state)

    fs = getattr(actor, "full_sheet", None) or {}
    cur_dice = int(fs.get("superiority_dice_current", 0) or 0) if isinstance(fs, dict) else 0
    if cur_dice <= 0:
        res_sup = entity_find_resource(actor, "superiorit", "superiority")
        if res_sup and res_sup.get("current", 0) > 0:
            entity_spend_resource(actor, ("superiorit", "superiority"), 1)
        elif not data.get("free_test", False):
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Dadi di Superiorità esauriti!"))
            return
    elif isinstance(fs, dict):
        fs["superiority_dice_current"] = cur_dice - 1

    die_type = fs.get("superiority_die_type", "d8") if isinstance(fs, dict) else "d8"
    die_val = roll_dice(f"1{die_type}")["total"]
    str_mod = entity_get_attr_mod(actor, "FOR")
    dex_mod = entity_get_attr_mod(actor, "DES")
    pb = ((entity_get_total_level(actor) - 1) // 4) + 2
    man_dc = 8 + pb + max(str_mod, dex_mod)

    if "precis" in maneuver:
        msg = f"🎯 [MANOVRA: ATTACCO PRECISO] {actor.name} spende 1 Dado di Superiorità ({die_type}) e aggiunge +{die_val} al Tiro per Colpire!"
    elif "minacc" in maneuver or "menac" in maneuver:
        if target:
            ts_mod = get_effective_save_bonus_from_dict(target, "SAG")
            ts_roll = roll_dice(f"1d20{'+' if ts_mod >= 0 else ''}{ts_mod}")["total"]
            if ts_roll < man_dc:
                imm, _ = is_immune_to_frightened_by_aura(target, game_state)
                if imm:
                    res_txt = f"Immune a Spaventato!"
                else:
                    if "Spaventato" not in target.conditions:
                        target.conditions.append("Spaventato")
                    _sync_sheet_conditions(target)
                    res_txt = f"TS SAG {ts_roll} < {man_dc} -> SPAVENTATO!"
            else:
                res_txt = f"TS SAG {ts_roll} >= {man_dc} (Resiste)"
            msg = f"😱 [MANOVRA: ATTACCO MINACCIOSO] {actor.name} aggiunge +{die_val} ai danni contro {target.name}: {res_txt}"
        else:
            msg = f"😱 [MANOVRA: ATTACCO MINACCIOSO] {actor.name} ottiene +{die_val} danni extra (CD TS SAG {man_dc})."
    elif "disarm" in maneuver:
        if target:
            ts_mod = get_effective_save_bonus_from_dict(target, "FOR")
            ts_roll = roll_dice(f"1d20{'+' if ts_mod >= 0 else ''}{ts_mod}")["total"]
            if ts_roll < man_dc:
                if "Disarmato" not in target.conditions:
                    target.conditions.append("Disarmato")
                _sync_sheet_conditions(target)
                res_txt = f"TS FOR {ts_roll} < {man_dc} -> DISARMATO (arma a terra)!"
            else:
                res_txt = f"TS FOR {ts_roll} >= {man_dc} (Mantiene la presa)"
            msg = f"⚔️ [MANOVRA: ATTACCO DISARMANTE] {actor.name} +{die_val} danni su {target.name}: {res_txt}"
        else:
            msg = f"⚔️ [MANOVRA: ATTACCO DISARMANTE] {actor.name} ottiene +{die_val} danni (CD TS FOR {man_dc})."
    elif "ripost" in maneuver or "rispost" in maneuver:
        actor.has_reacted_this_turn = True
        msg = f"⚡ [MANOVRA: RISPOSTA (REAZIONE)] {actor.name} contrattacca immediatamente con +{die_val} ai danni!"
    else:  # Trip Attack (Sbilanciare)
        if target:
            ts_mod = get_effective_save_bonus_from_dict(target, "FOR")
            ts_roll = roll_dice(f"1d20{'+' if ts_mod >= 0 else ''}{ts_mod}")["total"]
            if ts_roll < man_dc:
                if "Prono" not in target.conditions:
                    target.conditions.append("Prono")
                _sync_sheet_conditions(target)
                res_txt = f"TS FOR {ts_roll} < {man_dc} -> ATTERRATO (Prono)!"
            else:
                res_txt = f"TS FOR {ts_roll} >= {man_dc} (Resta in piedi)"
            msg = f"🦵 [MANOVRA: SBILANCIARE] {actor.name} aggiunge +{die_val} danni contro {target.name}: {res_txt}"
        else:
            msg = f"🦵 [MANOVRA: SBILANCIARE] {actor.name} ottiene +{die_val} danni (CD TS FOR {man_dc})."

    if target:
        broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(msg)


# ==============================================================================
# ROGUE: CUNNING ACTION & HIDE
# ==============================================================================

def handle_hide_request(data, player, game_state):
    """Azione Nascondersi (PHB p. 192 / Azione Scaltra se Ladro 2+): tira Furtività e imposta is_hidden e stealth_score."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    if _check_surprised_block(actor, game_state, "nascondersi"):
        return
    as_bonus = bool(data.get("as_bonus_action", False))
    if as_bonus:
        rogue_lvl = entity_get_class_level(actor, "ladro", "rogue")
        ranger_lvl = entity_get_class_level(actor, "ranger")
        can_ba_hide = (
            rogue_lvl >= 2
            or ranger_lvl >= 14
            or entity_has_keyword(actor, "azione scaltra", "cunning action", "svanire", "vanish")
        )
        if not can_ba_hide:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Nascondersi come Azione Bonus richiede Azione Scaltra (Ladro Lv 2+)."))
            return
        actor.bonus_action_used_this_turn = True
    else:
        actor.has_acted_this_turn = True

    fs = getattr(actor, "full_sheet", None) or {}
    dex_mod = entity_get_attr_mod(actor, "DES")
    skills = fs.get("skills", {}) if isinstance(fs, dict) else {}
    stealth_prof = int(skills.get("Furtività", skills.get("Stealth", 0)) or 0)
    pb = ((entity_get_total_level(actor) - 1) // 4) + 2
    stealth_bonus = dex_mod + (pb * stealth_prof)
    forced_roll = data.get("forced_roll")
    p_conds = getattr(actor, "conditions", []) or []
    is_invis = is_condition_active(p_conds, "Invisibile")
    has_dis = getattr(actor, "exhaustion_level", 0) >= 1 or is_condition_active(p_conds, "Avvelenato") or is_condition_active(p_conds, "Spaventato")
    if forced_roll is not None:
        stealth_total = int(forced_roll)
    else:
        r1 = roll_dice(f"1d20{'+' if stealth_bonus >= 0 else ''}{stealth_bonus}")
        r2 = roll_dice(f"1d20{'+' if stealth_bonus >= 0 else ''}{stealth_bonus}")
        if is_invis and not has_dis:
            stealth_total = max(r1["total"], r2["total"])
        elif has_dis and not is_invis:
            stealth_total = min(r1["total"], r2["total"])
        else:
            stealth_total = r1["total"]
        if stealth_prof > 0 and entity_get_class_level(actor, "ladro", "rogue") >= 11:
            stealth_total = max(stealth_total, 10 + stealth_bonus)

    actor.stealth_score = stealth_total
    actor.is_hidden = True
    if "Nascosto" not in actor.conditions:
        actor.conditions.append("Nascosto")
    _sync_sheet_conditions(actor)

    # Verifica Percezione Passiva dei nemici (incl. Accecato, Scurovisione/Luce Fioca -5, Keen Senses, Blindsight/Truesight)
    is_actor_party = getattr(actor, "is_party_member", False) or getattr(actor, "is_companion", False)
    spotted_by = []
    from server.rules.reaction_magic import check_passive_perception, check_special_senses_see_target
    cur_map = getattr(game_state, "current_map", {}) or {}
    g_type = cur_map.get("grid_type", "hex")
    from common.hex_utils import Hex, grid_distance_3d
    for p in getattr(game_state, "players", []):
        if p.name == actor.name or getattr(p, "hp", 0) <= 0:
            continue
        p_party = getattr(p, "is_party_member", False) or getattr(p, "is_companion", False)
        if p_party == is_actor_party:
            continue
        dist_p = 1.0
        if getattr(actor, "position", None) and getattr(p, "position", None):
            dist_p = grid_distance_3d(Hex(actor.position[0], actor.position[1]), Hex(p.position[0], p.position[1]), getattr(actor, "elevation", 0), getattr(p, "elevation", 0), grid_type=g_type)
        special_see, special_why = check_special_senses_see_target(p, actor, dist_p)
        if is_invis and not special_see:
            # Una creatura invisibile resta occultata alla vista, salvo sensi speciali o rumore (se percepita acusticamente via sight_based=False)
            pass_perc = check_passive_perception(p, game_state, sight_based=False)
        else:
            pass_perc = check_passive_perception(p, game_state, sight_based=not special_see)
        if stealth_total < pass_perc:
            spotted_by.append(f"{p.name} (Perc. Passiva {pass_perc})")

    action_txt = " (Azione Bonus)" if as_bonus else ""
    if spotted_by:
        actor.is_hidden = False
        actor.conditions = [c for c in actor.conditions if c not in ("Nascosto", "Hidden")]
        _sync_sheet_conditions(actor)
        msg = f"👁️ [NASCONDERSI{action_txt}] {actor.name} tira Furtività {stealth_total}, ma viene individuato da: {', '.join(spotted_by)}!"
    else:
        msg = f"🥷 [NASCONDERSI{action_txt}] {actor.name} si nasconde con successo (Furtività: {stealth_total})!"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(actor.name, actor.hp, actor.max_hp, actor.initiative, actor.conditions, getattr(actor, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(msg)


def handle_cunning_action_request(data, player, game_state):
    """Ladro Lv 2+ - Azione Scaltra (PHB p. 96): Scatto, Disimpegno o Nascondersi come Azione Bonus."""
    sub = str(data.get("sub_action", "dash")).lower()
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    if _check_surprised_block(actor, game_state, "usare Azione Scaltra"):
        return
    rogue_lvl = entity_get_class_level(actor, "ladro", "rogue")
    if rogue_lvl < 2 and not entity_has_keyword(actor, "azione scaltra", "cunning action"):
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply("Azione Scaltra richiede Ladro Lv 2+."))
        return
    if "hide" in sub or "nascond" in sub:
        new_d = dict(data)
        new_d["as_bonus_action"] = True
        handle_hide_request(new_d, actor, game_state)
        return
    actor.bonus_action_used_this_turn = True
    if "disengage" in sub or "disimp" in sub:
        if "Disimpegno" not in actor.conditions:
            actor.conditions.append("Disimpegno")
        _sync_sheet_conditions(actor)
        msg = f"🌀 [AZIONE SCALTRA - DISIMPEGNO] {actor.name} si disimpegna come Azione Bonus (nessun AdO in questo turno)."
    else:
        if "Scatto" not in actor.conditions:
            actor.conditions.append("Scatto")
        _sync_sheet_conditions(actor)
        msg = f"💨 [AZIONE SCALTRA - SCATTO] {actor.name} usa Scatto come Azione Bonus (velocità raddoppiata)."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(actor.name, actor.hp, actor.max_hp, actor.initiative, actor.conditions, getattr(actor, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(msg)


# ==============================================================================
# MONK: KI ABILITIES (FLURRY OF BLOWS, PATIENT DEFENSE, STEP OF THE WIND, DIAMOND SOUL)
# ==============================================================================

def handle_ki_ability_request(data, player, game_state):
    """Monaco Lv 2+ (e Lv 14+ Anima di Diamante): Raffica di Colpi, Difesa Paziente, Passo del Vento, Anima di Diamante."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    if _check_surprised_block(actor, game_state, "usare Punti Ki"):
        return
    ability = str(data.get("ability", "flurry")).strip().lower()
    monk_lvl = entity_get_class_level(actor, "monaco", "monk")
    if monk_lvl < 2 and not entity_has_keyword(actor, "punti ki", "ki"):
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply("Le tecniche Ki richiedono Monaco Lv 2+."))
        return

    # Quietare la Mente (Stillness of Mind, Monaco Lv 7+, PHB p. 79): Azione (0 Ki) per terminare Affascinato/Spaventato
    if "stillness" in ability or "quiet" in ability:
        if monk_lvl < 7 and not entity_has_keyword(actor, "quietare la mente", "stillness of mind"):
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Quietare la Mente richiede Monaco Lv 7+."))
            return
        removed_s = []
        if hasattr(actor, "conditions"):
            new_c = []
            for c in actor.conditions:
                cl = str(c).lower()
                if cl.startswith(("affascinat", "charmed", "spaventat", "frightened")):
                    removed_s.append(c)
                else:
                    new_c.append(c)
            actor.conditions = new_c
        if hasattr(actor, "frightened_sources"):
            actor.frightened_sources = []
        if hasattr(actor, "charmed_by"):
            actor.charmed_by = None
        actor.has_acted_this_turn = True
        _sync_sheet_conditions(actor)
        msg_s = f"🧘 [QUIETARE LA MENTE] {actor.name} usa la propria Azione per liberarsi da {', '.join(removed_s) if removed_s else 'Affascinato/Spaventato'}!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg_s))
        broadcast(game_state, make_player_stats_update(actor.name, actor.hp, actor.max_hp, actor.initiative, actor.conditions, getattr(actor, "temp_hp", 0)))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    # Corpo Vuoto (Empty Body, Monaco Lv 18+, PHB p. 79): 4 Ki -> Invisibile + Resistenza a tutti i danni eccetto Forza per 1 min (10 round)
    is_empty_body = ("empty" in ability or "vuoto" in ability)
    if is_empty_body and monk_lvl < 18 and not entity_has_keyword(actor, "corpo vuoto", "empty body"):
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply("Corpo Vuoto richiede Monaco Lv 18+."))
        return

    ki_cost = 4 if is_empty_body else 1
    ok, new_cur, mx = entity_spend_resource(actor, ("punti ki", "ki"), ki_cost)
    if not ok:
        if entity_find_resource(actor, "punti ki", "ki") is None and monk_lvl >= 2:
            if monk_lvl < ki_cost:
                if getattr(actor, "conn", None):
                    send_message(actor.conn, make_error_reply(f"Servono {ki_cost} Punti Ki."))
                return
            res = {"name": "Punti Ki", "current": max(0, monk_lvl - ki_cost), "max": monk_lvl, "reset_on": "short"}
            if isinstance(getattr(actor, "full_sheet", None), dict):
                actor.full_sheet.setdefault("custom_resources", []).append(res)
            new_cur, mx = res["current"], res["max"]
        else:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Punti Ki esauriti (ricaricali con Riposo Breve)!"))
            return

    if is_empty_body:
        actor.has_acted_this_turn = True
        if not hasattr(actor, "conditions"):
            actor.conditions = []
        if "Invisibile" not in actor.conditions:
            actor.conditions.append("Invisibile")
        if hasattr(actor, "add_effect"):
            actor.add_effect({
                "id": "empty_body",
                "name": "Corpo Vuoto",
                "duration_rounds": 10,
                "source": actor.name,
            })
        msg = f"👻 [CORPO VUOTO - 4 Ki] {actor.name} diventa Invisibile e ottiene Resistenza a tutti i danni (eccetto Forza) per 1 minuto! ({new_cur}/{mx} Ki rimasti)"
    elif "patient" in ability or "difesa" in ability:
        actor.bonus_action_used_this_turn = True
        if "Schivata" not in actor.conditions:
            actor.conditions.append("Schivata")
        msg = f"🧘 [DIFESA PAZIENTE - 1 Ki] {actor.name} assume Schivata come Azione Bonus ({new_cur}/{mx} Ki rimasti)."
    elif "step" in ability or "vento" in ability:
        actor.bonus_action_used_this_turn = True
        sub_mode = str(data.get("sub_mode", "dash")).lower()
        cond = "Disimpegno" if "disengage" in sub_mode or "disimp" in sub_mode else "Scatto"
        if cond not in actor.conditions:
            actor.conditions.append(cond)
        msg = f"🌬️ [PASSO DEL VENTO - 1 Ki] {actor.name} usa {cond} come Azione Bonus e raddoppia la distanza di salto ({new_cur}/{mx} Ki rimasti)!"
    elif "diamond" in ability or "diamante" in ability:
        stat = data.get("stat", "DES")
        dc = int(data.get("dc", 12) or 12)
        mod = get_effective_save_bonus_from_dict(actor, stat)
        r = roll_dice(f"1d20{'+' if mod >= 0 else ''}{mod}")["total"]
        st = "✅ SUPERATO" if r >= dc else "❌ FALLITO"
        msg = f"💎 [ANIMA DI DIAMANTE - 1 Ki] {actor.name} ritira TS {stat} (CD {dc}): {r} [{st}] ({new_cur}/{mx} Ki rimasti)."
    else:  # Flurry of Blows (Raffica di Colpi)
        actor.bonus_action_used_this_turn = True
        martial_sides = 4 if monk_lvl < 5 else (6 if monk_lvl < 11 else (8 if monk_lvl < 17 else 10))
        dex_m = entity_get_attr_mod(actor, "DES")
        str_m = entity_get_attr_mod(actor, "FOR")
        atk_m = max(dex_m, str_m)
        pb = ((entity_get_total_level(actor) - 1) // 4) + 2
        txc = atk_m + pb
        msg = f"🥋 [RAFFICA DI COLPI - 1 Ki] {actor.name} effettua 2 Colpi Senz'Armi extra (+{txc} TxC, 1d{martial_sides}+{atk_m} Contundenti ciascuno)! ({new_cur}/{mx} Ki rimasti)"

    _sync_sheet_conditions(actor)
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(actor.name, actor.hp, actor.max_hp, actor.initiative, actor.conditions, getattr(actor, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(msg)


# ==============================================================================
# WARLOCK: MYSTIC ARCANUM & ELDRITCH BLAST / SCORCHING RAY / MAGIC MISSILE + SILENCE + BA SPELL RULE
# ==============================================================================

def handle_mystic_arcanum_request(data, player, game_state):
    """Warlock Lv 11+ - Arcanum Mistico (PHB p. 108): incantesimi 6°-9° separati dagli slot del Patto (1/Riposo Lungo)."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    slot_lvl = int(data.get("level", 6) or 6)
    spell_name = data.get("spell_name") or f"Arcanum {slot_lvl}° Livello"
    kw = f"{slot_lvl}°"
    ok, new_cur, mx = entity_spend_resource(actor, (f"arcanum mistico ({slot_lvl}", f"mystic arcanum ({slot_lvl}", f"arcanum {slot_lvl}"), 1)
    if not ok:
        w_lvl = entity_get_class_level(actor, "warlock")
        req_lvl = {6: 11, 7: 13, 8: 15, 9: 17}.get(slot_lvl, 99)
        if w_lvl < req_lvl:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply(f"Arcanum Mistico di {slot_lvl}° livello richiede Warlock Lv {req_lvl}+."))
            return
        if entity_find_resource(actor, f"arcanum mistico ({slot_lvl}", f"arcanum {slot_lvl}") is None:
            res = {"name": f"Arcanum Mistico ({slot_lvl}° liv)", "current": 0, "max": 1, "reset_on": "long"}
            if isinstance(getattr(actor, "full_sheet", None), dict):
                actor.full_sheet.setdefault("custom_resources", []).append(res)
        else:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply(f"Hai già usato l'Arcanum Mistico di {slot_lvl}° livello oggi!"))
            return

    actor.has_acted_this_turn = True
    msg = f"👁️ [ARCANUM MISTICO {slot_lvl}°] {actor.name} lancia '{spell_name}' senza consumare Slot del Patto (1/Riposo Lungo)!"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(msg)


def _is_silenced_for_verbal(actor, game_state) -> bool:
    """PHB p. 203 & 275: In zona di Silenzio o con condizione Silenziato/Imbavagliato non si possono lanciare incantesimi Verbali (V)."""
    conds = [str(c).lower() for c in getattr(actor, "conditions", [])]
    if any(k in c for c in conds for k in ("silenzi", "silenc", "imbavagliat", "gagged", "muto")):
        return True
    pos = getattr(actor, "position", None)
    if pos and game_state:
        hex_a = Hex(pos[0], pos[1])
        grid_type = game_state.current_map.get("grid_type", "hex") if getattr(game_state, "current_map", None) else "hex"
        for aoe in getattr(game_state, "active_aoes", []):
            if not isinstance(aoe, dict):
                continue
            name_aoe = f"{aoe.get('label', '')} {aoe.get('name', '')}".lower()
            if "silenzio" in name_aoe or "silence" in name_aoe:
                orig = aoe.get("origin")
                rad = int(aoe.get("size", 4) or 4)
                if orig and grid_distance(Hex(orig[0], orig[1]), hex_a, grid_type) <= rad:
                    return True
    return False


def validate_spell_casting_rules(actor, spell_level: int, casting_time: str = "action", has_verbal: bool = True, game_state=None) -> Tuple[bool, str]:
    """
    Valida le regole fondamentali del lancio incantesimi 5e RAW:
    1. Silenzio / Componenti Verbali (PHB p. 203)
    2. Regola Incantesimi Azione Bonus (PHB p. 202): se lanci un incantesimo come Azione Bonus in questo turno,
       l'unico altro incantesimo che puoi lanciare come Azione è un Trucchetto (livello 0)!
    """
    if has_verbal and _is_silenced_for_verbal(actor, game_state):
        return False, f"🔇 {actor.name} è in area di SILENZIO / Silenziato e non può lanciare incantesimi con componente Verbale (V)!"
    from common.feats_and_classes import get_armor_nonproficiency_penalties
    _armor_pen = get_armor_nonproficiency_penalties(actor)
    if _armor_pen.get("cannot_cast_spells"):
        return False, f"🛡️ {actor.name} indossa armatura/scudo senza competenza ({', '.join(_armor_pen.get('missing', []))}) e non può lanciare incantesimi (PHB p. 144)!"

    ct = str(casting_time or "action").lower()
    is_bonus = ("bonus" in ct)
    lvl = int(spell_level or 0)

    if is_bonus:
        prior_action_lvl = getattr(actor, "spell_cast_action_level_this_turn", None)
        if prior_action_lvl is not None and int(prior_action_lvl) > 0:
            return False, (
                f"⏳ Regola Incantesimi Azione Bonus (PHB p. 202): {actor.name} ha già lanciato un incantesimo "
                f"di {prior_action_lvl}° livello come Azione in questo turno!"
            )
    else:
        if getattr(actor, "spell_cast_bonus_action_this_turn", False) and lvl > 0:
            return False, (
                f"⏳ Regola Incantesimi Azione Bonus (PHB p. 202): {actor.name} ha già lanciato un incantesimo come "
                f"Azione Bonus in questo turno; può lanciare solo un Trucchetto (liv. 0) con tempo di 1 Azione!"
            )
    return True, "OK"


def handle_cast_special_spell_request(data, player, game_state):
    """
    Gestisce Dardo Incantato (Magic Missile), Deflagrazione Occulta (Eldritch Blast), Raggio Rovente (Scorching Ray),
    e verifica Silenzio / Regola Azione Bonus / Adepto Elementale / Maledizioni (Remove Curse).
    """
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    if _check_surprised_block(actor, game_state, "lanciare incantesimi"):
        return

    spell_name = str(data.get("spell_name", "Dardo Incantato")).strip()
    s_low = spell_name.lower()
    cast_level = int(data.get("cast_level", 1) or 1)
    casting_time = data.get("casting_time", "action")
    has_verbal = bool(data.get("has_verbal", True))
    is_bonus_spell = "bonus" in str(casting_time).lower()
    base_lvl = 0 if ("deflagrazione" in s_low or "eldritch blast" in s_low or int(data.get("base_level", 1) or 1) == 0) else cast_level

    ok_rules, err_msg = validate_spell_casting_rules(actor, base_lvl, casting_time, has_verbal, game_state)
    if not ok_rules:
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply(err_msg))
        broadcast(game_state, make_chat_broadcast("Sistema", err_msg))
        return

    if is_bonus_spell:
        actor.spell_cast_bonus_action_this_turn = True
        actor.bonus_action_used_this_turn = True
    else:
        actor.spell_cast_action_level_this_turn = base_lvl
        actor.has_acted_this_turn = True

    # Rituale PHB p. 201: aggiunge +10 minuti all'orologio di gioco
    if bool(data.get("is_ritual", False)):
        if hasattr(game_state, "advance_game_time"):
            game_state.advance_game_time(minutes=10)
        broadcast(game_state, make_chat_broadcast("Sistema", f"🕯️ [RITUALE +10 min] {actor.name} officia il lancio rituale di '{spell_name}'."))

    # Durata Concentrazione in round (PHB p. 203)
    if bool(data.get("concentration", False)):
        from common.feats_and_classes import parse_spell_duration_rounds
        dur_r = parse_spell_duration_rounds(str(data.get("duration", "") or ""))
        actor.concentrating_on = spell_name
        actor.concentration_rounds_remaining = dur_r if (dur_r and dur_r > 0) else None
        if str(data.get("metamagic", "") or "").lower() == "extended" and getattr(actor, "concentration_rounds_remaining", None):
            actor.concentration_rounds_remaining = min(14400, actor.concentration_rounds_remaining * 2)

    # Abiuratore Lv 2+: incantesimo di Abiurazione di 1°+ liv. ricarica Interdizione Arcana
    _sch_l = str(data.get("school", "") or "").lower()
    if base_lvl >= 1 and ("abiuraz" in _sch_l or "abjur" in _sch_l):
        from common.feats_and_classes import recharge_arcane_ward_hp
        gained_w = recharge_arcane_ward_hp(actor, cast_level)
        if gained_w > 0:
            broadcast(game_state, make_chat_broadcast("Sistema", f"🛡️ [INTERDIZIONE ARCANA] {actor.name} ricarica +{gained_w} PF alla propria Interdizione Arcana!"))

    if base_lvl >= 1:
        from server.rules.reaction_magic import maybe_prompt_counterspell_reactions
        maybe_prompt_counterspell_reactions(actor, spell_name, cast_level, game_state)

    from server.rules.combat import apply_damage
    target = _get_target_or_self(data, actor, game_state)

    # 1. Dardo Incantato / Magic Missile (PHB p. 257): colpisce automaticamente, bloccato totalmente da Scudo/Shield!
    if "dardo incantato" in s_low or "magic missile" in s_low:
        num_darts = 3 + max(0, cast_level - 1)
        if not target:
            broadcast(game_state, make_chat_broadcast("Sistema", f"✨ [DARDO INCANTATO Lv.{cast_level}] {actor.name} lancia {num_darts} dardi di forza ({num_darts} x 1d4+1)."))
            return
        conds = [str(c).lower() for c in getattr(target, "conditions", [])]
        has_shield = any(c in ("scudo", "shield") for c in conds)
        if has_shield or entity_has_keyword(target, "spilla di protezione", "brooch of shielding"):
            msg = f"🛡️ [DARDO INCANTATO BLOCCATO!] I {num_darts} dardi lanciati da {actor.name} contro {target.name} vengono completamente assorbiti da Scudo/Protezione (0 danni)!"
            broadcast(game_state, make_chat_broadcast("Sistema", msg))
            game_state.log_dm_message(msg)
            return
        darts = [roll_dice("1d4+1")["total"] for _ in range(num_darts)]
        tot_force = sum(darts)
        final_d, note, _, _ = apply_damage(target, tot_force, damage_type="Forza", game_state=game_state)
        msg = f"✨ [DARDO INCANTATO Lv.{cast_level}] {actor.name} colpisce AUTOMATICAMENTE {target.name} con {num_darts} dardi {darts} = {final_d} danni da Forza!{note} (PV {target.name}: {target.hp}/{target.max_hp})"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    # 2. Rimuovi Maledizione / Remove Curse: libera oggetti maledetti sull'alleato
    if "rimuovi maledizione" in s_low or "remove curse" in s_low:
        from common.item_modifiers import lift_curse_on_inventory
        t_obj = target or actor
        lifted = lift_curse_on_inventory(t_obj)
        if hasattr(t_obj, "conditions"):
            t_obj.conditions = [c for c in t_obj.conditions if "maledett" not in str(c).lower() and "cursed" not in str(c).lower()]
        _sync_sheet_conditions(t_obj)
        msg = f"✨ [RIMUOVI MALEDIZIONE] {actor.name} spezza ogni maledizione su {t_obj.name}! Oggetti liberati: {', '.join(lifted) if lifted else 'condizioni rimosse'}."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    # 3. Multi-raggio: Deflagrazione Occulta (Eldritch Blast) o Raggio Rovente (Scorching Ray)
    is_eb = ("deflagrazione" in s_low or "eldritch blast" in s_low)
    is_sr = ("raggio rovente" in s_low or "scorching ray" in s_low)
    if is_eb or is_sr:
        tot_lvl = entity_get_total_level(actor)
        num_rays = (1 if tot_lvl < 5 else (2 if tot_lvl < 11 else (3 if tot_lvl < 17 else 4))) if is_eb else (3 + max(0, cast_level - 2))
        spell_atk = int(data.get("hit_bonus") or (entity_get_attr_mod(actor, "CAR" if is_eb else "INT") + ((tot_lvl - 1) // 4 + 2)))
        target_ac = getattr(target, "ac", 12) if target else 12
        dmg_type = "Forza" if is_eb else "Fuoco"
        agonizing = is_eb and entity_has_keyword(actor, "deflagrazione agonizzante", "agonizing blast")
        repelling = is_eb and entity_has_keyword(actor, "deflagrazione respingente", "repelling blast")
        cha_mod = max(0, entity_get_attr_mod(actor, "CAR")) if agonizing else 0
        elem_adept = entity_has_keyword(actor, "adepto elementale", "elemental adept") and not is_eb

        ray_logs = []
        total_dealt = 0
        pushes = 0
        for idx in range(num_rays):
            atk_r = roll_dice(f"1d20{'+' if spell_atk >= 0 else ''}{spell_atk}")
            is_c = (atk_r.get("natural_roll") == 20)
            hits = is_c or (atk_r.get("natural_roll") != 1 and atk_r["total"] >= target_ac)
            if hits:
                dmg_formula = "1d10" if is_eb else "2d6"
                r_dmg = roll_dice(dmg_formula, is_crit=is_c, elemental_adept=elem_adept)["total"] + cha_mod
                if target:
                    if elem_adept and "Fuoco" in dmg_type:
                        # Adepto Elementale ignora Resistenza Fuoco
                        old_res = list(getattr(target, "damage_resistances", []))
                        target.damage_resistances = [r for r in old_res if "fuoco" not in str(r).lower() and "fire" not in str(r).lower()]
                        f_dmg, _, _, _ = apply_damage(target, r_dmg, damage_type=dmg_type, game_state=game_state, is_crit=is_c)
                        target.damage_resistances = old_res
                    else:
                        f_dmg, _, _, _ = apply_damage(target, r_dmg, damage_type=dmg_type, game_state=game_state, is_crit=is_c)
                else:
                    f_dmg = r_dmg
                total_dealt += f_dmg
                if repelling:
                    pushes += 1
                tag = " 🌟CRIT!" if is_c else ""
                ray_logs.append(f"Raggio #{idx+1}: TxC {atk_r['total']} vs CA {target_ac} -> COLPITO ({f_dmg} {dmg_type}{tag})")
            else:
                ray_logs.append(f"Raggio #{idx+1}: TxC {atk_r['total']} vs CA {target_ac} -> MANCATO")

        if repelling and pushes > 0 and target and getattr(actor, "position", None) and getattr(target, "position", None):
            # Spinge indietro il bersaglio di 2 celle per raggio colpito
            dq = target.position[0] - actor.position[0]
            dr = target.position[1] - actor.position[1]
            norm = max(1, abs(dq), abs(dr))
            step_q = round(dq / norm)
            step_r = round(dr / norm)
            target.position = [target.position[0] + step_q * (2 * pushes), target.position[1] + step_r * (2 * pushes)]
            ray_logs.append(f"💨 Deflagrazione Respingente: {target.name} spinto indietro di {pushes * 3} m ({pushes * 10} ft)!")

        t_name = target.name if target else "Bersaglio"
        msg = f"⚡ [{spell_name.upper()}] {actor.name} lancia {num_rays} raggi su {t_name} (Totale: {total_dealt} {dmg_type}):\n• " + "\n• ".join(ray_logs)
        if target:
            broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    msg = f"🔮 {actor.name} lancia {spell_name} (Liv. {cast_level}) rispettando le regole 5e."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


# ==============================================================================
# ACTIVE FEATS (HEALER, INSPIRING LEADER) & NON-LETHAL TOGGLE
# ==============================================================================

def handle_toggle_non_lethal_request(data, player, game_state):
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    actor.non_lethal_mode = bool(data.get("non_lethal", not getattr(actor, "non_lethal_mode", False)))
    msg = f"🥊 {actor.name} imposta i colpi in mischia su: {'NON LETALI (KO Stabile a 0 PF)' if actor.non_lethal_mode else 'LETALI (Standard)'}."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


def handle_healer_feat_request(data, player, game_state):
    """Talento Guaritore (Healer, PHB p. 167): 1d6 + 4 + livello PF con Kit da Guaritore."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    if not entity_has_keyword(actor, "guaritore", "healer"):
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply("Richiede il talento Guaritore (Healer)."))
        return
    target = _get_target_or_self(data, actor, game_state) or actor
    t_fs_hl = getattr(target, "full_sheet", None) or {}
    t_type_hl = (str(t_fs_hl.get("type", "")) + " " + str(target.name)).lower()
    if getattr(target, "is_object", False) or any(k in t_type_hl for k in ("costrutto", "construct", "non morto", "non-morto", "undead", "golem")):
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply("Il talento Guaritore non può curare Oggetti, Costrutti o Non Morti (PHB p. 167)."))
        return
    t_lvl = entity_get_total_level(target)
    heal_val = roll_dice("1d6+4")["total"] + t_lvl
    old_hp = target.hp
    target.hp = min(target.max_hp, target.hp + heal_val)
    if old_hp == 0 and target.hp > 0:
        target.conditions = [c for c in getattr(target, "conditions", []) if c not in ("Incosciente", "Stabilizzato")]
    _sync_sheet_conditions(target)
    actor.has_acted_this_turn = True
    msg = f"🩹 [TALENTO GUARITORE] {actor.name} cura {target.name} con Kit da Guaritore per +{heal_val} PF (1d6+4+{t_lvl}) -> {target.hp}/{target.max_hp} PF!"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


def handle_inspiring_leader_request(data, player, game_state):
    """Talento Condottiero Ispiratore (Inspiring Leader, PHB p. 167): +Livello + Mod CAR Temp HP al party."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    if not entity_has_keyword(actor, "condottiero ispiratore", "inspiring leader"):
        if getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply("Richiede il talento Condottiero Ispiratore (Inspiring Leader)."))
        return
    temp_amt = max(1, entity_get_total_level(actor) + entity_get_attr_mod(actor, "CAR"))
    buffed = []
    for p in getattr(game_state, "players", []):
        if (getattr(p, "is_party_member", False) or getattr(p, "is_companion", False) or p.name == actor.name) and getattr(p, "hp", 0) > 0:
            p.temp_hp = max(getattr(p, "temp_hp", 0), temp_amt)
            _sync_sheet_conditions(p)
            buffed.append(p.name)
            broadcast(game_state, make_player_stats_update(p.name, p.hp, p.max_hp, p.initiative, p.conditions, p.temp_hp))
    msg = f"🚩 [CONDOTTIERO ISPIRATORE] Il discorso di {actor.name} conferisce +{temp_amt} PF Temporanei a: {', '.join(buffed[:6])}!"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


# ==============================================================================
# MONSTER MANUAL: FRIGHTFUL PRESENCE, SWALLOW & OOZE SPLIT
# ==============================================================================

def handle_frightful_presence_request(data, player, game_state):
    """MM - Presenza Terrificante (Frightful Presence): 120 ft (24 celle) TS SAG o Spaventato 1 min; immune 24h su successo."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    dc = int(data.get("dc", 16) or 16)
    pos_a = getattr(actor, "position", None) or [0, 0]
    hex_a = Hex(pos_a[0], pos_a[1])
    grid_type = game_state.current_map.get("grid_type", "hex") if getattr(game_state, "current_map", None) else "hex"
    is_actor_party = getattr(actor, "is_party_member", False)

    logs = []
    for p in getattr(game_state, "players", []):
        if p.name == actor.name or getattr(p, "hp", 0) <= 0:
            continue
        if (getattr(p, "is_party_member", False) or getattr(p, "is_companion", False)) == is_actor_party:
            continue
        imm_list = getattr(p, "frightful_immune_list", []) or []
        if actor.name in imm_list:
            logs.append(f"{p.name}: Immune (24h)")
            continue
        aur_imm, aur_src = is_immune_to_frightened_by_aura(p, game_state)
        if aur_imm:
            logs.append(f"{p.name}: Immune (Aura di Coraggio di {aur_src})")
            continue
        pos_p = getattr(p, "position", None)
        if pos_p and grid_distance(hex_a, Hex(pos_p[0], pos_p[1]), grid_type) <= 24:
            ts_mod = get_effective_save_bonus_from_dict(p, "SAG")
            r = roll_dice(f"1d20{'+' if ts_mod >= 0 else ''}{ts_mod}")["total"]
            if r >= dc:
                if not isinstance(getattr(p, "frightful_immune_list", None), list):
                    p.frightful_immune_list = []
                p.frightful_immune_list.append(actor.name)
                logs.append(f"{p.name}: TS SAG {r} >= {dc} -> Immune 24h")
            else:
                if "Spaventato" not in p.conditions:
                    p.conditions.append("Spaventato")
                p.condition_durations["Spaventato"] = 10
                _sync_sheet_conditions(p)
                broadcast(game_state, make_player_stats_update(p.name, p.hp, p.max_hp, p.initiative, p.conditions, getattr(p, "temp_hp", 0)))
                logs.append(f"{p.name}: TS SAG {r} < {dc} -> 😱 SPAVENTATO!")
    msg = f"🐉 [PRESENZA TERRIFICANTE - CD {dc}] {actor.name}: " + (" | ".join(logs) if logs else "Nessun bersaglio nel raggio di 36 m.")
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


def handle_swallow_request(data, player, game_state):
    """MM - Inghiottire / Engulf: applica Inghiottito, Accecato, Trattenuto e traccia il predatore."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    target = _get_target_or_self(data, player, game_state)
    release = bool(data.get("release", False))
    if not actor or not target:
        return
    if release:
        target.swallowed_by = None
        target.conditions = [c for c in target.conditions if c not in ("Inghiottito", "Swallowed", "Accecato", "Blinded", "Trattenuto", "Restrained")]
        _sync_sheet_conditions(target)
        msg = f"🤮 {target.name} è stato rigurgitato/liberato dallo stomaco di {actor.name}!"
    else:
        target.swallowed_by = actor.name
        for c in ("Inghiottito", "Accecato", "Trattenuto"):
            if c not in target.conditions:
                target.conditions.append(c)
        if data.get("damage_formula") and isinstance(getattr(actor, "full_sheet", None), dict):
            actor.full_sheet["swallow_damage_formula"] = data["damage_formula"]
        _sync_sheet_conditions(target)
        msg = f"🐍 [INGHIOTTITO!] {actor.name} inghiotte {target.name} (Accecato, Trattenuto, Copertura Totale; subisce danno acido a inizio turno)!"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


def try_ooze_split(target_player, damage_type: str, game_state) -> Optional[str]:
    """
    MM p. 243 (Gelatina Ocra / Budino Nero - Scissione):
    Se una melma con tratto Scissione (Split) e almeno 10 PF subisce danni Taglienti o da Fulmine,
    si divide in due nuove melme aventi ciascuna metà dei PF attuali e taglia ridotta.
    """
    if not target_player or not game_state:
        return None
    if getattr(target_player, "hp", 0) < 10:
        return None
    dt = str(damage_type or "").lower()
    if not any(k in dt for k in ("tagliente", "slashing", "fulmine", "lightning")):
        return None
    has_split = entity_has_keyword(target_player, "scissione", "split")
    if not has_split:
        return None

    from common.game_state import Player
    half_hp = max(1, target_player.hp // 2)
    target_player.hp = half_hp
    cur_sz = getattr(target_player, "size", 2)
    if isinstance(cur_sz, (int, float)):
        target_player.size = max(1, int(cur_sz) - 1)
    else:
        _sz_step = {
            "mastodontica": "Enorme", "gargantuan": "Enorme",
            "enorme": "Grande", "huge": "Grande",
            "grande": "Media", "large": "Media",
            "media": "Piccola", "medium": "Piccola",
            "piccola": "Minuscola", "small": "Minuscola",
        }
        target_player.size = _sz_step.get(str(cur_sz or "Media").strip().lower(), "Piccola")
    if isinstance(getattr(target_player, "full_sheet", None), dict):
        target_player.full_sheet["hp_current"] = half_hp

    # Trova nome univoco per il clone diviso
    base_name = target_player.name.split(" #")[0]
    existing_names = {p.name for p in getattr(game_state, "players", [])}
    idx = 2
    clone_name = f"{base_name} #{idx}"
    while clone_name in existing_names:
        idx += 1
        clone_name = f"{base_name} #{idx}"

    clone = Player(clone_name)
    pos = getattr(target_player, "position", [0, 0]) or [0, 0]
    clone.position = [pos[0] + 1, pos[1]]
    clone.hp = half_hp
    clone.max_hp = half_hp
    clone.ac = getattr(target_player, "ac", 8)
    clone.speed = getattr(target_player, "speed", 20)
    clone.size = target_player.size
    clone.initiative = getattr(target_player, "initiative", 0)
    clone.in_combat = getattr(target_player, "in_combat", False)
    clone.damage_immunities = list(getattr(target_player, "damage_immunities", []))
    clone.damage_resistances = list(getattr(target_player, "damage_resistances", []))
    if isinstance(getattr(target_player, "full_sheet", None), dict):
        import copy
        clone.full_sheet = copy.deepcopy(target_player.full_sheet)
        clone.full_sheet["name"] = clone_name
        clone.full_sheet["hp_current"] = half_hp
        clone.full_sheet["hp_max"] = half_hp
    game_state.players.append(clone)
    return f"🧫 [SCISSIONE MELMA!] Il danno {damage_type} divide {target_player.name} in DUE melme ({target_player.name} e {clone_name}) con {half_hp} PF ciascuna!"


# ==============================================================================
# DMG OPTIONAL MANEUVERS, MADNESS, POISONS/DISEASES, CHASES, SURVIVAL, MOUNT, SURPRISE, BREATH
# ==============================================================================

def _is_dmg_opt_enabled(game_state, key: str) -> bool:
    if not game_state or not isinstance(getattr(game_state, "automation_settings", None), dict):
        return False
    return bool(game_state.automation_settings.get(key, False))


def handle_dmg_maneuver_request(data, player, game_state):
    """DMG p. 271-272: Disarm (Disarmare), Overrun (Oltrepassare), Tumble (Capovolta), Shove Aside (Spinta Laterale), Climb Onto Bigger Creature."""
    man = str(data.get("maneuver", "disarm")).strip().lower()
    is_climb_man = any(k in man for k in ("climb", "scal", "bigger", "grande"))
    climb_enabled = _is_dmg_opt_enabled(game_state, "opt_climb_bigger") or _is_dmg_opt_enabled(game_state, "opt_dmg_maneuvers")
    if is_climb_man and not climb_enabled:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Scalare Creature Più Grandi (DMG p.271) è disabilitata dal Master."))
        return
    if not is_climb_man and not _is_dmg_opt_enabled(game_state, "opt_dmg_maneuvers"):
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Le Manovre Opzionali DMG sono disabilitate dal Master nel pannello automazioni."))
        return
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    target = _get_target_or_self(data, player, game_state)
    if not actor or not target:
        return
    if _check_surprised_block(actor, game_state, "usare una Manovra DMG"):
        return

    atk_str = entity_get_attr_mod(actor, "FOR")
    atk_dex = entity_get_attr_mod(actor, "DES")
    pb = ((entity_get_total_level(actor) - 1) // 4) + 2

    if is_climb_man:
        def _dmg_size_rank(ent):
            sh = getattr(ent, "full_sheet", None) or {}
            raw = sh.get("size", getattr(ent, "size", 1))
            if isinstance(raw, (int, float)):
                return 0 if raw < 1 else int(raw) + 1
            s_low = str(raw or "").strip().lower()
            if s_low.isdigit():
                v = int(s_low)
                return 0 if v < 1 else v + 1
            smap = {"tiny": 0, "minuscol": 0, "piccolissim": 0, "small": 1, "piccol": 1, "medium": 2, "media": 2, "large": 3, "grand": 3, "huge": 4, "enorm": 4, "gargantuan": 5, "mastodontic": 5}
            for k, r in smap.items():
                if k in s_low:
                    return r
            return 2

        a_sz = _dmg_size_rank(actor)
        t_sz = _dmg_size_rank(target)
        if t_sz < a_sz + 2:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply(f"{target.name} deve essere almeno 2 taglie più grande per scalarla (DMG p. 271)!"))
            return
        atk_bonus = max(atk_str, atk_dex) + pb
        r_a = roll_dice(f"1d20{'+' if atk_bonus >= 0 else ''}{atk_bonus}")["total"]
        t_dex = entity_get_attr_mod(target, "DES") + ((entity_get_total_level(target) - 1) // 4 + 2)
        r_t = roll_dice(f"1d20{'+' if t_dex >= 0 else ''}{t_dex}")["total"]
        ok = r_a >= r_t
        if ok:
            actor.climbing_on_target = target.name
            if getattr(target, "position", None):
                actor.position = list(target.position)
        msg = f"🧗 [SCALARE CREATURA GRANDE (DMG p.271)] {actor.name} ({r_a}) vs {target.name} Acrobazia ({r_t}): {'✅ Si aggrappa sopra! (Vantaggio agli attacchi in mischia contro di essa)' if ok else '❌ Scivola giù!'}"
    elif "overrun" in man or "oltrepass" in man:
        r_a = roll_dice(f"1d20+{atk_str + pb}")["total"]
        t_str = entity_get_attr_mod(target, "FOR") + ((entity_get_total_level(target) - 1) // 4 + 2)
        r_t = roll_dice(f"1d20+{t_str}")["total"]
        ok = r_a >= r_t
        if ok and getattr(actor, "position", None) and getattr(target, "position", None):
            dq = target.position[0] - actor.position[0]
            dr = target.position[1] - actor.position[1]
            actor.position = [target.position[0] + (1 if dq > 0 else (-1 if dq < 0 else 0)), target.position[1] + (1 if dr > 0 else (-1 if dr < 0 else 0))]
        msg = f"🐂 [OLTREPASSARE (DMG)] {actor.name} ({r_a}) vs {target.name} ({r_t}): {'✅ Oltrepassa lo spazio nemico!' if ok else '❌ Bloccato!'}"
    elif "tumble" in man or "capovolt" in man:
        r_a = roll_dice(f"1d20+{atk_dex + pb}")["total"]
        t_dex = entity_get_attr_mod(target, "DES") + ((entity_get_total_level(target) - 1) // 4 + 2)
        r_t = roll_dice(f"1d20+{t_dex}")["total"]
        ok = r_a >= r_t
        if ok and getattr(actor, "position", None) and getattr(target, "position", None):
            dq = target.position[0] - actor.position[0]
            dr = target.position[1] - actor.position[1]
            actor.position = [target.position[0] + (1 if dq > 0 else (-1 if dq < 0 else 0)), target.position[1] + (1 if dr > 0 else (-1 if dr < 0 else 0))]
        msg = f"🤸 [CAPOVOLTA (DMG)] {actor.name} Acrobazia ({r_a}) vs {target.name} ({r_t}): {'✅ Attraversa lo spazio ostile!' if ok else '❌ Fermato!'}"
    elif "shove_aside" in man or "laterale" in man:
        r_a = roll_dice(f"1d20+{atk_str + pb}")["total"]
        t_def = max(entity_get_attr_mod(target, "FOR"), entity_get_attr_mod(target, "DES"))
        r_t = roll_dice(f"1d20+{t_def}")["total"]
        ok = r_a >= r_t
        if ok and getattr(actor, "position", None) and getattr(target, "position", None):
            dq = target.position[0] - actor.position[0]
            dr = target.position[1] - actor.position[1]
            # Spinta laterale: ruota di 90 gradi rispetto alla congiungente
            lat_q = -1 if dr > 0 else (1 if dr < 0 else 1)
            lat_r = 1 if dq > 0 else (-1 if dq < 0 else 0)
            target.position = [target.position[0] + lat_q, target.position[1] + lat_r]
        msg = f"💨 [SPINTA LATERALE (DMG)] {actor.name} ({r_a}) vs {target.name} ({r_t}): {'✅ Spinto di lato di 1,5 m (5 ft)!' if ok else '❌ Spinta respinta!'}"
    else:  # Disarm DMG p. 271 (TxC vs Atletica/Acrobazia bersaglio)
        r_a = roll_dice(f"1d20+{max(atk_str, atk_dex) + pb}")["total"]
        t_def = max(entity_get_attr_mod(target, "FOR"), entity_get_attr_mod(target, "DES")) + ((entity_get_total_level(target) - 1) // 4 + 2)
        r_t = roll_dice(f"1d20+{t_def}")["total"]
        ok = r_a >= r_t
        if ok and "Disarmato" not in target.conditions:
            target.conditions.append("Disarmato")
            _sync_sheet_conditions(target)
        msg = f"🗡️ [DISARMARE (DMG p.271)] {actor.name} TxC ({r_a}) vs {target.name} ({r_t}): {'✅ Oggetto fatto cadere!' if ok else '❌ Presa salda!'}"

    actor.has_acted_this_turn = True
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


def handle_madness_request(data, player, game_state):
    """DMG p. 258-260: Applica una Follia Breve / Lunga / Indefinita (opzionale selezionata dal DM)."""
    if not _is_dmg_opt_enabled(game_state, "opt_madness"):
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("La regola opzionale Follia (DMG) è disabilitata dal Master."))
        return
    target = _get_target_or_self(data, player, game_state)
    if not target:
        return
    tier = data.get("tier", "short")
    roll_val = data.get("roll_val")
    res = roll_madness(tier=tier, roll_val=roll_val)
    if not isinstance(getattr(target, "madness_effects", None), list):
        target.madness_effects = []
    target.madness_effects.append(res)
    tag = f"{res['tier']} ({res['duration']})"
    if tag not in target.conditions:
        target.conditions.append(tag)
    _sync_sheet_conditions(target)
    msg = f"🧠 [{res['tier'].upper()} - d100: {res['roll']}] {target.name} soffre per {res['duration']}: {res['desc']}"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


def handle_apply_poison_or_disease_request(data, player, game_state):
    """DMG p. 256-258: Applica un Veleno o Malattia ufficiale con TS su Costituzione automatico."""
    if not _is_dm(player):
        return
    target = _get_target_or_self(data, player, game_state)
    if not target:
        return
    kind = data.get("kind", "poison")  # "poison" | "disease"
    item_name = data.get("name", "")
    ts_mod = get_effective_save_bonus_from_dict(target, "COS")

    if kind == "disease":
        d_info = DMG_DISEASES.get(item_name) or next(iter(DMG_DISEASES.values()))
        dc = int(data.get("dc") or d_info.get("dc", 12))
        r = roll_dice(f"1d20{'+' if ts_mod >= 0 else ''}{ts_mod}")["total"]
        if r >= dc:
            msg = f"🦠 [MALATTIA - {item_name}] {target.name} supera TS COS {r} >= {dc} ed evita il contagio!"
        else:
            if not isinstance(getattr(target, "diseases", None), list):
                target.diseases = []
            if item_name not in target.diseases:
                target.diseases.append(item_name)
            if f"Malato: {item_name}" not in target.conditions:
                target.conditions.append(f"Malato: {item_name}")
            _sync_sheet_conditions(target)
            msg = f"🦠 [MALATTIA CONTRATTA - {item_name}] {target.name} fallisce TS COS {r} < {dc}! Effetto: {d_info.get('desc')}"
    else:
        p_info = DMG_POISONS.get(item_name) or next(iter(DMG_POISONS.values()))
        dc = int(data.get("dc") or p_info.get("dc", 13))
        r = roll_dice(f"1d20{'+' if ts_mod >= 0 else ''}{ts_mod}")["total"]
        dmg_f = str(p_info.get("dmg", "0"))
        raw_d = roll_dice(dmg_f.split()[0])["total"] if dmg_f != "0" and "d" in dmg_f else 0
        passed = (r >= dc)
        from server.rules.combat import apply_damage
        if passed:
            dmg_app = raw_d // 2 if p_info.get("half_on_save") else 0
            if dmg_app > 0:
                fin, _, _, _ = apply_damage(target, dmg_app, damage_type="Veleno", game_state=game_state)
            else:
                fin = 0
            msg = f"🧪 [VELENO - {item_name}] {target.name} supera TS COS {r} >= {dc}! Danni da Veleno dimezzati/evitati: {fin} PV."
        else:
            fin, _, _, _ = apply_damage(target, raw_d, damage_type="Veleno", game_state=game_state) if raw_d > 0 else (0, "", 0, 0)
            if "Avvelenato" not in target.conditions and "avvelenat" in str(p_info.get("condition", "")).lower():
                target.conditions.append("Avvelenato")
            _sync_sheet_conditions(target)
            msg = f"☠️ [VELENO - {item_name}] {target.name} FALLISCE TS COS {r} < {dc}! Subisce {fin} danni da Veleno ({p_info.get('condition')})."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


def handle_chase_dash_request(data, player, game_state):
    """DMG p. 252-255: Inseguimenti - Scatti gratuiti = 3 + mod COS, oltre scatta TS COS CD 10 o Sfinimento + Complicazione d20."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    con_mod = entity_get_attr_mod(actor, "COS")
    free_limit = get_max_free_dashes(con_mod)
    actor.chases_dashes_used = int(getattr(actor, "chases_dashes_used", 0) or 0) + 1
    exh_msg = ""
    if actor.chases_dashes_used > free_limit:
        ts_mod = get_effective_save_bonus_from_dict(actor, "COS")
        r = roll_dice(f"1d20{'+' if ts_mod >= 0 else ''}{ts_mod}")["total"]
        if r < 10:
            actor.exhaustion_level = min(6, int(getattr(actor, "exhaustion_level", 0) or 0) + 1)
            actor.conditions = [c for c in actor.conditions if not str(c).startswith("Sfinimento")]
            actor.conditions.append(f"Sfinimento (Liv. {actor.exhaustion_level})")
            exh_msg = f" ⚠️ Scatto extra oltre il limite ({actor.chases_dashes_used}/{free_limit}): TS COS {r} < 10 -> +1 Sfinimento (Liv. {actor.exhaustion_level})!"
        else:
            exh_msg = f" ✅ Scatto extra ({actor.chases_dashes_used}/{free_limit}): TS COS {r} >= 10, resiste alla fatica."
    comp = roll_chase_complication(data.get("forced_comp_roll"))
    _sync_sheet_conditions(actor)
    msg = f"🏃 [INSEGUIMENTO - SCATTO #{actor.chases_dashes_used}/{free_limit}] {actor.name}.{exh_msg} | Complicazione (d20={comp['roll']}): {comp['desc']}"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(actor.name, actor.hp, actor.max_hp, actor.initiative, actor.conditions, getattr(actor, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


def handle_survival_tick_request(data, player, game_state):
    """DMG p. 110-111: Fame, Sete & Clima Estremo (opzionale selezionata dal DM)."""
    if not _is_dmg_opt_enabled(game_state, "opt_hunger_thirst_weather"):
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Sopravvivenza Rigida (Fame/Sete/Clima) è disabilitata dal Master."))
        return
    if not _is_dm(player):
        return
    event = str(data.get("event", "day_pass")).lower()  # "day_pass" | "extreme_heat" | "extreme_cold"
    fed_set = set(data.get("fed_players", []))
    watered_set = set(data.get("watered_players", []))
    logs = []
    for p in getattr(game_state, "players", []):
        if not (getattr(p, "is_party_member", False) or getattr(p, "is_companion", False)) or getattr(p, "hp", 0) <= 0:
            continue
        con_mod = entity_get_attr_mod(p, "COS")
        ts_mod = get_effective_save_bonus_from_dict(p, "COS")
        if event in ("extreme_heat", "extreme_cold"):
            dc = int(data.get("dc", 10 if event == "extreme_cold" else 5) or 10)
            r = roll_dice(f"1d20{'+' if ts_mod >= 0 else ''}{ts_mod}")["total"]
            if r < dc:
                p.exhaustion_level = min(6, int(getattr(p, "exhaustion_level", 0) or 0) + 1)
                p.conditions = [c for c in p.conditions if not str(c).startswith("Sfinimento")]
                p.conditions.append(f"Sfinimento (Liv. {p.exhaustion_level})")
                logs.append(f"{p.name}: TS COS {r}<{dc} (+1 Sfinimento)")
            else:
                logs.append(f"{p.name}: TS COS {r}>={dc} (Resiste)")
        else:
            if p.name in fed_set:
                p.hunger_days = 0
            else:
                p.hunger_days = int(getattr(p, "hunger_days", 0) or 0) + 1
                max_hunger = max(1, 3 + con_mod)
                if p.hunger_days > max_hunger:
                    p.exhaustion_level = min(6, int(getattr(p, "exhaustion_level", 0) or 0) + 1)
                    logs.append(f"{p.name}: Digiuno {p.hunger_days}>{max_hunger}g (+1 Sfinimento)")
            if p.name in watered_set:
                p.water_days = 0
            else:
                p.water_days = int(getattr(p, "water_days", 0) or 0) + 1
                r_w = roll_dice(f"1d20{'+' if ts_mod >= 0 else ''}{ts_mod}")["total"]
                if p.water_days >= 1 and r_w < 15:
                    step = 2 if getattr(p, "exhaustion_level", 0) >= 1 else 1
                    p.exhaustion_level = min(6, int(getattr(p, "exhaustion_level", 0) or 0) + step)
                    logs.append(f"{p.name}: Disidratazione TS {r_w}<15 (+{step} Sfinimento)")
            if p.exhaustion_level > 0:
                p.conditions = [c for c in p.conditions if not str(c).startswith("Sfinimento")]
                p.conditions.append(f"Sfinimento (Liv. {p.exhaustion_level})")
        _sync_sheet_conditions(p)
        broadcast(game_state, make_player_stats_update(p.name, p.hp, p.max_hp, p.initiative, p.conditions, getattr(p, "temp_hp", 0)))
    msg = f"🧭 [SOPRAVVIVENZA DMG - {event.upper()}] " + (" | ".join(logs) if logs else "Il gruppo ha consumato razioni e acqua normalmente.")
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


def handle_mount_request(data, player, game_state):
    """Combattimento in Sella (PHB p. 198): collega o smonta un cavaliere dalla cavalcatura."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    mount_name = data.get("mount_name")
    if not mount_name or data.get("dismount"):
        prev = getattr(actor, "mount_name", None)
        if getattr(game_state, "combat_active", False) and prev:
            from common.i18n import speed_to_hexes
            half_cost = max(1, speed_to_hexes(getattr(actor, "speed", 30), getattr(actor, "speed_unit", None)) // 2)
            actor.movement_spent_this_turn = getattr(actor, "movement_spent_this_turn", 0) + half_cost
        actor.mount_name = None
        msg = f"🐎 {actor.name} scende di sella{f' da {prev}' if prev else ''}."
    else:
        mount = game_state.find_player(mount_name)
        if not mount:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply(f"Cavalcatura '{mount_name}' non trovata."))
            return
        from server.rules.combat import _get_entity_size_rank
        a_sz = _get_entity_size_rank(actor)
        m_sz = _get_entity_size_rank(mount)
        # Se m_sz e' impostata esplicitamente (es. Media vs Cavallo non indicato, default Large se ha horse/cavallo/worg/drake/griffon nel nome)
        m_name_low = str(mount.name).lower()
        if m_sz <= a_sz and any(kw in m_name_low for kw in ("cavallo", "horse", "destriero", "steed", "pon", "worg", "grifone", "griffon", "orso", "bear", "pantera", "elk", "cervo", "mulo", "mule")):
            m_sz = max(m_sz, 3)
        if m_sz < a_sz + 1:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply(f"{mount.name} non è abbastanza grande per essere cavalcata da {actor.name} (serve almeno 1 taglia superiore, PHB p. 198)!"))
            return
        if getattr(game_state, "combat_active", False):
            from common.i18n import speed_to_hexes
            max_h = speed_to_hexes(getattr(actor, "speed", 30), getattr(actor, "speed_unit", None))
            half_cost = max(1, max_h // 2)
            if (getattr(actor, "movement_spent_this_turn", 0) + half_cost) > max_h and (getattr(game_state, "automation_settings", {}) or {}).get("strict_movement_limits", True):
                if getattr(actor, "conn", None):
                    send_message(actor.conn, make_error_reply("Movimento insufficiente per montare in sella (costa metà velocità, PHB p. 198)!"))
                return
            actor.movement_spent_this_turn = getattr(actor, "movement_spent_this_turn", 0) + half_cost
        actor.mount_name = mount.name
        if getattr(mount, "position", None):
            actor.position = list(mount.position)
        msg = f"🐎 [IN SELLA] {actor.name} monta in sella a {mount.name} (costo metà movimento, movimenti sincronizzati)."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


def handle_surprise_request(data, player, game_state):
    """Imposta o rimuove la condizione Sorpreso (PHB p. 189)."""
    if not _is_dm(player):
        return
    target = _get_target_or_self(data, player, game_state)
    if not target:
        return
    surprised = bool(data.get("surprised", True))
    target.surprised = surprised
    if surprised and "Sorpreso" not in target.conditions:
        target.conditions.append("Sorpreso")
    elif not surprised:
        target.conditions = [c for c in target.conditions if c not in ("Sorpreso", "Surprised")]
    _sync_sheet_conditions(target)
    msg = f"😱 {target.name} è SORPRESO (perde movimento/azioni nel 1° turno e reazioni fino alla fine del turno)!" if surprised else f"😌 {target.name} non è più Sorpreso."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


def handle_submerged_breath_request(data, player, game_state):
    """Combattimento Subacqueo & Soffocamento (PHB p. 183 & 198)."""
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    action = str(data.get("action", "toggle_submerged")).lower()
    con_mod = entity_get_attr_mod(actor, "COS")
    from server.dm_monster_engine import has_water_breathing
    can_breathe_water = has_water_breathing(actor)
    if action == "toggle_submerged":
        actor.is_submerged = bool(data.get("submerged", not getattr(actor, "is_submerged", False)))
        if actor.is_submerged:
            actor.breath_rounds_left = None if can_breathe_water else get_breath_hold_rounds(con_mod)
            if "Immerso" not in actor.conditions:
                actor.conditions.append("Immerso")
            if can_breathe_water:
                msg = f"🌊 {actor.name} è ora IMMERSO sott'acqua (Respirare Sott'Acqua/Anfibio: nessun rischio di soffocamento!)."
            else:
                msg = f"🌊 {actor.name} è ora IMMERSO sott'acqua (Resistenza al Fuoco attiva; Apnea: {actor.breath_rounds_left} round)."
        else:
            actor.breath_rounds_left = None
            actor.conditions = [c for c in actor.conditions if c != "Immerso"]
            msg = f"🌬️ {actor.name} riemerge in superficie e respira normalmente."
    else:  # tick_round
        if can_breathe_water:
            actor.breath_rounds_left = None
            msg = f"🌊 {actor.name} respira liberamente sott'acqua (Anfibio / Respirare Sott'Acqua)."
            _sync_sheet_conditions(actor)
            broadcast(game_state, make_chat_broadcast("Sistema", msg))
            broadcast(game_state, make_player_stats_update(actor.name, actor.hp, actor.max_hp, actor.initiative, actor.conditions, getattr(actor, "temp_hp", 0)))
            broadcast(game_state, make_game_state(game_state.get_state_dict()))
            return
        cur = getattr(actor, "breath_rounds_left", None)
        if cur is None:
            cur = get_breath_hold_rounds(con_mod)
        cur -= int(data.get("rounds", 1) or 1)
        actor.breath_rounds_left = cur
        if cur <= -get_suffocation_rounds(con_mod):
            actor.hp = 0
            if "Incosciente" not in actor.conditions:
                actor.conditions.append("Incosciente")
            msg = f"🫧 [SOFFOCAMENTO!] {actor.name} esaurisce l'aria e crolla a 0 PF!"
        elif cur <= 0:
            rem = get_suffocation_rounds(con_mod) + cur
            msg = f"🫧 [SENZA RESPIRO!] {actor.name} sta soffocando! Round prima di crollare a 0 PF: {rem}."
        else:
            msg = f"🌊 {actor.name} trattiene il respiro ({cur} round di apnea rimasti)."
    _sync_sheet_conditions(actor)
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(actor.name, actor.hp, actor.max_hp, actor.initiative, actor.conditions, getattr(actor, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))


def handle_class_feature_request(data, player, game_state):
    """
    Gestore unificato privilegi di classe PHB mancanti:
    - Bard Countercharm (Lv 6+)
    - Paladin Cleansing Touch (Lv 14+)
    - Druid Natural Recovery (Lv 2 Land) & Moon Combat Wild Shape Heal
    - Cleric Domain Channel Divinity (Preserve Life, Radiance of the Dawn, Destructive Wrath, Guided Strike)
    - Sorcerer Font of Magic & Metamagic active selection
    """
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    if not actor:
        return
    if _check_surprised_block(actor, game_state, "usare un privilegio di classe"):
        return

    feat = str(data.get("feature", "") or "").strip().lower()
    target = _get_target_or_self(data, actor, game_state) or actor
    fs = getattr(actor, "full_sheet", None)
    if not isinstance(fs, dict):
        fs = {}
        actor.full_sheet = fs

    # 1. Bard Countercharm (PHB p. 54, Lv 6+)
    if feat in ("countercharm", "controfascino", "contro-fascino"):
        bard_l = entity_get_class_level(actor, "bardo", "bard")
        if bard_l < 6 and not entity_has_keyword(actor, "controfascino", "countercharm"):
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Controfascino richiede Bardo Lv 6+."))
            return
        actor.has_acted_this_turn = True
        pos_a = getattr(actor, "position", None)
        gtype = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
        buffed = []
        for p in getattr(game_state, "players", []):
            if getattr(p, "hp", 0) <= 0:
                continue
            if getattr(p, "is_party_member", False) != getattr(actor, "is_party_member", False):
                continue
            in_range = (p.name == actor.name)
            if not in_range and pos_a and getattr(p, "position", None):
                in_range = grid_distance(Hex(pos_a[0], pos_a[1]), Hex(p.position[0], p.position[1]), gtype) <= 6
            if in_range:
                if hasattr(p, "add_effect"):
                    p.add_effect({"id": "countercharm", "name": "Controfascino (Vant. TS Spaventato/Affascinato)", "duration_rounds": 1, "source": actor.name})
                buffed.append(p.name)
        msg = f"🎼 [CONTROFASCINO] {actor.name} intona una melodia protettiva: {', '.join(buffed) or actor.name} ottengono Vantaggio ai TS contro Spaventato/Affascinato fino al termine del prossimo turno!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    # 2. Paladin Cleansing Touch (PHB p. 85, Lv 14+)
    if feat in ("cleansing_touch", "tocco_purificatore", "tocco purificatore"):
        pal_l = entity_get_class_level(actor, "paladino", "paladin")
        if pal_l < 14 and not entity_has_keyword(actor, "tocco purificatore", "cleansing touch"):
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Tocco Purificatore richiede Paladino Lv 14+."))
            return
        cha_uses = max(1, entity_get_attr_mod(actor, "CAR"))
        if entity_find_resource(actor, "tocco purificatore", "cleansing touch") is None:
            fs.setdefault("custom_resources", []).append({"name": "Tocco Purificatore", "current": cha_uses, "max": cha_uses, "reset_on": "long"})
        ok, new_c, mx = entity_spend_resource(actor, ("tocco purificatore", "cleansing touch"), 1)
        if not ok:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Usi di Tocco Purificatore esauriti."))
            return
        actor.has_acted_this_turn = True
        spell_to_end = str(data.get("spell_name", "") or "").strip()
        ended = []
        if spell_to_end:
            ended.append(spell_to_end)
            if hasattr(target, "remove_effect"):
                target.remove_effect(spell_to_end)
        elif hasattr(target, "active_effects") and target.active_effects:
            last_fx = target.active_effects.pop()
            ended.append(str(last_fx.get("name", last_fx.get("id", "Incantesimo"))))
        if not ended and getattr(target, "conditions", None):
            for c in list(target.conditions):
                if any(k in str(c).lower() for k in ("affascinat", "spaventat", "paralizz", "accec", "assord", "malat", "charm", "fright", "paralyz")):
                    target.conditions.remove(c)
                    ended.append(c)
                    break
        _sync_sheet_conditions(target)
        msg = f"✨ [TOCCO PURIFICATORE] {actor.name} tocca {target.name} e termina: {', '.join(ended) if ended else 'un effetto magico attivo'} ({new_c}/{mx} usi)."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    # 3. Druid Natural Recovery (Lv 2+ Circolo della Terra, PHB p. 68)
    if feat in ("natural_recovery", "recupero_naturale", "recupero naturale"):
        dr_l = entity_get_class_level(actor, "druido", "druid")
        if dr_l < 2:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Recupero Naturale richiede Druido Lv 2+."))
            return
        if entity_find_resource(actor, "recupero naturale", "natural recovery") is None:
            fs.setdefault("custom_resources", []).append({"name": "Recupero Naturale", "current": 1, "max": 1, "reset_on": "long"})
        ok, new_c, mx = entity_spend_resource(actor, ("recupero naturale", "natural recovery"), 1)
        if not ok:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Recupero Naturale già utilizzato oggi."))
            return
        budget = max(1, (dr_l + 1) // 2)
        slots = fs.get("spell_slots", {})
        rec = []
        rem = budget
        for sl_k in sorted([int(k) for k in slots.keys() if str(k).isdigit() and int(k) <= 5], reverse=True):
            s_obj = slots.get(str(sl_k))
            if isinstance(s_obj, dict):
                while rem >= sl_k and s_obj.get("current", 0) < s_obj.get("max", 0):
                    s_obj["current"] += 1
                    rem -= sl_k
                    rec.append(f"{sl_k}°")
        msg = f"🌿 [RECUPERO NATURALE] {actor.name} medita durante il Riposo Breve (budget {budget} liv.): recupera slot [{', '.join(rec) if rec else 'nessuno mancante'}]."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    # 4. Moon Druid Combat Wild Shape Heal (Azione Bonus: 1d8/livello slot)
    if feat in ("combat_wild_shape_heal", "cura_forma_selvatica", "combat wild shape heal"):
        dr_l = entity_get_class_level(actor, "druido", "druid")
        if dr_l < 2:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Richiede Druido della Luna Lv 2+."))
            return
        slot_l = max(1, min(9, int(data.get("slot_level", 1) or 1)))
        from common.character_schema import consume_spell_or_pact_slot
        ok, s_desc = consume_spell_or_pact_slot(fs, slot_l, prefer_pact=False)
        if not ok:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply(f"Nessuno slot incantesimo di {slot_l}°+ disponibile."))
            return
        heal_r = roll_dice(f"{slot_l}d8")
        old_hp = actor.hp
        actor.hp = min(actor.max_hp, actor.hp + heal_r["total"])
        actor.bonus_action_used_this_turn = True
        msg = f"🐾 [FORMA SELVATICA DA COMBATTIMENTO] {actor.name} spende {s_desc} (Azione Bonus) e si cura di {actor.hp - old_hp} PF ({heal_r['total']} tirato)!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_player_stats_update(actor.name, actor.hp, actor.max_hp, actor.initiative, actor.conditions, getattr(actor, "temp_hp", 0)))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    # 5. Cleric Domain Channel Divinity (Preserve Life / Radiance of the Dawn / Destructive Wrath / Guided Strike)
    if feat in ("preserve_life", "preserva_vita", "radiance_dawn", "radianza_alba", "destructive_wrath", "ira_distruttiva", "guided_strike", "colpo_guidato"):
        cl_l = entity_get_class_level(actor, "chierico", "cleric")
        if cl_l < 2:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Incanalare Divinità richiede Chierico Lv 2+."))
            return
        max_cd = 1 if cl_l < 6 else (2 if cl_l < 18 else 3)
        if entity_find_resource(actor, "incanalare divinit", "channel divinity") is None:
            fs.setdefault("custom_resources", []).append({"name": "Incanalare Divinità", "current": max_cd, "max": max_cd, "reset_on": "short"})
        ok, new_c, mx = entity_spend_resource(actor, ("incanalare divinit", "channel divinity"), 1)
        if not ok:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Incanalare Divinità esaurito."))
            return
        if feat in ("preserve_life", "preserva_vita"):
            pool = 5 * cl_l
            cap = max(1, target.max_hp // 2)
            healed = max(0, min(pool, cap - max(0, target.hp)))
            target.hp = min(target.max_hp, target.hp + healed)
            actor.has_acted_this_turn = True
            msg = f"☀️ [PRESERVA VITA] {actor.name} invoca il Dominio della Vita su {target.name}: +{healed} PF (fino a metà PV max, {target.hp}/{target.max_hp})! ({new_c}/{mx} usi)"
            broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
        elif feat in ("radiance_dawn", "radianza_alba"):
            actor.has_acted_this_turn = True
            dc = 8 + ((entity_get_total_level(actor) - 1) // 4 + 2) + entity_get_attr_mod(actor, "SAG")
            dmg_r = roll_dice(f"2d10+{cl_l}")
            from server.rules.combat import apply_damage
            hit_logs = []
            for p in getattr(game_state, "players", []):
                if p.name == actor.name or getattr(p, "is_party_member", False) == getattr(actor, "is_party_member", False) or getattr(p, "hp", 0) <= 0:
                    continue
                con_m = get_effective_save_bonus_from_dict(p, "COS")
                sr = roll_dice(f"1d20{'+' if con_m >= 0 else ''}{con_m}")["total"]
                raw = (dmg_r["total"] // 2) if sr >= dc else dmg_r["total"]
                fd, _, _, _ = apply_damage(p, raw, damage_type="Radioso", game_state=game_state, is_spell=True)
                hit_logs.append(f"{p.name} ({fd} {'[1/2]' if sr >= dc else '[pieno]'})")
            msg = f"🌅 [RADIANZA DELL'ALBA - CD {dc} COS] {actor.name} scaccia oscurità e infligge {dmg_r['total']} Radiosi: {', '.join(hit_logs) if hit_logs else 'nessun nemico colpito'}. ({new_c}/{mx} usi)"
        elif feat in ("destructive_wrath", "ira_distruttiva"):
            actor.destructive_wrath_active = True
            msg = f"⚡ [IRA DISTRUTTIVA] Il prossimo tiro di danni da Fulmine o Tuono di {actor.name} sarà MASSIMIZZATO! ({new_c}/{mx} usi)"
        else:  # guided_strike
            actor.guided_strike_bonus = 10
            msg = f"⚔️ [COLPO GUIDATO] {actor.name} ottiene +10 al prossimo Tiro per Colpire! ({new_c}/{mx} usi)"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    # 6. Sorcerer Font of Magic / Metamagic state
    if feat in ("font_of_magic", "fonte_di_magia", "metamagic", "metamagia"):
        sorc_l = entity_get_class_level(actor, "stregone", "sorcerer")
        if sorc_l < 2:
            if getattr(actor, "conn", None):
                send_message(actor.conn, make_error_reply("Fonte di Magia richiede Stregone Lv 2+."))
            return
        mode = str(data.get("mode", "to_slot")).lower()
        slot_l = max(1, min(5, int(data.get("slot_level", 1) or 1)))
        slot_costs = {1: 2, 2: 3, 3: 5, 4: 6, 5: 7}
        if entity_find_resource(actor, "punti stregoneria", "sorcery points") is None:
            fs.setdefault("custom_resources", []).append({"name": "Punti Stregoneria", "current": sorc_l, "max": sorc_l, "reset_on": "long"})
        slots = fs.setdefault("spell_slots", {})
        if mode == "to_points":
            from common.character_schema import consume_spell_or_pact_slot
            ok_s, s_desc = consume_spell_or_pact_slot(fs, slot_l, prefer_pact=False)
            if not ok_s:
                if getattr(actor, "conn", None):
                    send_message(actor.conn, make_error_reply(f"Nessuno slot di {slot_l}° disponibile."))
                return
            res_sp = entity_find_resource(actor, "punti stregoneria", "sorcery points")
            if res_sp:
                res_sp["current"] = min(int(res_sp.get("max", sorc_l)), int(res_sp.get("current", 0)) + slot_l)
            msg = f"✨ [FONTE DI MAGIA] {actor.name} converte {s_desc} in +{slot_l} Punti Stregoneria!"
        elif mode == "set_metamagic":
            meta_name = str(data.get("metamagic", "quickened") or "quickened").lower()
            meta_cost = int(data.get("cost", 1) or 1)
            ok_m, new_c, mx = entity_spend_resource(actor, ("punti stregoneria", "sorcery points"), meta_cost)
            if not ok_m:
                if getattr(actor, "conn", None):
                    send_message(actor.conn, make_error_reply("Punti Stregoneria insufficienti."))
                return
            actor.active_metamagic = meta_name
            msg = f"🔮 [METAMAGIA - {meta_name.upper()}] {actor.name} attiva {meta_name} ({new_c}/{mx} PS rimasti)."
        else:
            cost_sp = slot_costs[slot_l]
            ok_sp, new_c, mx = entity_spend_resource(actor, ("punti stregoneria", "sorcery points"), cost_sp)
            if not ok_sp:
                if getattr(actor, "conn", None):
                    send_message(actor.conn, make_error_reply(f"Servono {cost_sp} Punti Stregoneria per creare uno slot {slot_l}°."))
                return
            sl_entry = slots.setdefault(str(slot_l), {"max": 0, "current": 0})
            if isinstance(sl_entry, dict):
                sl_entry["current"] = int(sl_entry.get("current", 0)) + 1
            msg = f"✨ [FONTE DI MAGIA] {actor.name} spende {cost_sp} Punti Stregoneria e crea 1 Slot di {slot_l}° livello ({new_c}/{mx} PS rimasti)!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return
