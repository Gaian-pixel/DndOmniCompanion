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


_XGTE_MAGIC_CRAFT_COSTS: Dict[str, Tuple[int, float]] = {
    "comune": (1, 50.0),
    "common": (1, 50.0),
    "non comune": (2, 200.0),
    "uncommon": (2, 200.0),
    "raro": (10, 2000.0),
    "rare": (10, 2000.0),
    "molto raro": (25, 20000.0),
    "very rare": (25, 20000.0),
    "leggendario": (50, 100000.0),
    "legendary": (50, 100000.0),
}

_XGTE_COMPLICATIONS: Tuple[str, ...] = (
    "Un rivale sabota o cerca di sottrarre il tuo lavoro o contatto.",
    "Voci esagerate sul tuo conto attirano curiosi o strozzini.",
    "Un fornitore o contatto richiede un favore imprevisto.",
    "Un incidente burocratico o tassa cittadina richiede 25 mo extra.",
    "L'oggetto o l'informazione presenta un difetto o un avvertimento nascosto.",
    "Un vecchio nemico scopre dove alloggi e ti osserva.",
)


def _norm_rarity_key(rarity: str) -> str:
    r = str(rarity or "non comune").strip().lower()
    if r in _XGTE_MAGIC_CRAFT_COSTS:
        return r
    return "non comune"


