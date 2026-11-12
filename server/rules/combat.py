import re
import random
import math
import threading
from common.protocol import *
from common.hex_utils import Hex, hex_distance, grid_distance, grid_distance_3d, get_sphere_hexes, hex_linedraw, get_cover_between
from common.network_utils import send_message, broadcast
from common.dice import roll_dice
from common.i18n import is_condition_active
from common.item_modifiers import get_effective_attribute_from_dict, get_effective_save_bonus_from_dict

def has_effect_or_condition(entity, name_it, name_en=None):
    """Verifica se un'entità è soggetta a un effetto attivo o a una condizione (D&D 5e)."""
    if not entity:
        return False
    conds = [str(c).lower() for c in getattr(entity, "conditions", [])]
    effs = []
    for e in getattr(entity, "active_effects", []):
        if isinstance(e, dict):
            effs.append(str(e.get("name", "")).lower())
            if e.get("key"):
                effs.append(str(e.get("key")).lower())
    keys = [name_it.lower()]
    if name_en:
        keys.append(name_en.lower())
    for k in keys:
        if any(k in c for c in conds) or any(k in e for e in effs):
            return True
    return False

def _spawn_corpse_loot(target_player, game_state):
    """Spawna automaticamente un forziere con le spoglie sulla mappa quando un mostro o PNG muore a 0 HP."""
    if not game_state or not getattr(game_state, "current_map", None):
        return
    if getattr(target_player, "is_companion", False) or getattr(target_player, "companion_type", None):
        c_type = getattr(target_player, "companion_type", "familiar")
        if c_type == "familiar":
            msg = f"✨ Il famiglio {target_player.name} svanisce in un soffio di spirito."
        elif c_type == "summon":
            msg = f"✨ La creatura evocata {target_player.name} si dissolve."
        else:
            msg = f"☠️ Il compagno {target_player.name} è caduto a 0 HP!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[COMPAGNO] {msg}")
        return
    pos = getattr(target_player, "position", None)
    if not pos:
        return
    loots = game_state.current_map.setdefault("loots", [])
    loot_name = f"Spoglie di {target_player.name}"
    already_looted = any(l.get("q") == pos[0] and l.get("r") == pos[1] and l.get("item") == loot_name for l in loots)
    if not already_looted:
        sheet = getattr(target_player, "full_sheet", {}) or {}
        loot_items = []
        if isinstance(sheet.get("inventory_grid"), list):
            for it in sheet["inventory_grid"]:
                if isinstance(it, dict) and it.get("name"):
                    it_copy = dict(it)
                    it_copy["attuned"] = False
                    it_copy["container"] = "backpack"
                    loot_items.append(it_copy)
        
        coins = dict(sheet.get("wallet", {})) if isinstance(sheet.get("wallet"), dict) else {}
        if not coins and not sheet.get("gold"):
            cr = sheet.get("cr", 1)
            try:
                cr_num = float(cr)
            except (ValueError, TypeError):
                cr_num = 1.0
            if cr_num <= 4:
                sp = sum(random.randint(1, 6) for _ in range(3))
                gp = sum(random.randint(1, 6) for _ in range(2))
                coins = {"MO": gp, "MA": sp}
            else:
                gp = sum(random.randint(1, 6) for _ in range(4)) * 10
                coins = {"MO": gp}

        loots.append({
            "q": pos[0],
            "r": pos[1],
            "item": loot_name,
            "qty": 1,
            "contents": {
                "items": loot_items,
                "wallet": coins
            }
        })
        msg = f"☠️ {target_player.name} è caduto! Un forziere con le sue spoglie è apparso sulla mappa."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[LOOT] {msg}")
        broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))

def recover_expended_ammunition(player, game_state):
    """
    Recupera il 50% delle munizioni spese durante il combattimento (D&D 5e PHB p. 146).
    'Al termine del combattimento, il personaggio può dedicare un minuto a setacciare
    il campo di battaglia per recuperare metà delle munizioni impiegate.'
    """
    expended = getattr(player, "expended_ammo", {})
    if not expended or not any(v > 0 for v in expended.values()):
        return {}

    recovered = {}
    sheet = getattr(player, "full_sheet", None)
    
    for ammo_name, count in list(expended.items()):
        rec_count = count // 2 # 50% arrotondato per difetto
        if rec_count > 0:
            recovered[ammo_name] = rec_count
            if isinstance(sheet, dict) and isinstance(sheet.get("inventory_grid"), list):
                found = False
                for item in sheet["inventory_grid"]:
                    if isinstance(item, dict) and (ammo_name.lower() in item.get("name", "").lower()):
                        item["qty"] = int(item.get("qty", 0)) + rec_count
                        found = True
                        break
                if not found:
                    for idx, slot in enumerate(sheet["inventory_grid"]):
                        if slot is None:
                            sheet["inventory_grid"][idx] = {
                                "name": ammo_name, "type": "Munizioni", "qty": rec_count,
                                "weight": 0.05 * rec_count, "attuned": False, "desc": "Munizioni recuperate RAW"
                            }
                            found = True
                            break
        expended[ammo_name] = 0

    if recovered:
        summary = ", ".join([f"{qty}x {name}" for name, qty in recovered.items()])
        msg = f"🏹 **Recupero Munizioni (RAW PHB p. 146)**: {player.name} cerca sul campo di battaglia e recupera metà delle munizioni: **{summary}**!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[MUNIZIONI] {msg}")
        game_state._trigger_gui_update()
    return recovered

def drop_concentration(player, game_state, notify=True, reason=None):
    """Interrompe la concentrazione di un personaggio (5e RAW) e rimuove le sue AoE attive collegate."""
    had_conc = False
    old_conc_spell = str(
        getattr(player, "concentrating_on", "")
        or (player.full_sheet.get("concentrating_on", "") if isinstance(getattr(player, "full_sheet", None), dict) else "")
        or ""
    ).lower()
    if getattr(player, "concentrating_on", None):
        player.concentrating_on = None
        had_conc = True
    if hasattr(player, "conditions") and "Concentrazione" in player.conditions:
        player.conditions.remove("Concentrazione")
        had_conc = True
    if getattr(player, "full_sheet", None):
        if player.full_sheet.get("concentrating_on"):
            player.full_sheet["concentrating_on"] = None
            had_conc = True
        if isinstance(player.full_sheet.get("conditions"), list) and "Concentrazione" in player.full_sheet["conditions"]:
            player.full_sheet["conditions"].remove("Concentrazione")
            had_conc = True

    removed_aoes = False
    if game_state and hasattr(game_state, "active_aoes"):
        for aoe in list(game_state.active_aoes):
            if aoe.get("caster") == player.name and aoe.get("concentration"):
                game_state.active_aoes.remove(aoe)
                removed_aoes = True
        if removed_aoes:
            broadcast(game_state, make_combat_state_update_broadcast(
                game_state.combat_active, game_state.turn_index, game_state.round_number, game_state.active_aoes
            ))

    removed_effects = []
    removed_summons = []
    if game_state and hasattr(game_state, "players"):
        for p in list(game_state.players):
            if hasattr(p, "active_effects") and p.active_effects:
                for fx in list(p.active_effects):
                    caster = fx.get("concentration_caster")
                    if caster == player.name or (p.name == player.name and fx.get("concentration")):
                        p.remove_effect(fx.get("id") or fx.get("name"))
                        removed_effects.append((p.name, fx.get("name", "Effetto")))
                        had_conc = True
                        broadcast(game_state, make_player_stats_update(
                            p.name, p.hp, p.max_hp, p.initiative, p.conditions, getattr(p, "temp_hp", 0), active_effects=getattr(p, "active_effects", [])
                        ))
            if getattr(p, "companion_type", None) == "summon" and getattr(p, "master_name", None) == player.name:
                if hasattr(game_state, "remove_player"):
                    game_state.remove_player(p)
                elif p in game_state.players:
                    game_state.players.remove(p)
                removed_summons.append(p.name)
                from common.protocol import make_player_left
                broadcast(game_state, make_player_left(p.name))

    if (had_conc or removed_aoes or removed_effects or removed_summons) and game_state:
        if notify:
            reason_str = f" ({reason})" if reason else ""
            break_msg = f"La concentrazione di {player.name} si spezza{reason_str}! Gli effetti ad essa legati svaniscono."
            if removed_effects:
                fx_summary = ", ".join([f"'{fx_name}' su {target}" for target, fx_name in removed_effects])
                break_msg += f" (Effetti terminati: {fx_summary})"
            if removed_summons:
                s_summary = ", ".join(removed_summons)
                break_msg += f" (Creature evocate dissolte: {s_summary})"
            broadcast(game_state, make_chat_broadcast("Sistema", break_msg))
            game_state.log_dm_message(f"[CONCENTRAZIONE] {break_msg}")

        # D&D 5e RAW (PHB p. 191): La caduta per rottura di concentrazione avviene SOLO se l'effetto interrotto concedeva il volo
        flight_spells = ("volo", "volare", "fly", "flying", "levitazione", "levitate", "vento", "wind walk")
        conc_spell = old_conc_spell
        caster_flew_by_conc = any(fs in conc_spell for fs in flight_spells)

        for target_name, fx_name in removed_effects:
            for p in getattr(game_state, "players", []):
                if p.name == target_name and getattr(p, "elevation", 0) > 0:
                    if any(fs in fx_name.lower() for fs in flight_spells):
                        resolve_falling(p, p.elevation, game_state)
        if caster_flew_by_conc and getattr(player, "elevation", 0) > 0:
            sheet = getattr(player, "full_sheet", {}) or {}
            speed_types = str(sheet.get("speed", "")).lower()
            traits = str(sheet.get("traits", [])).lower()
            has_natural_flight = any(k in speed_types or k in traits for k in ["volo", "fly", "ali", "wings", "stazionario", "hover"])
            if not has_natural_flight:
                resolve_falling(player, player.elevation, game_state)

