"""
server/rules/downtime.py - Attività di Tempo Libero (Downtime) e Stile di Vita (Lifestyle Expenses).
Basato su PHB p. 157, 187 e Xanathar's Guide to Everything (XGtE p. 123-134).
"""

from __future__ import annotations

import random
from typing import Any, Dict, Tuple

from common.network_utils import broadcast, send_message
from common.protocol import make_chat_broadcast, make_error_reply, make_game_state


LIFESTYLE_EXPENSES_GP: Dict[str, Tuple[str, float]] = {
    "wretched": ("Miserabile (Wretched)", 0.0),
    "squalid": ("Squallido (Squalid)", 0.1),
    "poor": ("Povero (Poor)", 0.2),
    "modest": ("Modesto (Modest)", 1.0),
    "comfortable": ("Confortevole (Comfortable)", 2.0),
    "wealthy": ("Agiato (Wealthy)", 4.0),
    "aristocratic": ("Aristocratico (Aristocratic)", 10.0),
}


def _deduct_gp(player: Any, cost_gp: float) -> Tuple[bool, float]:
    """Scala il costo in monete d'oro dal borsello (supporta pp/gp/ep/sp/cp) convertendo se necessario."""
    sheet = getattr(player, "full_sheet", None)
    curr = getattr(player, "currency", None)
    if not isinstance(curr, dict) and isinstance(sheet, dict):
        curr = sheet.get("currency")
    if not isinstance(curr, dict):
        return True, 0.0  # PG/NPC senza dizionario currency tracciato

    total_cp = (
        int(curr.get("pp", 0) or 0) * 1000
        + int(curr.get("gp", 0) or 0) * 100
        + int(curr.get("ep", 0) or 0) * 50
        + int(curr.get("sp", 0) or 0) * 10
        + int(curr.get("cp", 0) or 0)
    )
    need_cp = int(round(cost_gp * 100))
    if total_cp < need_cp:
        return False, total_cp / 100.0

    rem_cp = total_cp - need_cp
    curr["pp"] = 0
    curr["gp"] = rem_cp // 100
    rem_cp %= 100
    curr["sp"] = rem_cp // 10
    curr["cp"] = rem_cp % 10
    curr["ep"] = 0
    if isinstance(sheet, dict):
        sheet["currency"] = dict(curr)
    return True, curr["gp"] + curr["sp"] / 10.0 + curr["cp"] / 100.0