def resolve_downtime_activity(player: Any, data: Dict[str, Any], game_state: Any = None) -> Tuple[bool, str]:
    """
    Risolve un'attività di Tempo Libero (Downtime) PHB/XGtE:
    - activity: 'crafting' | 'crafting_magic' | 'buy_magic_item' | 'sell_magic_item' | 'pit_fighting'
      | 'religious_service' | 'training' | 'research' | 'work' | 'recuperating' | 'carousing'
      | 'gambling' | 'crime' | 'lifestyle'
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
    attrs = sheet.get("attributes") or {}
    str_mod = (int(attrs.get("FOR", attrs.get("STR", 10)) or 10) - 10) // 2
    dex_mod = (int(attrs.get("DES", attrs.get("DEX", 10)) or 10) - 10) // 2
    con_mod = (int(attrs.get("COS", attrs.get("CON", 10)) or 10) - 10) // 2
    cha_mod = (int(attrs.get("CAR", attrs.get("CHA", 10)) or 10) - 10) // 2

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

    elif activity in ("crafting_magic", "craft_magic_item"):
        # XGtE p. 128-129: settimane & costo totale per rarità (consumabile = metà)
        item_name = str(data.get("item_name") or "Oggetto Magico").strip()
        rk = _norm_rarity_key(data.get("rarity", "non comune"))
        req_weeks, req_gp = _XGTE_MAGIC_CRAFT_COSTS[rk]
        if data.get("consumable"):
            req_weeks = max(0.5, req_weeks / 2.0)
            req_gp = req_gp / 2.0
        weeks_done = max(0.25, days / 7.0)
        frac = min(1.0, weeks_done / max(0.5, float(req_weeks)))
        extra_cost = round(req_gp * frac, 2)
        if not hasattr(player, "downtime_projects") or not isinstance(player.downtime_projects, dict):
            player.downtime_projects = {}
        key = f"magic:{item_name}"
        cur_w = float(player.downtime_projects.get(key, 0.0) or 0.0) + weeks_done
        player.downtime_projects[key] = min(float(req_weeks), cur_w)
        if player.downtime_projects[key] >= req_weeks:
            detail = f"✨ Forgia Magica (XGtE p.128, {rk}) **{item_name}** COMPLETATA ({req_weeks} sett., {extra_cost} mo questa sessione)!"
        else:
            detail = f"✨ Forgia Magica (XGtE p.128, {rk}) **{item_name}**: {player.downtime_projects[key]:.1f}/{req_weeks} sett. (materiali {extra_cost} mo)."

    elif activity in ("buy_magic_item", "buying_magic"):
        # XGtE p. 126: 1 settimana + almeno 100 mo per ricerca + prova Persuasione (+1 ogni 100 mo extra)
        item_name = str(data.get("item_name") or "Oggetto Magico").strip()
        budget_extra = max(0.0, float(data.get("item_value_gp", 100.0) or 100.0) - 100.0)
        extra_cost = 100.0 + min(500.0, budget_extra)
        bonus = min(10, int(budget_extra // 100.0))
        d20 = int(data["forced_roll"]) if data.get("forced_roll") is not None else random.randint(1, 20)
        chk = d20 + cha_mod + bonus
        if chk >= 25:
            tier = "Tavola I (Leggendario/Molto Raro disponibile sul mercato)"
        elif chk >= 20:
            tier = "Tavola G/H (Raro / Molto Raro disponibile)"
        elif chk >= 15:
            tier = "Tavola D/E/F (Non Comune / Raro consumabile disponibile)"
        elif chk >= 10:
            tier = "Tavola A/B/C (Comune / Non Comune minore disponibile)"
        else:
            tier = "Nessun oggetto degno trovato questa settimana"
        detail = f"🛒 Ricerca Acquisto Magico (XGtE p.126) «{item_name}»: Persuasione {chk} -> {tier} (spese ricerca {extra_cost} mo)."

    elif activity in ("sell_magic_item", "selling_magic"):
        # XGtE p. 133: 1 settimana + 25 mo ricerca acquirente + prova Persuasione
        item_name = str(data.get("item_name") or "Oggetto Magico").strip()
        base_val = max(25.0, float(data.get("item_value_gp", 100.0) or 100.0))
        broker_fee = 25.0
        d20 = int(data["forced_roll"]) if data.get("forced_roll") is not None else random.randint(1, 20)
        chk = d20 + cha_mod
        if chk >= 21:
            mult, label = 1.5, "Offerta generosa (150%)"
        elif chk >= 11:
            mult, label = 1.0, "Prezzo pieno (100%)"
        else:
            mult, label = 0.5, "Offerta al ribasso (50%)"
        sale_gain = round(base_val * mult, 2)
        extra_cost = broker_fee - sale_gain
        detail = f"💎 Vendita Oggetto Magico (XGtE p.133) «{item_name}»: Persuasione {chk} -> {label} (+{sale_gain} mo, tassa {broker_fee} mo)."

    elif activity == "pit_fighting":
        # XGtE p. 131: 3 prove (Atletica/Acrobazia, COS, TxC) -> 0/1/2/3 vittorie => 0/50/100/200 mo
        forced = data.get("forced_wins")
        if forced is not None:
            wins = max(0, min(3, int(forced)))
        else:
            dc1, dc2, dc3 = 10 + random.randint(1, 10), 10 + random.randint(1, 10), 10 + random.randint(1, 10)
            c1 = random.randint(1, 20) + max(str_mod, dex_mod)
            c2 = random.randint(1, 20) + con_mod
            c3 = random.randint(1, 20) + max(str_mod, dex_mod) + 2
            wins = int(c1 >= dc1) + int(c2 >= dc2) + int(c3 >= dc3)
        purse = 200.0 if wins == 3 else (100.0 if wins == 2 else (50.0 if wins == 1 else 0.0))
        extra_cost = -purse
        detail = f"⚔️ Combattimento nell'Arena (XGtE p.131): {wins}/3 vittorie -> Borsa +{purse} mo!"

    elif activity == "religious_service":
        # XGtE p. 132: Servizio Religioso -> favori del tempio
        d20 = int(data["forced_roll"]) if data.get("forced_roll") is not None else random.randint(1, 20)
        chk = d20 + cha_mod
        favors = 2 if chk >= 21 else (1 if chk >= 11 else 0)
        detail = f"⛪ Servizio Religioso (XGtE p.132): Prova {chk} -> {favors} favore/i ottenuto/i dal tempio."

    elif activity == "lifestyle":
        detail = f"🏡 Solo mantenimento stile di vita {ls_label} per {days} giorni."

    else:
        detail = f"💼 Lavoro/Professione per {days} giorni: mantiene stile di vita {ls_label} senza perdite nette."

    comp_note = ""
    if (
        game_state
        and getattr(game_state, "automation_settings", {}).get("opt_xgte_downtime_complications", False)
        and not data.get("skip_complication", False)
    ):
        c_roll = int(data["forced_complication_roll"]) if data.get("forced_complication_roll") is not None else random.randint(1, 100)
        if c_roll <= 10:
            comp_note = f" ⚠️ Complicazione XGtE (d100={c_roll}): {random.choice(_XGTE_COMPLICATIONS)}"

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

    summary = f"⏳ **[TEMPO LIBERO - {days}g | Stile: {ls_label}]** {player.name}: {detail} (Costo netto: {total_cost} mo){comp_note}"
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
