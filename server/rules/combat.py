import re
import random
import math
import threading
from common.protocol import *
from common.hex_utils import Hex, hex_distance, grid_distance, grid_distance_3d, get_sphere_hexes, hex_linedraw, get_cover_between
from common.network_utils import send_message, broadcast
from common.dice import roll_dice
from common.i18n import is_condition_active

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
            loot_items = [dict(it) for it in sheet["inventory_grid"] if isinstance(it, dict) and it.get("name")]
        
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
        conc_spell = str(getattr(player, "concentrating_on", "") or "").lower()
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

def resolve_falling(entity, fall_distance_ft, game_state, is_voluntary=False):
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

    dice_count = min(20, int(fall_distance_ft // 10))
    rolls = [random.randint(1, 6) for _ in range(dice_count)]
    raw_dmg = sum(rolls)

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
        # 2. Controllo Caduta Lenta del Monaco (Monk 4+ Slow Fall)
        sheet = getattr(entity, "full_sheet", {}) or {}
        cls_name = str(sheet.get("class", "")).lower()
        lvl = int(sheet.get("level", 1))
        if ("monaco" in cls_name or "monk" in cls_name) and lvl >= 4:
            reduction = lvl * 5
            raw_dmg = max(0, raw_dmg - reduction)
            mitigated = True
            mitigation_note = f" (Ridotto di {reduction} da Caduta Lenta del Monaco)"

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

def apply_damage(target_player, raw_damage, damage_type="Tagliente", game_state=None, is_crit=False):
    """
    Applica il danno secondo le regole D&D 5e:
    1. Resistenze, Immunità e Vulnerabilità (inclusa Ira Barbarica e full_sheet)
    2. Assorbimento Punti Ferita Temporanei (Temp HP) prima degli HP effettivi
    3. Morte istantanea (danno residuo >= HP max)
    4. Condizioni Incosciente/Prono o Morto per i mostri + drop spoglie
    5. Tiro Salvezza Concentrazione (e interruzione su condizioni invalidanti)
    Ritorna: (danno_finale, note_moltiplicatore, temp_assorbiti, danno_a_hp)
    """
    if raw_damage <= 0:
        return 0, "", 0, 0
        
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
    
    # Ira Barbarica: resistenza ai danni fisici (tagliente, perforante, contundente)
    if "Ira" in getattr(target_player, "conditions", []):
        all_target_res.extend(["tagliente", "perforante", "contundente", "slashing", "piercing", "bludgeoning"])
        
    is_immune = any(dt in damage_map.get(k, [k]) for k in all_target_imm) or (dt in all_target_imm)
    is_resistant = any(dt in damage_map.get(k, [k]) for k in all_target_res) or (dt in all_target_res)
    is_vulnerable = any(dt in damage_map.get(k, [k]) for k in all_target_vul) or (dt in all_target_vul)
    
    note = ""
    if is_immune:
        multiplier = 0.0
        note = f" (Immune a {damage_type}: 0 danni!)"
    elif is_resistant and not is_vulnerable:
        multiplier = 0.5
        note = f" (Resistenza a {damage_type}: dimezzato)"
    elif is_vulnerable and not is_resistant:
        multiplier = 2.0
        note = f" (Vulnerabilità a {damage_type}: raddoppiato!)"
    else:
        multiplier = 1.0
        
    final_dmg = int(raw_damage * multiplier)
    
    # Assorbimento Punti Ferita Temporanei (Temp HP)
    cur_temp = getattr(target_player, "temp_hp", 0)
    temp_absorbed = 0
    if cur_temp > 0:
        temp_absorbed = min(cur_temp, final_dmg)
        target_player.temp_hp = cur_temp - temp_absorbed
        dmg_to_hp = final_dmg - temp_absorbed
    else:
        dmg_to_hp = final_dmg
        
    old_hp = target_player.hp
    new_hp_unbounded = old_hp - dmg_to_hp
    excess_damage = abs(new_hp_unbounded) if new_hp_unbounded < 0 else 0
    target_player.hp = max(0, new_hp_unbounded)
    
    is_npc = (not hasattr(target_player, "conn") or target_player.conn is None) and not getattr(target_player, "is_party_member", False)
    auto_death = True
    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
        auto_death = game_state.automation_settings.get("auto_death_saves", True)
    
    incapacitating = ("incapacitato", "incapacitated", "incosciente", "unconscious", "paralizzato", "paralyzed", "stordito", "stunned", "pietrificato", "petrified", "morto", "dead")
    if target_player.hp == 0 or any(str(c).strip().lower() in incapacitating for c in getattr(target_player, "conditions", [])):
        drop_concentration(target_player, game_state, notify=(not is_npc))

    if target_player.hp == 0:
        if is_npc:
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
        _trigger_concentration_check(target_player, final_dmg, game_state)
        
    return final_dmg, note, temp_absorbed, dmg_to_hp

def _apply_hp_change(target_player, new_hp_unbounded, game_state):
    """Gestisce variazioni dirette di HP (cure, comandi DM o statistiche)."""
    old_hp = target_player.hp
    excess_damage = 0
    if new_hp_unbounded < 0:
        excess_damage = abs(new_hp_unbounded)
    
    target_player.hp = max(0, min(target_player.max_hp, new_hp_unbounded))
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

def handle_start_combat_request(data, player, game_state):
    initiator_name = data.get("initiator")
    game_state.gui_queue.put({"type": "SHOW_COMBAT_CONFIG", "payload": {"initiator": initiator_name}})

def _trigger_concentration_check(target_player, dmg_val, game_state):
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
            
        if getattr(target_player, "conn", None):
            send_message(target_player.conn, make_prompt_save("COS", dc, "", False, "Sistema (Concentrazione)", "Contundente"))
        else:
            mod = 0
            if target_player.full_sheet:
                attr = target_player.full_sheet.get("attributes", {})
                if "COS" in attr:
                    try:
                        mod = (int(attr["COS"]) - 10) // 2
                    except (ValueError, TypeError):
                        pass
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            save_result = roll_dice(f"1d20{mod_str}")
            roll_tot = save_result["total"]
            is_crit = save_result["rolls"][0] == 20
            is_fail = save_result["rolls"][0] == 1
            threading.Timer(0.1, _process_save_result, args=(target_player.name, "COS", roll_tot, is_crit, is_fail, dc, "", False, "Sistema (Concentrazione)", game_state, "Contundente")).start()

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
        
        # 1. Fine Turno per prev_p
        if prev_p:
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
                            mod = 0
                            if getattr(prev_p, "full_sheet", None):
                                attr = prev_p.full_sheet.get("attributes", {})
                                stat_aliases = {
                                    "FOR": "FOR", "STR": "FOR",
                                    "DES": "DES", "DEX": "DES",
                                    "COS": "COS", "CON": "COS",
                                    "INT": "INT",
                                    "SAG": "SAG", "WIS": "SAG",
                                    "CAR": "CAR", "CHA": "CAR"
                                }
                                standard_stat = stat_aliases.get(stat, stat)
                                raw_val = 10
                                for k, v in attr.items():
                                    if stat_aliases.get(k.upper(), k.upper()) == standard_stat:
                                        try: raw_val = int(v); break
                                        except (ValueError, TypeError): pass
                                mod = (raw_val - 10) // 2
                                saves = prev_p.full_sheet.get("saving_throw_proficiencies", []) or prev_p.full_sheet.get("saving_throws", [])
                                if any(stat_aliases.get(str(s).upper(), str(s).upper()) == standard_stat for s in saves):
                                    prof = prev_p.full_sheet.get("proficiency_bonus", 2)
                                    try: mod += int(prof)
                                    except (ValueError, TypeError): mod += 2
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

            # D&D 5e Lair Actions: Se c'è una creatura con Azione di Tana a inizio round (Iniziativa 20)
            has_lair_boss = any(getattr(p, "has_lair_actions", False) for p in game_state.players)
            if has_lair_boss and game_state.turn_index == 0:
                lair_msg = "🏰 [AZIONE DI TANA - Iniziativa 20] La tana del Boss risponde alla volontà del suo padrone! Il DM può attivare un'Azione di Tana."
                broadcast(game_state, make_chat_broadcast("Sistema", lair_msg))
                game_state.log_dm_message(f"[BOSS] {lair_msg}")

            # Notifica al DM per Azioni Leggendarie disponibili a fine turno altrui
            for p in game_state.players:
                if getattr(p, "legendary_actions_max", 0) > 0 and getattr(p, "legendary_actions_current", 0) > 0 and p.name != next_p.name:
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
        
    cur_actions = getattr(boss, "legendary_actions_current", 0)
    max_actions = getattr(boss, "legendary_actions_max", 0)
    
    if cur_actions < cost:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Azioni leggendarie insufficienti: {cur_actions}/{max_actions} (richieste: {cost})."))
        return
        
    boss.legendary_actions_current = cur_actions - cost
    msg = f"👑 {boss.name} usa l'Azione Leggendaria '{action_name}' (Costo: {cost})! Azioni rimaste: {boss.legendary_actions_current}/{max_actions}."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
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

    is_reaction = data.get("is_reaction", False)
    if getattr(game_state, "combat_active", False) and strict_lock and not is_reaction:
        curr_turn = game_state.get_current_turn_player()
        if curr_turn and curr_turn.name != player.name:
            if player and getattr(player, "conn", None):
                send_message(player.conn, make_error_reply(f"Non è il tuo turno in combattimento! È il turno di {curr_turn.name}."))
            return
    
    try:
        # 1. Roll to Hit
        adv_reasons = []
        dis_reasons = []
        
        t_cond = getattr(target_player, "conditions", [])
        
        # Vantaggio per l'attaccante
        if is_condition_active(p_cond, "Invisibile"): adv_reasons.append("Invisibile")
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

                if dist_3d > max_range_hex:
                    if player and getattr(player, "conn", None):
                        send_message(player.conn, make_error_reply(f"Bersaglio oltre la gittata massima! ({int(max_range_hex * 5)} ft / {int(max_range_hex)} caselle)."))
                    return
                elif dist_3d > normal_range_hex:
                    dis_reasons.append(f"Oltre la Gittata Normale ({int(normal_range_hex * 5)} ft - Svantaggio)")

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
                        feats = [str(f).lower() for f in sheet.get("features", [])]
                        traits = [str(t).lower() for t in sheet.get("traits", [])]
                        all_text = " ".join(conds + feats + traits)
                        return "vista del diavolo" in all_text or "devil's sight" in all_text or "truesight" in all_text or "visione del vero" in all_text
                    
                    if getattr(entity_obj, "has_darkvision", None) is not None:
                        return bool(entity_obj.has_darkvision)
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
                        traits = [str(t).lower() for t in sheet.get("traits", [])]
                        if any("scurovisione" in t or "darkvision" in t for t in traits):
                            return True
                        feats = [str(f).lower() for f in sheet.get("features", [])]
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
        if auto_calc_adv and has_adv:
            base_roll = max(roll1, roll2)
            d20_detail = f"max({roll1}, {roll2})={base_roll}"
        elif auto_calc_adv and has_dis:
            base_roll = min(roll1, roll2)
            d20_detail = f"min({roll1}, {roll2})={base_roll}"
        else:
            base_roll = roll1
            d20_detail = str(base_roll)
            
        try:
            hit_roll = base_roll + int(hit_bonus)
        except ValueError:
            hit_roll = base_roll

        # Traccia munizioni impiegate per armi a distanza (D&D 5e PHB p. 146)
        w_lower = str(weapon_name).lower()
        is_ranged_att = bool(data.get("is_ranged")) or any(k in w_lower for k in ["arco", "bow", "balestra", "crossbow", "dardo", "dart", "fionda", "sling", "distanza", "ranged"])
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
        
        # 2. CA Bersaglio
        target_ac = 10
        if target_player.full_sheet:
            try:
                target_ac = int(target_player.full_sheet.get("ac", 10))
            except (ValueError, TypeError):
                pass
                
        scudo_applicato = False
        if has_effect_or_condition(target_player, "Scudo", "Shield"):
            target_ac += 5
            scudo_applicato = True

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
        if scudo_applicato:
            log_msg += " (Scudo +5 CA applicato)"
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
            if not is_crit and dist <= 1 and any(is_condition_active(t_cond, c) for c in ["Incosciente", "Paralizzato", "Unconscious", "Paralyzed"]):
                is_crit = True
                log_msg += " 🌟 (CRITICO AUTOMATICO: Bersaglio Incosciente/Paralizzato entro 1.5m!)"
            elif is_crit:
                log_msg += " 🌟 (CRITICO! 20 Naturale - Dadi danno raddoppiati!)"
            if damage_formula:
                dmg_result = roll_dice(damage_formula, is_crit=is_crit)
                dmg_val = max(0, dmg_result["total"])
                
                # Bonus danno Ira Barbarica (RAW 5e: solo attacchi in mischia che usano Forza, scalato col livello)
                if is_condition_active(getattr(player, "conditions", []), "Ira"):
                    barb_lvl = 1
                    if getattr(player, "full_sheet", None):
                        try: barb_lvl = int(player.full_sheet.get("level", 1))
                        except (ValueError, TypeError): barb_lvl = 1
                    rage_bonus = 2 if barb_lvl < 9 else (3 if barb_lvl < 16 else 4)
                    w_lower = str(weapon_name).lower()
                    if not (data.get("is_ranged") or any(k in w_lower for k in ["arco", "bow", "balestra", "crossbow", "fionda", "sling"])):
                        dmg_val += rage_bonus
                        log_msg += f" (+{rage_bonus} Ira Barbarica)"

                # Regola D&D 5e: Attacco Furtivo del Ladro (Sneak Attack)
                # Requisiti: classe Ladro, arma accurata/distanza, vantaggio OPPURE alleato entro 1 esagono senza svantaggio, max 1 volta per turno
                is_rogue = False
                rogue_lvl = 1
                if getattr(player, "full_sheet", None) or hasattr(player, "char_class"):
                    sheet = getattr(player, "full_sheet", {}) or {}
                    cls_name = str(sheet.get("class", sheet.get("char_class", getattr(player, "char_class", "")))).lower()
                    feat_obj = sheet.get("features", getattr(player, "features", []))
                    features_str = " ".join(str(f).lower() for f in feat_obj) if isinstance(feat_obj, list) else str(feat_obj).lower()
                    if "ladro" in cls_name or "rogue" in cls_name or "furtivo" in features_str or "sneak" in features_str:
                        is_rogue = True
                        try:
                            rogue_lvl = int(sheet.get("level", getattr(player, "level", 1)))
                        except (ValueError, TypeError):
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
                    
                auto_apply = True
                if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
                    auto_apply = game_state.automation_settings.get("auto_apply_damage", True)

                if auto_apply:
                    final_dmg, note, temp_absorbed, dmg_to_hp = apply_damage(target_player, dmg_val, damage_type, game_state, is_crit=is_crit)
                    log_msg += f" Danno: {final_dmg} ({damage_type}){note}."
                    if temp_absorbed > 0:
                        log_msg += f" [{temp_absorbed} assorbiti da Temp HP]."
                    log_msg += f" HP {target_name}: {target_player.hp}/{target_player.max_hp}"
                    if getattr(target_player, "temp_hp", 0) > 0:
                        log_msg += f" (+{target_player.temp_hp} Temp)"
                    
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
            
        game_state.log_dm_message(f"[COMBAT] {log_msg}")
        broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
        
    except Exception as e:
        send_message(player.conn, make_error_reply(f"Errore nell'attacco: {str(e)}"))

def _process_save_result(target_name, stat, roll_total, is_crit, is_fail, dc, damage_formula, half_on_success, source_name, game_state, damage_type="Fuoco", cover="none"):
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
    if stat in ("DES", "DEX"):
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
    
    # D&D 5e: Resistenze Leggendarie (es. 3/giorno)
    # Se la creatura fallisce un TS, può scegliere di considerarlo automaticamente un successo.
    used_legendary_resistance = False
    if not success and getattr(target_player, "legendary_resistances_current", 0) > 0:
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
        if source_name == "Sistema (Concentrazione)":
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
                if has_evasion:
                    dmg_val = 0
                    log_msg += " (Elusione 5e: 0 danni con TS superato!)"
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
                mod = 0
                s_map = {"STR": "FOR", "DEX": "DES", "CON": "COS", "INT": "INT", "WIS": "SAG", "CHA": "CAR"}
                c_stat = s_map.get(str(stat).upper(), str(stat).upper())
                if target_player.full_sheet:
                    sheet = target_player.full_sheet
                    # Verifica esplicita tiri salvezza dei mostri (es. {"DES": "+5"} o {"dex": 5})
                    st_dict = sheet.get("saving_throws", {})
                    found_st = False
                    if isinstance(st_dict, dict):
                        for k, v in st_dict.items():
                            if s_map.get(str(k).upper(), str(k).upper()) == c_stat:
                                try:
                                    mod = int(str(v).replace("+", "").strip())
                                    found_st = True
                                    break
                                except Exception:
                                    pass
                    if not found_st:
                        attr = sheet.get("attributes", {})
                        val = attr.get(c_stat, attr.get(stat))
                        if val is not None:
                            try: mod = (int(val) - 10) // 2
                            except (ValueError, TypeError): pass
                        prof_saves = [s_map.get(str(s).upper(), str(s).upper()) for s in sheet.get("saving_throw_proficiencies", [])]
                        if c_stat in prof_saves:
                            cr_or_lvl = sheet.get("cr", sheet.get("level", 1))
                            try: num = float(cr_or_lvl)
                            except Exception: num = 1.0
                            pb = 2 + max(0, int(num - 1) // 4)
                            mod += pb
                
                # Vantaggio ai TS su DES per Schivata
                if c_stat == "DES" and is_condition_active(getattr(target_player, "conditions", []), "Schivata"):
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
    target_name = data.get("target_name")
    if not target_name: return
    target_player = game_state.find_player(target_name)
    if not target_player: return
    if not hasattr(target_player, "conditions") or target_player.conditions is None:
        target_player.conditions = []
    if "Aiutato" not in target_player.conditions:
        target_player.conditions.append("Aiutato")
    player.has_acted_this_turn = True
    broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions, getattr(target_player, "temp_hp", 0)))
    broadcast(game_state, make_chat_broadcast("Sistema", f"🤝 {player.name} compie l'Azione di Aiuto contro {target_name}! Il prossimo attacco alleato contro {target_name} avrà Vantaggio."))
    game_state.log_dm_message(f"[COMBAT] {player.name} ha usato Aiuto contro {target_name}.")
    game_state._trigger_gui_update()

def _get_entity_ability_mod(entity, stat="FOR"):
    sheet = getattr(entity, "full_sheet", None) or {}
    attrs = sheet.get("attributes", {})
    val = attrs.get(stat, attrs.get("STR" if stat=="FOR" else ("DEX" if stat=="DES" else stat), 10))
    try:
        return (int(val) - 10) // 2
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
    att_dis = getattr(player, "exhaustion_level", 0) >= 1 or is_condition_active(p_cond, "Spaventato")
    
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
    def_dis = getattr(target_player, "exhaustion_level", 0) >= 1 or is_condition_active(def_cond, "Spaventato")
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
    att_dis = getattr(player, "exhaustion_level", 0) >= 1 or is_condition_active(p_cond, "Spaventato")
    
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
    def_dis = getattr(target_player, "exhaustion_level", 0) >= 1 or is_condition_active(def_cond, "Spaventato")
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
            
            # D&D 5e RAW: I Warlock ricaricano gli slot Patto (fino al 5° livello) con un Riposo Breve
            char_cls = str(sheet.get("char_class", "")).lower()
            if "warlock" in char_cls and isinstance(sheet.get("spell_slots"), dict):
                for sl_lvl, sl_info in sheet["spell_slots"].items():
                    try:
                        if int(sl_lvl) <= 5 and isinstance(sl_info, dict):
                            sl_info["current"] = sl_info.get("max", 0)
                    except (ValueError, TypeError):
                        pass

        if hp_rec > 0:
            player.hp = min(player.max_hp, player.hp + hp_rec)
            if sheet:
                sheet["hp_current"] = player.hp
            broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, getattr(player, "conditions", []), getattr(player, "temp_hp", 0)))
            game_state._trigger_gui_update()

    msg = f"☕ {player.name} ha completato un Riposo Breve (ha speso {hd_spent} Dado/i Vita e recuperato {hp_rec} HP)!"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    game_state.log_dm_message(f"[RIPOSO] {msg}")

def handle_reaction_response(data, player, game_state):
    """Gestisce la risposta del client a un prompt di reazione 5e (Attacco d'Opportunità, Scudo, ecc.)."""
    reaction_type = data.get("reaction_type")
    accepted = data.get("accepted", False)
    target_name = data.get("target_name")
    details = data.get("details", {})
    
    if not accepted or not player:
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
        
    elif reaction_type == "SHIELD_SPELL":
        conds = getattr(player, "conditions", [])
        if "Scudo" not in conds:
            conds.append("Scudo")
        msg = f"🛡️ {player.name} usa la propria REAZIONE per lanciare l'incantesimo Scudo! Ottiene +5 CA fino all'inizio del suo prossimo turno."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[REAZIONE] {msg}")
        broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
        game_state._trigger_gui_update()

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
    
    from server.rules.character import _apply_hp_change
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