def resolve_downtime_activity(player: Any, data: Dict[str, Any], game_state: Any = None) -> Tuple[bool, str]:
    """
    Risolve un'attività di Tempo Libero (Downtime) PHB/XGtE:
    - activity: 'crafting' | 'training' | 'research' | 'work' | 'recuperating' | 'carousing' | 'gambling' | 'crime' | 'lifestyle'
    - days: numero di giorni (default 7 = 1 settimana lavorativa XGtE)
    - lifestyle: 'wretched'..'aristocratic' (default 'modest')
    """
    activity = str(data.get("activity", "work") or "work").strip().lower()
    days = max(1, int(data.get("days", 7) or 7))
    lifestyle = str(data.get("lifestyle", "modest") or "modest").strip().lower()
    if lifestyle not in LIFESTYLE_EXPENSES_GP:
        lifestyle = "modest"

    ls_label, ls_gp_day = LIFESTYLE_EXPENSES_GP[lifestyle]
    lifestyle_cost = round(ls_gp_day * days, 2)
    if activity == "work":
        # PHB p. 187: Esercitare una professione copre fino a stile di vita Modesto (Confortevole con Intrattenimento/Gilda)
        lifestyle_cost = max(0.0, lifestyle_cost - round(min(ls_gp_day, 2.0 if data.get("performance") else 1.0) * days, 2))

    extra_cost = 0.0
    detail = ""
    sheet = getattr(player, "full_sheet", None) or {}

    if activity == "crafting":
        # PHB p. 187: 5 mo/giorno di avanzamento (metà costo materiali); XGtE: 50 mo/settimana lavorativa
        item_name = str(data.get("item_name") or "Oggetto Artigianale").strip()
        item_val = max(5.0, float(data.get("item_value_gp", 50.0) or 50.0))
        rate_per_day = float(data.get("rate_gp_per_day", 5.0 if days < 5 else 50.0 / 5.0) or 5.0)
        progress_val = min(item_val, round(days * rate_per_day, 2))
        extra_cost = round(progress_val / 2.0, 2)
        if not hasattr(player, "downtime_projects") or not isinstance(player.downtime_projects, dict):
            player.downtime_projects = {}
        cur_p = float(player.downtime_projects.get(item_name, 0.0) or 0.0) + progress_val
        player.downtime_projects[item_name] = min(item_val, cur_p)
        if player.downtime_projects[item_name] >= item_val:
            detail = f"🔨 Forgia/Crea **{item_name}** ({item_val} mo completati! Oggetto pronto)."
        else:
            detail = f"🔨 Lavora su **{item_name}**: +{progress_val} mo ({player.downtime_projects[item_name]}/{item_val} mo)."

    elif activity == "training":
        # XGtE p. 134 / PHB p. 187: Addestramento (Linguaggio/Strumento), 25 mo/settimana
        skill_or_tool = str(data.get("target_proficiency") or "Nuovo Strumento/Linguaggio").strip()
        extra_cost = round((days / 7.0) * 25.0, 2)
        int_mod = (int((sheet.get("attributes") or {}).get("INT", 10) or 10) - 10) // 2
        needed_days = max(35, (10 - max(0, int_mod)) * 7) if data.get("use_xgte", True) else 250
        if not hasattr(player, "downtime_projects") or not isinstance(player.downtime_projects, dict):
            player.downtime_projects = {}
        key = f"train:{skill_or_tool}"
        done = int(player.downtime_projects.get(key, 0) or 0) + days
        player.downtime_projects[key] = done
        if done >= needed_days:
            detail = f"📚 Addestramento completato in **{skill_or_tool}** ({done}/{needed_days} giorni)!"
        else:
            detail = f"📚 Addestramento in **{skill_or_tool}**: {done}/{needed_days} giorni (costo {extra_cost} mo)."

    elif activity == "research":
        # XGtE p. 132: Ricerca informazioni con 50 mo base/settimana + prova INT
        topic = str(data.get("topic") or "Segreti Arcani").strip()
        extra_cost = round((days / 7.0) * 50.0, 2)
        int_mod = (int((sheet.get("attributes") or {}).get("INT", 10) or 10) - 10) // 2
        chk = random.randint(1, 20) + int_mod + min(4, int(extra_cost // 50))
        clues = 3 if chk >= 21 else (2 if chk >= 11 else (1 if chk >= 6 else 0))
        detail = f"📜 Ricerca su *«{topic}»*: Prova {chk} -> {clues} frammenti/indizi scoperti (spesi {extra_cost} mo)."

    elif activity == "recuperating":
        # PHB p. 187: almeno 3 giorni -> vantaggio TS vs malattie/veleni + cure accelerate
        player.conditions = [c for c in getattr(player, "conditions", []) if str(c).lower() not in ("malato", "avvelenato", "poisoned", "diseased")]
        if days >= 3:
            player.exhaustion_level = max(0, getattr(player, "exhaustion_level", 0) - days)
            player.hp = getattr(player, "max_hp", player.hp)
        detail = f"🛌 Convalescenza ({days} giorni): PF ripristinati, rimozione condizioni/indebolimento, vantaggio ai TS contro veleni e malattie."

    elif activity == "carousing":
        extra_cost = round((days / 7.0) * (10.0 if lifestyle in ("wretched", "squalid", "poor") else (50.0 if lifestyle in ("modest", "comfortable") else 250.0)), 2)
        cha_mod = (int((sheet.get("attributes") or {}).get("CAR", sheet.get("attributes", {}).get("CHA", 10)) or 10) - 10) // 2
        chk = random.randint(1, 20) + cha_mod
        contacts = 2 if chk >= 21 else (1 if chk >= 11 else 0)
        detail = f"🍻 Baldoria e Contatti (XGtE): Prova CAR {chk} -> {contacts} nuovo/i contatto/i alleato/i (spese {extra_cost} mo)."

    elif activity == "gambling":
        stake = max(5.0, float(data.get("stake_gp", 25.0) or 25.0))
        chk = random.randint(1, 20) + 2
        if chk >= 16:
            net = stake
            detail = f"🎲 Gioco d'Azzardo: Prova {chk} -> Vince +{net} mo!"
            extra_cost = -net
        elif chk >= 11:
            net = round(stake * 0.5, 2)
            detail = f"🎲 Gioco d'Azzardo: Prova {chk} -> Vince +{net} mo."
            extra_cost = -net
        else:
            extra_cost = stake
            detail = f"🎲 Gioco d'Azzardo: Prova {chk} -> Perde -{stake} mo."

    elif activity == "crime":
        chk = random.randint(1, 20) + 3
        if chk >= 20:
            loot = 200.0
            extra_cost = -loot
            detail = f"🗝️ Furto/Crimine (XGtE): Prova {chk} -> Colpo riuscito! (+{loot} mo)"
        elif chk >= 12:
            loot = 50.0
            extra_cost = -loot
            detail = f"🗝️ Furto/Crimine: Prova {chk} -> Colpo minore (+{loot} mo)."
        else:
            extra_cost = 50.0
            detail = f"🚨 Furto/Crimine: Prova {chk} -> Catturato! Multa/Cauzione {extra_cost} mo."

    else:
        detail = f"💼 Lavoro/Professione per {days} giorni: mantiene stile di vita {ls_label} senza perdite nette."

    total_cost = round(lifestyle_cost + extra_cost, 2)
    if total_cost > 0:
        ok_gp, rem = _deduct_gp(player, total_cost)
        if not ok_gp:
            return False, f"Fondi insufficienti per completare l'attività ({total_cost} mo richieste, disponibili {rem:.2f} mo)."
    elif total_cost < 0:
        sheet = getattr(player, "full_sheet", None)
        curr = getattr(player, "currency", None)
        if isinstance(curr, dict):
            curr["gp"] = int(curr.get("gp", 0) or 0) + int(abs(total_cost))
            if isinstance(sheet, dict):
                sheet["currency"] = dict(curr)

    if game_state and getattr(game_state, "automation_settings", {}).get("auto_advance_time", True) and hasattr(game_state, "advance_game_time"):
        game_state.advance_game_time(hours=days * 24)

    summary = f"⏳ **[TEMPO LIBERO - {days}g | Stile: {ls_label}]** {player.name}: {detail} (Costo netto: {total_cost} mo)"
    return True, summary


def handle_downtime_request(data, player, game_state):
    """Handler server per DOWNTIME_REQUEST."""
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    if not player:
        return
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    actor = actor or player

    ok, msg = resolve_downtime_activity(actor, data or {}, game_state)
    if not ok:
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(msg))
        return
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(f"[DOWNTIME] {msg}")
    game_state._trigger_gui_update()