def resolve_falling(entity, fall_distance_ft, game_state, is_voluntary=False, into_water=False, target_creature=None):
    """
    Risolve la caduta secondo le regole autentiche D&D 5e (PHB p. 183):
    - 1d6 danni contundenti per ogni 10 piedi di caduta, fino a un massimo di 20d6.
    - La creatura atterra prona (condizione Prono), a meno che non eviti completamente il danno.
    - Verifica capacità speciali: Caduta Lenta del Monaco (liv. 4+: riduce il danno di 5 x livello Monaco)
      e incantesimo Caduta Morbida (Feather Fall: 0 danni).
    """
    if not entity or fall_distance_ft < 10:
        if entity:
            entity.elevation = max(0, getattr(entity, "elevation", 0) - fall_distance_ft)
            broadcast(game_state, make_player_stats_update(
                entity.name, entity.hp, entity.max_hp, entity.initiative,
                getattr(entity, "conditions", []), getattr(entity, "temp_hp", 0),
                elevation=entity.elevation
            ))
        return 0

    opt_fall_xge = bool(getattr(game_state, "automation_settings", {}).get("opt_falling_xge_tce", False)) if game_state else False
    # XGtE p. 77: velocità di caduta 500 ft/round; se resta in aria > 0 ft al termine del turno non impatta ancora
    if opt_fall_xge and fall_distance_ft > 500 and getattr(entity, "elevation", 0) > 500:
        entity.fall_remaining_ft = int(fall_distance_ft - 500)
        entity.elevation = max(0, getattr(entity, "elevation", 0) - 500)
        if hasattr(game_state, "combat_log"):
            game_state.combat_log.append(f"💨 {entity.name} precipita di 500 ft (restano {entity.fall_remaining_ft} ft / quota {entity.elevation} ft, XGtE).")
        return 0

    dice_count = min(20, int(fall_distance_ft // 10))
    rolls = [random.randint(1, 6) for _ in range(dice_count)]
    raw_dmg = sum(rolls)

    # Verifica caduta in acqua (esplicita o casella mappa water/acqua)
    on_water = bool(into_water)
    if not on_water and game_state and getattr(entity, "position", None):
        pos = entity.position
        if len(pos) >= 2:
            cur_map = getattr(game_state, "current_map", {}) or {}
            hex_obj = (cur_map.get("hexes", {}) or {}).get(f"{pos[0]},{pos[1]}")
            if isinstance(hex_obj, dict):
                t_str = str(hex_obj.get("terrain", "") or hex_obj.get("type", "")).lower()
                if any(w in t_str for w in ("water", "acqua", "river", "fiume", "lake", "lago", "sea", "mare")):
                    on_water = True
    if on_water and raw_dmg > 0:
        if opt_fall_xge:
            # TCE p. 170: TS/Prova CD 15 Atletica o Acrobazia per tuffarsi dimezzando i danni (altrimenti pieni)
            ath = get_effective_skill_bonus_from_dict(entity, "Atletica") if "get_effective_skill_bonus_from_dict" in globals() else 0
            acr = get_effective_skill_bonus_from_dict(entity, "Acrobazia") if "get_effective_skill_bonus_from_dict" in globals() else 0
            best_b = max(ath, acr)
            dive_roll = roll_dice(f"1d20{'+' if best_b >= 0 else ''}{best_b}")["total"]
            if dive_roll >= 15:
                raw_dmg = raw_dmg // 2
                if hasattr(game_state, "combat_log"):
                    game_state.combat_log.append(f"🌊 {entity.name} si tuffa in acqua (Prova {dive_roll} >= CD 15): danni da caduta dimezzati a {raw_dmg}.")
        elif is_voluntary:
            raw_dmg = raw_dmg // 2

    mitigated = False
    mitigation_note = ""

    # 1. Controllo Caduta Morbida (Feather Fall)
    has_feather_fall = False
    for fx in getattr(entity, "active_effects", []):
        fn = str(fx.get("name", "")).lower()
        if "feather fall" in fn or "caduta morbida" in fn:
            has_feather_fall = True
            break

    if has_feather_fall:
        raw_dmg = 0
        mitigated = True
        mitigation_note = " (Annullato da Caduta Morbida / Feather Fall)"
    else:
        # 2. Controllo Caduta Lenta del Monaco (Monk 4+ Slow Fall, multiclasse-aware)
        from common.dnd5e_tables import entity_get_class_level
        monk_lvl = entity_get_class_level(entity, "monaco", "monk")
        if monk_lvl >= 4:
            reduction = monk_lvl * 5
            raw_dmg = max(0, raw_dmg - reduction)
            mitigated = True
            mitigation_note = f" (Ridotto di {reduction} da Caduta Lenta del Monaco)"

    # TCE p. 170: Impatto su altra creatura (TS DES CD 15 per dividere i danni 50/50)
    if opt_fall_xge and target_creature is not None and raw_dmg > 0:
        t_dex = get_effective_save_bonus_from_dict(target_creature, "DES")
        t_save = roll_dice(f"1d20{'+' if t_dex >= 0 else ''}{t_dex}")["total"]
        if t_save < 15:
            split_dmg = raw_dmg // 2
            other_dmg = raw_dmg - split_dmg
            raw_dmg = split_dmg
            apply_damage(target_creature, other_dmg, "Contundente", game_state)
            if not hasattr(target_creature, "conditions"):
                target_creature.conditions = []
            if "Prono" not in target_creature.conditions:
                target_creature.conditions.append("Prono")
            if hasattr(game_state, "combat_log"):
                game_state.combat_log.append(f"💥 {entity.name} rovina su {target_creature.name} (TS DES {t_save} < 15): danni da caduta divisi ({split_dmg}/{other_dmg})!")

    final_dmg = raw_dmg
    entity.elevation = max(0, getattr(entity, "elevation", 0) - fall_distance_ft)

    if final_dmg > 0:
        _apply_hp_change(entity, entity.hp - final_dmg, game_state)
        conds = getattr(entity, "conditions", [])
        if "Prono" not in conds:
            conds.append("Prono")
        if getattr(entity, "full_sheet", None) and isinstance(entity.full_sheet.get("conditions"), list):
            if "Prono" not in entity.full_sheet["conditions"]:
                entity.full_sheet["conditions"].append("Prono")

    log_text = f"🍂 **Caduta (Falling - RAW PHB p. 183)**: {entity.name} precipita per {fall_distance_ft} ft!"
    if mitigation_note:
        log_text += mitigation_note
    if final_dmg > 0:
        log_text += f"\n• Danno: **{final_dmg}** danni contundenti ({dice_count}d6: {rolls})"
        log_text += f"\n• {entity.name} si schianta a terra ed è ora **PRONO**!"
    else:
        log_text += f"\n• {entity.name} atterra dolcemente sui propri piedi senza subire danni."

    broadcast(game_state, make_chat_broadcast("Sistema", log_text))
    game_state.log_dm_message(f"[CADUTA] {log_text}")
    broadcast(game_state, make_player_stats_update(
        entity.name, entity.hp, entity.max_hp, entity.initiative,
        getattr(entity, "conditions", []), getattr(entity, "temp_hp", 0),
        elevation=entity.elevation,
        active_effects=getattr(entity, "active_effects", [])
    ))
    game_state._trigger_gui_update()
    return final_dmg


def _check_zero_hp_survival_features(target_player, old_hp, excess_damage, game_state):
    """
    Gestisce i privilegi D&D 5e RAW che impediscono di scendere a 0 PF (purché non ci sia morte istantanea):
    - Protezione contro la Morte (Death Ward - PHB p. 254)
    - Tenacia Implacabile del Mezzorco (Relentless Endurance - PHB p. 41, 1/Riposo Lungo)
    """
    if old_hp <= 0 or target_player.hp > 0:
        return ""
    if excess_damage >= target_player.max_hp:
        if target_player.hp <= 0 and game_state:
            from server.rules.reaction_magic import release_grapples_held_by
            release_grapples_held_by(target_player, game_state, "è sceso a 0 HP")
        return ""

    # 1. Protezione contro la Morte (Death Ward)
    if has_effect_or_condition(target_player, "Protezione contro la Morte", "Death Ward"):
        target_player.hp = 1
        conds = getattr(target_player, "conditions", [])
        for c_dw in list(conds):
            if str(c_dw).strip().lower() in ("protezione contro la morte", "death ward"):
                conds.remove(c_dw)
        if hasattr(target_player, "active_effects") and isinstance(target_player.active_effects, list):
            target_player.active_effects = [
                fx for fx in target_player.active_effects
                if str(fx.get("name", "")).strip().lower() not in ("protezione contro la morte", "death ward")
            ]
        msg_dw = f"✨ Protezione contro la Morte (PHB p. 254): L'incantesimo si consuma e {target_player.name} resta a 1 PF invece di cadere a 0!"
        if game_state:
            broadcast(game_state, make_chat_broadcast("Sistema", msg_dw))
            game_state.log_dm_message(f"[COMBAT] {msg_dw}")
        return " [✨ Protezione contro la Morte: resta a 1 PF!]"

    # 2. Tenacia Implacabile del Mezzorco (Relentless Endurance - PHB p. 41)
    sheet = getattr(target_player, "full_sheet", None)
    sheet_dict = sheet if isinstance(sheet, dict) else {}
    used_re = bool(getattr(target_player, "relentless_endurance_used", False) or sheet_dict.get("relentless_endurance_used", False))
    if not used_re:
        race_str = str(sheet_dict.get("race", getattr(target_player, "race", "")) or "").lower()
        feats_raw = sheet_dict.get("features", getattr(target_player, "features", ""))
        feats_str = " ".join(str(x) for x in feats_raw).lower() if isinstance(feats_raw, list) else str(feats_raw or "").lower()
        flist = sheet_dict.get("features_list", getattr(target_player, "features_list", [])) or []
        flist_str = " ".join(f"{x.get('name', '')} {x.get('desc', '')}" for x in flist if isinstance(x, dict)).lower()
        has_re = (
            "mezzorco" in race_str or "half-orc" in race_str
            or "tenacia implacabile" in feats_str or "relentless endurance" in feats_str
            or "tenacia implacabile" in flist_str or "relentless endurance" in flist_str
        )
        if has_re:
            target_player.hp = 1
            target_player.relentless_endurance_used = True
            if isinstance(sheet, dict):
                sheet["relentless_endurance_used"] = True
            msg_re = f"💪 Tenacia Implacabile (PHB p. 41): {target_player.name} rifiuta di cadere e rimane a 1 PF (1/Riposo Lungo)!"
            if game_state:
                broadcast(game_state, make_chat_broadcast("Sistema", msg_re))
                game_state.log_dm_message(f"[COMBAT] {msg_re}")
            return " [💪 Tenacia Implacabile: resta a 1 PF!]"

    # 3. Ira Implacabile (Barbaro Lv 11+, PHB p. 49): TS Costituzione CD 10 (+5 per uso) per restare a 1 PF
    from common.dnd5e_tables import entity_get_class_level, entity_has_keyword
    in_rage = is_condition_active(getattr(target_player, "conditions", []), "Ira")
    barb_lvl = entity_get_class_level(target_player, "barbar", "barbarian")
    if in_rage and (barb_lvl >= 11 or entity_has_keyword(target_player, "ira implacabile", "relentless rage")):
        uses = int(getattr(target_player, "relentless_rage_uses", 0) or 0)
        dc_rr = 10 + (5 * uses)
        con_mod = get_effective_save_bonus_from_dict(target_player, "COS")
        rr_roll = roll_dice(f"1d20{'+' if con_mod >= 0 else ''}{con_mod}")["total"]
        if rr_roll >= dc_rr:
            target_player.hp = 1
            target_player.relentless_rage_uses = uses + 1
            msg_rr = f"🪓 [IRA IMPLACABILE] {target_player.name} supera TS COS {rr_roll} >= CD {dc_rr} e rimane in piedi a 1 PF!"
            if game_state:
                broadcast(game_state, make_chat_broadcast("Sistema", msg_rr))
                game_state.log_dm_message(f"[COMBAT] {msg_rr}")
            return f" [🪓 Ira Implacabile: {rr_roll} >= CD {dc_rr}, resta a 1 PF!]"

    if target_player.hp <= 0 and game_state:
        from server.rules.reaction_magic import release_grapples_held_by
        release_grapples_held_by(target_player, game_state, "è sceso a 0 HP")
    return ""


def get_paladin_aura_save_bonus(target_player, game_state):
    """
    Calcola il bonus ai Tiri Salvezza conferito dall'Aura di Protezione del Paladino (PHB p. 85):
    - Paladino di livello >= 6 cosciente e non incapacitato.
    - Raggio: 10 ft (2 caselle) dal liv. 6, 30 ft (6 caselle) dal liv. 18.
    - Bonus: +Mod CAR del Paladino (minimo +1). Non cumulabile tra più Paladini (si applica il più alto).
    """
    if not target_player or not game_state:
        return 0, None
    t_pos = getattr(target_player, "position", None)
    if not t_pos or len(t_pos) < 2:
        return 0, None

    target_party = bool(getattr(target_player, "is_party_member", False) or getattr(target_player, "conn", None))
    cur_map = getattr(game_state, "current_map", {}) or {}
    grid_type = cur_map.get("grid_type", "hex")
    from common.hex_utils import Hex, grid_distance_3d
    from common.item_modifiers import get_effective_attribute_from_dict

    incap_conds = ("incapacitato", "incapacitated", "incosciente", "unconscious", "paralizzato", "paralyzed", "stordito", "stunned", "pietrificato", "petrified", "morto", "dead")
    best_bonus = 0
    best_paladin = None

    for p in getattr(game_state, "players", []):
        if getattr(p, "hp", 0) <= 0:
            continue
        p_conds = [str(c).strip().lower() for c in getattr(p, "conditions", [])]
        if any(c in incap_conds for c in p_conds):
            continue
        p_party = bool(getattr(p, "is_party_member", False) or getattr(p, "conn", None))
        if p_party != target_party:
            continue
        p_pos = getattr(p, "position", None)
        if not p_pos or len(p_pos) < 2:
            continue

        sheet = getattr(p, "full_sheet", None)
        sheet_d = sheet if isinstance(sheet, dict) else {}
        classes_d = sheet_d.get("classes", getattr(p, "classes", {})) or {}
        pal_lvl = 0
        if isinstance(classes_d, dict):
            for k_c, v_c in classes_d.items():
                if "paladin" in str(k_c).lower():
                    try:
                        pal_lvl = max(pal_lvl, int(v_c))
                    except (ValueError, TypeError):
                        pass
        cls_str = str(sheet_d.get("char_class", sheet_d.get("class", getattr(p, "char_class", ""))) or "").lower()
        if pal_lvl == 0 and "paladin" in cls_str:
            try:
                pal_lvl = int(sheet_d.get("level", getattr(p, "level", 1)) or 1)
            except (ValueError, TypeError):
                pal_lvl = 1

        if pal_lvl < 6:
            continue

        aura_radius_hex = 6.0 if pal_lvl >= 18 else 2.0
        dist = grid_distance_3d(
            Hex(t_pos[0], t_pos[1]),
            Hex(p_pos[0], p_pos[1]),
            getattr(target_player, "elevation", 0),
            getattr(p, "elevation", 0),
            grid_type=grid_type
        )
        if dist <= aura_radius_hex:
            cha_val = get_effective_attribute_from_dict(sheet_d if sheet_d else p, "CAR")
            cha_mod = max(1, (cha_val - 10) // 2)
            if cha_mod > best_bonus:
                best_bonus = cha_mod
                best_paladin = p.name

    return best_bonus, best_paladin


def _has_entity_halfling_luck(entity) -> bool:
    sheet = getattr(entity, "full_sheet", None)
    sheet_d = sheet if isinstance(sheet, dict) else {}
    race_s = str(sheet_d.get("race", getattr(entity, "race", "")) or "").lower()
    if "halfling" in race_s:
        return True
    feats = sheet_d.get("features", getattr(entity, "features", ""))
    f_str = " ".join(str(x) for x in feats).lower() if isinstance(feats, list) else str(feats or "").lower()
    return "fortuna dell'halfling" in f_str or "halfling luck" in f_str


def _has_entity_gwf(entity) -> bool:
    sheet = getattr(entity, "full_sheet", None)
    sheet_d = sheet if isinstance(sheet, dict) else {}
    feats = sheet_d.get("features", getattr(entity, "features", ""))
    f_str = " ".join(str(x) for x in feats).lower() if isinstance(feats, list) else str(feats or "").lower()
    flist = sheet_d.get("features_list", getattr(entity, "features_list", [])) or []
    fl_str = " ".join(f"{x.get('name', '')} {x.get('desc', '')}" for x in flist if isinstance(x, dict)).lower()
    combined = f"{f_str} {fl_str}"
    return "armi possenti" in combined or "great weapon fighting" in combined


def apply_damage(target_player, raw_damage, damage_type="Tagliente", game_state=None, is_crit=False, is_non_lethal=False, ignore_resistance=False, is_magical=False, is_silvered=False, is_adamantine=False, is_spell=False, attacker=None):
    """
    Applica il danno secondo le regole D&D 5e:
    1. Oggetti e Soglia di Danno (DMG p. 246), Resistenze, Immunità e Vulnerabilità (Ira, Totem dell'Orso, Immersione)
    2. Assorbimento Punti Ferita Temporanei (Temp HP) prima degli HP effettivi
    3. Morte istantanea o Colpo Non Letale (PHB p. 198)
    4. Condizioni Incosciente/Prono o Morto per i mostri + drop spoglie
    5. Regole opzionali DMG (Danno Massiccio, Ferite Permanenti) e Scissione Melme (MM)
    6. Tiro Salvezza Concentrazione (e interruzione su condizioni invalidanti)
    Ritorna: (danno_finale, note_moltiplicatore, temp_assorbiti, danno_a_hp)
    """
    if raw_damage <= 0:
        return 0, "", 0, 0

    # DMG p. 246-247: Oggetti e Soglia di Danno (Damage Threshold)
    if getattr(target_player, "is_object", False):
        if is_adamantine:
            is_crit = True
        from common.dnd5e_tables import evaluate_object_damage
        obj_dmg, obj_note = evaluate_object_damage(raw_damage, damage_type, getattr(target_player, "damage_threshold", 0))
        if obj_dmg <= 0:
            return 0, f" ({obj_note})", 0, 0
        raw_damage = obj_dmg
        
    dt = str(damage_type).strip().lower() if damage_type else "tagliente"
    
    # Mappatura bilingue per tipi di danno 5e
    damage_map = {
        "tagliente": ["tagliente", "slashing"], "slashing": ["tagliente", "slashing"],
        "perforante": ["perforante", "piercing"], "piercing": ["perforante", "piercing"],
        "contundente": ["contundente", "bludgeoning"], "bludgeoning": ["contundente", "bludgeoning"],
        "fuoco": ["fuoco", "fire"], "fire": ["fuoco", "fire"],
        "freddo": ["freddo", "cold"], "cold": ["freddo", "cold"],
        "fulmine": ["fulmine", "lightning"], "lightning": ["fulmine", "lightning"],
        "veleno": ["veleno", "poison"], "poison": ["veleno", "poison"],
        "acido": ["acido", "acid"], "acid": ["acido", "acid"],
        "psichico": ["psichico", "psychic"], "psychic": ["psichico", "psychic"],
        "necrotico": ["necrotico", "necrotic"], "necrotic": ["necrotico", "necrotic"],
        "radioso": ["radioso", "radiant"], "radiant": ["radioso", "radiant"],
        "forza": ["forza", "force"], "force": ["forza", "force"],
        "tuono": ["tuono", "thunder"], "thunder": ["tuono", "thunder"]
    }
    
    fs = getattr(target_player, "full_sheet", None) or {}
    fs_imm = fs.get("damage_immunities", []) if isinstance(fs, dict) else []
    fs_res = fs.get("damage_resistances", []) if isinstance(fs, dict) else []
    fs_vul = fs.get("damage_vulnerabilities", []) if isinstance(fs, dict) else []

    all_target_imm = [str(x).strip().lower() for x in (list(getattr(target_player, "damage_immunities", [])) + list(fs_imm))]
    all_target_res = [str(x).strip().lower() for x in (list(getattr(target_player, "damage_resistances", [])) + list(fs_res))]
    all_target_vul = [str(x).strip().lower() for x in (list(getattr(target_player, "damage_vulnerabilities", [])) + list(fs_vul))]
    
    # Ira Barbarica: resistenza ai danni fisici (Totem dell'Orso: tutti i tipi eccetto Psichico!)
    if "Ira" in getattr(target_player, "conditions", []):
        from common.dnd5e_tables import entity_has_keyword
        if entity_has_keyword(target_player, "totem dell'orso", "bear totem", "totem of the bear"):
            all_target_res.extend([
                "tagliente", "slashing", "perforante", "piercing", "contundente", "bludgeoning",
                "fuoco", "fire", "freddo", "cold", "fulmine", "lightning", "veleno", "poison",
                "acido", "acid", "necrotico", "necrotic", "radioso", "radiant", "forza", "force", "tuono", "thunder"
            ])
        else:
            all_target_res.extend(["tagliente", "perforante", "contundente", "slashing", "piercing", "bludgeoning"])

    # Combattimento Subacqueo (PHB p. 198): creatura immersa ha Resistenza ai danni da Fuoco
    if getattr(target_player, "is_submerged", False) or is_condition_active(getattr(target_player, "conditions", []), "Immerso"):
        all_target_res.extend(["fuoco", "fire"])

    if is_condition_active(getattr(target_player, "conditions", []), "Pietrificato"):
        # PHB p. 291: Pietrificato conferisce resistenza a tutti i danni e immunità al veleno
        all_target_res.append("tutti")
        all_target_imm.extend(["veleno", "poison"])

    from server.rules.reaction_magic import match_conditional_damage_modifier
    is_immune, imm_bypass_note = match_conditional_damage_modifier(
        all_target_imm, dt, damage_map, is_magical=is_magical, is_silvered=is_silvered, is_adamantine=is_adamantine
    )
    is_resistant, res_bypass_note = match_conditional_damage_modifier(
        all_target_res, dt, damage_map, is_magical=is_magical, is_silvered=is_silvered, is_adamantine=is_adamantine
    )
    is_vulnerable = any(dt in damage_map.get(k, [k]) for k in all_target_vul) or (dt in all_target_vul)

    if not is_immune and raw_damage > 0:
        dt_canon = None
        if dt in ("fuoco", "fire"):
            dt_canon = "fuoco"
        elif dt in ("acido", "acid"):
            dt_canon = "acido"
        elif dt in ("radiante", "radiant"):
            dt_canon = "radiante"
        if dt_canon:
            blocked = getattr(target_player, "regenerated_blocked_types", None)
            if not isinstance(blocked, list):
                blocked = []
                target_player.regenerated_blocked_types = blocked
            if dt_canon not in blocked:
                blocked.append(dt_canon)
    
    note = ""
    if is_immune:
        multiplier = 0.0
        note = f" (Immune a {damage_type}: 0 danni!)"
    elif is_resistant and ignore_resistance and not is_vulnerable:
        multiplier = 1.0
        note = f" (Adepto Elementale: Resistenza a {damage_type} ignorata!)"
    elif is_resistant and not is_vulnerable:
        multiplier = 0.5
        note = f" (Resistenza a {damage_type}: dimezzato)"
    elif is_vulnerable and not is_resistant:
        multiplier = 2.0
        note = f" (Vulnerabilità a {damage_type}: raddoppiato!)"
    else:
        multiplier = 1.0
        
    # Monaco Lv 18+ Corpo Vuoto (Empty Body): Resistenza a tutti i danni eccetto Forza
    dt_check = str(damage_type or "").lower()
    if multiplier > 0 and not any(k in dt_check for k in ("forza", "force")):
        has_empty_body = any(
            isinstance(fx, dict) and (fx.get("id") == "empty_body" or "corpo vuoto" in str(fx.get("name", "")).lower())
            for fx in getattr(target_player, "active_effects", [])
        )
        if has_empty_body and multiplier >= 1.0:
            multiplier *= 0.5
            note += " [👻 Corpo Vuoto: Dimezzato]"

    # Paladino Giuramento degli Antichi Lv 7+ Aura di Custodia: Resistenza ai danni da incantesimo
    if is_spell and multiplier >= 1.0 and game_state is not None and "Dimezzato" not in note:
        from common.dnd5e_tables import entity_get_class_level as _ao_cls, entity_has_keyword as _ao_kw
        t_pos = getattr(target_player, "position", None)
        t_party = bool(getattr(target_player, "is_party_member", False) or getattr(target_player, "conn", None))
        g_type_ao = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
        has_warding = False
        for p_ao in getattr(game_state, "players", []):
            if getattr(p_ao, "hp", 0) <= 0:
                continue
            p_party = bool(getattr(p_ao, "is_party_member", False) or getattr(p_ao, "conn", None))
            if p_party != t_party:
                continue
            pal_l = _ao_cls(p_ao, "paladino", "paladin")
            sub_ao = str((getattr(p_ao, "full_sheet", {}) or {}).get("subclass", "") or "").lower()
            if (pal_l >= 7 and any(k in sub_ao for k in ("antichi", "ancients"))) or _ao_kw(p_ao, "aura di custodia", "aura of warding"):
                conds_ao = [str(c).lower() for c in getattr(p_ao, "conditions", [])]
                if any(ic in conds_ao for ic in ("incosciente", "unconscious", "incapacitato", "incapacitated", "morto", "dead")):
                    continue
                rad_ao = 6.0 if pal_l >= 18 else 2.0
                if p_ao.name == target_player.name:
                    has_warding = True
                    break
                if t_pos and getattr(p_ao, "position", None):
                    if grid_distance_3d(Hex(p_ao.position[0], p_ao.position[1]), Hex(t_pos[0], t_pos[1]), getattr(p_ao, "elevation", 0), getattr(target_player, "elevation", 0), grid_type=g_type_ao) <= rad_ao:
                        has_warding = True
                        break
        if has_warding:
            multiplier *= 0.5
            note += " [🌿 Aura di Custodia: Dimezzato]"

    # Maestria nelle Armature Pesanti (Heavy Armor Master, PHB p. 167): -3 prima di resistenza/vulnerabilità
    from common.feats_and_classes import get_heavy_armor_master_reduction, consume_arcane_ward_hp
    ham_red = get_heavy_armor_master_reduction(target_player, damage_type, is_magical=is_magical) if multiplier > 0 else 0
    eff_raw_damage = max(0, raw_damage - ham_red)
    if ham_red > 0:
        note += f" [🛡️ Armatura Pesante: -{ham_red}]"

    final_dmg = int(eff_raw_damage * multiplier)

    # MM Trasferimento del Danno (Cloaker / Mantello): 50/50 con il bersaglio vincolato
    if final_dmg > 1:
        from server.dm_monster_engine import apply_damage_transfer
        final_dmg, dt_note = apply_damage_transfer(target_player, final_dmg, damage_type, game_state)
        if dt_note:
            note += f" [{dt_note}]"

    # Mago Abiurazione Lv 2+ Interdizione Arcana (Arcane Ward, PHB p. 115): assorbe prima dei Temp HP e PF
    if final_dmg > 0:
        final_dmg, ward_absorbed = consume_arcane_ward_hp(target_player, final_dmg)
        if ward_absorbed > 0:
            note += f" [🔷 Interdizione Arcana assorbe {ward_absorbed}]"
    
    # Assorbimento Punti Ferita Temporanei (Temp HP)
    cur_temp = getattr(target_player, "temp_hp", 0)
    temp_absorbed = 0
    if cur_temp > 0:
        temp_absorbed = min(cur_temp, final_dmg)
        target_player.temp_hp = cur_temp - temp_absorbed
        dmg_to_hp = final_dmg - temp_absorbed
    else:
        dmg_to_hp = final_dmg

    # Forma Selvatica (Druido D&D 5e RAW PHB p. 66): il danno consuma i PV della bestia prima di intaccare i PV reali
    ws = getattr(target_player, "wild_shape", None) or (target_player.full_sheet.get("wild_shape") if isinstance(getattr(target_player, "full_sheet", None), dict) else None)
    if isinstance(ws, dict) and ws.get("active", False):
        beast_hp = int(ws.get("beast_hp", target_player.hp))
        if dmg_to_hp < beast_hp:
            ws["beast_hp"] = beast_hp - dmg_to_hp
            target_player.hp = ws["beast_hp"]
            if getattr(target_player, "full_sheet", None) and isinstance(target_player.full_sheet, dict):
                target_player.full_sheet["hp_current"] = target_player.hp
            note += f" (Assorbito da Forma Selvatica: {target_player.hp}/{ws.get('beast_max_hp', beast_hp)} PV bestia)"
            return final_dmg, note, temp_absorbed, dmg_to_hp
        else:
            # La Forma Selvatica cede: il danno in eccesso si trasferisce ai PV normali del Druido!
            excess_to_druid = dmg_to_hp - beast_hp
            orig_hp = int(ws.get("original_hp", target_player.max_hp))
            orig_max = int(ws.get("original_max_hp", target_player.max_hp))
            orig_ac = int(ws.get("original_ac", 10))
            orig_speed = int(ws.get("original_speed", 30))
            orig_attrs = ws.get("original_attributes", {})

            target_player.max_hp = orig_max
            target_player.ac = orig_ac
            target_player.speed = orig_speed
            if orig_attrs and hasattr(target_player, "attributes") and isinstance(target_player.attributes, dict):
                target_player.attributes.update(orig_attrs)

            ws["active"] = False
            ws["beast_hp"] = 0

            old_hp = orig_hp
            new_hp_unbounded = old_hp - excess_to_druid
            excess_damage = abs(new_hp_unbounded) if new_hp_unbounded < 0 else 0
            target_player.hp = max(0, new_hp_unbounded)
            if getattr(target_player, "full_sheet", None) and isinstance(target_player.full_sheet, dict):
                target_player.full_sheet["hp_current"] = target_player.hp
                target_player.full_sheet["hp_max"] = target_player.max_hp
                target_player.full_sheet["ac"] = target_player.ac
                target_player.full_sheet["wild_shape"] = ws

            note += f" 🌿 (Forma Selvatica infranta! {excess_to_druid} danno residuo trasferito ai PV del Druido: {target_player.hp}/{target_player.max_hp})"
            if game_state:
                broadcast(game_state, make_chat_broadcast("Sistema", f"🌿 La Forma Selvatica di {target_player.name} è stata infranta! Ritorna alla forma umanoide subendo {excess_to_druid} danni residui (PV: {target_player.hp}/{target_player.max_hp})."))
            dmg_to_hp = excess_to_druid
    else:
        old_hp = target_player.hp
        new_hp_unbounded = old_hp - dmg_to_hp
        excess_damage = abs(new_hp_unbounded) if new_hp_unbounded < 0 else 0
        target_player.hp = max(0, new_hp_unbounded)
    survival_note = _check_zero_hp_survival_features(target_player, old_hp, excess_damage, game_state)
    if survival_note:
        note += survival_note

    if target_player.hp == 0 and not is_non_lethal:
        from server.dm_monster_engine import check_and_trigger_mythic_awakening
        awakened, myth_msg = check_and_trigger_mythic_awakening(target_player, game_state)
        if awakened and myth_msg:
            note += " [🔱 RISVEGLIO MITICO!]"
    
    is_npc = (not hasattr(target_player, "conn") or target_player.conn is None) and not getattr(target_player, "is_party_member", False)
    auto_death = True
    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
        auto_death = game_state.automation_settings.get("auto_death_saves", True)
    
    incapacitating = ("incapacitato", "incapacitated", "incosciente", "unconscious", "paralizzato", "paralyzed", "stordito", "stunned", "pietrificato", "petrified", "morto", "dead")
    if target_player.hp == 0 or any(str(c).strip().lower() in incapacitating for c in getattr(target_player, "conditions", [])):
        drop_concentration(target_player, game_state, notify=(not is_npc))

    if target_player.hp == 0:
        if is_non_lethal:
            # PHB p. 198: Colpo Non Letale - mette KO la creatura rendendola Incosciente e Stabile
            if not hasattr(target_player, "conditions"): target_player.conditions = []
            for cond_nl in ("Incosciente", "Stabilizzato", "Prono"):
                if cond_nl not in target_player.conditions:
                    target_player.conditions.append(cond_nl)
            note += " [🥊 Colpo Non Letale: Incosciente & Stabilizzato!]"
            if game_state:
                msg_nl = f"🥊 {target_player.name} viene messo KO da un Colpo Non Letale (0 PF, Incosciente e Stabile)!"
                broadcast(game_state, make_chat_broadcast("Sistema", msg_nl))
                game_state.log_dm_message(f"[COMBAT] {msg_nl}")
        elif is_npc:
            if auto_death:
                if "Morto" not in getattr(target_player, "conditions", []):
                    if not hasattr(target_player, "conditions"): target_player.conditions = []
                    target_player.conditions.append("Morto")
                    _spawn_corpse_loot(target_player, game_state)
                    if game_state and hasattr(game_state, "record_journal_event"):
                        try:
                            game_state.record_journal_event("combat", "Nemico Abbattuto", f"{target_player.name} è stato abbattuto.", actor=target_player.name)
                        except Exception:
                            pass
            else:
                msg = f"💀 {target_player.name} scende a 0 HP! (In attesa di verdetto DM: sconfitto/ucciso/arreso)"
                if game_state:
                    broadcast(game_state, make_chat_broadcast("Sistema", msg))
                    game_state.log_dm_message(f"[COMBAT] {msg}")
        else:
            if excess_damage >= target_player.max_hp and auto_death:
                if not hasattr(target_player, "conditions"): target_player.conditions = []
                if "Morto" not in target_player.conditions:
                    target_player.conditions.append("Morto")
                    msg = f"!!! {target_player.name} E' MORTO SUL COLPO A CAUSA DI DANNO MASSICCIO ({excess_damage} in eccesso) !!!"
                    if game_state:
                        broadcast(game_state, make_chat_broadcast("Sistema", msg))
                        game_state.log_dm_message(msg)
                        if hasattr(game_state, "record_journal_event"):
                            try:
                                game_state.record_journal_event("death", "Morte Istantanea", f"💀 {target_player.name} è morto sul colpo per danno massiccio!", actor=target_player.name)
                            except Exception:
                                pass
            else:
                if not hasattr(target_player, "conditions"): target_player.conditions = []
                if "Incosciente" not in target_player.conditions:
                    target_player.conditions.append("Incosciente")
                if "Prono" not in target_player.conditions:
                    target_player.conditions.append("Prono")
                if game_state and hasattr(game_state, "record_journal_event") and old_hp > 0:
                    try:
                        game_state.record_journal_event("combat", "Eroe a 0 PV", f"⚠️ {target_player.name} è caduto a 0 PV ed è privo di sensi!", actor=target_player.name)
                    except Exception:
                        pass
                if getattr(target_player, "elevation", 0) > 0:
                    resolve_falling(target_player, target_player.elevation, game_state)
                if old_hp == 0 and dmg_to_hp > 0:
                    if "Stabilizzato" in getattr(target_player, "conditions", []):
                        target_player.conditions.remove("Stabilizzato")
                    if "Stable" in getattr(target_player, "conditions", []):
                        target_player.conditions.remove("Stable")
                    if not hasattr(target_player, "death_saves") or not isinstance(target_player.death_saves, dict):
                        target_player.death_saves = {"successes": 0, "failures": 0}
                    fail_add = 2 if is_crit else 1
                    target_player.death_saves["failures"] += fail_add
                    msg = f"💀 {target_player.name} subisce danni mentre è a 0 HP! Perde lo stato Stabilizzato e subisce {fail_add} fallimento/i nel TS contro la morte (Totale: {target_player.death_saves['failures']}/3)!"
                    if target_player.death_saves["failures"] >= 3:
                        if not hasattr(target_player, "conditions"): target_player.conditions = []
                        if "Morto" not in target_player.conditions:
                            target_player.conditions.append("Morto")
                        msg += f" ⚰️ {target_player.name} ha accumulato 3 fallimenti ed è MORTO!"
                        _spawn_corpse_loot(target_player, game_state)
                    if game_state:
                        broadcast(game_state, make_chat_broadcast("Sistema", msg))
                        game_state.log_dm_message(msg)
        if not is_non_lethal and old_hp > 0 and game_state:
            from server.dm_monster_engine import trigger_death_burst_on_zero_hp
            db_msg = trigger_death_burst_on_zero_hp(target_player, game_state)
            if db_msg:
                note += " [💥 Esplosione alla Morte!]"
        # MM Swallow Regurgitation: se il mostro cade a 0 HP/muore, rigurgita eventuali creature ingoiate
        if game_state:
            for sw_v in getattr(game_state, "players", []):
                if getattr(sw_v, "swallowed_by", None) == target_player.name:
                    sw_v.swallowed_by = None
                    if not hasattr(sw_v, "conditions") or not isinstance(sw_v.conditions, list):
                        sw_v.conditions = []
                    for sc_rem in ("Ingoiato", "Inghiottito", "Swallowed", "Accecato", "Trattenuto"):
                        if sc_rem in sw_v.conditions:
                            sw_v.conditions.remove(sc_rem)
                    if "Prono" not in sw_v.conditions:
                        sw_v.conditions.append("Prono")
                    if getattr(target_player, "position", None):
                        sw_v.position = list(target_player.position)
                    reg_msg = f"🤢 {target_player.name} crolla e **rigurgita** {sw_v.name} (cade Prono a terra)!"
                    broadcast(game_state, make_chat_broadcast("Sistema", reg_msg))
                    broadcast(game_state, make_player_stats_update(sw_v.name, sw_v.hp, sw_v.max_hp, sw_v.initiative, sw_v.conditions, getattr(sw_v, "temp_hp", 0)))
    elif target_player.hp > 0:
        if old_hp == 0:
            if "Incosciente" in getattr(target_player, "conditions", []):
                target_player.conditions.remove("Incosciente")
            if "Stabilizzato" in getattr(target_player, "conditions", []):
                target_player.conditions.remove("Stabilizzato")
            if hasattr(target_player, "death_saves") and isinstance(target_player.death_saves, dict):
                target_player.death_saves = {"successes": 0, "failures": 0}
            
    # Concentrazione 5e (RAW: cade su 0 HP o condizioni invalidanti, o su TS subito per danni)
    incapacitating = ("incapacitato", "incapacitated", "incosciente", "unconscious", "paralizzato", "paralyzed", "stordito", "stunned", "pietrificato", "petrified", "morto", "dead")
    if target_player.hp == 0 or any(str(c).strip().lower() in incapacitating for c in getattr(target_player, "conditions", [])):
        drop_concentration(target_player, game_state, notify=True)
    elif final_dmg > 0 and game_state:
        _trigger_concentration_check(target_player, final_dmg, game_state, attacker=attacker)

    # Regole Opzionali DMG (se abilitate dal DM) & Scissione Melme MM
    dm_settings = getattr(game_state, "automation_settings", {}) if game_state else {}
    if isinstance(dm_settings, dict):
        # Danno Massiccio / Shock Sistemico (DMG p. 273)
        if dm_settings.get("opt_massive_damage", False) and final_dmg >= (max(1, target_player.max_hp) / 2.0) and target_player.hp > 0:
            con_mod = get_effective_save_bonus_from_dict(target_player, "COS")
            shock_save = roll_dice(f"1d20{'+' if con_mod >= 0 else ''}{con_mod}")["total"]
            if shock_save < 15:
                from common.dnd5e_tables import roll_system_shock
                sh = roll_system_shock()
                if not hasattr(target_player, "conditions"): target_player.conditions = []
                if not hasattr(target_player, "active_effects") or not isinstance(target_player.active_effects, list):
                    target_player.active_effects = []
                target_player.active_effects.append({
                    "name": f"Shock da Sistema: {sh.get('label', sh.get('desc', 'Effetto'))}",
                    "duration_rounds": 1,
                    "no_reactions": True,
                    "disadvantage": True,
                    "source": "Shock da Sistema",
                })
                if sh["roll"] <= 3:
                    target_player.hp = 0
                    if "Incosciente" not in target_player.conditions:
                        target_player.conditions.append("Incosciente")
                    if sh["roll"] >= 2 and "Stabilizzato" not in target_player.conditions:
                        target_player.conditions.append("Stabilizzato")
                elif sh["condition"] and sh["condition"] not in target_player.conditions:
                    target_player.conditions.append(sh["condition"])
                note += f" [💥 Shock Sistemico (TS COS {shock_save}<15, d10={sh['roll']}): {sh['effect']}]"
                if game_state:
                    msg_sh = f"💥 [DANNO MASSICCIO DMG] {target_player.name} subisce >=50% PF Max, fallisce TS COS {shock_save}<15 (d10={sh['roll']}): {sh['desc']}"
                    broadcast(game_state, make_chat_broadcast("Sistema", msg_sh))
                    game_state.log_dm_message(f"[DMG_OPT] {msg_sh}")

        # Ferite Permanenti (Lingering Injuries DMG p. 272)
        if dm_settings.get("opt_lingering_injuries", False) and (is_crit or (target_player.hp == 0 and not is_non_lethal)):
            from common.dnd5e_tables import roll_lingering_injury
            inj = roll_lingering_injury()
            if not isinstance(getattr(target_player, "injuries", None), list):
                target_player.injuries = []
            target_player.injuries.append(inj)
            if not hasattr(target_player, "conditions"): target_player.conditions = []
            inj_tag = f"Ferita: {inj['name']}"
            if inj_tag not in target_player.conditions:
                target_player.conditions.append(inj_tag)
            note += f" [🩸 Ferita Permanente (d20={inj['roll']}): {inj['name']}]"
            if game_state:
                msg_inj = f"🩸 [FERITA PERMANENTE DMG] {target_player.name} (d20={inj['roll']}): {inj['name']} - {inj['desc']}"
                broadcast(game_state, make_chat_broadcast("Sistema", msg_inj))
                game_state.log_dm_message(f"[DMG_OPT] {msg_inj}")

    # Scissione Melme (MM Gelatina Ocra / Budino Nero)
    if target_player.hp >= 10 and game_state:
        from server.rules.class_abilities import try_ooze_split
        split_msg = try_ooze_split(target_player, damage_type, game_state)
        if split_msg:
            note += " [🧫 Scissione!]"
            broadcast(game_state, make_chat_broadcast("Sistema", split_msg))
            game_state.log_dm_message(f"[MONSTER] {split_msg}")

    if isinstance(getattr(target_player, "full_sheet", None), dict):
        target_player.full_sheet["hp_current"] = target_player.hp
        target_player.full_sheet["hp"] = target_player.hp
        target_player.full_sheet["current_hp"] = target_player.hp
        target_player.full_sheet["temp_hp"] = getattr(target_player, "temp_hp", 0)
        target_player.full_sheet["conditions"] = list(getattr(target_player, "conditions", []))
        
    return final_dmg, note, temp_absorbed, dmg_to_hp

def _apply_hp_change(target_player, new_hp_unbounded, game_state):
    """Gestisce variazioni dirette di HP (cure, comandi DM o statistiche)."""
    old_hp = target_player.hp
    excess_damage = 0
    if new_hp_unbounded < 0:
        excess_damage = abs(new_hp_unbounded)

    eff_max = target_player.max_hp
    if getattr(target_player, "exhaustion_level", 0) >= 4:
        eff_max = max(1, target_player.max_hp // 2)
    target_player.hp = max(0, min(eff_max, new_hp_unbounded))
    _check_zero_hp_survival_features(target_player, old_hp, excess_damage, game_state)
    is_npc = (not hasattr(target_player, "conn") or target_player.conn is None) and not getattr(target_player, "is_party_member", False)
    
    if target_player.hp == 0:
        drop_concentration(target_player, game_state, notify=(not is_npc))
        if is_npc:
            if "Morto" not in getattr(target_player, "conditions", []):
                if not hasattr(target_player, "conditions"): target_player.conditions = []
                target_player.conditions.append("Morto")
                _spawn_corpse_loot(target_player, game_state)
        else:
            if excess_damage >= target_player.max_hp:
                if "Morto" not in getattr(target_player, "conditions", []):
                    if not hasattr(target_player, "conditions"): target_player.conditions = []
                    target_player.conditions.append("Morto")
                    msg = f"!!! {target_player.name} E' MORTO SUL COLPO A CAUSA DI DANNO MASSICCIO !!!"
                    if game_state:
                        broadcast(game_state, make_chat_broadcast("Sistema", msg))
                        game_state.log_dm_message(msg)
            else:
                if not hasattr(target_player, "conditions"): target_player.conditions = []
                if "Incosciente" not in target_player.conditions:
                    target_player.conditions.append("Incosciente")
                if "Prono" not in target_player.conditions:
                    target_player.conditions.append("Prono")
                if getattr(target_player, "elevation", 0) > 0:
                    resolve_falling(target_player, target_player.elevation, game_state)
                if old_hp == 0 and new_hp_unbounded < 0:
                    if not hasattr(target_player, "death_saves") or not isinstance(target_player.death_saves, dict):
                        target_player.death_saves = {"successes": 0, "failures": 0}
                    target_player.death_saves["failures"] += 1
                    msg = f"💀 {target_player.name} subisce danni mentre è a 0 HP! Segna 1 fallimento nel TS contro la morte (Totale: {target_player.death_saves['failures']}/3)!"
                    if target_player.death_saves["failures"] >= 3:
                        if not hasattr(target_player, "conditions"): target_player.conditions = []
                        if "Morto" not in target_player.conditions:
                            target_player.conditions.append("Morto")
                        msg += f" ⚰️ {target_player.name} ha accumulato 3 fallimenti ed è MORTO!"
                        _spawn_corpse_loot(target_player, game_state)
                    if game_state:
                        broadcast(game_state, make_chat_broadcast("Sistema", msg))
                        game_state.log_dm_message(msg)
        if old_hp > 0 and game_state:
            from server.dm_monster_engine import trigger_death_burst_on_zero_hp
            trigger_death_burst_on_zero_hp(target_player, game_state)
        # MM Swallow Regurgitation: se il mostro cade a 0 HP/muore, rigurgita eventuali creature ingoiate
        if game_state:
            for sw_v in getattr(game_state, "players", []):
                if getattr(sw_v, "swallowed_by", None) == target_player.name:
                    sw_v.swallowed_by = None
                    if not hasattr(sw_v, "conditions") or not isinstance(sw_v.conditions, list):
                        sw_v.conditions = []
                    for sc_rem in ("Ingoiato", "Inghiottito", "Swallowed", "Accecato", "Trattenuto"):
                        if sc_rem in sw_v.conditions:
                            sw_v.conditions.remove(sc_rem)
                    if "Prono" not in sw_v.conditions:
                        sw_v.conditions.append("Prono")
                    if getattr(target_player, "position", None):
                        sw_v.position = list(target_player.position)
                    reg_msg = f"🤢 {target_player.name} crolla e **rigurgita** {sw_v.name} (cade Prono a terra)!"
                    broadcast(game_state, make_chat_broadcast("Sistema", reg_msg))
                    broadcast(game_state, make_player_stats_update(sw_v.name, sw_v.hp, sw_v.max_hp, sw_v.initiative, sw_v.conditions, getattr(sw_v, "temp_hp", 0)))
    elif target_player.hp > 0:
        if old_hp == 0:
            if "Incosciente" in getattr(target_player, "conditions", []):
                target_player.conditions.remove("Incosciente")
            if "Stabilizzato" in getattr(target_player, "conditions", []):
                target_player.conditions.remove("Stabilizzato")
            if hasattr(target_player, "death_saves") and isinstance(target_player.death_saves, dict):
                target_player.death_saves = {"successes": 0, "failures": 0}
        
        dmg_val = old_hp - new_hp_unbounded
        if dmg_val > 0 and game_state:
            _trigger_concentration_check(target_player, dmg_val, game_state)

    if isinstance(getattr(target_player, "full_sheet", None), dict):
        target_player.full_sheet["hp_current"] = target_player.hp
        target_player.full_sheet["hp"] = target_player.hp
        target_player.full_sheet["current_hp"] = target_player.hp
        target_player.full_sheet["temp_hp"] = getattr(target_player, "temp_hp", 0)
        target_player.full_sheet["conditions"] = list(getattr(target_player, "conditions", []))

def handle_start_combat_request(data, player, game_state):
    initiator_name = data.get("initiator")
    game_state.gui_queue.put({"type": "SHOW_COMBAT_CONFIG", "payload": {"initiator": initiator_name}})

def _trigger_concentration_check(target_player, dmg_val, game_state, attacker=None):
    if dmg_val > 0 and is_condition_active(getattr(target_player, "conditions", []), "Concentrazione"):
        dc = max(10, dmg_val // 2)
        auto_conc = True
        if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
            auto_conc = game_state.automation_settings.get("auto_concentration_check", True)
        if not auto_conc:
            msg = f"⚠️ {target_player.name} subisce danni mentre è concentrato! Richiesto TS Costituzione CD {dc} (Gestione DM)."
            broadcast(game_state, make_chat_broadcast("Sistema", msg))
            game_state.log_dm_message(f"[CONCENTRAZIONE] {msg}")
            return
            
        from common.dnd5e_tables import entity_has_keyword
        has_mage_slayer_dis = False
        if attacker and attacker.name != target_player.name and entity_has_keyword(attacker, "sterminatore di maghi", "mage slayer"):
            if getattr(attacker, "position", None) and getattr(target_player, "position", None):
                gt_ms = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
                if grid_distance_3d(Hex(attacker.position[0], attacker.position[1]), Hex(target_player.position[0], target_player.position[1]), getattr(attacker, "elevation", 0), getattr(target_player, "elevation", 0), grid_type=gt_ms) <= 1.5:
                    has_mage_slayer_dis = True
            else:
                has_mage_slayer_dis = True

        src_lbl = "Sistema (Concentrazione - Svantaggio Sterminatore di Maghi)" if has_mage_slayer_dis else "Sistema (Concentrazione)"
        if getattr(target_player, "conn", None):
            send_message(target_player.conn, make_prompt_save("COS", dc, "", False, src_lbl, "Contundente"))
        else:
            has_warcaster = entity_has_keyword(target_player, "incantatore da guerra", "war caster")
            mod = get_effective_save_bonus_from_dict(target_player, "COS")
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            adv_s = ""
            if has_warcaster and not has_mage_slayer_dis:
                adv_s = " adv"
            elif has_mage_slayer_dis and not has_warcaster:
                adv_s = " dis"
            f_roll = f"1d20{mod_str}{adv_s}"
            save_result = roll_dice(f_roll)
            roll_tot = save_result["total"]
            is_crit = save_result["rolls"][0] == 20
            is_fail = save_result["rolls"][0] == 1
            threading.Timer(0.1, _process_save_result, args=(target_player.name, "COS", roll_tot, is_crit, is_fail, dc, "", False, src_lbl, game_state, "Contundente")).start()

def advance_combat_turn(game_state, ending_player=None):
    """
    Avanza il turno di combattimento (D&D 5e RAW):
    1. Fine turno creatura uscente:
       - Risoluzione Save-Ends (TS automatici o prompt) per effetti con timing 'end_of_turn'.
       - Decremento e scadenza effetti con timing 'end_of_turn'.
       - Pulizia condizioni temporanee di fine turno (Scatto, Disimpegno).
    2. Avanzamento turno in GameState:
       - Se round_advanced: decremento e scadenza effetti a round ('round_end') per tutti i combattenti.
    3. Inizio turno creatura entrante:
       - Pulizia condizioni di inizio turno (Schivata, Scudo).
       - Decremento e scadenza effetti 'start_of_turn'.
       - Ricarica Azioni Leggendarie per Boss.
       - Annuncio inizio round e Azioni di Tana (Iniziativa 20) / Boss.
       - Notifica turno e broadcast aggiornamenti.
    """
    with game_state.lock:
        combatants = game_state._get_combatants() if hasattr(game_state, "_get_combatants") else game_state.players
        if not game_state.combat_active or not combatants:
            return
            
        prev_p = ending_player or game_state.get_current_turn_player()
        prev_init = getattr(prev_p, "initiative", None) if prev_p else None
        
        # 1. Fine Turno per prev_p
        if prev_p:
            prev_p.has_acted_in_combat = True
            prev_p.savage_attacker_used_this_turn = False
            prev_p.colossus_slayer_used_this_turn = False
            prev_p.gwm_ba_unlocked = False
            for _cp in combatants:
                if hasattr(_cp, "_hit_this_turn_by") and isinstance(_cp._hit_this_turn_by, set):
                    _cp._hit_this_turn_by.clear()
            # Pulizia condizioni temporanee di fine turno
            changed_temp = False
            for temp_c in ["Scatto", "Disimpegno", "Dash", "Disengage"]:
                if temp_c in getattr(prev_p, "conditions", []):
                    prev_p.conditions.remove(temp_c)
                    changed_temp = True
            if getattr(prev_p, "full_sheet", None) and isinstance(prev_p.full_sheet.get("conditions"), list):
                for temp_c in ["Scatto", "Disimpegno", "Dash", "Disengage"]:
                    if temp_c in prev_p.full_sheet["conditions"]:
                        prev_p.full_sheet["conditions"].remove(temp_c)
                        changed_temp = True
                        
            # Controlla effetti attivi con Save-Ends a fine turno
            if hasattr(prev_p, "active_effects") and prev_p.active_effects:
                for fx in list(prev_p.active_effects):
                    save_cfg = fx.get("save_ends")
                    if save_cfg and save_cfg.get("timing", "end_of_turn") == "end_of_turn":
                        stat = str(save_cfg.get("stat", "SAG")).upper()
                        try: dc = int(save_cfg.get("dc", 10))
                        except (ValueError, TypeError): dc = 10
                        fx_name = fx.get("name", "Effetto")
                        
                        # Se il giocatore è connesso, invia prompt interattivo
                        if getattr(prev_p, "conn", None):
                            prompt_msg = f"🎲 {prev_p.name} deve effettuare un Tiro Salvezza su {stat} (CD {dc}) per liberarsi da '{fx_name}'!"
                            broadcast(game_state, make_chat_broadcast("Sistema", prompt_msg))
                            game_state.log_dm_message(f"[SAVE-ENDS] {prompt_msg}")
                            send_message(prev_p.conn, make_prompt_save(stat, dc, "", False, f"Save-Ends: {fx_name}", "Contundente"))
                        else:
                            # NPC/Mostro o non connesso: tiro automatico dal server
                            mod = get_effective_save_bonus_from_dict(prev_p, stat)
                            mod_str = f"+{mod}" if mod >= 0 else str(mod)
                            res = roll_dice(f"1d20{mod_str}")
                            is_crit = res["rolls"][0] == 20
                            is_fail = res["rolls"][0] == 1
                            threading.Timer(0.1, _process_save_result, args=(
                                prev_p.name, stat, res["total"], is_crit, is_fail, dc, "", False, f"Save-Ends: {fx_name}", game_state, "Contundente"
                            )).start()

            # Decrementa effetti di fine turno
            if hasattr(prev_p, "active_effects") and prev_p.active_effects:
                expired_eot = []
                for fx in list(prev_p.active_effects):
                    if fx.get("decrement_timing") == "end_of_turn" and fx.get("duration_rounds") is not None:
                        fx["duration_rounds"] -= 1
                        if fx["duration_rounds"] <= 0:
                            expired_eot.append(fx.get("name"))
                            prev_p.remove_effect(fx.get("id") or fx.get("name"))
                if expired_eot:
                    for exp_name in expired_eot:
                        exp_msg = f"⏳ L'effetto '{exp_name}' su {prev_p.name} è terminato a fine turno."
                        broadcast(game_state, make_chat_broadcast("Sistema", exp_msg))
                        game_state.log_dm_message(f"[EFFETTO] {exp_msg}")

            broadcast(game_state, make_player_stats_update(
                prev_p.name, prev_p.hp, prev_p.max_hp, prev_p.initiative, getattr(prev_p, "conditions", []), 
                getattr(prev_p, "temp_hp", 0), active_effects=getattr(prev_p, "active_effects", [])
            ))

            # MM Movimento Incorporeo: termina il turno dentro un muro/oggetto solido -> 1d10 danni Forza
            from server.dm_monster_engine import is_incorporeal_entity
            if is_incorporeal_entity(prev_p) and getattr(prev_p, "hp", 0) > 0 and getattr(prev_p, "position", None) and getattr(game_state, "current_map", None):
                from server.rules.movement import get_effective_map_walls
                _walls_inc = get_effective_map_walls(game_state.current_map) or []
                _p_pos = [prev_p.position[0], prev_p.position[1]]
                if _p_pos in _walls_inc or tuple(_p_pos) in _walls_inc:
                    _inc_dmg = max(1, int(roll_dice("1d10")["total"]))
                    apply_damage(prev_p, _inc_dmg, "Forza", game_state)
                    _inc_msg = f"👻 [Movimento Incorporeo] {prev_p.name} termina il turno dentro un oggetto/muro solido e subisce {_inc_dmg} danni da Forza!"
                    broadcast(game_state, make_chat_broadcast("Sistema", _inc_msg))
                    game_state.log_dm_message(f"[MONSTER] {_inc_msg}")

        # 2. Avanza l'indice di turno nel GameState (evita doppio decremento end_of_turn già gestito sopra)
        old_round = game_state.round_number
        try:
            game_state.next_turn(tick_end_of_turn=False)
        except TypeError:
            game_state.next_turn()
        round_advanced = (game_state.round_number > old_round)

        # 3. Inizio Turno per next_p
        next_p = game_state.get_current_turn_player()
        if next_p:
            next_p.has_reacted_this_turn = False
            # Scadenza eventuale Azione Preparata non innescata (PHB p. 193)
            if getattr(next_p, "readied_action_data", None) or "Azione Preparata" in getattr(next_p, "conditions", []):
                next_p.readied_action_data = None
                if "Azione Preparata" in getattr(next_p, "conditions", []):
                    next_p.conditions.remove("Azione Preparata")
                exp_r_msg = f"⏳ L'Azione Preparata di {next_p.name} non si è innescata ed è scaduta all'inizio del suo turno."
                broadcast(game_state, make_chat_broadcast("Sistema", exp_r_msg))
                game_state.log_dm_message(f"[COMBAT] {exp_r_msg}")

            # Aura dinamica Spiriti Guardiani (Spirit Guardians - PHB p. 278: 3d8 radiosi/necrotici entro 15 ft / 3 caselle a inizio turno)
            if getattr(next_p, "hp", 0) > 0 and "Morto" not in getattr(next_p, "conditions", []) and getattr(next_p, "position", None):
                next_party = bool(getattr(next_p, "is_party_member", False) or getattr(next_p, "conn", None))
                cur_map = getattr(game_state, "current_map", {}) or {}
                grid_type = cur_map.get("grid_type", "hex")
                from common.hex_utils import Hex, grid_distance_3d
                for caster_p in list(getattr(game_state, "players", [])):
                    if caster_p.name == next_p.name or getattr(caster_p, "hp", 0) <= 0 or not getattr(caster_p, "position", None):
                        continue
                    caster_party = bool(getattr(caster_p, "is_party_member", False) or getattr(caster_p, "conn", None))
                    if caster_party == next_party:
                        continue
                    if has_effect_or_condition(caster_p, "Spiriti Guardiani", "Spirit Guardians"):
                        dist_sg = grid_distance_3d(
                            Hex(next_p.position[0], next_p.position[1]),
                            Hex(caster_p.position[0], caster_p.position[1]),
                            getattr(next_p, "elevation", 0),
                            getattr(caster_p, "elevation", 0),
                            grid_type=grid_type
                        )
                        if dist_sg <= 3.0:
                            c_sheet = getattr(caster_p, "full_sheet", None)
                            c_dc = 14
                            if isinstance(c_sheet, dict):
                                from common.item_modifiers import get_effective_attribute_from_dict
                                wis_v = get_effective_attribute_from_dict(c_sheet, "SAG")
                                pb_v = 2 + (max(1, int(c_sheet.get("level", 5) or 5)) - 1) // 4
                                c_dc = 8 + pb_v + ((wis_v - 10) // 2)
                            from common.item_modifiers import get_effective_attribute_from_dict
                            t_sheet = getattr(next_p, "full_sheet", None)
                            t_wis = get_effective_attribute_from_dict(t_sheet if isinstance(t_sheet, dict) else next_p, "SAG")
                            t_mod = (t_wis - 10) // 2
                            r_sg = roll_dice(f"1d20{'+' if t_mod >= 0 else ''}{t_mod}")
                            _process_save_result(
                                next_p.name, "SAG", r_sg["total"],
                                r_sg["rolls"][0] == 20, r_sg["rolls"][0] == 1,
                                c_dc, "3d8", True, f"Spiriti Guardiani ({caster_p.name})", game_state, "Radioso"
                            )

            # Broadcast statistiche aggiornate
            broadcast(game_state, make_player_stats_update(
                next_p.name, next_p.hp, next_p.max_hp, next_p.initiative, getattr(next_p, "conditions", []), 
                getattr(next_p, "temp_hp", 0), active_effects=getattr(next_p, "active_effects", [])
            ))
            
            # D&D 5e: Le creature leggendarie recuperano le loro azioni leggendarie all'inizio del proprio turno
            if getattr(next_p, "legendary_actions_max", 0) > 0:
                next_p.legendary_actions_current = next_p.legendary_actions_max
                
            msg = f"Round {game_state.round_number} - Turno di {next_p.name}!"
            game_state.log_dm_message(f"[COMBAT] {msg}")
            broadcast(game_state, make_chat_broadcast("Sistema", msg))

            # D&D 5e Lair Actions: Se c'è una creatura con Azione di Tana a Iniziativa 20 (perdendo pareggi)
            if round_advanced or game_state.turn_index == 0:
                from server.dm_optional_tools import trigger_complex_traps_at_round_start
                if getattr(game_state, "active_complex_traps", None):
                    trigger_complex_traps_at_round_start(game_state, 20)
                    trigger_complex_traps_at_round_start(game_state, 10)
            from server.dm_monster_engine import trigger_lair_actions_if_crossed, is_incapacitated_entity
            next_init = getattr(next_p, "initiative", None) if next_p else None
            trigger_lair_actions_if_crossed(game_state, prev_init, next_init, round_advanced)

            # Notifica al DM per Azioni Leggendarie disponibili a fine turno altrui (solo se non incapacitato)
            for p in game_state.players:
                if getattr(p, "legendary_actions_max", 0) > 0 and getattr(p, "legendary_actions_current", 0) > 0 and p.name != next_p.name and not is_incapacitated_entity(p):
                    game_state.log_dm_message(f"[BOSS] 👑 {p.name} può usare un'Azione Leggendaria ({p.legendary_actions_current}/{p.legendary_actions_max} disponibili)!")

        next_name = next_p.name if next_p else ""
        broadcast(game_state, make_combat_state_update_broadcast(
            game_state.combat_active, game_state.turn_index, game_state.round_number, game_state.active_aoes, next_name
        ))
        game_state._trigger_gui_update()

def handle_end_turn_request(data, player, game_state):
    current = game_state.get_current_turn_player()
    if current and current.name == player.name:
        advance_combat_turn(game_state, ending_player=current)


def handle_spend_legendary_action_request(data, player, game_state):
    """
    Gestisce la spesa di Azioni Leggendarie (D&D 5e).
    Un boss leggendario spende azioni tra un turno e l'altro (costo solitamente 1, 2 o 3).
    """
    target_name = data.get("boss_name") or data.get("target_name") or (player.name if player else "")
    action_name = data.get("action_name", "Azione Leggendaria")
    cost = int(data.get("cost", 1))
    
    boss = game_state.find_player(target_name)
    if not boss:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Creatura '{target_name}' non trovata."))
        return
    is_dm = (player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if not is_dm and boss.name != player.name and getattr(boss, "owner", None) != player.name:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Solo il DM può attivare le Azioni Leggendarie di un Boss."))
        return

    from server.dm_monster_engine import is_incapacitated_entity
    if is_incapacitated_entity(boss):
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"{boss.name} è Incapacitato/Morto e non può spendere Azioni Leggendarie (MM p. 11)."))
        return
        
    cur_actions = getattr(boss, "legendary_actions_current", 0)
    max_actions = getattr(boss, "legendary_actions_max", 0)
    
    if cur_actions < cost:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Azioni leggendarie insufficienti: {cur_actions}/{max_actions} (richieste: {cost})."))
        return
        
    boss.legendary_actions_current = cur_actions - cost
    msg = f"👑 {boss.name} usa l'Azione Leggendaria '{action_name}' (Costo: {cost})! Azioni rimaste: {boss.legendary_actions_current}/{max_actions}."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(f"[BOSS] {msg}")
    game_state._trigger_gui_update()

def handle_apply_effect_request(data, player, game_state):
    target_name = data.get("target_name")
    effect_data = data.get("effect", {})
    if not target_name or not effect_data:
        return
        
    target_player = game_state.find_player(target_name)
    if not target_player:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Creatura '{target_name}' non trovata."))
        return
        
    is_dm = (player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if not is_dm and target_player.name != player.name and getattr(target_player, "owner", None) != player.name:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Solo il DM o il proprietario della pedina può applicare effetti."))
        return

    from server.dm_monster_engine import filter_swarm_condition, is_shapechanger_entity
    _req_fx_name = str(effect_data.get("name", ""))
    if not filter_swarm_condition(target_player, _req_fx_name):
        imm_msg = f"🐝 [Sciame] {target_player.name} è immune alla condizione '{_req_fx_name}' (MM)."
        broadcast(game_state, make_chat_broadcast("Sistema", imm_msg))
        return
    if is_shapechanger_entity(target_player) and ("polymorph" in _req_fx_name.lower() or "metamorfosi" in _req_fx_name.lower()) and not effect_data.get("voluntary", False):
        sc_msg = f"🎭 [Mutaforma] {target_player.name} è un Mutaforma (Shapechanger) e annulla automaticamente effetti involontari di Metamorfosi!"
        broadcast(game_state, make_chat_broadcast("Sistema", sc_msg))
        return
        
    with game_state.lock:
        applied_fx = target_player.add_effect(effect_data)
        
    dur = applied_fx.get("duration_rounds")
    dur_str = f"{dur} round" if dur else "permanente"
    save_ends = applied_fx.get("save_ends")
    save_str = f" [TS {save_ends.get('stat')} CD {save_ends.get('dc')}]" if save_ends else ""
    fx_name = applied_fx.get("name", "Effetto")
    icon = applied_fx.get("icon", "✨")
    
    msg = f"{icon} [EFFETTO] Applicato '{fx_name}' a {target_player.name} ({dur_str}{save_str})."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    game_state.log_dm_message(f"[EFFETTO] {msg}")
    broadcast(game_state, make_player_stats_update(
        target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, 
        target_player.conditions, getattr(target_player, "temp_hp", 0), 
        active_effects=getattr(target_player, "active_effects", [])
    ))
    game_state._trigger_gui_update()

def handle_remove_effect_request(data, player, game_state):
    target_name = data.get("target_name")
    effect_id = data.get("effect_id")
    if not target_name or not effect_id:
        return
        
    target_player = game_state.find_player(target_name)
    if not target_player:
        return
        
    is_dm = (player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if not is_dm and target_player.name != player.name and getattr(target_player, "owner", None) != player.name:
        return
        
    with game_state.lock:
        removed = target_player.remove_effect(effect_id)
        
    if removed:
        fx_name = removed.get("name", "Effetto")
        msg = f"✨ [EFFETTO] Rimosso '{fx_name}' da {target_player.name}."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[EFFETTO] {msg}")
        broadcast(game_state, make_player_stats_update(
            target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, 
            target_player.conditions, getattr(target_player, "temp_hp", 0), 
            active_effects=getattr(target_player, "active_effects", [])
        ))
        game_state._trigger_gui_update()


def handle_submit_initiative(data, player, game_state):
    init = data.get("initiative", 0)
    if getattr(player, "initiative_bonus", None) is None:
        player.initiative_bonus = getattr(player, "initiative", 0)
    player.initiative = init
    
    with game_state.lock:
        if game_state.combat_active and len(game_state.players) > 0:
            combatants_before = game_state._get_combatants() if hasattr(game_state, "_get_combatants") else [p for p in game_state.players if getattr(p, "in_combat", True)]
            current_active = combatants_before[game_state.turn_index] if 0 <= game_state.turn_index < len(combatants_before) else None
            game_state.players.sort(key=lambda p: (getattr(p, 'in_combat', True), p.initiative), reverse=True)
            if current_active:
                combatants_after = game_state._get_combatants() if hasattr(game_state, "_get_combatants") else [p for p in game_state.players if getattr(p, "in_combat", True)]
                try:
                    game_state.turn_index = combatants_after.index(current_active)
                except ValueError:
                    game_state.turn_index = 0
            
    game_state._trigger_gui_update()
    broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
    broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
    game_state.log_dm_message(f"[COMBAT] {player.name} tira iniziativa: {init}")

def handle_attack_request(data, player, game_state):
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    target_name = data.get("target_name")
    weapon_name = data.get("weapon_name", "Attacco")
    hit_bonus = data.get("hit_bonus", 0)
    damage_formula = data.get("damage_formula")
    damage_type = data.get("damage_type", "Tagliente")
    
    target_player = game_state.find_player(target_name)
    if not target_player: return

    p_cond = getattr(player, "conditions", [])
    blocking = ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto", "Incapacitato", "Incapacitated"]
    if any(is_condition_active(p_cond, c) for c in blocking) or getattr(player, "hp", 1) <= 0:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Non puoi attaccare mentre sei Incosciente, Paralizzato o a 0 HP!"))
        return

    # PHB p. 290: Affascinato (Charmed) — non può attaccare chi lo ha affascinato
    if is_condition_active(p_cond, "Affascinato") and getattr(player, "charmed_by", None):
        if str(target_player.name).lower() == str(player.charmed_by).lower():
            if player and getattr(player, "conn", None):
                send_message(player.conn, make_error_reply(f"Sei Affascinato da {player.charmed_by} e non puoi attaccarlo (PHB p. 290)!"))
            return

    from server.rules.class_abilities import _check_surprised_block
    if _check_surprised_block(player, game_state, "attaccare"):
        return

    # D&D 5e RAW: i famigli standard non possono compiere attacchi
    if getattr(player, "is_companion", False) and getattr(player, "companion_type", None) == "familiar":
        if not getattr(player, "can_attack", False):
            if player and getattr(player, "conn", None):
                send_message(player.conn, make_error_reply("I famigli standard non possono attaccare (D&D 5e PHB p. 240)! Possono compiere l'azione Aiuto, Schivata, Scatto o erogare incantesimi a contatto."))
            return

    strict_lock = False
    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
        strict_lock = game_state.automation_settings.get("strict_turn_lock", False)
    else:
        strict_lock = getattr(game_state, "strict_turn_lock", False)

    is_reaction = bool(data.get("is_reaction", False))
    is_bonus_action = bool(data.get("is_bonus_action", False))
    if getattr(game_state, "combat_active", False) and strict_lock and not is_reaction:
        curr_turn = game_state.get_current_turn_player()
        if curr_turn and curr_turn.name != player.name:
            if player and getattr(player, "conn", None):
                send_message(player.conn, make_error_reply(f"Non è il tuo turno in combattimento! È il turno di {curr_turn.name}."))
            return
        if is_bonus_action:
            if getattr(player, "bonus_action_used", False):
                if player and getattr(player, "conn", None):
                    send_message(player.conn, make_error_reply("Hai già consumato la tua Azione Bonus in questo turno!"))
                return
            player.bonus_action_used = True
        elif not data.get("extra_action"):
            if getattr(player, "has_acted_this_turn", False) and getattr(player, "attacks_made_this_turn", 0) == 0:
                if player and getattr(player, "conn", None):
                    send_message(player.conn, make_error_reply("Hai già consumato la tua Azione principale in questo turno!"))
                return

    # Colpo Senz'Armi / Two-Weapon Fighting defaults (PHB p. 195)
    from common.dnd5e_tables import entity_has_keyword, entity_get_class_level
    w_lower_init = str(weapon_name or "").lower()
    if not damage_formula and any(k in w_lower_init for k in ("senz'armi", "unarmed", "pugno", "pugni", "calci", "colpo senz")):
        str_mod = _get_entity_ability_mod(player, "FOR") if "_get_entity_ability_mod" in globals() else 0
        monk_lvl_u = entity_get_class_level(player, "monaco", "monk")
        if monk_lvl_u >= 17:
            u_die = "1d10"
        elif monk_lvl_u >= 11:
            u_die = "1d8"
        elif monk_lvl_u >= 5:
            u_die = "1d6"
        elif monk_lvl_u >= 1 or entity_has_keyword(player, "attaccabrighe", "tavern brawler", "arti marziali", "martial arts"):
            u_die = "1d4"
        elif entity_has_keyword(player, "combattimento senz'armi", "unarmed fighting"):
            u_die = "1d8" if data.get("two_hands_free") else "1d6"
        else:
            u_die = None
        if u_die:
            damage_formula = f"{u_die}{'+' + str(str_mod) if str_mod > 0 else (str(str_mod) if str_mod < 0 else '')}"
        else:
            damage_formula = str(max(1, 1 + str_mod))
    if damage_formula and data.get("is_offhand") and not entity_has_keyword(player, "combattere con due armi", "two-weapon fighting"):
        import re as _re_twf
        damage_formula = _re_twf.sub(r"\+\s*\d+\s*$", "", str(damage_formula)).strip() or str(damage_formula)

    # Attacco Extra & Risoluzione Azione di Attacco (D&D 5e RAW PHB p. 72 - multiclasse-aware)
    if not is_reaction and not is_bonus_action:
        f_lvl = entity_get_class_level(player, "guerriero", "fighter")
        max_attacks = 1
        if f_lvl > 0:
            max_attacks = 4 if f_lvl >= 20 else (3 if f_lvl >= 11 else (2 if f_lvl >= 5 else 1))
        elif any(entity_get_class_level(player, *k) >= 5 for k in (("barbar", "barbarian"), ("paladin",), ("ranger",), ("monac", "monk"))):
            max_attacks = 2
        else:
            p_sub = str((getattr(player, "full_sheet", None) or {}).get("subclass", getattr(player, "subclass", "")) or "").lower()
            bard_l = entity_get_class_level(player, "bardo", "bard")
            wiz_l = entity_get_class_level(player, "mago", "wizard")
            if (bard_l >= 6 and any(k in p_sub for k in ("valore", "valor", "spade", "swords"))) or (wiz_l >= 6 and any(k in p_sub for k in ("lama", "bladesing"))):
                max_attacks = 2

        if not hasattr(player, "attacks_made_this_turn"):
            player.attacks_made_this_turn = 0
        player.attacks_made_this_turn += 1
        if player.attacks_made_this_turn >= max_attacks:
            player.has_acted_this_turn = True
    
    try:
        # 1. Roll to Hit
        adv_reasons = []
        dis_reasons = []
        
        t_cond = getattr(target_player, "conditions", [])
        from common.dnd5e_tables import entity_has_keyword, entity_get_class_level
        target_has_alert = entity_has_keyword(target_player, "allerta", "alert") and not any(
            is_condition_active(t_cond, c) for c in ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto", "Incapacitato", "Incapacitated"]
        )

        # Vantaggio per l'attaccante
        if is_condition_active(p_cond, "Invisibile") and not target_has_alert:
            adv_reasons.append("Invisibile")
        if getattr(player, "reckless_attack_active", False) or is_condition_active(p_cond, "Attacco Irruento"):
            adv_reasons.append("Attacco Irruento (Barbaro)")
        if getattr(target_player, "reckless_attack_active", False) or is_condition_active(t_cond, "Attacco Irruento"):
            adv_reasons.append("Bersaglio esposto da Attacco Irruento")

        for c in ["Trattenuto", "Paralizzato", "Incosciente", "Accecato", "Pietrificato", "Stordito"]:
            if is_condition_active(t_cond, c): adv_reasons.append(f"Bersaglio {c}")
            
        # Azione di Aiuto: il bersaglio ha 'Aiutato', che conferisce vantaggio al primo attacco alleato
        if is_condition_active(t_cond, "Aiutato"):
            adv_reasons.append("Aiuto Alleato")
            if "Aiutato" in t_cond: t_cond.remove("Aiutato")
            elif "Helped" in t_cond: t_cond.remove("Helped")
            
        # Svantaggio per l'attaccante
        for c in ["Accecato", "Avvelenato", "Trattenuto", "Prono", "Spaventato"]:
            if is_condition_active(p_cond, c): dis_reasons.append(c)
        if is_condition_active(t_cond, "Invisibile"): dis_reasons.append("Bersaglio Invisibile")
        # RAW 5e: Schivata si perde se incapacitato o velocità scende a 0 (PHB p. 192)
        incaps_dodge = ["Incapacitato", "Incosciente", "Paralizzato", "Stordito", "Pietrificato", "Morto", "Trattenuto", "Afferrato", "Incapacitated"]
        t_speed = getattr(target_player, "speed", 30)
        if is_condition_active(t_cond, "Schivata") and not any(is_condition_active(t_cond, c) for c in incaps_dodge) and t_speed > 0:
            dis_reasons.append("Bersaglio in Schivata")
        
        # Indebolimento (Exhaustion) Lv 3+ impone svantaggio a tiri per colpire
        if getattr(player, "exhaustion_level", 0) >= 3:
            dis_reasons.append("Indebolimento Lv3+")
        
        # Gestione distanza e Prono / Fiancheggiamento
        dist = 999
        dist_3d = 999.0
        if hasattr(player, "position") and player.position and hasattr(target_player, "position") and target_player.position:
            q1, r1 = player.position[0], player.position[1]
            q2, r2 = target_player.position[0], target_player.position[1]
            z1 = getattr(player, "elevation", 0)
            z2 = getattr(target_player, "elevation", 0)
            dist = max(abs(q1 - q2), abs(q1 + r1 - q2 - r2), abs(r1 - r2))
            from common.hex_utils import grid_distance_3d, Hex
            cur_map = getattr(game_state, "current_map", {}) or {}
            grid_type = cur_map.get("grid_type", "hex")
            dist_3d = grid_distance_3d(Hex(q1, r1), Hex(q2, r2), z1, z2, grid_type=grid_type)
            # Controllo portata / gittata (D&D 5e RAW - PHB p. 146-147, 195)
            w_lower = str(weapon_name).lower()
            w_props = [str(p).lower() for p in data.get("weapon_props", [])]
            is_ranged_weapon = bool(data.get("is_ranged")) or any(k in w_lower for k in ["arco", "bow", "balestra", "crossbow", "dardo", "dart", "fionda", "sling", "distanza", "ranged"]) or any(k in w_props for k in ["ranged", "a distanza"])
            has_reach = any(k in w_lower for k in ["alabarda", "halberd", "glaive", "roncone", "picca", "pike", "frusta", "whip", "lancia da cavaliere", "lance"]) or any(k in w_props for k in ["reach", "portata"])

            if not is_ranged_weapon:
                # Mischia: portata 5 ft (1 casella) o 10 ft (2 caselle con proprietà Portata)
                max_reach = 2.0 if has_reach else 1.0
                if dist_3d > max_reach:
                    if player and getattr(player, "conn", None):
                        send_message(player.conn, make_error_reply(f"Bersaglio fuori portata! Portata dell'arma: {int(max_reach * 5)} ft ({int(max_reach)} caselle). Bersaglio a {dist_3d:.1f} caselle."))
                    return
            else:
                # Distanza: Svantaggio con nemico ostile attivo entro 5 ft (PHB p. 195)
                attacker_party = bool(getattr(player, "is_party_member", False) or getattr(player, "conn", None))
                has_hostile_adjacent = False
                for other in getattr(game_state, "players", []):
                    if other.name != player.name and getattr(other, "hp", 0) > 0 and getattr(other, "position", None):
                        other_party = bool(getattr(other, "is_party_member", False) or getattr(other, "conn", None))
                        if other_party != attacker_party:
                            d_adj = grid_distance_3d(Hex(q1, r1), Hex(other.position[0], other.position[1]), z1, getattr(other, "elevation", 0), grid_type=grid_type)
                            if d_adj <= 1.0:
                                o_conds = getattr(other, "conditions", [])
                                if not any(is_condition_active(o_conds, c) for c in ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto", "Incapacitato", "Incapacitated"]):
                                    has_hostile_adjacent = True
                                    break
                if has_hostile_adjacent:
                    has_cxb_or_sniper = entity_has_keyword(player, "esperto di balestre", "crossbow expert", "cecchino magico", "spell sniper")
                    if not has_cxb_or_sniper:
                        dis_reasons.append("Nemico Ostile adiacente a 5 ft (PHB p. 195)")

                # Gittata normale ed estrema
                normal_range_hex = 16.0
                max_range_hex = 64.0
                if any(k in w_lower for k in ["arco lungo", "longbow"]):
                    normal_range_hex, max_range_hex = 30.0, 120.0
                elif any(k in w_lower for k in ["balestra pesante", "heavy crossbow"]):
                    normal_range_hex, max_range_hex = 20.0, 80.0
                elif any(k in w_lower for k in ["pugnale", "dagger", "dardo", "dart", "martello leggero"]):
                    normal_range_hex, max_range_hex = 4.0, 12.0
                elif any(k in w_lower for k in ["balestra a mano", "hand crossbow"]):
                    normal_range_hex, max_range_hex = 6.0, 24.0

                if (getattr(player, "is_submerged", False) or is_condition_active(p_cond, "Immerso")) and dist_3d > normal_range_hex:
                    if player and getattr(player, "conn", None):
                        send_message(player.conn, make_error_reply("Attacco a distanza sott'acqua oltre la gittata normale manca automaticamente (PHB p. 198)!"))
                    return

                if dist_3d > max_range_hex:
                    if player and getattr(player, "conn", None):
                        send_message(player.conn, make_error_reply(f"Bersaglio oltre la gittata massima! ({int(max_range_hex * 5)} ft / {int(max_range_hex)} caselle)."))
                    return
                elif dist_3d > normal_range_hex:
                    dis_reasons.append(f"Oltre la Gittata Normale ({int(normal_range_hex * 5)} ft - Svantaggio)")

            # Combattimento Subacqueo (PHB p. 198): svantaggio mischia se non perforante e privo di velocità di nuoto
            if getattr(player, "is_submerged", False) or is_condition_active(p_cond, "Immerso"):
                has_swim = entity_has_keyword(player, "nuotare", "swim", "tritone", "triton") or (getattr(player, "speed_swim", 0) or 0) > 0
                dt_low = str(damage_type or "").lower()
                if not is_ranged_weapon:
                    is_piercing = any(k in dt_low for k in ("perforant", "piercing")) or any(
                        wk in w_lower for wk in ("stocco", "rapier", "pugnale", "dagger", "lancia", "spear", "spiedo", "tridente", "trident", "giavellotto", "javelin")
                    )
                    if not has_swim and not is_piercing:
                        dis_reasons.append("Combattimento Subacqueo (Arma non perforante - PHB p. 198)")
                else:
                    is_uw_ok = any(wk in w_lower for wk in ("balestra", "crossbow", "rete", "net", "giavellotto", "javelin", "lancia", "spear", "tridente", "trident", "dardo", "dart", "arpione"))
                    if not is_uw_ok:
                        dis_reasons.append("Combattimento Subacqueo (Arma a distanza - PHB p. 198)")

            # Tattica di Branco (Pack Tactics - MM): Vantaggio se un alleato attivo e' entro 1 cella dal bersaglio
            if entity_has_keyword(player, "tattica di branco", "pack tactics"):
                att_p = bool(getattr(player, "is_party_member", False) or getattr(player, "conn", None))
                for other in getattr(game_state, "players", []):
                    if other.name != player.name and other.name != target_player.name and getattr(other, "hp", 0) > 0 and getattr(other, "position", None):
                        oth_p = bool(getattr(other, "is_party_member", False) or getattr(other, "conn", None))
                        if oth_p == att_p:
                            d_pack = grid_distance_3d(Hex(q2, r2), Hex(other.position[0], other.position[1]), z2, getattr(other, "elevation", 0), grid_type=grid_type)
                            o_conds = getattr(other, "conditions", [])
                            if d_pack <= 1.0 and not any(is_condition_active(o_conds, c) for c in ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto", "Incapacitato", "Incapacitated"]):
                                adv_reasons.append("Tattica di Branco (MM)")
                                break

            if is_condition_active(t_cond, "Prono"):
                if dist_3d <= 1.0: adv_reasons.append("Bersaglio Prono (Mischia)")
                elif dist_3d > 1.0: dis_reasons.append("Bersaglio Prono (Distanza)")
            if dist_3d <= 1.0:
                enable_flanking = True
                if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
                    enable_flanking = game_state.automation_settings.get("enable_flanking", True)
                
                if enable_flanking and not is_ranged_weapon:
                    opp_q = q2 + (q2 - q1)
                    opp_r = r2 + (r2 - r1)
                    attacker_party = bool(getattr(player, "is_party_member", False) or getattr(player, "conn", None))
                    target_party = bool(getattr(target_player, "is_party_member", False) or getattr(target_player, "conn", None))
                    for p in getattr(game_state, "players", []):
                        if p.name != player.name and getattr(p, "hp", 0) > 0:
                            if hasattr(p, "position") and p.position and p.position[0] == opp_q and p.position[1] == opp_r:
                                p_z = getattr(p, "elevation", 0)
                                if abs(p_z - z2) <= 5: # Stessa quota del bersaglio (entro 5ft)
                                    p_c = getattr(p, "conditions", [])
                                    p_party = bool(getattr(p, "is_party_member", False) or getattr(p, "conn", None))
                                    is_ally = (p_party == attacker_party) if attacker_party != target_party else True
                                    incapacitated = any(is_condition_active(p_c, c) for c in ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto", "Incapacitato", "Incapacitated"])
                                    if is_ally and not incapacitated and "Invisibile" not in p_c and "Nascosto" not in p_c:
                                        adv_reasons.append("Fiancheggiamento (DMG p. 251)")
                                        break

            # Effetti Atmosferici D&D 5e (DMG p. 109-110)
            weather_val = str(getattr(game_state, "weather", "Sereno")).strip().lower()
            if weather_val in ("tempesta", "storm"):
                if is_ranged_weapon:
                    dis_reasons.append("Tempesta (Vento forte e pioggia battente)")
            elif weather_val in ("nebbia", "fog"):
                if is_ranged_weapon and dist_3d > 1.0:
                    dis_reasons.append("Nebbia fitta (Visibilità oscurata)")
            elif weather_val in ("pioggia", "rain"):
                if is_ranged_weapon and dist_3d >= 4.0:
                    dis_reasons.append("Pioggia intensa (Scarsa visibilità)")
            elif weather_val in ("neve", "snow"):
                if is_ranged_weapon and dist_3d >= 3.0:
                    dis_reasons.append("Neve e bufera (Scarsa visibilità)")

            # Oscurità Ambientale o Magica (D&D 5e PHB p. 183 & p. 194-195)
            is_global_darkness = weather_val in ("oscurita", "oscurità", "darkness", "buio")
            in_magical_darkness_aoe = False
            for aoe in getattr(game_state, "active_aoes", []):
                aoe_name = str(aoe.get("name", "")).lower()
                aoe_type = str(aoe.get("type", "")).lower()
                if "oscurit" in aoe_name or "darkness" in aoe_name or aoe_type == "darkness":
                    aoe_orig = aoe.get("origin", [0, 0])
                    aoe_r = aoe.get("size", 3)
                    d_att = max(abs(q1 - aoe_orig[0]), abs(q1 + r1 - aoe_orig[0] - aoe_orig[1]), abs(r1 - aoe_orig[1]))
                    d_def = max(abs(q2 - aoe_orig[0]), abs(q2 + r2 - aoe_orig[0] - aoe_orig[1]), abs(r2 - aoe_orig[1]))
                    if d_att <= aoe_r or d_def <= aoe_r:
                        in_magical_darkness_aoe = True
                        break

            if is_global_darkness or in_magical_darkness_aoe:
                def is_illuminated(pos_q, pos_r, entity_obj):
                    if getattr(entity_obj, "light_radius", 0) > 0:
                        return True
                    for other in getattr(game_state, "players", []):
                        if getattr(other, "light_radius", 0) > 0 and getattr(other, "position", None):
                            d_l = max(abs(pos_q - other.position[0]), abs(pos_q + pos_r - other.position[0] - other.position[1]), abs(pos_r - other.position[1]))
                            if d_l <= other.light_radius:
                                return True
                    return False

                att_in_light = is_illuminated(q1, r1, player)
                def_in_light = is_illuminated(q2, r2, target_player)

                def entity_has_darkvision(entity_obj):
                    if in_magical_darkness_aoe:
                        conds = [str(c).lower() for c in getattr(entity_obj, "conditions", [])]
                        sheet = getattr(entity_obj, "full_sheet", None) or {}
                        raw_feats = sheet.get("features", [])
                        feats = [raw_feats.lower()] if isinstance(raw_feats, str) else [str(f).lower() for f in (raw_feats or [])]
                        raw_flist = sheet.get("features_list", [])
                        if isinstance(raw_flist, list):
                            feats.extend(str(f.get("name", "") if isinstance(f, dict) else f).lower() for f in raw_flist)
                        raw_traits = sheet.get("traits", [])
                        traits = [raw_traits.lower()] if isinstance(raw_traits, str) else [str(t).lower() for t in (raw_traits or [])]
                        all_text = " ".join(conds + feats + traits)
                        return "vista del diavolo" in all_text or "devil's sight" in all_text or "truesight" in all_text or "visione del vero" in all_text
                    
                    if getattr(entity_obj, "has_darkvision", None) is not None:
                        return bool(entity_obj.has_darkvision)
                    if hasattr(entity_obj, "check_has_darkvision"):
                        return bool(entity_obj.check_has_darkvision())
                    conds = [str(c).lower() for c in getattr(entity_obj, "conditions", [])]
                    if any("scurovisione" in c or "darkvision" in c for c in conds):
                        return True
                    sheet = getattr(entity_obj, "full_sheet", None)
                    if isinstance(sheet, dict):
                        race = str(sheet.get("race", "")).lower()
                        dv_races = ("elfo", "elf", "nano", "dwarf", "mezzelfo", "half-elf", "mezzorco", "half-orc", "gnomo", "gnome", "tiefling", "drow", "duergar", "dragonide")
                        if any(r in race for r in dv_races):
                            return True
                        senses = str(sheet.get("senses", "")).lower()
                        if "scurovisione" in senses or "darkvision" in senses:
                            return True
                        raw_traits = sheet.get("traits", [])
                        traits = [raw_traits.lower()] if isinstance(raw_traits, str) else [str(t).lower() for t in (raw_traits or [])]
                        if any("scurovisione" in t or "darkvision" in t for t in traits):
                            return True
                        raw_feats = sheet.get("features", [])
                        feats = [raw_feats.lower()] if isinstance(raw_feats, str) else [str(f).lower() for f in (raw_feats or [])]
                        if any("scurovisione" in f or "darkvision" in f for f in feats):
                            return True
                    return getattr(entity_obj, "vision_radius", 6) > 6

                att_has_dv = entity_has_darkvision(player)
                def_has_dv = entity_has_darkvision(target_player)

                att_dv_range = getattr(player, "vision_radius", 12)
                def_dv_range = getattr(target_player, "vision_radius", 12)

                att_sees_def = def_in_light or (att_has_dv and dist <= att_dv_range)
                def_sees_att = att_in_light or (def_has_dv and dist <= def_dv_range)

                if not att_sees_def and not def_sees_att:
                    # Entrambi nel buio: vantaggio e svantaggio si annullano
                    dis_reasons.append("Bersaglio non visibile al buio")
                    adv_reasons.append("Attaccante celato nel buio")
                elif att_sees_def and not def_sees_att:
                    # Attaccante vede ma bersaglio non lo vede -> Vantaggio
                    adv_reasons.append("Attaccante Invisibile nell'Oscurità (Scurovisione/Luce)")
                elif not att_sees_def and def_sees_att:
                    # Bersaglio vede l'attaccante ma l'attaccante non vede il bersaglio -> Svantaggio
                    dis_reasons.append("Bersaglio Non Visibile nell'Oscurità (Attaccante Cieco)")

        # Sensi Speciali (Vista Cieca / Percezione Tellurica / Vista del Vero) & Sensibilità alla Luce Solare (MM)
        from server.rules.reaction_magic import (
            check_special_senses_see_target,
            has_entity_sunlight_sensitivity,
            is_in_sunlight,
        )
        eff_dist_h = dist if dist < 999 else 1
        att_sees_spec, _ = check_special_senses_see_target(player, target_player, eff_dist_h)
        if att_sees_spec:
            dis_reasons = [
                r for r in dis_reasons
                if r not in ("Accecato", "Bersaglio Invisibile", "Bersaglio non visibile al buio", "Bersaglio Non Visibile nell'Oscurità (Attaccante Cieco)")
            ]
        def_sees_spec, _ = check_special_senses_see_target(target_player, player, eff_dist_h)
        if def_sees_spec:
            adv_reasons = [
                r for r in adv_reasons
                if r not in ("Invisibile", "Attaccante Invisibile nell'Oscurità (Scurovisione/Luce)", "Attaccante celato nel buio")
            ]

        if has_entity_sunlight_sensitivity(player) and (is_in_sunlight(player, game_state) or is_in_sunlight(target_player, game_state)):
            dis_reasons.append("Sensibilità alla Luce Solare (MM)")

        # Regole PHB aggiuntive su Vantaggio/Svantaggio (Armatura senza competenza, Combattente in Sella, Lottatore, Assassinio, Sensi Ferini, Elusivo)
        from common.feats_and_classes import get_armor_nonproficiency_penalties
        _w_low_tmp = str(weapon_name).lower()
        _is_ranged_tmp = bool(data.get("is_ranged")) or any(k in _w_low_tmp for k in ["arco", "bow", "balestra", "crossbow", "dardo", "dart", "fionda", "sling", "distanza", "ranged"])
        if not data.get("is_spell"):
            if get_armor_nonproficiency_penalties(player).get("disadvantage_str_dex"):
                dis_reasons.append("Armatura senza competenza (PHB p. 144)")
            if not _is_ranged_tmp and getattr(player, "mount_name", None) and entity_has_keyword(player, "combattente in sella", "mounted combatant"):
                if not getattr(target_player, "mount_name", None):
                    _m_obj = game_state.find_player(player.mount_name) if game_state else None
                    _m_sz = _get_entity_size_rank(_m_obj) if _m_obj else 3
                    if _get_entity_size_rank(target_player) < _m_sz:
                        adv_reasons.append("Combattente in Sella (vs creatura più piccola)")
        if entity_has_keyword(player, "lottatore", "grappler") and getattr(target_player, "grappled_by", None) == player.name:
            adv_reasons.append("Lottatore vs Bersaglio Afferrato")
        _p_rogue_l = entity_get_class_level(player, "ladro", "rogue")
        _p_sub_low = str((getattr(player, "full_sheet", {}) or {}).get("subclass", "") or "").lower()
        if _p_rogue_l >= 3 and ("assassin" in _p_sub_low or entity_has_keyword(player, "assassinio", "assassinate")):
            if getattr(game_state, "combat_active", False) and getattr(game_state, "round_number", 1) == 1:
                if not getattr(target_player, "has_acted_this_turn", False) and not getattr(target_player, "has_acted_in_combat", False):
                    adv_reasons.append("Assassinio (Bersaglio non ha ancora agito)")
        if entity_get_class_level(player, "ranger") >= 18 or entity_has_keyword(player, "sensi ferini", "feral senses"):
            dis_reasons = [r for r in dis_reasons if "Invisibile" not in r and "non visibile al buio" not in r]
        _t_rogue_l = entity_get_class_level(target_player, "ladro", "rogue")
        if (_t_rogue_l >= 18 or entity_has_keyword(target_player, "elusivo", "elusive")) and not is_incapacitated_entity(target_player):
            adv_reasons = []

        # Shock Sistemico DMG p. 273 & Ferite Permanenti DMG p. 272
        if any(isinstance(fx, dict) and fx.get("disadvantage") for fx in (getattr(player, "active_effects", None) or [])):
            dis_reasons.append("Shock Sistemico (DMG)")
        from server.dm_optional_tools import get_lingering_injury_penalties, evaluate_facing_attack
        _att_inj = get_lingering_injury_penalties(player)
        if _is_ranged_tmp and _att_inj.get("ranged_attack_disadvantage"):
            dis_reasons.append("Ferita Permanente: Occhio Perso")
        # Regole Opzionali DMG: Climb Onto Bigger Creature & Facing
        _dm_s_dmg3 = getattr(game_state, "automation_settings", {}) or {}
        if _dm_s_dmg3.get("opt_climb_bigger", False) and not _is_ranged_tmp and getattr(player, "climbing_on_target", None) == target_player.name:
            adv_reasons.append("Scalare Creatura Grande (DMG p.271)")
        _facing_res = {"arc": "front", "ignore_shield": False, "grant_advantage": False}
        if _dm_s_dmg3.get("opt_facing", False):
            _g_t_fc = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
            _facing_res = evaluate_facing_attack(player, target_player, grid_type=_g_t_fc)
            if _facing_res.get("grant_advantage"):
                adv_reasons.append("Attacco alle Spalle / Facing (DMG p.252)")

        has_adv = len(adv_reasons) > 0
        has_dis = len(dis_reasons) > 0
        had_both_cancel = False
        if has_adv and has_dis:
            has_adv = False
            has_dis = False
            had_both_cancel = True
            
        auto_calc_adv = True
        if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
            auto_calc_adv = game_state.automation_settings.get("auto_calc_advantage", True)

        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        has_hl = _has_entity_halfling_luck(player)
        hl_note = ""
        if auto_calc_adv and has_adv:
            if has_hl and (roll1 == 1 or roll2 == 1):
                if roll1 == 1:
                    roll1 = random.randint(1, 20)
                elif roll2 == 1:
                    roll2 = random.randint(1, 20)
                hl_note = " [🍀 Fortuna dell'Halfling]"
            base_roll = max(roll1, roll2)
            d20_detail = f"max({roll1}, {roll2})={base_roll}{hl_note}"
        elif auto_calc_adv and has_dis:
            if has_hl and (roll1 == 1 or roll2 == 1):
                if roll1 == 1:
                    roll1 = random.randint(1, 20)
                elif roll2 == 1:
                    roll2 = random.randint(1, 20)
                hl_note = " [🍀 Fortuna dell'Halfling]"
            base_roll = min(roll1, roll2)
            d20_detail = f"min({roll1}, {roll2})={base_roll}{hl_note}"
        else:
            if has_hl and roll1 == 1:
                roll1 = random.randint(1, 20)
                hl_note = " [🍀 Fortuna dell'Halfling]"
            base_roll = roll1
            d20_detail = f"{base_roll}{hl_note}"
            
        try:
            hit_roll = base_roll + int(hit_bonus)
        except ValueError:
            hit_roll = base_roll

        guided_strike_applied = 0
        if getattr(player, "guided_strike_bonus", 0) > 0:
            guided_strike_applied = int(player.guided_strike_bonus)
            hit_roll += guided_strike_applied
            player.guided_strike_bonus = 0

        # Traccia munizioni impiegate per armi a distanza (D&D 5e PHB p. 146)
        w_lower = str(weapon_name).lower()
        is_ranged_att = bool(data.get("is_ranged")) or any(k in w_lower for k in ["arco", "bow", "balestra", "crossbow", "dardo", "dart", "fionda", "sling", "distanza", "ranged"])
        # Stile di Combattimento: Tiro con l'Arco (+2 al tiro per colpire a distanza con arma, PHB p. 72)
        if is_ranged_att and not data.get("is_spell") and not data.get("fighting_style_applied"):
            if entity_has_keyword(player, "tiro con l'arco", "archery"):
                hit_roll += 2
        if is_ranged_att:
            ammo_name = "Frecce"
            if any(k in w_lower for k in ["balestra", "crossbow"]): ammo_name = "Quadrelli"
            elif any(k in w_lower for k in ["fionda", "sling"]): ammo_name = "Proiettili da Fionda"
            elif any(k in w_lower for k in ["dardo", "dart"]): ammo_name = "Dardi"
            
            if not hasattr(player, "expended_ammo") or not isinstance(player.expended_ammo, dict):
                player.expended_ammo = {}
            player.expended_ammo[ammo_name] = player.expended_ammo.get(ammo_name, 0) + 1
            
        crit_thresh = 20
        if "crit_threshold" in data:
            try: crit_thresh = int(data["crit_threshold"])
            except (ValueError, TypeError): crit_thresh = 20
        elif getattr(player, "full_sheet", None):
            try: crit_thresh = int(player.full_sheet.get("crit_threshold", 20))
            except (ValueError, TypeError): crit_thresh = 20
        elif hasattr(player, "crit_threshold"):
            try: crit_thresh = int(player.crit_threshold)
            except (ValueError, TypeError): crit_thresh = 20

        # Critico Migliorato (Campione 19-20 / 18-20 PHB p. 72)
        if crit_thresh == 20:
            p_sheet = getattr(player, "full_sheet", None) or {}
            sub_str = str(p_sheet.get("subclass", getattr(player, "subclass", ""))).lower()
            feats_str = str(p_sheet.get("features", getattr(player, "features", ""))).lower()
            if any(k in sub_str or k in feats_str for k in ("campione", "champion", "critico migliorato", "improved critical")):
                f_lvl = int(p_sheet.get("level", getattr(player, "level", 1)) or 1)
                for ck, cv in p_sheet.get("classes", {}).items():
                    if any(k in str(ck).lower() for k in ("guerriero", "fighter")):
                        f_lvl = int(cv)
                crit_thresh = 18 if f_lvl >= 15 else 19
        is_crit = (base_roll >= crit_thresh)
        is_fail = (base_roll == 1)
        
        benedizione_bonus = 0
        if has_effect_or_condition(player, "Benedizione", "Bless"):
            benedizione_bonus = random.randint(1, 4)
            hit_roll += benedizione_bonus

        anatema_penalty = 0
        if has_effect_or_condition(player, "Anatema", "Bane"):
            anatema_penalty = random.randint(1, 4)
            hit_roll -= anatema_penalty

        _hero_b = int(getattr(player, "pending_hero_bonus", 0) or 0)
        if _hero_b > 0:
            hit_roll += _hero_b
            player.pending_hero_bonus = 0
        
        # 2. CA Bersaglio
        target_ac = getattr(target_player, "ac", 10) or 10
        if target_player.full_sheet:
            try:
                target_ac = int(target_player.full_sheet.get("ac", target_ac))
            except (ValueError, TypeError):
                pass
                
        scudo_applicato = False
        if has_effect_or_condition(target_player, "Scudo", "Shield"):
            target_ac += 5
            scudo_applicato = True
        if _facing_res.get("ignore_shield"):
            _sh_inv = (getattr(target_player, "full_sheet", {}) or {}).get("inventory_grid", []) or []
            _has_phys_shield = any(
                isinstance(it, dict) and it.get("equipped") and ("scudo" in str(it.get("name", "")).lower() or "shield" in str(it.get("name", "")).lower())
                for it in _sh_inv
            )
            if _has_phys_shield or target_ac >= 12:
                if _has_phys_shield:
                    target_ac = max(1, target_ac - 2)

        multiattack_def_ac = False
        if player.name in getattr(target_player, "_hit_this_turn_by", set()):
            if entity_has_keyword(target_player, "difesa contro attacchi multipli", "multiattack defense"):
                target_ac += 4
                multiattack_def_ac = True

        haste_ac = False
        if has_effect_or_condition(target_player, "Velocità", "Haste"):
            target_ac += 2
            haste_ac = True

        slow_ac = False
        if has_effect_or_condition(target_player, "Lentezza", "Slow"):
            target_ac -= 2
            slow_ac = True
                
        # Line of Sight e Copertura D&D 5e (Ostacoli e Creature Interposte)
        blocked_by_wall = False
        cover_bonus = 0
        cover_name = None
        
        if hasattr(player, "position") and player.position and hasattr(target_player, "position") and target_player.position:
            p_hex = Hex(player.position[0], player.position[1])
            t_hex = Hex(target_player.position[0], target_player.position[1])
            line = hex_linedraw(p_hex, t_hex)
            
            if getattr(game_state, "current_map", None):
                from server.rules.movement import get_effective_map_walls
                walls = get_effective_map_walls(game_state.current_map)
                for step in line[1:]:
                    if [step.q, step.r] in walls:
                        blocked_by_wall = True
                        break
                
                if not blocked_by_wall:
                    half_cover = game_state.current_map.get("half_cover", [])
                    three_quarters = game_state.current_map.get("three_quarters_cover", [])
                    other_creatures = [
                        p for p in game_state.players 
                        if p.name != player.name and p.name != target_player.name and getattr(p, "position", None)
                        and getattr(p, "hp", 1) > 0 and "Morto" not in getattr(p, "conditions", [])
                        and getattr(p, "layer", "token") != "gm"
                    ]
                    cover_bonus, cover_name = get_cover_between(p_hex, t_hex, half_cover, three_quarters, other_creatures)

        from server.rules.reaction_magic import get_entity_attack_flags
        is_mag_att, is_silv_att, is_adam_att = get_entity_attack_flags(player, weapon_name, data)

        # Copertura Tattica D&D 5e RAW esplicita inviata dal client o dal DM
        explicit_cover = str(data.get("cover", "auto")).lower()
        if explicit_cover in ("total", "totale"):
            blocked_by_wall = True
            cover_name = "Copertura Totale"
        elif explicit_cover in ("half", "mezza"):
            cover_bonus = 2
            cover_name = "Mezza Copertura (+2 CA)"
        elif explicit_cover in ("three_quarters", "3/4", "tre_quarti"):
            cover_bonus = 5
            cover_name = "Tre Quarti di Copertura (+5 CA)"
        elif explicit_cover in ("none", "nessuna"):
            cover_bonus = 0
            cover_name = None

        if cover_bonus > 0 and not blocked_by_wall:
            if is_ranged_att and entity_has_keyword(player, "tiratore scelto", "sharpshooter", "cecchino magico", "spell sniper"):
                cover_bonus = 0
                cover_name = "Copertura Ignorata (Tiratore Scelto/Cecchino)"
            else:
                target_ac += cover_bonus
                
        hits = (is_crit or (not is_fail and hit_roll >= target_ac)) and not blocked_by_wall
        
        log_msg = f"{player.name} attacca {target_name} con {weapon_name}."
        if has_adv:
            log_msg += f" Tiro con Vantaggio (causa: {', '.join(adv_reasons)})."
        elif has_dis:
            log_msg += f" Tiro con Svantaggio (causa: {', '.join(dis_reasons)})."
        elif had_both_cancel:
            log_msg += f" Tiro Normale (Vantaggio e Svantaggio si annullano: {', '.join(adv_reasons)} vs {', '.join(dis_reasons)})."
        log_msg += f" Tiro per colpire: {hit_roll} [d20: {d20_detail}]"
        if benedizione_bonus > 0:
            log_msg += f" (+{benedizione_bonus} Benedizione)"
        if anatema_penalty > 0:
            log_msg += f" (-{anatema_penalty} Anatema)"
        log_msg += f" vs CA {target_ac}."
        if guided_strike_applied > 0:
            log_msg += f" (+{guided_strike_applied} Colpo Guidato)"
        if data.get("weapon_proficient") is False and not data.get("is_spell"):
            log_msg += " [⚠️ Arma senza competenza]"
        if scudo_applicato:
            log_msg += " (Scudo +5 CA applicato)"
        if multiattack_def_ac:
            log_msg += " (Difesa Attacchi Multipli +4 CA)"
        if haste_ac:
            log_msg += " (Velocità +2 CA)"
        if slow_ac:
            log_msg += " (Lentezza -2 CA)"
        if cover_name and cover_bonus > 0:
            log_msg += f" ({cover_name})"
        
        if blocked_by_wall:
            if cover_name == "Copertura Totale":
                log_msg += " ATTACCO BLOCCATO: Bersaglio protetto da Copertura Totale!"
            else:
                log_msg += " Bloccato dal Muro."
        elif hits:

            log_msg += " COLPITO!"
            # Regola D&D 5e RAW: Qualsiasi attacco a segno entro 1.5m su bersaglio Incosciente o Paralizzato e' un critico automatico!
            if is_adam_att and getattr(target_player, "is_object", False) and not is_crit:
                is_crit = True
                log_msg += " ⚒️ (CRITICO AUTOMATICO: Arma in Adamantio vs Oggetto - XGtE p. 78!)"
            elif not is_crit and dist <= 1 and any(is_condition_active(t_cond, c) for c in ["Incosciente", "Paralizzato", "Unconscious", "Paralyzed"]):
                is_crit = True
                log_msg += " 🌟 (CRITICO AUTOMATICO: Bersaglio Incosciente/Paralizzato entro 1.5m!)"
            elif not is_crit and not data.get("is_spell") and (_p_rogue_l >= 3 and ("assassin" in _p_sub_low or entity_has_keyword(player, "assassinio", "assassinate"))) and (getattr(target_player, "surprised", False) or is_condition_active(t_cond, "Sorpreso")):
                is_crit = True
                log_msg += " 🗡️ (ASSASSINIO: Critico Automatico su Bersaglio Sorpreso - PHB p. 97!)"
            elif is_crit:
                log_msg += " 🌟 (CRITICO! 20 Naturale - Dadi danno raddoppiati!)"

            # DMG p. 271 Opzionale: Marcatura (Marking)
            dm_s_atk = getattr(game_state, "automation_settings", {}) or {}
            if dm_s_atk.get("opt_marking", False) and not is_ranged_att and not is_reaction:
                marked = getattr(player, "marked_targets", None)
                if not isinstance(marked, dict):
                    marked = {}
                    player.marked_targets = marked
                marked[target_player.name] = True
                log_msg += f" 🎯 [Marcatura DMG: {target_player.name} marcato da {player.name}]"
            if damage_formula:
                use_gwf = _has_entity_gwf(player) and any(
                    k in str(weapon_name).lower()
                    for k in ("spadone", "greatsword", "bipenne", "greataxe", "maglio", "maul", "alabarda", "halberd", "falcione", "glaive", "picca", "pike", "spada lunga", "longsword", "bastone ferrato", "quarterstaff", "martello da guerra", "warhammer", "ascia da battaglia", "battleaxe", "due mani", "two-handed", "versatile")
                )
                is_elem_adept = bool(data.get("is_spell")) and entity_has_keyword(player, "adepto elementale", "elemental adept")
                dmg_result = roll_dice(damage_formula, is_crit=is_crit, gwf_reroll=use_gwf, elemental_adept=is_elem_adept)
                dmg_val = max(0, dmg_result["total"])
                if dmg_result.get("rerolled_notes"):
                    log_msg += f" ({', '.join(dmg_result['rerolled_notes'])})"

                # Attaccante Selvaggio (Savage Attacker, PHB p. 169): 1/turno ritira i dadi danno arma in mischia e tieni il maggiore
                if not is_ranged_att and not data.get("is_spell") and not getattr(player, "savage_attacker_used_this_turn", False):
                    if entity_has_keyword(player, "attaccante selvaggio", "savage attacker"):
                        dmg_res_2 = roll_dice(damage_formula, is_crit=is_crit, gwf_reroll=use_gwf, elemental_adept=is_elem_adept)
                        v2 = max(0, dmg_res_2["total"])
                        player.savage_attacker_used_this_turn = True
                        if v2 > dmg_val:
                            log_msg += f" [🪓 Attaccante Selvaggio: {v2} vs {dmg_val}]"
                            dmg_val = v2

                # Chierico Tempesta: Ira Distruttiva (massimizza dadi Fulmine/Tuono)
                if getattr(player, "destructive_wrath_active", False) and any(k in str(damage_type or "").lower() for k in ("fulmine", "lightning", "tuono", "thunder")):
                    import re as _dw_re
                    _parts = _dw_re.findall(r"[+-]?\s*(?:\d+d\d+|\d+)", str(damage_formula or "0"))
                    _dw_tot = 0
                    for _pt in _parts:
                        _pts = _pt.replace(" ", "")
                        _sgn = -1 if _pts.startswith("-") else 1
                        _core = _pts.lstrip("+-")
                        if "d" in _core:
                            _n, _s = _core.split("d", 1)
                            _dw_tot += _sgn * int(_n or 1) * (2 if is_crit else 1) * int(_s or 1)
                        elif _core.isdigit():
                            _dw_tot += _sgn * int(_core)
                    player.destructive_wrath_active = False
                    if _dw_tot > dmg_val:
                        dmg_val = _dw_tot
                    log_msg += " [⚡ Ira Distruttiva: Danni Massimizzati]"

                # Ranger Cacciatore: Uccisore di Colossi (Colossus Slayer, +1d8 1/turno se bersaglio già ferito)
                if not data.get("is_spell") and not getattr(player, "colossus_slayer_used_this_turn", False):
                    if getattr(target_player, "hp", 0) < getattr(target_player, "max_hp", 0):
                        if entity_has_keyword(player, "uccisore di colossi", "colossus slayer"):
                            _cs_dmg = roll_dice("1d8", is_crit=is_crit)["total"]
                            dmg_val += _cs_dmg
                            player.colossus_slayer_used_this_turn = True
                            log_msg += f" (+{_cs_dmg} Uccisore di Colossi)"

                # Punizione Divina Migliorata (Paladino Lv 11+, PHB p. 85): +1d8 radiosi automatici in mischia con arma
                pal_lvl = entity_get_class_level(player, "paladino", "paladin")
                if not is_ranged_att and not data.get("is_spell") and (pal_lvl >= 11 or entity_has_keyword(player, "punizione divina migliorata", "improved divine smite")):
                    ids_dmg = roll_dice("1d8", is_crit=is_crit)["total"]
                    dmg_val += ids_dmg
                    log_msg += f" ☀️ (+{ids_dmg} Punizione Divina Migliorata [1d8 radiante])"

                # Carica / Balzo (Charge / Pounce - MM): se si è mosso almeno 2 celle (10-20 ft) in linea retta prima del colpo
                if not is_ranged_att and getattr(player, "moved_straight_hexes", 0) >= 2 and entity_has_keyword(player, "carica", "charge", "balzo", "pounce"):
                    chg_dmg = roll_dice("2d6", is_crit=is_crit)["total"]
                    dmg_val += chg_dmg
                    ch_dc = int(data.get("charge_dc") or 13)
                    t_str_m = get_effective_save_bonus_from_dict(target_player, "FOR")
                    ch_save = roll_dice(f"1d20{'+' if t_str_m >= 0 else ''}{t_str_m}")["total"]
                    if ch_save < ch_dc:
                        if "Prono" not in target_player.conditions:
                            target_player.conditions.append("Prono")
                        log_msg += f" 🦏 (+{chg_dmg} Carica/Balzo & TS FOR {ch_save}<{ch_dc} -> ATTERRATO!)"
                    else:
                        log_msg += f" 🦏 (+{chg_dmg} Carica/Balzo & TS FOR {ch_save}>={ch_dc} resiste)"

                # Sentinella (Sentinel - PHB p. 169): gli AdO a segno riducono a 0 la velocità
                if is_reaction and entity_has_keyword(player, "sentinella", "sentinel"):
                    target_player.movement_spent_this_turn = 9999
                    if "Velocità 0 (Sentinella)" not in target_player.conditions:
                        target_player.conditions.append("Velocità 0 (Sentinella)")
                    log_msg += " 🛑 [SENTINELLA: Velocità ridotta a 0!]"

                # Danno bonus da Assorbire Elementi (+1d6 elementale sul primo attacco in mischia)
                p_conds_list = getattr(player, "conditions", [])
                ae_cond = next((c for c in list(p_conds_list) if str(c).lower().startswith("assorbire elementi")), None)
                if ae_cond and not is_ranged_att:
                    ae_roll = roll_dice("1d6", is_crit=is_crit)
                    dmg_val += ae_roll["total"]
                    p_conds_list.remove(ae_cond)
                    log_msg += f" 🔥 (+{ae_roll['total']} {ae_cond})"
                
                # Stili di Combattimento (Duellare / Lancio con Armi)
                w_low_fs = str(weapon_name).lower()
                if not data.get("is_spell") and not data.get("fighting_style_applied"):
                    if not is_ranged_att and not data.get("is_two_handed") and not data.get("is_offhand"):
                        if entity_has_keyword(player, "duellare", "dueling") and not any(k in w_low_fs for k in ("due mani", "two-handed", "spadone", "greatsword", "bipenne", "greataxe", "maglio", "maul", "alabarda", "halberd", "picca", "pike", "falcione", "glaive")):
                            dmg_val += 2
                            log_msg += " (+2 Stile Duellare)"
                    if bool(data.get("is_thrown") or (is_ranged_att and any(k in w_low_fs for k in ("giavellotto", "javelin", "pugnale", "dagger", "ascia", "handaxe", "lancia", "spear", "dardo", "dart", "tridente", "trident")))):
                        if entity_has_keyword(player, "lancio con armi", "thrown weapon fighting"):
                            dmg_val += 2
                            log_msg += " (+2 Stile Lancio)"

                # Bonus danno Ira Barbarica (RAW 5e: solo attacchi in mischia che usano Forza, scalato col livello classe Barbaro)
                if is_condition_active(getattr(player, "conditions", []), "Ira"):
                    barb_lvl = entity_get_class_level(player, "barbar", "barbarian") or 1
                    rage_bonus = 2 if barb_lvl < 9 else (3 if barb_lvl < 16 else 4)
                    w_lower = str(weapon_name).lower()
                    if not (data.get("is_ranged") or any(k in w_lower for k in ["arco", "bow", "balestra", "crossbow", "fionda", "sling"])):
                        dmg_val += rage_bonus
                        log_msg += f" (+{rage_bonus} Ira Barbarica)"

                # Regola D&D 5e: Attacco Furtivo del Ladro (Sneak Attack, multiclasse-aware)
                # Requisiti: classe Ladro, arma accurata/distanza, vantaggio OPPURE alleato entro 1 esagono senza svantaggio, max 1 volta per turno
                rogue_lvl = entity_get_class_level(player, "ladro", "rogue")
                is_rogue = rogue_lvl > 0 or entity_has_keyword(player, "attacco furtivo", "sneak attack")
                if is_rogue and rogue_lvl <= 0:
                    rogue_lvl = 1

                w_name_l = str(weapon_name).lower()
                finesse_kws = ["accurata", "finesse", "stocco", "rapier", "pugnale", "dagger", "spada corta", "shortsword", "scimitarra", "scimitar", "frusta", "whip"]
                ranged_kws = ["arco", "bow", "balestra", "crossbow", "dardo", "dart", "fionda", "sling", "distanza", "ranged"]
                w_props = [str(p).lower() for p in data.get("weapon_props", [])]
                # D&D 5e RAW (PHB p. 96): L'Attacco Furtivo richiede necessariamente un'arma accurata o a distanza (esclusi Colpi Senz'Armi o magie)
                is_finesse_or_ranged = (any(k in w_name_l for k in finesse_kws) or any(k in w_name_l for k in ranged_kws) or any(k in w_props for k in ["finesse", "accurata", "ranged", "a distanza"]) or bool(data.get("is_ranged"))) and not any(k in w_name_l for k in ["senz'armi", "unarmed"])

                if is_rogue and is_finesse_or_ranged and not getattr(player, "sneak_attack_used_this_turn", False):
                    has_adjacent_ally = False
                    if hasattr(target_player, "position") and target_player.position:
                        tq, tr = target_player.position[0], target_player.position[1]
                        attacker_party = bool(getattr(player, "is_party_member", False) or getattr(player, "conn", None))
                        target_party = bool(getattr(target_player, "is_party_member", False) or getattr(target_player, "conn", None))
                        for other in getattr(game_state, "players", []):
                            if other.name != player.name and other.name != target_player.name and getattr(other, "hp", 0) > 0:
                                if hasattr(other, "position") and other.position:
                                    oq, or_ = other.position[0], other.position[1]
                                    d_o = max(abs(tq - oq), abs(tq + tr - oq - or_), abs(tr - or_))
                                    if d_o <= 1:
                                        other_party = bool(getattr(other, "is_party_member", False) or getattr(other, "conn", None))
                                        is_ally = (other_party == attacker_party) if attacker_party != target_party else True
                                        o_conds = getattr(other, "conditions", [])
                                        incap = any(is_condition_active(o_conds, c) for c in ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto", "Incapacitato", "Incapacitated"])
                                        if is_ally and not incap:
                                            has_adjacent_ally = True
                                            break
                    
                    if has_adv or (has_adjacent_ally and not has_dis):
                        sneak_dice_count = max(1, math.ceil(rogue_lvl / 2))
                        sneak_formula = f"{sneak_dice_count}d6"
                        s_res = roll_dice(sneak_formula, is_crit=is_crit)
                        sneak_dmg = s_res["total"]
                        dmg_val += sneak_dmg
                        player.sneak_attack_used_this_turn = True
                        log_msg += f" 🗡️ (+{sneak_dmg} Attacco Furtivo [{sneak_formula}])"

                # Punizione Divina del Paladino (Divine Smite PHB p. 85)
                # Spende uno slot 1°-5°: +2d8 (+1d8/livello sopra il 1°, max 5d8), +1d8 vs Non Morti/Immondi (max 6d8). Raddoppiato su critico!
                smite_slot = data.get("smite_slot") or data.get("divine_smite_slot")
                if smite_slot and not is_ranged_att:
                    try:
                        s_lvl = int(smite_slot)
                        if 1 <= s_lvl <= 5:
                            p_sheet = getattr(player, "full_sheet", None) or {}
                            p_slots = p_sheet.get("spell_slots", {})
                            lvl_str = str(s_lvl)
                            if isinstance(p_slots.get(lvl_str), dict) and p_slots[lvl_str].get("current", 0) > 0:
                                p_slots[lvl_str]["current"] -= 1
                            elif isinstance(p_slots.get(lvl_str), list) and len(p_slots[lvl_str]) >= 2 and p_slots[lvl_str][0] > 0:
                                p_slots[lvl_str][0] -= 1

                            base_smite_dice = min(5, 1 + s_lvl)
                            t_fs = getattr(target_player, "full_sheet", None) or {}
                            t_type_str = (str(t_fs.get("type", "")) + " " + str(target_player.name) + " " + " ".join(getattr(target_player, "conditions", []))).lower()
                            undead_fiend_kws = ("non morto", "non-morto", "undead", "immondo", "fiend", "zombie", "scheletro", "skeleton", "demone", "demon", "diavolo", "devil", "ghoul", "ghast", "mummia", "mummy", "spettro", "specter", "fantasma", "ghost", "wraith", "vampiro", "vampire", "lich")
                            if any(k in t_type_str for k in undead_fiend_kws):
                                base_smite_dice = min(6, base_smite_dice + 1)

                            smite_formula = f"{base_smite_dice}d8"
                            smite_res = roll_dice(smite_formula, is_crit=is_crit)
                            smite_dmg = smite_res["total"]
                            dmg_val += smite_dmg
                            log_msg += f" ⚡ (+{smite_dmg} Punizione Divina [{smite_formula} radiante])"
                    except Exception:
                        pass

                # Critico Brutale (Barbaro PHB p. 49) & Attacchi Selvaggi (Mezzorco PHB p. 41)
                if is_crit and not is_ranged_att:
                    p_sheet = getattr(player, "full_sheet", None) or {}
                    p_race = str(p_sheet.get("race", getattr(player, "race", ""))).lower()
                    p_feats = str(p_sheet.get("features", getattr(player, "features", ""))).lower()
                    extra_crit_dice = 0
                    if "mezzorco" in p_race or "half-orc" in p_race or "attacchi selvaggi" in p_feats:
                        extra_crit_dice += 1

                    barb_lvl = entity_get_class_level(player, "barbar", "barbarian")

                    if barb_lvl >= 17:
                        extra_crit_dice += 3
                    elif barb_lvl >= 13:
                        extra_crit_dice += 2
                    elif barb_lvl >= 9:
                        extra_crit_dice += 1

                    if extra_crit_dice > 0:
                        import re
                        m_die = re.search(r'd(\d+)', str(damage_formula))
                        sides = m_die.group(1) if m_die else "8"
                        crit_bonus_formula = f"{extra_crit_dice}d{sides}"
                        bc_res = roll_dice(crit_bonus_formula, is_crit=False)
                        bc_dmg = bc_res["total"]
                        dmg_val += bc_dmg
                        log_msg += f" 💥 (+{bc_dmg} Critico Brutale/Attacchi Selvaggi [{crit_bonus_formula}])"

                # Colpo Stordente del Monaco (Stunning Strike PHB p. 79)
                if data.get("use_stunning_strike") and not is_ranged_att:
                    from common.dnd5e_tables import entity_get_total_level, entity_spend_resource
                    p_sheet = getattr(player, "full_sheet", None) or {}
                    spent_ki = False
                    if "ki_current" in p_sheet and p_sheet["ki_current"] > 0:
                        p_sheet["ki_current"] -= 1
                        spent_ki = True
                    else:
                        spent_ki, _, _ = entity_spend_resource(player, ("punti ki", "ki points", "ki"), 1)
                    char_lvl = entity_get_total_level(player)
                    pb = ((char_lvl - 1) // 4) + 2
                    wis_val = 10
                    if "attributes" in p_sheet and isinstance(p_sheet["attributes"], dict):
                        wis_val = p_sheet["attributes"].get("SAG", p_sheet["attributes"].get("WIS", 10))
                    wis_mod = (int(wis_val) - 10) // 2
                    ki_dc = 8 + pb + wis_mod

                    t_con_mod = get_effective_save_bonus_from_dict(target_player, "COS")
                    save_roll = random.randint(1, 20) + t_con_mod
                    if save_roll < ki_dc:
                        if not hasattr(target_player, "conditions") or not isinstance(target_player.conditions, list):
                            target_player.conditions = []
                        if "Stordito" not in target_player.conditions:
                            target_player.conditions.append("Stordito")
                        if not hasattr(target_player, "condition_durations") or not isinstance(target_player.condition_durations, dict):
                            target_player.condition_durations = {}
                        target_player.condition_durations["Stordito"] = 2
                        log_msg += f" 🥋 [Colpo Stordente! {target_name} fallisce TS COS ({save_roll} vs CD {ki_dc}) ed è STORDITO!]"
                    else:
                        log_msg += f" 🥋 [Colpo Stordente: {target_name} supera TS COS ({save_roll} vs CD {ki_dc})]"
                    
                auto_apply = True
                if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
                    auto_apply = game_state.automation_settings.get("auto_apply_damage", True)

                if auto_apply:
                    from server.dm_monster_engine import get_swarm_damage_divisor
                    _sw_div = get_swarm_damage_divisor(player)
                    if _sw_div > 1 and dmg_val > 1:
                        dmg_val = max(1, dmg_val // _sw_div)
                        log_msg += " [🐝 Sciame <= 50% PF: Danni dimezzati]"
                    old_target_hp_before_hit = target_player.hp
                    is_non_lethal = bool(data.get("non_lethal") or getattr(player, "non_lethal_mode", False)) and not is_ranged_att
                    final_dmg, note, temp_absorbed, dmg_to_hp = apply_damage(
                        target_player, dmg_val, damage_type, game_state,
                        is_crit=is_crit, is_non_lethal=is_non_lethal, ignore_resistance=is_elem_adept,
                        is_magical=is_mag_att, is_silvered=is_silv_att, is_adamantine=is_adam_att,
                        is_spell=bool(data.get("is_spell", False)), attacker=player
                    )
                    if not hasattr(target_player, "_hit_this_turn_by") or not isinstance(target_player._hit_this_turn_by, set):
                        target_player._hit_this_turn_by = set()
                    target_player._hit_this_turn_by.add(player.name)
                    if not is_ranged_att and not data.get("is_spell") and (is_crit or (target_player.hp == 0 and old_target_hp_before_hit > 0)):
                        if entity_has_keyword(player, "maestro d'armi pesanti", "great weapon master"):
                            player.gwm_ba_unlocked = True
                            log_msg += " [⚔️ GWM: Attacco Bonus sbloccato!]"
                    if target_player.hp == 0 and old_target_hp_before_hit > 0:
                        from common.feats_and_classes import apply_dark_ones_blessing
                        _dob_gain = apply_dark_ones_blessing(player, target_player, game_state)
                        if _dob_gain > 0:
                            log_msg += f" [😈 Benedizione dell'Oscuro: Temp HP -> {_dob_gain}]"
                    log_msg += f" Danno: {final_dmg} ({damage_type}){note}."
                    if temp_absorbed > 0:
                        log_msg += f" [{temp_absorbed} assorbiti da Temp HP]."
                    log_msg += f" HP {target_name}: {target_player.hp}/{target_player.max_hp}"
                    if getattr(target_player, "temp_hp", 0) > 0:
                        log_msg += f" (+{target_player.temp_hp} Temp)"

                    target_player._last_hit_for_reaction = {
                        "attacker": player.name,
                        "hit_roll": hit_roll,
                        "base_ac": target_ac,
                        "is_crit": is_crit,
                        "is_ranged": is_ranged_att,
                        "final_dmg": final_dmg,
                        "dmg_to_hp": dmg_to_hp,
                        "temp_absorbed": temp_absorbed,
                        "old_hp": old_target_hp_before_hit,
                    }

                    # Schivata Prodigiosa (Uncanny Dodge - Ladro Lv 5+, PHB p. 96): Prompt anche su colpo che porta a 0 HP se il dimezzamento mantiene >= 1 PF
                    t_rogue_lvl = entity_get_class_level(target_player, "ladro", "rogue")
                    auto_react_ud = True
                    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
                        auto_react_ud = game_state.automation_settings.get("auto_prompt_reactions", True)
                    can_survive_ud = target_player.hp > 0 or (old_target_hp_before_hit > (dmg_to_hp - (dmg_to_hp // 2)))
                    if (t_rogue_lvl >= 5 or entity_has_keyword(target_player, "schivata prodigiosa", "uncanny dodge")) and old_target_hp_before_hit > 0 and can_survive_ud and final_dmg > 1:
                        att_visible = not is_condition_active(p_cond, "Invisibile") and not is_condition_active(t_cond, "Accecato")
                        if att_visible and not getattr(target_player, "has_reacted_this_turn", False) and not getattr(target_player, "surprised", False):
                            if auto_react_ud and getattr(target_player, "conn", None):
                                send_message(target_player.conn, make_prompt_reaction(
                                    "UNCANNY_DODGE", player.name,
                                    {"weapon_name": weapon_name, "damage_taken": final_dmg, "dmg_to_hp": dmg_to_hp}
                                ))

                    # Prompt live per Scudo (Shield) e Deflettere Missili (Deflect Missiles)
                    from server.rules.reaction_magic import maybe_prompt_defense_reactions
                    maybe_prompt_defense_reactions(target_player, player, target_player._last_hit_for_reaction, game_state)

                    # Morale Mostri DMG p. 273
                    if game_state and (target_player.hp == 0 or target_player.hp <= (max(1, target_player.max_hp) / 2.0)):
                        from server.dm_optional_tools import evaluate_morale_checks
                        _t_leader = any(k in str(target_player.name).lower() for k in ("boss", "capo", "leader", "commander", "re", "lord"))
                        evaluate_morale_checks(game_state, trigger_reason=("leader_down" if (_t_leader and target_player.hp == 0) else "casualties"))

                    # Spazzata / Cleaving through Creatures (DMG p. 272 - Opzionale DM)
                    opt_cleave = False
                    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
                        opt_cleave = bool(game_state.automation_settings.get("opt_cleaving", False))
                    if opt_cleave and not is_ranged_att and target_player.hp == 0 and old_target_hp_before_hit >= target_player.max_hp:
                        excess_cleave = max(0, final_dmg - temp_absorbed - old_target_hp_before_hit)
                        if excess_cleave > 0 and getattr(target_player, "position", None):
                            att_p_c = bool(getattr(player, "is_party_member", False) or getattr(player, "conn", None))
                            g_type = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
                            for adj_e in getattr(game_state, "players", []):
                                if adj_e.name in (player.name, target_player.name) or getattr(adj_e, "hp", 0) <= 0:
                                    continue
                                e_p_c = bool(getattr(adj_e, "is_party_member", False) or getattr(adj_e, "conn", None))
                                if e_p_c == att_p_c or not getattr(adj_e, "position", None):
                                    continue
                                d_att_e = grid_distance_3d(Hex(player.position[0], player.position[1]), Hex(adj_e.position[0], adj_e.position[1]), getattr(player, "elevation", 0), getattr(adj_e, "elevation", 0), grid_type=g_type) if getattr(player, "position", None) else 999
                                d_t_e = grid_distance_3d(Hex(target_player.position[0], target_player.position[1]), Hex(adj_e.position[0], adj_e.position[1]), getattr(target_player, "elevation", 0), getattr(adj_e, "elevation", 0), grid_type=g_type)
                                adj_ac = getattr(adj_e, "ac", 10)
                                if d_t_e <= 1.0 and d_att_e <= 2.0 and hit_roll >= adj_ac:
                                    cl_dmg, _, _, _ = apply_damage(adj_e, excess_cleave, damage_type, game_state)
                                    log_msg += f" ⚔️ [SPAZZATA DMG: +{cl_dmg} danni residui traboccano su {adj_e.name} (PV {adj_e.hp}/{adj_e.max_hp})!]"
                                    broadcast(game_state, make_player_stats_update(adj_e.name, adj_e.hp, adj_e.max_hp, adj_e.initiative, adj_e.conditions, getattr(adj_e, "temp_hp", 0)))
                                    break
                    
                    broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions, getattr(target_player, "temp_hp", 0)))
                    game_state._trigger_gui_update()
                else:
                    import uuid
                    pending_id = f"dmg_{uuid.uuid4().hex[:8]}"
                    pending_info = {
                        "id": pending_id,
                        "attacker": player.name,
                        "target": target_name,
                        "raw_damage": dmg_val,
                        "damage_type": damage_type,
                        "is_crit": is_crit,
                        "weapon_name": weapon_name
                    }
                    if not hasattr(game_state, "pending_damages"):
                        game_state.pending_damages = {}
                    game_state.pending_damages[pending_id] = pending_info
                    
                    log_msg += f" 🎯 Danno Calcolato: {dmg_val} ({damage_type}). [In attesa di conferma DM]"
                    if hasattr(game_state, "gui_queue") and game_state.gui_queue:
                        game_state.gui_queue.put({"type": "PENDING_DAMAGE_PROMPT", "payload": pending_info})
                    game_state._trigger_gui_update()
        else:
            if is_fail:
                log_msg += " 💀 MANCATO! (FALLIMENTO CRITICO - 1 Naturale!)"
            else:
                log_msg += " MANCATO!"

            # DMG p. 272 Opzionale: Colpire la Copertura (Hitting Cover)
            dm_s_cov = getattr(game_state, "automation_settings", {}) or {}
            if (
                dm_s_cov.get("opt_hitting_cover", False)
                and not blocked_by_wall
                and cover_bonus > 0
                and hit_roll >= (target_ac - cover_bonus)
                and hasattr(player, "position") and player.position
                and hasattr(target_player, "position") and target_player.position
            ):
                p_hx = Hex(player.position[0], player.position[1])
                t_hx = Hex(target_player.position[0], target_player.position[1])
                c_line = hex_linedraw(p_hx, t_hx)[1:-1]
                for step in c_line:
                    cov_creatures = [
                        c for c in getattr(game_state, "players", [])
                        if c.name not in (player.name, target_player.name)
                        and getattr(c, "position", None) == [step.q, step.r]
                        and getattr(c, "hp", 1) > 0
                        and getattr(c, "layer", "token") != "gm"
                    ]
                    if cov_creatures:
                        cov_c = cov_creatures[0]
                        cov_ac = getattr(cov_c, "ac", 10) or 10
                        if hit_roll >= cov_ac and damage_formula:
                            cd_res = roll_dice(damage_formula, is_crit=False)["total"]
                            cd_fin, _, _, _ = apply_damage(
                                cov_c, cd_res, damage_type, game_state,
                                is_magical=is_mag_att, is_silvered=is_silv_att, is_adamantine=is_adam_att
                            )
                            log_msg += f" 💥 [COLPIRE LA COPERTURA DMG: l'attacco colpisce {cov_c.name} (CA {cov_ac}) per {cd_fin} danni!]"
                            broadcast(game_state, make_player_stats_update(cov_c.name, cov_c.hp, cov_c.max_hp, cov_c.initiative, getattr(cov_c, "conditions", []), getattr(cov_c, "temp_hp", 0)))
                        break
            
        game_state.log_dm_message(f"[COMBAT] {log_msg}")
        broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
        
    except Exception as e:
        send_message(player.conn, make_error_reply(f"Errore nell'attacco: {str(e)}"))

def _process_save_result(target_name, stat, roll_total, is_crit, is_fail, dc, damage_formula, half_on_success, source_name, game_state, damage_type="Fuoco", cover="none", spell_school=""):
    if hasattr(target_name, "name"):
        target_player = target_name
        target_name = target_player.name
    else:
        target_player = game_state.find_player(target_name)
    if not target_player: return
    
    try: roll_total = int(roll_total)
    except (ValueError, TypeError): roll_total = 0
    try: dc = int(dc)
    except (ValueError, TypeError): dc = 10

    benedizione_bonus = 0
    if has_effect_or_condition(target_player, "Benedizione", "Bless"):
        benedizione_bonus = random.randint(1, 4)
        roll_total += benedizione_bonus

    anatema_penalty = 0
    if has_effect_or_condition(target_player, "Anatema", "Bane"):
        anatema_penalty = random.randint(1, 4)
        roll_total -= anatema_penalty
        
    extra_adv_note = ""
    _save_hero_b = int(getattr(target_player, "pending_hero_bonus", 0) or 0)
    if _save_hero_b > 0:
        roll_total += _save_hero_b
        target_player.pending_hero_bonus = 0
        extra_adv_note += f" (+{_save_hero_b} Punto Eroe)"
    from common.feats_and_classes import get_armor_nonproficiency_penalties
    if str(stat or "").upper() in ("FOR", "STR", "DES", "DEX"):
        if get_armor_nonproficiency_penalties(target_player).get("disadvantage_str_dex"):
            extra_adv_note += " (Svantaggio: Armatura senza competenza)"
    aura_bonus, aura_paladin = get_paladin_aura_save_bonus(target_player, game_state)
    if aura_bonus > 0:
        roll_total += aura_bonus
        extra_adv_note += f" (+{aura_bonus} Aura di Protezione di {aura_paladin})"
    if stat in ("DES", "DEX"):
        from common.dnd5e_tables import entity_get_class_level, entity_has_keyword
        barb_lvl = entity_get_class_level(target_player, "barbar", "barbarian")
        if (barb_lvl >= 2 or entity_has_keyword(target_player, "percezione del pericolo", "danger sense")):
            t_c_low = [str(c).lower() for c in getattr(target_player, "conditions", [])]
            if not any(ic in t_c_low for ic in ("accecato", "blinded", "assordato", "deafened", "incapacitato", "incapacitated")):
                extra_adv_note += " (Vantaggio da Percezione del Pericolo)"
        if is_condition_active(getattr(target_player, "conditions", []), "Schivata"):
            extra_adv_note += " (Vantaggio da Schivata)"
        if has_effect_or_condition(target_player, "Velocità", "Haste"):
            extra_adv_note += " (Vantaggio da Velocità)"
        if has_effect_or_condition(target_player, "Lentezza", "Slow"):
            roll_total -= 2
            extra_adv_note += " (-2 Lentezza)"
        cover_val = str(cover).lower()
        if cover_val in ("half", "mezza"):
            roll_total += 2
            extra_adv_note += " (+2 TS Mezza Copertura)"
        elif cover_val in ("three_quarters", "3/4", "tre_quarti"):
            roll_total += 5
            extra_adv_note += " (+5 TS Tre Quarti di Copertura)"

    # MM Magic Resistance (Resistenza alla Magia): nota visibile nei TS
    from common.dnd5e_tables import entity_has_keyword as _ehk_mr
    if _ehk_mr(target_player, "resistenza alla magia", "magic resistance"):
        extra_adv_note += " (Resistenza alla Magia: Vantaggio vs incantesimi/effetti magici)"
    if stat in ("DES", "DEX") and is_condition_active(getattr(target_player, "conditions", []), "Trattenuto"):
        extra_adv_note += " (Svantaggio TS DES: Trattenuto)"
    if getattr(target_player, "exhaustion_level", 0) >= 3:
        extra_adv_note += " (Svantaggio TS: Indebolimento Lv3+)"


    # Regola 5e: Creature Incoscienti, Paralizzate o Stordite falliscono automaticamente i TS su Forza e Destrezza
    auto_fail_cond = None
    if stat in ("FOR", "DES", "STR", "DEX"):
        for c in ["Incosciente", "Paralizzato", "Stordito", "Pietrificato"]:
            if is_condition_active(getattr(target_player, "conditions", []), c):
                auto_fail_cond = c
                break

    if auto_fail_cond:
        success = False
        extra_adv_note += f" (Fallimento automatico per condizione: {auto_fail_cond})"
    else:
        # D&D 5e RAW (PHB p. 179): I Tiri Salvezza (tranne TS Morte) NON hanno successo o fallimento automatico su 20 o 1 naturale.
        # Il totale ottenuto deve raggiungere o superare la CD richiesta.
        success = (roll_total >= dc)

    # Paladino Aura di Coraggio (Lv 10+): immune a Spaventato
    _src_low = str(source_name or "").lower()
    if any(k in _src_low for k in ("spavent", "fright", "paura", "fear", "terrore")):
        from server.rules.class_abilities import is_immune_to_frightened_by_aura
        _imm_f, _f_src = is_immune_to_frightened_by_aura(target_player, game_state)
        if _imm_f:
            success = True
            extra_adv_note += f" [🛡️ Immune Spaventato: Aura di Coraggio di {_f_src}]"

    # Talento Sterminatore di Maghi (Mage Slayer, PHB p. 168): Vantaggio ai TS contro incantesimi entro 5 ft
    _caster_obj = game_state.find_player(source_name) if (game_state and source_name) else None
    if _caster_obj and _caster_obj.name != target_player.name and entity_has_keyword(target_player, "sterminatore di maghi", "mage slayer"):
        if getattr(_caster_obj, "position", None) and getattr(target_player, "position", None):
            _gt_ms = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
            if grid_distance_3d(Hex(_caster_obj.position[0], _caster_obj.position[1]), Hex(target_player.position[0], target_player.position[1]), getattr(_caster_obj, "elevation", 0), getattr(target_player, "elevation", 0), grid_type=_gt_ms) <= 1.5:
                extra_adv_note += " (Vantaggio: Sterminatore di Maghi)"

    # Mago Invocazione Lv 2+ Plasmare Incantesimi (Sculpt Spells, PHB p. 117): alleati superano automaticamente TS Evocazione e subiscono 0 danni
    sculpted_evocation = False
    if _caster_obj and _caster_obj.name != target_player.name:
        _same_side = bool(getattr(_caster_obj, "is_party_member", False) or getattr(_caster_obj, "conn", None)) == bool(getattr(target_player, "is_party_member", False) or getattr(target_player, "conn", None))
        _c_wiz = entity_get_class_level(_caster_obj, "mago", "wizard")
        _c_sub = str((getattr(_caster_obj, "full_sheet", {}) or {}).get("subclass", "") or "").lower()
        _is_evoc_school = any(k in f"{spell_school} {_src_low}".lower() for k in ("evoc", "invoc", "palla di fuoco", "fireball", "mani brucianti", "burning hands", "fulmine", "lightning", "cono di freddo", "cone of cold", "onda tonante", "thunderwave", "frantumare", "shatter"))
        if _same_side and _is_evoc_school and ((_c_wiz >= 2 and ("evoc" in _c_sub or "invoc" in _c_sub)) or entity_has_keyword(_caster_obj, "plasmare incantesimi", "sculpt spells")):
            sculpted_evocation = True
            success = True
            extra_adv_note += f" [✨ Plasmare Incantesimi ({_caster_obj.name}): Successo Automatico]"
    
    # D&D 5e: Resistenze Leggendarie (es. 3/giorno)
    # Se opt_legendary_res_prompt è attivo, invia prompt al DM invece di spendere automaticamente.
    used_legendary_resistance = False
    if not success and getattr(target_player, "legendary_resistances_current", 0) > 0:
        opt_lr_prompt = bool((getattr(game_state, "automation_settings", {}) or {}).get("opt_legendary_res_prompt", False))
        if opt_lr_prompt and game_state:
            import uuid as _uuid_lr
            lr_id = f"lr_{_uuid_lr.uuid4().hex[:8]}"
            if not hasattr(game_state, "pending_legendary_resistances") or not isinstance(game_state.pending_legendary_resistances, dict):
                game_state.pending_legendary_resistances = {}
            lr_info = {
                "id": lr_id,
                "target": target_name,
                "stat": stat,
                "dc": dc,
                "roll_total": roll_total,
                "source": source_name,
                "remaining": target_player.legendary_resistances_current,
            }
            game_state.pending_legendary_resistances[lr_id] = lr_info
            if hasattr(game_state, "gui_queue") and game_state.gui_queue:
                game_state.gui_queue.put({"type": "PENDING_LEGENDARY_RES_PROMPT", "payload": lr_info})
            extra_adv_note += f" [👑 Resistenza Leggendaria disponibile ({target_player.legendary_resistances_current}): in attesa di decisione DM]"
        else:
            target_player.legendary_resistances_current -= 1
            success = True
            used_legendary_resistance = True
            if game_state:
                game_state._trigger_gui_update()
    
    log_msg = f"{target_name} effettua un TS su {stat} contro CD {dc} di {source_name}. Risultato: {roll_total}{extra_adv_note}"
    if benedizione_bonus > 0:
        log_msg += f" (+{benedizione_bonus} Benedizione)"
    if anatema_penalty > 0:
        log_msg += f" (-{anatema_penalty} Anatema)"
    log_msg += "."
    if used_legendary_resistance:
        if is_fail:
            log_msg += " (1 Naturale annullato!)"
        log_msg += f" 👑 RESISTENZA LEGGENDARIA USATA! Il fallimento si trasforma in SUCCESSO! (Rimaste: {target_player.legendary_resistances_current}/{target_player.legendary_resistances_max})"
    elif success:
        crit_str = " 🌟 [20 Naturale!]" if is_crit else ""
        log_msg += f"{crit_str} SUPERATO!"
        if str(source_name).startswith("Save-Ends:"):
            eff_name = str(source_name).replace("Save-Ends:", "").strip()
            removed = target_player.remove_effect(eff_name)
            log_msg += f" ✨ {target_name} supera il TS e si libera dall'effetto '{eff_name}'!"
            broadcast(game_state, make_player_stats_update(
                target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, 
                target_player.conditions, getattr(target_player, "temp_hp", 0), 
                active_effects=getattr(target_player, "active_effects", [])
            ))
            game_state._trigger_gui_update()
    else:
        fumble_str = " 💀 [1 Naturale!]" if is_fail else ""
        log_msg += f"{fumble_str} FALLITO!"
        if str(source_name).startswith("Save-Ends:"):
            eff_name = str(source_name).replace("Save-Ends:", "").strip()
            log_msg += f" ❌ L'effetto '{eff_name}' su {target_name} persiste!"
        if str(source_name).startswith("Sistema (Concentrazione)"):
            drop_concentration(target_player, game_state, notify=True)
            broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions, getattr(target_player, "temp_hp", 0)))
            game_state._trigger_gui_update()
        
    if damage_formula:
        try:
            clean_dmg = str(damage_formula).strip()
            if clean_dmg.isdigit():
                dmg_val = int(clean_dmg)
            else:
                dmg_res = roll_dice(clean_dmg)
                dmg_val = dmg_res["total"]
            
            # Elusione (Evasion) D&D 5e: Ladro/Monaco su TS Destrezza (non utilizzabile se Incapacitato/Paralizzato/Stordito)
            has_evasion = False
            incap_evasion = ["incapacitato", "incapacitated", "incosciente", "unconscious", "paralizzato", "paralyzed", "stordito", "stunned", "pietrificato", "petrified", "morto", "dead"]
            t_conds_low = [str(c).lower() for c in getattr(target_player, "conditions", [])]
            is_incap = any(c in t_conds_low for c in incap_evasion)
            if stat in ("DES", "DEX") and target_player and not is_incap:
                tokens = [str(c) for c in getattr(target_player, "conditions", [])]
                feat_obj = getattr(target_player, "features", [])
                if isinstance(feat_obj, list):
                    tokens.extend([str(f) for f in feat_obj])
                elif isinstance(feat_obj, str) and feat_obj:
                    tokens.append(feat_obj)
                sheet = getattr(target_player, "full_sheet", None)
                if isinstance(sheet, dict):
                    sf = sheet.get("features", [])
                    if isinstance(sf, list):
                        tokens.extend([str(f) for f in sf])
                    elif isinstance(sf, str) and sf:
                        tokens.append(sf)
                p_text = " ".join(tokens).lower()
                if "elusione" in p_text or "evasion" in p_text:
                    has_evasion = True

            if success:
                if sculpted_evocation:
                    dmg_val = 0
                    log_msg += " (✨ Plasmare Incantesimi PHB: 0 danni subiti dall'alleato!)"
                elif has_evasion:
                    dmg_val = 0
                    log_msg += " (Elusione 5e: 0 danni con TS superato!)"
                elif stat in ("DES", "DEX") and half_on_success and not is_incap and not getattr(target_player, "has_reacted_this_turn", False) and entity_has_keyword(target_player, "maestro di scudi", "shield master"):
                    dmg_val = 0
                    target_player.has_reacted_this_turn = True
                    log_msg += " (🛡️ Maestro di Scudi PHB [Reazione]: 0 danni con TS superato!)"
                elif half_on_success:
                    dmg_val = dmg_val // 2
                else:
                    dmg_val = 0
            else:
                if has_evasion and half_on_success:
                    dmg_val = dmg_val // 2
                    log_msg += " (Elusione 5e: subisce solo metà danni nonostante il TS fallito!)"
                    
            if dmg_val > 0:
                auto_apply_aoe = True
                if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
                    auto_apply_aoe = game_state.automation_settings.get("auto_apply_aoe_damage", game_state.automation_settings.get("auto_apply_damage", True))
                
                if auto_apply_aoe:
                    final_dmg, note, temp_absorbed, dmg_to_hp = apply_damage(target_player, dmg_val, damage_type, game_state)
                    log_msg += f" Subisce {final_dmg} danni ({damage_type}){note}!"
                    if temp_absorbed > 0:
                        log_msg += f" [{temp_absorbed} assorbiti da Temp HP]."
                    log_msg += f" HP: {target_player.hp}/{target_player.max_hp}"
                    if getattr(target_player, "temp_hp", 0) > 0:
                        log_msg += f" (+{target_player.temp_hp} Temp)"
                    broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions, getattr(target_player, "temp_hp", 0)))
                    game_state._trigger_gui_update()
                else:
                    import uuid
                    pending_id = f"dmg_{uuid.uuid4().hex[:8]}"
                    pending_info = {
                        "id": pending_id,
                        "attacker": source_name,
                        "target": target_name,
                        "raw_damage": dmg_val,
                        "damage_type": damage_type,
                        "is_crit": False,
                        "weapon_name": f"TS {stat} ({source_name})"
                    }
                    if not hasattr(game_state, "pending_damages"):
                        game_state.pending_damages = {}
                    game_state.pending_damages[pending_id] = pending_info
                    log_msg += f" 🎯 Danno Calcolato (TS): {dmg_val} ({damage_type}). [In attesa di conferma DM]"
                    if hasattr(game_state, "gui_queue") and game_state.gui_queue:
                        game_state.gui_queue.put({"type": "PENDING_DAMAGE_PROMPT", "payload": pending_info})
                    game_state._trigger_gui_update()
            else:
                log_msg += " Non subisce danni."
        except Exception as e:
            log_msg += f" (Errore formula danni: {e})"
            
    game_state.log_dm_message(f"[TS] {log_msg}")
    broadcast(game_state, make_chat_broadcast("Sistema", log_msg))

def handle_force_save_request(data, player, game_state):
    is_dm = (player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if not is_dm:
        return
    targets = data.get("targets", [])
    stat = data.get("stat")
    dc = data.get("dc")
    damage_formula = data.get("damage_formula")
    half_on_success = data.get("half_on_success", True)
    damage_type = data.get("damage_type", "Fuoco")
    
    # D&D 5e RAW (PHB p. 196): I danni degli incantesimi/effetti ad area si tirano una sola volta per tutti i bersagli!
    resolved_damage = None
    if damage_formula:
        clean_f = str(damage_formula).strip()
        if clean_f.isdigit():
            resolved_damage = clean_f
        else:
            try:
                from common.dice import roll_dice
                resolved_damage = str(roll_dice(clean_f)["total"])
            except Exception:
                resolved_damage = damage_formula

    for t_name in targets:
        target_player = game_state.find_player(t_name)
        if not target_player: continue
        
        target_formula = resolved_damage if resolved_damage else damage_formula
        if getattr(target_player, "conn", None):
            send_message(target_player.conn, make_prompt_save(stat, dc, target_formula, half_on_success, player.name if player else "DM", damage_type))
        else:
            try:
                s_map = {"STR": "FOR", "DEX": "DES", "CON": "COS", "INT": "INT", "WIS": "SAG", "CHA": "CAR"}
                c_stat = s_map.get(str(stat).upper(), str(stat).upper())
                mod = get_effective_save_bonus_from_dict(target_player, c_stat)
                
                # Vantaggio ai TS su DES per Schivata, o Resistenza alla Magia (MM) su incantesimi/effetti magici
                from common.dnd5e_tables import entity_has_keyword as _ehk_fs
                has_magic_res = bool(data.get("is_magical", False) or data.get("is_spell", False)) and _ehk_fs(target_player, "resistenza alla magia", "magic resistance")
                if (c_stat == "DES" and is_condition_active(getattr(target_player, "conditions", []), "Schivata")) or has_magic_res:
                    r1 = random.randint(1, 20)
                    r2 = random.randint(1, 20)
                    base_roll = max(r1, r2)
                else:
                    base_roll = random.randint(1, 20)
                    
                roll_tot = base_roll + mod
                is_crit = (base_roll == 20)
                is_fail = (base_roll == 1)
                
                _process_save_result(target_player.name, stat, roll_tot, is_crit, is_fail, dc, target_formula, half_on_success, player.name if player else "DM", game_state, damage_type)
            except Exception as e:
                print("Errore nel roll NPC per TS:", e)

def handle_save_result_request(data, player, game_state):
    stat = data.get("stat")
    try: roll_total = int(data.get("roll_total", 0))
    except (ValueError, TypeError): roll_total = 0
    is_crit = bool(data.get("is_crit", False))
    is_fail = bool(data.get("is_fail", False))
    try: dc = int(data.get("dc", 10))
    except (ValueError, TypeError): dc = 10
    damage_formula = data.get("damage_formula")
    half_on_success = data.get("half_on_success")
    source_name = data.get("source_name")
    damage_type = data.get("damage_type", "Fuoco")
    cover = data.get("cover", "none")
    
    _process_save_result(player.name, stat, roll_total, is_crit, is_fail, dc, damage_formula, half_on_success, source_name, game_state, damage_type, cover=cover)


def _validate_combat_tactical_action(player, game_state, action_label: str) -> bool:
    """Verifica che il combattimento sia attivo, il personaggio non sia incapacitato e (se strict_turn_lock) sia il suo turno."""
    if not getattr(game_state, "combat_active", False):
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Puoi usare l'azione di {action_label} solo durante il combattimento!"))
        return False

    p_cond = getattr(player, "conditions", []) if player else []
    blocking = ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto", "Incapacitato", "Incapacitated"]
    if any(is_condition_active(p_cond, c) for c in blocking) or getattr(player, "hp", 1) <= 0:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Non puoi compiere l'azione di {action_label} mentre sei Incosciente, Paralizzato, Stordito o a 0 HP!"))
        return False

    strict_lock = game_state.automation_settings.get("strict_turn_lock", False) if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict) else getattr(game_state, "strict_turn_lock", False)
    if strict_lock:
        curr_turn = game_state.get_current_turn_player()
        if curr_turn and player and curr_turn.name != player.name:
            if getattr(player, "conn", None):
                send_message(player.conn, make_error_reply(f"Non è il tuo turno in combattimento! È il turno di {curr_turn.name}."))
            return False

    return True

def handle_dash_request(data, player, game_state):
    if not _validate_combat_tactical_action(player, game_state, "Scatto"):
        return
    if "Scatto" not in getattr(player, "conditions", []):
        if not hasattr(player, "conditions") or player.conditions is None:
            player.conditions = []
        player.conditions.append("Scatto")
        player.has_acted_this_turn = True
        broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
        broadcast(game_state, make_chat_broadcast("Sistema", f"🏃 {player.name} compie l'Azione di Scatto! Velocità raddoppiata per questo turno."))
        game_state.log_dm_message(f"[COMBAT] {player.name} ha usato Scatto.")
        game_state._trigger_gui_update()

def handle_disengage_request(data, player, game_state):
    if not _validate_combat_tactical_action(player, game_state, "Disimpegno"):
        return
    if "Disimpegno" not in getattr(player, "conditions", []):
        if not hasattr(player, "conditions") or player.conditions is None:
            player.conditions = []
        player.conditions.append("Disimpegno")
        player.has_acted_this_turn = True
        broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
        broadcast(game_state, make_chat_broadcast("Sistema", f"💨 {player.name} compie l'Azione di Disimpegno! I suoi movimenti non provocheranno attacchi d'opportunità per questo turno."))
        game_state.log_dm_message(f"[COMBAT] {player.name} ha usato Disimpegno.")
        game_state._trigger_gui_update()

def handle_dodge_request(data, player, game_state):
    if not _validate_combat_tactical_action(player, game_state, "Schivata"):
        return
    p_cond_d = getattr(player, "conditions", [])
    if (
        (getattr(player, "speed", 30) or 0) <= 0
        or getattr(player, "exhaustion_level", 0) >= 5
        or is_condition_active(p_cond_d, "Afferrato")
        or is_condition_active(p_cond_d, "Trattenuto")
    ):
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Non puoi compiere Schivata quando la tua velocità è 0 (PHB p. 192)!"))
        return
    if "Schivata" not in getattr(player, "conditions", []):
        if not hasattr(player, "conditions") or player.conditions is None:
            player.conditions = []
        player.conditions.append("Schivata")
        player.has_acted_this_turn = True
        broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
        broadcast(game_state, make_chat_broadcast("Sistema", f"🛡️ {player.name} compie l'Azione di Schivata! Gli attacchi contro di lui avranno svantaggio e ha vantaggio ai TS su Destrezza fino all'inizio del suo prossimo turno."))
        game_state.log_dm_message(f"[COMBAT] {player.name} ha usato Schivata.")
        game_state._trigger_gui_update()

def handle_help_request(data, player, game_state):
    if not _validate_combat_tactical_action(player, game_state, "Aiuto"):
        return
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    target_name = data.get("target_name")
    if not target_name: return
    target_player = game_state.find_player(target_name)
    if not target_player: return

    help_type = str(data.get("help_type", "")).lower()
    att_party = bool(getattr(player, "is_party_member", False) or getattr(player, "conn", None))
    tgt_party = bool(getattr(target_player, "is_party_member", False) or getattr(target_player, "conn", None))
    is_ally_help = (help_type == "skill") or (att_party and tgt_party and target_player.name != player.name and help_type != "attack")

    if not is_ally_help and getattr(player, "position", None) and getattr(target_player, "position", None):
        cur_map = getattr(game_state, "current_map", {}) or {}
        grid_type = cur_map.get("grid_type", "hex")
        from common.hex_utils import Hex, grid_distance
        dist_h = int(grid_distance(Hex(player.position[0], player.position[1]), Hex(target_player.position[0], target_player.position[1]), grid_type=grid_type))
        if dist_h > 1:
            if player and getattr(player, "conn", None):
                send_message(player.conn, make_error_reply(f"{target_name} è oltre 5 ft ({dist_h} caselle) per distrarlo con Aiuto (PHB p. 192)!"))
            return

    if not hasattr(target_player, "conditions") or target_player.conditions is None:
        target_player.conditions = []
    if not hasattr(player, "helped_targets_this_turn") or not isinstance(player.helped_targets_this_turn, list):
        player.helped_targets_this_turn = []

    if is_ally_help:
        skill_lbl = data.get("skill_name") or "prova di caratteristica"
        target_player._helped_skill = True
        player.has_acted_this_turn = True
        msg_h = f"🤝 {player.name} compie l'Azione di Aiuto su {target_name}: Vantaggio alla prossima {skill_lbl} (PHB p. 192)!"
    else:
        if "Aiutato" not in target_player.conditions:
            target_player.conditions.append("Aiutato")
        if target_player.name not in player.helped_targets_this_turn:
            player.helped_targets_this_turn.append(target_player.name)
        player.has_acted_this_turn = True
        msg_h = f"🤝 {player.name} compie l'Azione di Aiuto contro {target_name}! Il prossimo attacco alleato contro {target_name} avrà Vantaggio."
    broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions, getattr(target_player, "temp_hp", 0)))
    broadcast(game_state, make_chat_broadcast("Sistema", msg_h))
    game_state.log_dm_message(f"[COMBAT] {msg_h}")
    game_state._trigger_gui_update()

def _get_entity_ability_mod(entity, stat="FOR"):
    eff_val = get_effective_attribute_from_dict(entity, stat)
    try:
        return (int(eff_val) - 10) // 2
    except (ValueError, TypeError):
        return 0

def _get_entity_skill_bonus(entity, skill_it, skill_en, fallback_stat):
    sheet = getattr(entity, "full_sheet", None) or {}
    skills = sheet.get("skills", {})
    mod = _get_entity_ability_mod(entity, fallback_stat)
    lvl = sheet.get("level", getattr(entity, "level", 1))
    try:
        lvl = int(lvl)
    except (ValueError, TypeError):
        lvl = 1
    pb = 2 + max(0, (lvl - 1) // 4)
    
    val = skills.get(skill_it, skills.get(skill_en))
    if val is not None:
        try:
            num_val = int(val)
            if num_val == 1:
                return mod + pb
            elif num_val >= 2:
                return mod + 2 * pb
            else:
                return mod
        except (ValueError, TypeError):
            try:
                return int(str(val).replace("+", ""))
            except Exception:
                pass
    return mod

def _get_entity_size_rank(entity):
    sheet = getattr(entity, "full_sheet", None) or {}
    size_str = str(sheet.get("size", getattr(entity, "size", "Medium"))).lower()
    size_map = {
        "tiny": 0, "piccolissima": 0,
        "small": 1, "piccola": 1,
        "medium": 2, "media": 2,
        "large": 3, "grande": 3,
        "huge": 4, "enorme": 4,
        "gargantuan": 5, "mastodontica": 5
    }
    for k, v in size_map.items():
        if k in size_str:
            return v
    return 2

def handle_shove_request(data, player, game_state):
    """
    Risolve la manovra Spingere (Shove - D&D 5e PHB p. 195):
    - Attacco speciale in mischia in sostituzione di un attacco.
    - Bersaglio max 1 taglia più grande.
    - Prova contrapposta: Forza (Atletica) vs Forza (Atletica) o Destrezza (Acrobazia).
    - Se l'attaccante vince:
        * option == 'prone': atterra il bersaglio ('Prono').
        * option == 'push': spinge indietro il bersaglio di 5 piedi (1 casella) lungo la linea d'attacco.
    """
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    target_name = data.get("target_name")
    option = data.get("option", "prone").lower()
    
    target_player = game_state.find_player(target_name)
    if not target_player or not player:
        return
        
    p_cond = getattr(player, "conditions", [])
    blocking = ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto", "Incapacitato", "Incapacitated"]
    if any(is_condition_active(p_cond, c) for c in blocking) or getattr(player, "hp", 1) <= 0:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Non puoi compiere manovre mentre sei Incosciente o Incapacitato!"))
        return

    strict_lock = False
    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
        strict_lock = game_state.automation_settings.get("strict_turn_lock", False)
    if getattr(game_state, "combat_active", False) and strict_lock:
        curr_turn = game_state.get_current_turn_player()
        if curr_turn and curr_turn.name != player.name:
            if player and getattr(player, "conn", None):
                send_message(player.conn, make_error_reply(f"Non è il tuo turno in combattimento! È il turno di {curr_turn.name}."))
            return

    if not (hasattr(player, "position") and player.position and hasattr(target_player, "position") and target_player.position):
        return
    q1, r1 = player.position[0], player.position[1]
    q2, r2 = target_player.position[0], target_player.position[1]
    cur_map = getattr(game_state, "current_map", {}) or {}
    grid_type = cur_map.get("grid_type", "hex")
    from common.hex_utils import Hex, grid_distance
    dist = int(grid_distance(Hex(q1, r1), Hex(q2, r2), grid_type=grid_type))
    if dist > 1:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"{target_name} è troppo distante per una spinta in mischia ({dist} caselle)!"))
        return

    att_size = _get_entity_size_rank(player)
    def_size = _get_entity_size_rank(target_player)
    if def_size > att_size + 1:
        msg = f"❌ {target_player.name} è troppo grande per essere spinto da {player.name} (differenza di oltre 1 taglia)!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        return

    att_ath_bonus = _get_entity_skill_bonus(player, "Atletica", "Athletics", "FOR")
    att_adv = is_condition_active(p_cond, "Ira")
    att_dis = getattr(player, "exhaustion_level", 0) >= 1 or is_condition_active(p_cond, "Spaventato") or is_condition_active(p_cond, "Avvelenato")
    
    ar1 = random.randint(1, 20)
    ar2 = random.randint(1, 20)
    if att_adv and not att_dis:
        att_d20 = max(ar1, ar2)
        att_detail = f"max({ar1}, {ar2})={att_d20} (Ira/Vantaggio)"
    elif att_dis and not att_adv:
        att_d20 = min(ar1, ar2)
        att_detail = f"min({ar1}, {ar2})={att_d20} (Svantaggio)"
    else:
        att_d20 = ar1
        att_detail = str(att_d20)
    att_total = att_d20 + att_ath_bonus

    def_cond = getattr(target_player, "conditions", [])
    def_ath = _get_entity_skill_bonus(target_player, "Atletica", "Athletics", "FOR")
    def_acr = _get_entity_skill_bonus(target_player, "Acrobazia", "Acrobatics", "DES")
    use_acr = (def_acr > def_ath)
    def_bonus = def_acr if use_acr else def_ath
    def_skill_name = "Acrobazia" if use_acr else "Atletica"
    
    def_adv = is_condition_active(def_cond, "Ira") and not use_acr
    def_dis = getattr(target_player, "exhaustion_level", 0) >= 1 or is_condition_active(def_cond, "Spaventato") or is_condition_active(def_cond, "Avvelenato")
    def_incap = any(is_condition_active(def_cond, c) for c in ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Incapacitato", "Incapacitated"])

    dr1 = random.randint(1, 20)
    dr2 = random.randint(1, 20)
    if def_adv and not def_dis:
        def_d20 = max(dr1, dr2)
        def_detail = f"max({dr1}, {dr2})={def_d20}"
    elif def_dis and not def_adv:
        def_d20 = min(dr1, dr2)
        def_detail = f"min({dr1}, {dr2})={def_d20}"
    else:
        def_d20 = dr1
        def_detail = str(def_d20)
    def_total = def_d20 + def_bonus if not def_incap else -99

    attacker_wins = (att_total > def_total) or def_incap
    
    opt_label = "Atterrare" if option == "prone" else "Spingere Indietro"
    log_text = f"💨 **Spinta (Shove - PHB p. 195: {opt_label})**: {player.name} tenta di spingere {target_player.name}!\n"
    log_text += f"• {player.name} [Atletica]: {att_total} ({att_detail} + {att_ath_bonus})\n"
    if def_incap:
        log_text += f"• {target_player.name} è Incapacitato e fallisce automaticamente la contesa!\n"
    else:
        log_text += f"• {target_player.name} [{def_skill_name}]: {def_total} ({def_detail} + {def_bonus})\n"

    if attacker_wins:
        if option == "prone":
            from server.dm_monster_engine import filter_swarm_condition
            if not filter_swarm_condition(target_player, "Prono"):
                log_text += f"🐝 **IMMUNITÀ SCIAME!** {target_player.name} è uno Sciame e non può essere reso **PRONO**!"
            else:
                if "Prono" not in def_cond:
                    def_cond.append("Prono")
                if getattr(target_player, "full_sheet", None) and isinstance(target_player.full_sheet.get("conditions"), list):
                    if "Prono" not in target_player.full_sheet["conditions"]:
                        target_player.full_sheet["conditions"].append("Prono")
                log_text += f"💥 **SUCCESSO!** {target_player.name} viene spinto a terra ed è ora **PRONO**!"
                broadcast(game_state, make_player_stats_update(
                    target_player.name, target_player.hp, target_player.max_hp, target_player.initiative,
                    def_cond, getattr(target_player, "temp_hp", 0), active_effects=getattr(target_player, "active_effects", [])
                ))
                if getattr(target_player, "elevation", 0) > 0:
                    resolve_falling(target_player, target_player.elevation, game_state)
                if getattr(target_player, "mount_name", None):
                    m_dex = get_effective_save_bonus_from_dict(target_player, "DES")
                    m_sv = roll_dice(f"1d20{'+' if m_dex >= 0 else ''}{m_dex}")["total"]
                    if m_sv < 10:
                        prev_m = target_player.mount_name
                        target_player.mount_name = None
                        log_text += f" 🐎 ({target_player.name} fallisce TS DES {m_sv} < 10 e cade da {prev_m}!)"
        else:
            dq = q2 - q1
            dr = r2 - r1
            dest_q = q2 + dq
            dest_r = r2 + dr
            from server.rules.movement import get_effective_map_walls
            walls = get_effective_map_walls(cur_map)
            if [dest_q, dest_r] in walls:
                log_text += f"💥 **SUCCESSO!** {target_player.name} viene spinto indietro ma sbatte contro un ostacolo sulla casella ({dest_q}, {dest_r})!"
            else:
                target_player.position = [dest_q, dest_r]
                log_text += f"💥 **SUCCESSO!** {target_player.name} viene spinto indietro di 5 ft alla casella ({dest_q}, {dest_r})!"
                from server.rules.reaction_magic import break_grapple_if_out_of_reach
                break_grapple_if_out_of_reach(target_player, game_state)
                for v in getattr(game_state, "players", []):
                    if getattr(v, "grappled_by", None) == target_player.name:
                        break_grapple_if_out_of_reach(v, game_state)
                if getattr(target_player, "mount_name", None):
                    m_dex = get_effective_save_bonus_from_dict(target_player, "DES")
                    m_sv = roll_dice(f"1d20{'+' if m_dex >= 0 else ''}{m_dex}")["total"]
                    if m_sv < 10:
                        prev_m = target_player.mount_name
                        target_player.mount_name = None
                        if "Prono" not in def_cond:
                            def_cond.append("Prono")
                        log_text += f" 🐎 ({target_player.name} fallisce TS DES {m_sv} < 10 e cade Prono da {prev_m}!)"
                broadcast(game_state, make_map_data_update_broadcast(cur_map))
                broadcast(game_state, make_player_move(target_player.name, [dest_q, dest_r]))
    else:
        log_text += f"🛡️ **FALLITO!** {target_player.name} resiste saldamente e non cede alla spinta."

    player.has_acted_this_turn = True
    broadcast(game_state, make_chat_broadcast("Sistema", log_text))
    game_state.log_dm_message(f"[SPINTA] {log_text}")
    game_state._trigger_gui_update()

def handle_grapple_request(data, player, game_state):
    """
    Risolve la manovra Lottare (Grapple - D&D 5e PHB p. 195):
    - Attacco speciale in mischia in sostituzione di un attacco.
    - Bersaglio max 1 taglia più grande.
    - Prova contrapposta: Forza (Atletica) vs Forza (Atletica) o Destrezza (Acrobazia).
    - Se l'attaccante vince: bersaglio subisce la condizione 'Afferrato' (Velocità 0).
    """
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    target_name = data.get("target_name")
    
    target_player = game_state.find_player(target_name)
    if not target_player or not player:
        return
        
    p_cond = getattr(player, "conditions", [])
    blocking = ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto", "Incapacitato", "Incapacitated"]
    if any(is_condition_active(p_cond, c) for c in blocking) or getattr(player, "hp", 1) <= 0:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Non puoi lottare mentre sei Incosciente o Incapacitato!"))
        return

    strict_lock = False
    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
        strict_lock = game_state.automation_settings.get("strict_turn_lock", False)
    if getattr(game_state, "combat_active", False) and strict_lock:
        curr_turn = game_state.get_current_turn_player()
        if curr_turn and curr_turn.name != player.name:
            if player and getattr(player, "conn", None):
                send_message(player.conn, make_error_reply(f"Non è il tuo turno in combattimento! È il turno di {curr_turn.name}."))
            return

    if not (hasattr(player, "position") and player.position and hasattr(target_player, "position") and target_player.position):
        return
    q1, r1 = player.position[0], player.position[1]
    q2, r2 = target_player.position[0], target_player.position[1]
    cur_map = getattr(game_state, "current_map", {}) or {}
    grid_type = cur_map.get("grid_type", "hex")
    from common.hex_utils import Hex, grid_distance
    dist = int(grid_distance(Hex(q1, r1), Hex(q2, r2), grid_type=grid_type))
    if dist > 1:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"{target_name} è troppo distante per essere afferrato ({dist} caselle)!"))
        return

    att_size = _get_entity_size_rank(player)
    def_size = _get_entity_size_rank(target_player)
    if def_size > att_size + 1:
        msg = f"❌ {target_player.name} è troppo grande per essere afferrato da {player.name} (oltre 1 taglia di differenza)!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        return

    att_ath_bonus = _get_entity_skill_bonus(player, "Atletica", "Athletics", "FOR")
    att_adv = is_condition_active(p_cond, "Ira")
    att_dis = getattr(player, "exhaustion_level", 0) >= 1 or is_condition_active(p_cond, "Spaventato") or is_condition_active(p_cond, "Avvelenato")
    
    ar1, ar2 = random.randint(1, 20), random.randint(1, 20)
    if att_adv and not att_dis:
        att_d20 = max(ar1, ar2)
        att_detail = f"max({ar1}, {ar2})={att_d20} (Ira/Vantaggio)"
    elif att_dis and not att_adv:
        att_d20 = min(ar1, ar2)
        att_detail = f"min({ar1}, {ar2})={att_d20} (Svantaggio)"
    else:
        att_d20 = ar1
        att_detail = str(att_d20)
    att_total = att_d20 + att_ath_bonus

    def_cond = getattr(target_player, "conditions", [])
    def_ath = _get_entity_skill_bonus(target_player, "Atletica", "Athletics", "FOR")
    def_acr = _get_entity_skill_bonus(target_player, "Acrobazia", "Acrobatics", "DES")
    use_acr = (def_acr > def_ath)
    def_bonus = def_acr if use_acr else def_ath
    def_skill_name = "Acrobazia" if use_acr else "Atletica"
    
    def_adv = is_condition_active(def_cond, "Ira") and not use_acr
    def_dis = getattr(target_player, "exhaustion_level", 0) >= 1 or is_condition_active(def_cond, "Spaventato") or is_condition_active(def_cond, "Avvelenato")
    def_incap = any(is_condition_active(def_cond, c) for c in ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Incapacitato", "Incapacitated"])

    dr1, dr2 = random.randint(1, 20), random.randint(1, 20)
    if def_adv and not def_dis:
        def_d20 = max(dr1, dr2)
        def_detail = f"max({dr1}, {dr2})={def_d20}"
    elif def_dis and not def_adv:
        def_d20 = min(dr1, dr2)
        def_detail = f"min({dr1}, {dr2})={def_d20}"
    else:
        def_d20 = dr1
        def_detail = str(def_d20)
    def_total = def_d20 + def_bonus if not def_incap else -99

    attacker_wins = (att_total > def_total) or def_incap

    log_text = f"🤼 **Lotta (Grapple - PHB p. 195)**: {player.name} tenta di afferrare {target_player.name}!\n"
    log_text += f"• {player.name} [Atletica]: {att_total} ({att_detail} + {att_ath_bonus})\n"
    if def_incap:
        log_text += f"• {target_player.name} è Incapacitato e non può opporsi alla presa!\n"
    else:
        log_text += f"• {target_player.name} [{def_skill_name}]: {def_total} ({def_detail} + {def_bonus})\n"

    if attacker_wins:
        from server.dm_monster_engine import filter_swarm_condition
        if not filter_swarm_condition(target_player, "Afferrato"):
            log_text += f"🐝 **IMMUNITÀ SCIAME!** {target_player.name} è uno Sciame ed è immune alla condizione **AFFERRATO**!"
        else:
            if "Afferrato" not in def_cond:
                def_cond.append("Afferrato")
            if getattr(target_player, "full_sheet", None) and isinstance(target_player.full_sheet.get("conditions"), list):
                if "Afferrato" not in target_player.full_sheet["conditions"]:
                    target_player.full_sheet["conditions"].append("Afferrato")
            target_player.grappled_by = player.name
            log_text += f"💥 **SUCCESSO!** {target_player.name} è ora **AFFERRATO** da {player.name} (Velocità 0)!"
            broadcast(game_state, make_player_stats_update(
                target_player.name, target_player.hp, target_player.max_hp, target_player.initiative,
                def_cond, getattr(target_player, "temp_hp", 0), active_effects=getattr(target_player, "active_effects", [])
            ))
    else:
        log_text += f"🛡️ **FALLITO!** {target_player.name} schiva la presa di {player.name} e rimane libero."

    player.has_acted_this_turn = True
    broadcast(game_state, make_chat_broadcast("Sistema", log_text))
    game_state.log_dm_message(f"[LOTTA] {log_text}")
    game_state._trigger_gui_update()

def handle_short_rest_request(data, player, game_state):
    if getattr(game_state, "combat_active", False):
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Non puoi effettuare un Riposo Breve durante il combattimento!"))
        return

    hd_spent = int(data.get("hd_spent", 1) or 1)
    try: hp_rec = max(0, int(data.get("hp_recovered", 0)))
    except (ValueError, TypeError): hp_rec = 0

    if not player:
        return

    with game_state.lock:
        sheet = getattr(player, "full_sheet", None)
        if sheet:
            cur_hd = int(sheet.get("hit_dice_current", sheet.get("level", 1)) or 0)
            if cur_hd < hd_spent:
                if getattr(player, "conn", None):
                    send_message(player.conn, make_error_reply(f"Dadi Vita insufficienti! Ne possiedi {cur_hd}."))
                return
            sheet["hit_dice_current"] = max(0, cur_hd - hd_spent)
            
            # D&D 5e RAW (PHB p. 164): Warlock ricarica gli slot di Magia del Patto a Riposo Breve senza ricaricare slot di altre classi
            pact = sheet.get("pact_slots") if isinstance(sheet, dict) else None
            if isinstance(pact, dict) and pact.get("max", 0) > 0:
                pact["current"] = pact.get("max", 0)
                player.pact_slots_max = pact.get("max", 0)
                player.pact_slots_current = pact["current"]
                player.pact_slot_level = pact.get("level", 0)
            else:
                from common.dnd5e_tables import entity_get_class_level
                war_lvl = entity_get_class_level(player, "warlock")
                other_caster = any(
                    entity_get_class_level(player, *keys) > 0
                    for keys in (("mago", "wizard"), ("chierico", "cleric"), ("stregone", "sorcerer"), ("bardo", "bard"), ("druido", "druid"), ("paladino", "paladin"), ("ranger",), ("artefice", "artificer"))
                )
                char_cls = str(sheet.get("char_class", "")).lower()
                if (war_lvl > 0 or "warlock" in char_cls) and not other_caster and isinstance(sheet.get("spell_slots"), dict):
                    for sl_lvl, sl_info in sheet["spell_slots"].items():
                        try:
                            if int(sl_lvl) <= 5 and isinstance(sl_info, dict):
                                sl_info["current"] = sl_info.get("max", 0)
                        except (ValueError, TypeError):
                            pass

        if hp_rec > 0:
            # Canto di Riposo (Song of Rest - Bardo Lv 2+, PHB p. 54): cura extra se spende almeno 1 Dado Vita e un Bardo è nel party
            song_bonus = 0
            if hd_spent > 0:
                from common.dnd5e_tables import entity_get_class_level
                best_bard = entity_get_class_level(player, "bardo", "bard")
                for ally in getattr(game_state, "players", []):
                    if getattr(ally, "is_party_member", False) and getattr(ally, "hp", 0) > 0:
                        best_bard = max(best_bard, entity_get_class_level(ally, "bardo", "bard"))
                if best_bard >= 2:
                    sor_sides = 6 if best_bard < 9 else (8 if best_bard < 13 else (10 if best_bard < 17 else 12))
                    song_bonus = random.randint(1, sor_sides)
                    hp_rec += song_bonus
            player.relentless_rage_uses = 0
            player.hp = min(player.max_hp, player.hp + hp_rec)
            if sheet:
                sheet["hp_current"] = player.hp
            broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, getattr(player, "conditions", []), getattr(player, "temp_hp", 0)))
            game_state._trigger_gui_update()

    msg = f"☕ {player.name} ha completato un Riposo Breve (ha speso {hd_spent} Dado/i Vita e recuperato {hp_rec} HP)!"
    # Variante Riposo DMG (opt_rest_variant) + avanzamento tempo
    dm_settings = getattr(game_state, "automation_settings", {}) or {}
    rest_key = dm_settings.get("opt_rest_variant", "standard")
    from common.dnd5e_tables import REST_VARIANTS
    r_info = REST_VARIANTS.get(rest_key, REST_VARIANTS["standard"])
    if rest_key != "standard":
        msg += f" [Variante DMG {r_info.get('label', rest_key)}: {r_info.get('short_hours', 1)}h]"
    if dm_settings.get("auto_advance_time", True) and hasattr(game_state, "advance_game_time"):
        short_mins = int(round(float(r_info.get("short_hours", 1)) * 60))
        if short_mins > 0:
            game_state.advance_game_time(minutes=short_mins)
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    game_state.log_dm_message(f"[RIPOSO] {msg}")

def handle_reaction_response(data, player, game_state):
    """Gestisce la risposta del client a un prompt di reazione 5e (Attacco d'Opportunità, Scudo, Schivata Prodigiosa, ecc.)."""
    reaction_type = data.get("reaction_type")
    accepted = data.get("accepted", False)
    target_name = data.get("target_name")
    details = data.get("details", {})
    
    if not accepted or not player:
        return

    from server.rules.reaction_magic import is_incapacitated, entity_has_available_slot
    from common.character_schema import consume_spell_or_pact_slot
    from common.dnd5e_tables import entity_get_class_level
    last_hit = getattr(player, "_last_hit_for_reaction", None) or {}
    can_ud_rescue = (
        reaction_type == "UNCANNY_DODGE"
        and getattr(player, "hp", 0) <= 0
        and last_hit
        and int(last_hit.get("old_hp", 0) or 0) > (int(last_hit.get("dmg_to_hp", 0) or 0) - (int(last_hit.get("dmg_to_hp", 0) or 0) // 2))
    )
    if (is_incapacitated(player) or getattr(player, "hp", 1) <= 0) and not can_ud_rescue:
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Non puoi usare una Reazione mentre sei Incapacitato o a 0 HP!"))
        return

    from server.rules.class_abilities import _check_surprised_block
    if _check_surprised_block(player, game_state, "usare una Reazione"):
        return
        
    if getattr(player, "has_reacted_this_turn", False):
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Hai già consumato la tua Reazione per questo round!"))
        return
        
    player.has_reacted_this_turn = True
    
    if reaction_type == "OPPORTUNITY_ATTACK":
        msg = f"⚔️ {player.name} usa la propria REAZIONE per effettuare un Attacco d'Opportunità contro {target_name}!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[REAZIONE] {msg}")
        
        w_name = details.get("weapon_name", "Attacco d'Opportunità")
        hit_bonus = details.get("hit_bonus", 0)
        damage_formula = details.get("damage_formula", "1d8")
        damage_type = details.get("damage_type", "Tagliente")
        
        handle_attack_request({
            "target_name": target_name,
            "weapon_name": w_name,
            "hit_bonus": hit_bonus,
            "damage_formula": damage_formula,
            "damage_type": damage_type,
            "is_reaction": True
        }, player, game_state)

    elif reaction_type == "UNCANNY_DODGE":
        inc_dmg = int(details.get("dmg_to_hp") or details.get("damage_taken") or last_hit.get("dmg_to_hp") or last_hit.get("final_dmg") or 0)
        halved = inc_dmg // 2
        if halved > 0 and (getattr(player, "hp", 0) > 0 or can_ud_rescue):
            if getattr(player, "hp", 0) <= 0 and can_ud_rescue:
                for c_rm in ("Incosciente", "Morente", "Dying", "Unconscious"):
                    if c_rm in getattr(player, "conditions", []):
                        player.conditions.remove(c_rm)
            player.hp = min(player.max_hp, player.hp + halved)
            if isinstance(getattr(player, "full_sheet", None), dict):
                player.full_sheet["hp_current"] = player.hp
            broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, getattr(player, "conditions", []), getattr(player, "temp_hp", 0)))
            game_state._trigger_gui_update()
        msg = f"🥷 [SCHIVATA PRODIGIOSA] {player.name} usa la Reazione per dimezzare i danni dell'attacco di {target_name} (recupera {halved} PF -> PV: {player.hp}/{player.max_hp})!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[REAZIONE] {msg}")
        
    elif reaction_type == "SHIELD_SPELL":
        if not details.get("slot_consumed") and entity_has_available_slot(player, 1):
            consume_spell_or_pact_slot(player, 1)
        conds = getattr(player, "conditions", [])
        if "Scudo" not in conds:
            conds.append("Scudo")
        shield_note = ""
        if last_hit and not last_hit.get("is_crit") and (int(last_hit.get("hit_roll", 999)) < int(last_hit.get("base_ac", 0)) + 5):
            r_hp = int(last_hit.get("dmg_to_hp", 0) or 0)
            r_tmp = int(last_hit.get("temp_absorbed", 0) or 0)
            if r_hp > 0:
                player.hp = min(player.max_hp, player.hp + r_hp)
                if isinstance(getattr(player, "full_sheet", None), dict):
                    player.full_sheet["hp_current"] = player.hp
            if r_tmp > 0:
                player.temp_hp = getattr(player, "temp_hp", 0) + r_tmp
            player._last_hit_for_reaction = None
            shield_note = f" L'attacco precedente ({last_hit.get('hit_roll')}) manca contro CA {int(last_hit.get('base_ac', 0)) + 5} (ripristinati {r_hp} PF)!"
        msg = f"🛡️ {player.name} usa la propria REAZIONE per lanciare l'incantesimo Scudo! Ottiene +5 CA fino all'inizio del suo prossimo turno.{shield_note}"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[REAZIONE] {msg}")
        broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
        game_state._trigger_gui_update()

    elif reaction_type == "ABSORB_ELEMENTS":
        elem = str(details.get("damage_type", "Fuoco") or "Fuoco").capitalize()
        if not hasattr(player, "damage_resistances") or not isinstance(player.damage_resistances, list):
            player.damage_resistances = []
        if elem.lower() not in [str(r).lower() for r in player.damage_resistances]:
            player.damage_resistances.append(elem)
        conds = getattr(player, "conditions", [])
        ae_label = f"Assorbire Elementi ({elem})"
        if ae_label not in conds:
            conds.append(ae_label)
        msg = f"🔥 {player.name} usa la propria REAZIONE per lanciare Assorbire Elementi! Ottiene Resistenza ai danni da {elem} e +1d6 danni da {elem} al prossimo attacco in mischia!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[REAZIONE] {msg}")
        broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
        game_state._trigger_gui_update()

    elif reaction_type == "COUNTERSPELL":
        spell_lvl = int(details.get("spell_level", 3) or 3)
        slot_lvl = int(details.get("slot_level", 3) or 3)
        caster_nm = target_name or details.get("caster_name", "l'incantatore nemico")
        cast_id = details.get("cast_id")
        if not details.get("slot_consumed") and entity_has_available_slot(player, slot_lvl):
            consume_spell_or_pact_slot(player, slot_lvl)
        countered = False
        if slot_lvl >= spell_lvl:
            countered = True
            msg = f"✋ {player.name} usa la propria REAZIONE per lanciare Controincantesimo (Liv. {slot_lvl}) e ANNULLA automaticamente l'incantesimo di {caster_nm} (Liv. {spell_lvl})!"
        else:
            from common.item_modifiers import get_effective_attribute_from_dict
            sheet = getattr(player, "full_sheet", None)
            s_dict = sheet if isinstance(sheet, dict) else player
            best_mental = max(
                get_effective_attribute_from_dict(s_dict, "INT"),
                get_effective_attribute_from_dict(s_dict, "SAG"),
                get_effective_attribute_from_dict(s_dict, "CAR"),
            )
            mod_c = (best_mental - 10) // 2
            r_cs = random.randint(1, 20)
            tot_cs = r_cs + mod_c
            dc_cs = 10 + spell_lvl
            countered = (tot_cs >= dc_cs)
            outcome = "✅ ANNULLATO!" if countered else "❌ FALLITO (l'incantesimo ha effetto)!"
            msg = f"✋ {player.name} lancia Controincantesimo (Liv. {slot_lvl}) contro l'incantesimo di Liv. {spell_lvl} di {caster_nm}: Prova d'Incantatore [d20: {r_cs}] + {mod_c} = {tot_cs} vs CD {dc_cs} -> {outcome}"
        if countered and cast_id and game_state:
            if not hasattr(game_state, "_cancelled_cast_ids"):
                game_state._cancelled_cast_ids = set()
            game_state._cancelled_cast_ids.add(cast_id)
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[REAZIONE] {msg}")
        game_state._trigger_gui_update()

    elif reaction_type == "DEFLECT_MISSILES":
        from common.item_modifiers import get_effective_attribute_from_dict
        sheet = getattr(player, "full_sheet", None)
        s_dict = sheet if isinstance(sheet, dict) else player
        dex_val = get_effective_attribute_from_dict(s_dict, "DES")
        dex_mod = (dex_val - 10) // 2
        monk_lvl = entity_get_class_level(player, "monaco", "monk")
        if monk_lvl <= 0:
            monk_lvl = int((sheet.get("level", getattr(player, "level", 3)) if isinstance(sheet, dict) else getattr(player, "level", 3)) or 3)
        d10_r = random.randint(1, 10)
        reduction = max(1, d10_r + dex_mod + monk_lvl)
        inc_dmg = int(details.get("incoming_damage", 0) or last_hit.get("dmg_to_hp", 0) or 0)
        if inc_dmg > 0:
            restored = min(inc_dmg, reduction)
            player.hp = min(player.max_hp, player.hp + restored)
            if isinstance(sheet, dict):
                sheet["hp_current"] = player.hp
        caught_note = " 🎯 Danno ridotto a 0: afferra il proiettile e può spendere 1 Punto Ki per rilanciarlo!" if (inc_dmg > 0 and reduction >= inc_dmg) else ""
        msg = f"🥋 {player.name} usa Deflettere Missili (Reazione): riduce il danno a distanza di **{reduction}** [1d10({d10_r}) + DES({dex_mod}) + Liv({monk_lvl})]!{caught_note}"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[REAZIONE] {msg}")
        broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
        game_state._trigger_gui_update()


def handle_ready_action_request(data, player, game_state):
    """
    Azione 'Preparare' (Ready Action - D&D 5e RAW PHB p. 193):
    - Consuma l'Azione del turno corrente.
    - Registra l'innesco (trigger) e l'azione preparata.
    - Se l'azione preparata è un incantesimo, richiede Concentrazione fino all'innesco.
    """
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    if not player:
        return
    trigger_text = str(data.get("trigger_text", "Appena si verifica la condizione") or "Appena si verifica la condizione").strip()
    readied_action = str(data.get("readied_action", "Attacco") or "Attacco").strip()
    is_spell = bool(data.get("is_spell", False))

    player.readied_action_data = {
        "trigger": trigger_text,
        "action": readied_action,
        "is_spell": is_spell,
        "slot_level": data.get("slot_level"),
        "action_payload": data.get("action_payload"),
    }
    player.has_acted_this_turn = True
    if not hasattr(player, "conditions") or not isinstance(player.conditions, list):
        player.conditions = []
    if "Azione Preparata" not in player.conditions:
        player.conditions.append("Azione Preparata")

    conc_note = ""
    if is_spell:
        # PHB p. 193: preparare un incantesimo consuma subito lo slot e richiede Concentrazione (rompe quella precedente)
        drop_concentration(player, game_state, notify=True)
        if data.get("slot_level"):
            try:
                from common.character_schema import consume_spell_or_pact_slot
                consume_spell_or_pact_slot(player, int(data["slot_level"]))
            except (ValueError, TypeError):
                pass
        if "Concentrazione" not in player.conditions:
            player.conditions.append("Concentrazione")
        player.concentrating_spell = f"Preparato: {readied_action}"
        conc_note = " [🧠 Concentrazione attiva sull'incantesimo preparato (PHB p. 193)]"

    msg = f"⏱️ **Azione Preparata (PHB p. 193)**: {player.name} prepara «{readied_action}» con innesco: *«{trigger_text}»*{conc_note}."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    game_state.log_dm_message(f"[COMBAT] {msg}")
    broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
    game_state._trigger_gui_update()


def handle_trigger_readied_action_request(data, player, game_state):
    """
    Innesca l'Azione Preparata consumando la Reazione del personaggio (PHB p. 193).
    """
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    if not player:
        return
    if getattr(player, "has_reacted_this_turn", False):
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Hai già consumato la tua Reazione in questo round!"))
        return

    r_data = getattr(player, "readied_action_data", None)
    if not r_data and "Azione Preparata" not in getattr(player, "conditions", []):
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Non hai alcuna Azione Preparata attiva!"))
        return

    trigger_str = r_data.get("trigger", "Innesco verificato") if isinstance(r_data, dict) else "Innesco verificato"
    action_str = r_data.get("action", "Azione Preparata") if isinstance(r_data, dict) else "Azione Preparata"
    target_name = data.get("target_name")
    target_suffix = f" su {target_name}" if target_name else ""

    player.has_reacted_this_turn = True
    player.readied_action_data = None
    if "Azione Preparata" in getattr(player, "conditions", []):
        player.conditions.remove("Azione Preparata")

    msg = f"⚡ **Innesco Azione Preparata**: {player.name} usa la propria REAZIONE in risposta a *«{trigger_str}»* ed esegue **{action_str}**{target_suffix}!"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    game_state.log_dm_message(f"[REAZIONE] {msg}")
    broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
    game_state._trigger_gui_update()

    if isinstance(r_data, dict) and isinstance(r_data.get("action_payload"), dict):
        payload = dict(r_data["action_payload"])
        if target_name:
            payload.setdefault("target_name", target_name)
        payload["is_reaction"] = True
        if payload.get("target_name"):
            handle_attack_request(payload, player, game_state)

def handle_set_automation_mode_request(data, player, game_state):
    """Gestisce la modifica della modalità di automazione (manual, hybrid, full) da parte del DM."""
    is_dm = (player is None or getattr(player, "role", "") == "DM")
    if not is_dm:
        return
    mode = data.get("mode", "hybrid")
    settings = data.get("settings", {})
    game_state.set_automation_mode(mode, settings)
    
    mode_names = {
        "manual": "🎲 Tavolo Tradizionale (Controllo DM & Pen & Paper)",
        "hybrid": "⚖️ Ibrido Assistito (Consigliato)",
        "full": "⚡ Full Automation (Tattico Rapido)"
    }
    mode_title = mode_names.get(mode, mode.upper())
    msg = f"🎮 Modalità di Gestione Campagna impostata su: '{mode_title}' dal DM."
    game_state.log_dm_message(f"[SISTEMA] {msg}")
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    from common.protocol import make_automation_settings_broadcast
    broadcast(game_state, make_automation_settings_broadcast(mode, game_state.automation_settings))
    game_state._trigger_gui_update()

def handle_apply_pending_damage_request(data, player, game_state):
    """Permette al DM di confermare, dimezzare o annullare un danno calcolato prima di applicarlo agli HP."""
    is_dm = (player is None or getattr(player, "role", "") == "DM")
    if not is_dm:
        return
        
    pending_id = data.get("pending_id")
    action = data.get("action", "apply") # "apply", "half", "cancel", "custom"
    custom_amount = data.get("custom_amount")
    
    if not hasattr(game_state, "pending_damages") or pending_id not in game_state.pending_damages:
        return
        
    pending = game_state.pending_damages.pop(pending_id)
    target_name = pending["target"]
    target_player = game_state.find_player(target_name)
    attacker_name = pending.get("attacker", "Attaccante")
    damage_type = pending.get("damage_type", "Tagliente")
    raw_damage = pending.get("raw_damage", 0)
    
    if action == "cancel":
        msg = f"❌ Il DM ha ANNULLATO il danno ({raw_damage} {damage_type}) inflitto da {attacker_name} su {target_name}."
        game_state.log_dm_message(f"[COMBAT] {msg}")
        broadcast(game_state, make_chat_broadcast("DM", msg))
        game_state._trigger_gui_update()
        return
        
    if not target_player:
        return
        
    if action == "half":
        calc_dmg = max(1, raw_damage // 2)
        desc_prefix = f"🛡️ Il DM applica DANNO DIMEZZATO ({raw_damage} -> {calc_dmg} {damage_type})"
    elif action == "custom" and custom_amount is not None:
        try:
            calc_dmg = max(0, int(custom_amount))
            desc_prefix = f"🎯 Il DM applica DANNO PERSONALIZZATO ({calc_dmg} {damage_type})"
        except (ValueError, TypeError):
            calc_dmg = raw_damage
            desc_prefix = f"⚔️ Il DM applica DANNO PIENO ({calc_dmg} {damage_type})"
    else: # "apply"
        calc_dmg = raw_damage
        desc_prefix = f"⚔️ Il DM applica DANNO PIENO ({calc_dmg} {damage_type})"
        
    is_crit = pending.get("is_crit", False)
    final_dmg, note, temp_absorbed, dmg_to_hp = apply_damage(target_player, calc_dmg, damage_type, game_state, is_crit=is_crit)
    log_msg = f"{desc_prefix} a {target_name}{note}."
    if temp_absorbed > 0:
        log_msg += f" [{temp_absorbed} assorbiti da Temp HP]."
    log_msg += f" HP {target_name}: {target_player.hp}/{target_player.max_hp}"
    if getattr(target_player, "temp_hp", 0) > 0:
        log_msg += f" (+{target_player.temp_hp} Temp)"
        
    game_state.log_dm_message(f"[COMBAT] {log_msg}")
    broadcast(game_state, make_chat_broadcast("DM", log_msg))
    broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions, getattr(target_player, "temp_hp", 0)))
    game_state._trigger_gui_update()

def handle_summon_companion_request(data, player, game_state):
    """
    Evoca un famiglio (Find Familiar), compagno animale (Ranger) o creatura evocata (5e RAW).
    """
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    if not player:
        return
        
    comp_type = data.get("companion_type", "familiar")
    template_key = data.get("template_key", "owl")
    custom_name = data.get("custom_name", "")
    ranger_lvl = data.get("ranger_level", 1)
    ranger_pb = data.get("ranger_pb", 2)
    
    from common.companions_data import create_companion_player_dict
    from common.game_state import Player
    
    comp_dict = create_companion_player_dict(
        companion_type=comp_type,
        template_key=template_key,
        master_player=player,
        custom_name=custom_name,
        ranger_level=ranger_lvl,
        ranger_pb=ranger_pb
    )
    
    # Se il giocatore ha già un famiglio attivo dello stesso tipo, rimuovi il vecchio (PHB p. 240)
    if comp_type == "familiar":
        old_familiars = [p for p in game_state.players if getattr(p, "companion_type", None) == "familiar" and getattr(p, "master_name", None) == player.name]
        for old_f in old_familiars:
            if hasattr(game_state, "remove_player"):
                game_state.remove_player(old_f)
            elif old_f in game_state.players:
                game_state.players.remove(old_f)
            from common.protocol import make_player_left
            broadcast(game_state, make_player_left(old_f.name))
            
    comp_player = Player.from_dict(comp_dict)
    
    with game_state.lock:
        game_state.players.append(comp_player)
        
    from common.protocol import make_player_joined
    broadcast(game_state, make_player_joined(comp_player.to_dict()))
    broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
    game_state._trigger_gui_update()
    
    type_labels = {"familiar": "Famiglio", "beast": "Compagno Animale", "summon": "Creatura Evocata"}
    t_label = type_labels.get(comp_type, "Compagno")
    msg = f"🐾 [5e {t_label}] {player.name} ha evocato {comp_player.name} al proprio fianco!"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    game_state.log_dm_message(f"[COMPAGNO] {msg}")

def handle_dismiss_familiar_request(data, player, game_state):
    """
    Gestisce il congedo o richiamo del famiglio (tasca dimensionale o congedo definitivo).
    """
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    comp_name = data.get("companion_name")
    action = data.get("action", "pocket")
    
    comp = game_state.find_player(comp_name)
    if not comp:
        return
        
    is_dm = (player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if not is_dm and getattr(comp, "master_name", None) != player.name and getattr(comp, "owner", None) != player.name:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Non puoi gestire compagni non tuoi."))
        return
        
    if action == "pocket":
        comp.in_pocket_dimension = True
        comp.is_hidden = True
        msg = f"🚪 {comp.name} entra temporaneamente nella tasca dimensionale magica."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[FAMIGLIO] {msg}")
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        game_state._trigger_gui_update()
    elif action == "recall":
        comp.in_pocket_dimension = False
        comp.is_hidden = False
        if player and hasattr(player, "position") and player.position:
            comp.position = [player.position[0] + 1, player.position[1]]
        msg = f"✨ {comp.name} riappare al fianco di {player.name if player else 'padrone'} dalla tasca dimensionale!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[FAMIGLIO] {msg}")
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        game_state._trigger_gui_update()
    elif action == "dismiss":
        with game_state.lock:
            if comp in game_state.players:
                game_state.players.remove(comp)
        msg = f"💀 {comp.name} è stato congedato definitivamente."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[COMPAGNO] {msg}")
        from common.protocol import make_player_left
        broadcast(game_state, make_player_left(comp.name))
        game_state._trigger_gui_update()

def handle_deliver_touch_spell_request(data, player, game_state):
    """
    Eroga un incantesimo a contatto attraverso il famiglio (D&D 5e RAW PHB p. 240).
    - Famiglio entro 100 ft (20 esagoni) dal padrone
    - Bersaglio entro portata di contatto (1 esagono) dal famiglio
    - Il famiglio consuma la sua reazione
    """
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    if not player:
        return
        
    familiar_name = data.get("familiar_name")
    target_name = data.get("target_name")
    spell_name = data.get("spell_name", "Incantesimo a Contatto")
    action_type = data.get("action_type", "damage")
    formula = data.get("formula", "1d8")
    damage_type = data.get("damage_type", "Fulmine")
    
    familiar = game_state.find_player(familiar_name)
    if not familiar:
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Famiglio '{familiar_name}' non trovato sulla mappa."))
        return
        
    if getattr(familiar, "master_name", None) != player.name and getattr(familiar, "owner", None) != player.name:
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Puoi erogare incantesimi solo attraverso il tuo famiglio!"))
        return
        
    if getattr(familiar, "in_pocket_dimension", False):
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Il famiglio è nella tasca dimensionale! Richiamalo prima di lanciare."))
        return
        
    target = game_state.find_player(target_name)
    if not target:
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Bersaglio '{target_name}' non trovato."))
        return
        
    # Verifica distanza padrone-famiglio (max 100 ft / 20 esagoni)
    p_pos = getattr(player, "position", [0, 0])
    f_pos = getattr(familiar, "position", [0, 0])
    t_pos = getattr(target, "position", [0, 0])
    
    cur_m = getattr(game_state, "current_map", None)
    g_type = cur_m.get("grid_type", "hex") if cur_m else "hex"
    d_rule = "standard"
    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
        d_rule = game_state.automation_settings.get("square_diagonal_rule", "standard")

    dist_master_fam = grid_distance_3d(Hex(p_pos[0], p_pos[1]), Hex(f_pos[0], f_pos[1]), getattr(player, "elevation", 0), getattr(familiar, "elevation", 0), grid_type=g_type, diagonal_rule=d_rule)
    if dist_master_fam > 20:
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Il famiglio è troppo lontano dal padrone ({dist_master_fam:.1f} caselle > 20 caselle / 100 ft)!"))
        return
        
    # Verifica distanza famiglio-bersaglio (portata a contatto: 1 casella)
    dist_fam_target = grid_distance_3d(Hex(f_pos[0], f_pos[1]), Hex(t_pos[0], t_pos[1]), getattr(familiar, "elevation", 0), getattr(target, "elevation", 0), grid_type=g_type, diagonal_rule=d_rule)
    if dist_fam_target > 1:
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Il bersaglio non è a portata di contatto dal famiglio ({dist_fam_target:.1f} caselle > 1 casella)!"))
        return
        
    # Il famiglio spende la propria reazione (5e RAW)
    familiar.has_reacted_this_turn = True
    
    # Esegui effetto (danno o cura)
    res = roll_dice(formula)
    val = res["total"]
    
    if action_type in ["cura", "heal"]:
        _apply_hp_change(target, target.hp + val, game_state)
        msg = f"🦉 {player.name} eroga '{spell_name}' a contatto tramite il famiglio {familiar.name}: {target.name} recupera {val} PV! (HP: {target.hp}/{target.max_hp})"
    else:
        final_dmg, note, temp_absorbed, dmg_to_hp = apply_damage(target, val, damage_type, game_state)
        msg = f"⚡ {player.name} eroga '{spell_name}' a contatto tramite il famiglio {familiar.name}: {target.name} subisce {final_dmg} danni ({damage_type}){note}!"
        
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    game_state.log_dm_message(f"[TOUCH-SPELL] {msg}")
    broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
    game_state._trigger_gui_update()


