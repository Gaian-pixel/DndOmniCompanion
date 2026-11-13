"""
common/spell_effects_engine.py
Motore unificato D&D 5e (PHB / XGtE) per:
- Tutte le 8 opzioni di Metamagia dello Stregone + costi reali (PHB p. 102)
- Tabella completa Impulsi di Magia Selvaggia (50 fasce d100, PHB p. 104) + Ondate di Caos
- Effetti meccanici runtime di 20+ incantesimi iconici PHB / XGtE
  (Absorb Elements, Hellish Rebuke, Silvery Barbs, Hunter's Mark, Hex,
   Mirror Image, Blur, Sanctuary, Armor of Agathys, Aid, Mage Armor, Shield of Faith,
   Greater Invisibility, Spiritual Weapon, Heat Metal, Hold Person, Web, Spike Growth,
   Hunger of Hadar, Wall of Fire).
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from common.dice import roll_dice
from common.dnd5e_tables import (
    entity_find_resource,
    entity_get_attr_mod,
    entity_get_class_level,
    entity_get_total_level,
    entity_has_keyword,
    entity_spend_resource,
)


# ==============================================================================
# 1. METAMAGIA STREGONE (PHB p. 102) & ADEPTO DELLA METAMAGIA (TCE)
# ==============================================================================

METAMAGIC_CATALOG: Dict[str, Dict[str, Any]] = {
    "careful": {
        "name_it": "Incantesimo Attento",
        "name_en": "Careful Spell",
        "cost": 1,
        "summary": "Fino a max(1, mod CAR) alleati superano automaticamente il TS iniziale.",
    },
    "distant": {
        "name_it": "Incantesimo Distante",
        "name_en": "Distant Spell",
        "cost": 1,
        "summary": "Raddoppia la gittata dell'incantesimo (o Contatto diventa 30 ft / 9 m).",
    },
    "empowered": {
        "name_it": "Incantesimo Potenziato",
        "name_en": "Empowered Spell",
        "cost": 1,
        "summary": "Ritira fino a max(1, mod CAR) dadi di danno; cumulabile con altra metamagia.",
    },
    "extended": {
        "name_it": "Incantesimo Esteso",
        "name_en": "Extended Spell",
        "cost": 1,
        "summary": "Raddoppia la durata dell'incantesimo (fino a un massimo di 24 ore).",
    },
    "heightened": {
        "name_it": "Incantesimo Intensificato",
        "name_en": "Heightened Spell",
        "cost": 3,
        "summary": "Un bersaglio subisce Svantaggio al primo TS contro l'incantesimo.",
    },
    "quickened": {
        "name_it": "Incantesimo Rapido",
        "name_en": "Quickened Spell",
        "cost": 2,
        "summary": "Riduce il tempo di lancio da 1 Azione a 1 Azione Bonus.",
    },
    "subtle": {
        "name_it": "Incantesimo Celato",
        "name_en": "Subtle Spell",
        "cost": 1,
        "summary": "Lancia senza componenti Verbali o Somatiche (aggira Silenzio e Controincantesimo).",
    },
    "twinned": {
        "name_it": "Incantesimo Raddoppiato",
        "name_en": "Twinned Spell",
        "cost": "level",
        "summary": "Bersaglia una seconda creatura con un incantesimo a bersaglio singolo non Personale.",
    },
}


def normalize_metamagic_key(raw: str) -> str:
    txt = str(raw or "").strip().lower()
    aliases = {
        "careful": ("careful", "attent"),
        "distant": ("distant", "distant", "lontan"),
        "empowered": ("empowered", "potenziat"),
        "extended": ("extended", "estes"),
        "heightened": ("heightened", "intensificat", "inasprit"),
        "quickened": ("quickened", "rapid", "veloce"),
        "subtle": ("subtle", "celat", "sottil"),
        "twinned": ("twinned", "raddoppiat", "gemellat"),
    }
    for key, pats in aliases.items():
        if any(p in txt for p in pats):
            return key
    return ""


def get_metamagic_cost(meta_key: str, spell_level: int = 1) -> int:
    key = normalize_metamagic_key(meta_key)
    entry = METAMAGIC_CATALOG.get(key)
    if not entry:
        return 1
    if entry["cost"] == "level":
        return max(1, int(spell_level or 0))
    return int(entry["cost"])


def can_use_metamagic(entity: Any) -> bool:
    if entity_get_class_level(entity, "stregone", "sorcerer") >= 3:
        return True
    if int(getattr(entity, "sorcery_points_max", 0) or 0) > 0:
        return True
    return entity_has_keyword(entity, "adepto della metamagia", "metamagic adept")


def spend_metamagic_points(caster: Any, meta_key: str, spell_level: int = 1) -> Tuple[bool, int, str]:
    key = normalize_metamagic_key(meta_key)
    if not key:
        return False, 0, "Opzione di Metamagia non riconosciuta."
    cost = get_metamagic_cost(key, spell_level)
    label = METAMAGIC_CATALOG[key]["name_it"]

    # 1. Prova metodo nativo Character.use_metamagic / sorcery_points_current
    if hasattr(caster, "sorcery_points_current") and getattr(caster, "sorcery_points_max", 0) > 0:
        cur = int(getattr(caster, "sorcery_points_current", 0) or 0)
        if cur < cost:
            return False, cur, f"Punti Stregoneria insufficienti per {label} (servono {cost}, hai {cur})."
        caster.sorcery_points_current = cur - cost
        res_sp = entity_find_resource(caster, "punti stregoneria", "sorcery points")
        if res_sp:
            res_sp["current"] = caster.sorcery_points_current
        return True, caster.sorcery_points_current, f"{label} (-{cost} PS, rimasti {caster.sorcery_points_current})"

    # 2. Altrimenti gestisci via custom_resources (Player / NPC)
    ok, rem, _mx = entity_spend_resource(caster, ("punti stregoneria", "sorcery points"), cost)
    if not ok:
        return False, rem, f"Punti Stregoneria insufficienti per {label} (servono {cost})."
    return True, rem, f"{label} (-{cost} PS, rimasti {rem})"


def apply_metamagic_to_cast(caster: Any, spell_dict: Dict[str, Any], meta_key: str, cast_level: int) -> Dict[str, Any]:
    """Applica gli effetti meccanici della Metamagia a un lancio di incantesimo."""
    key = normalize_metamagic_key(meta_key)
    if not key:
        return {"ok": False, "key": "", "note": ""}

    label = METAMAGIC_CATALOG[key]["name_it"]
    meta: Dict[str, Any] = {
        "ok": True,
        "key": key,
        "label": label,
        "bypasses_verbal_somatic": key == "subtle",
        "quickened_bonus_action": key == "quickened",
        "duration_multiplier": 2 if key == "extended" else 1,
        "range_multiplier": 2 if key == "distant" else 1,
        "heightened_disadvantage": key == "heightened",
        "careful_auto_save": key == "careful",
        "twinned_extra_target": key == "twinned",
        "empowered_rerolls": max(1, entity_get_attr_mod(caster, "CAR")) if key == "empowered" else 0,
        "note": f"✨ [METAMAGIA: {label}] {METAMAGIC_CATALOG[key]['summary']}",
    }
    if key == "distant":
        rng_txt = str(spell_dict.get("range", "") or "").lower()
        if any(k in rng_txt for k in ("contatto", "touch")):
            meta["modified_range"] = "30 ft (9 m)"
    return meta


# ==============================================================================
# 2. TABELLA IMPULSI DI MAGIA SELVAGGIA (PHB p. 104 - 50 fasce d100)
# ==============================================================================

WILD_MAGIC_SURGE_TABLE: List[Tuple[int, int, str, str]] = [
    (1, 2, "Tiri su questa tabella all'inizio di ogni tuo turno per il prossimo minuto (ignorando questo risultato).", "recurring_surge"),
    (3, 4, "Per il prossimo minuto puoi vedere qualsiasi creatura invisibile entro la tua visuale.", "see_invisibility"),
    (5, 6, "Un modron scelto dal DM appare in uno spazio libero entro 1,5 m per 1 minuto.", "summon_modron"),
    (7, 8, "Lanci Palla di Fuoco di 3° livello centrata su te stesso!", "fireball_self"),
    (9, 10, "Lanci Dardo Incantato di 5° livello contro bersagli casuali.", "magic_missile_5"),
    (11, 12, "Tira 1d10: la tua altezza varia di tanti pollici (pari aumenta, dispari diminuisce).", "height_shift"),
    (13, 14, "Lanci Confusione centrata su te stesso.", "confusion_self"),
    (15, 16, "Per il prossimo minuto recuperi 5 PF all'inizio di ciascuno dei tuoi turni.", "regen_5"),
    (17, 18, "Ti cresce una lunga barba di piume finché non starnutisci.", "feather_beard"),
    (19, 20, "Lanci Unto centrato su te stesso.", "grease_self"),
    (21, 22, "Le creature hanno Svantaggio ai TS contro il prossimo incantesimo che lanci entro 1 minuto.", "disadv_next_save"),
    (23, 24, "La tua pelle assume una tonalità blu brillante finché Rimuovi Maledizione non viene lanciato.", "blue_skin"),
    (25, 26, "Un terzo occhio appare sulla tua fronte: Vantaggio alle prove di Percezione per 1 minuto.", "third_eye"),
    (27, 28, "Per il prossimo minuto tutti gli incantesimi con tempo 1 Azione richiedono invece 1 Azione Bonus.", "quicken_aura"),
    (29, 30, "Ti teletrasporti fino a 18 m (60 ft) in uno spazio libero visibile.", "teleport_60"),
    (31, 32, "Vieni trasportato nel Piano Astrale fino alla fine del tuo prossimo turno.", "astral_blink"),
    (33, 34, "Massimizza i danni del prossimo incantesimo dannoso lanciato entro 1 minuto!", "max_damage_next"),
    (35, 36, "Tira 1d10: la tua età cambia di tanti anni (dispari ringiovanisci, pari invecchi).", "age_shift"),
    (37, 38, "1d6 flumph spaventati compaiono entro 18 m e scappano dopo 1 minuto.", "flumphs"),
    (39, 40, "Recuperi 2d10 Punti Ferita immediatamente!", "heal_2d10"),
    (41, 42, "Ti trasformi in una pianta in vaso fino all'inizio del tuo prossimo turno.", "potted_plant"),
    (43, 44, "Per il prossimo minuto puoi teletrasportarti fino a 6 m come Azione Bonus.", "misty_bonus"),
    (45, 46, "Lanci Levitazione su te stesso.", "levitate_self"),
    (47, 48, "Un unicorno controllato dal DM appare entro 1,5 m per 1 minuto.", "summon_unicorn"),
    (49, 50, "Non puoi parlare per il prossimo minuto: emetti solo bolle rosa dalla bocca.", "pink_bubbles"),
    (51, 52, "Uno scudo spettrale fluttua intorno a te: +2 CA e immunità a Dardo Incantato per 1 minuto.", "spectral_shield"),
    (53, 54, "Sei immune all'ubriachezza da alcol per i prossimi 5d6 giorni.", "alcohol_immunity"),
    (55, 56, "Tutti i tuoi capelli cadono ma ricrescono entro 24 ore.", "hair_loss"),
    (57, 58, "Per il prossimo minuto qualsiasi oggetto infiammabile toccato prende fuoco.", "fiery_touch"),
    (59, 60, "Recuperi il tuo slot incantesimo speso di livello più basso!", "regain_slot"),
    (61, 62, "Per il prossimo minuto urli a squarciagola ogni volta che parli.", "shouting"),
    (63, 64, "Lanci Nebbia Obscurante centrata su te stesso.", "fog_cloud_self"),
    (65, 66, "Fino a 3 creature scelte entro 9 m subiscono 4d10 danni da Fulmine.", "lightning_4d10"),
    (67, 68, "Sei Spaventato dalla creatura più vicina fino alla fine del tuo prossimo turno.", "frightened_nearest"),
    (69, 70, "Ogni creatura entro 9 m diventa Invisibile per 1 minuto (termina se attacca/lancia).", "mass_invis"),
    (71, 72, "Ottieni Resistenza a tutti i danni per il prossimo minuto!", "resist_all"),
    (73, 74, "Una creatura casuale entro 18 m è Avvelenata per 1d4 ore.", "poison_random"),
    (75, 76, "Emetti luce intensa per 9 m per 1 minuto; chi inizia il turno entro 1,5 m è Accecato.", "bright_aura"),
    (77, 78, "Lanci Metamorfosi su te stesso trasformandoti in una pecora (se fallisci TS).", "sheep_self"),
    (79, 80, "Sciami di farfalle illusorie e petali fluttuano entro 3 m da te per 1 minuto.", "butterflies"),
    (81, 82, "Puoi compiere una Azione aggiuntiva immediatamente in questo turno!", "extra_action"),
    (83, 84, "Ogni creatura entro 9 m subisce 1d10 danni Necrotici; tu recuperi pari PF!", "necrotic_drain"),
    (85, 86, "Lanci Immagine Speculare su te stesso!", "mirror_image_self"),
    (87, 88, "Lanci Volare su una creatura casuale entro 18 m.", "fly_random"),
    (89, 90, "Diventi Invisibile per il prossimo minuto (non puoi essere udito o visto finché non attacchi).", "invis_self"),
    (91, 92, "Se muori entro il prossimo minuto, torni immediatamente in vita tramite Reincarnazione.", "reincarnate_ward"),
    (93, 94, "La tua taglia aumenta di una categoria per il prossimo minuto.", "enlarge_self"),
    (95, 96, "Tu e tutte le creature entro 9 m diventate vulnerabili ai danni Perforanti per 1 minuto.", "vuln_piercing"),
    (97, 98, "Una musica eterea e lieve ti circonda per 1 minuto.", "ethereal_music"),
    (99, 100, "Recuperi TUTTI i Punti Stregoneria spesi!", "regain_all_sp"),
]


def is_wild_magic_sorcerer(entity: Any) -> bool:
    sub = str(getattr(entity, "subclass", "") or "").lower()
    if any(k in sub for k in ("magia selvaggia", "wild magic", "selvaggia")):
        return True
    return entity_has_keyword(entity, "impulso di magia selvaggia", "wild magic surge")


def lookup_wild_magic_entry(d100_roll: int) -> Tuple[str, str]:
    r = max(1, min(100, int(d100_roll)))
    for lo, hi, desc, code in WILD_MAGIC_SURGE_TABLE:
        if lo <= r <= hi:
            return desc, code
    return WILD_MAGIC_SURGE_TABLE[-1][2], WILD_MAGIC_SURGE_TABLE[-1][3]


def maybe_trigger_wild_magic_surge(
    caster: Any,
    spell_level: int,
    game_state: Any = None,
    forced_d20: Optional[int] = None,
    forced_d100: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    PHB p. 103: quando uno Stregone della Magia Selvaggia lancia un incantesimo di 1°+ livello,
    tira 1d20 -> con 1 (o automaticamente se Ondate di Caos attive) si scatena un Impulso 1d100.
    """
    if not caster or int(spell_level or 0) < 1 or not is_wild_magic_sorcerer(caster):
        return None
    if game_state and isinstance(getattr(game_state, "automation_settings", None), dict):
        if game_state.automation_settings.get("opt_wild_magic_surge", True) is False:
            return None

    tides_pending = bool(getattr(caster, "wild_magic_tides_used", False))
    d20 = int(forced_d20) if forced_d20 is not None else random.randint(1, 20)
    if not tides_pending and d20 != 1:
        return {"triggered": False, "d20": d20}

    d100 = int(forced_d100) if forced_d100 is not None else random.randint(1, 100)
    desc, code = lookup_wild_magic_entry(d100)
    if tides_pending:
        caster.wild_magic_tides_used = False

    note_extra = ""
    if code == "heal_2d10":
        heal_amt = roll_dice("2d10")["total"]
        old_hp = int(getattr(caster, "hp", getattr(caster, "hp_current", 0)) or 0)
        mx_hp = int(getattr(caster, "max_hp", getattr(caster, "hp_max", old_hp)) or old_hp)
        new_hp = min(mx_hp, old_hp + heal_amt)
        if hasattr(caster, "hp"):
            caster.hp = new_hp
        if hasattr(caster, "hp_current"):
            caster.hp_current = new_hp
        note_extra = f" (+{new_hp - old_hp} PF -> {new_hp}/{mx_hp})"
    elif code == "regain_all_sp":
        if hasattr(caster, "sorcery_points_max") and int(getattr(caster, "sorcery_points_max", 0) or 0) > 0:
            caster.sorcery_points_current = caster.sorcery_points_max
        res_sp = entity_find_resource(caster, "punti stregoneria", "sorcery points")
        if res_sp:
            res_sp["current"] = res_sp.get("max", res_sp.get("current", 0))
        note_extra = " (Tutti i PS ripristinati!)"
    elif code == "regain_slot":
        slots = getattr(caster, "spell_slots", None)
        if not isinstance(slots, dict) and isinstance(getattr(caster, "full_sheet", None), dict):
            slots = caster.full_sheet.get("spell_slots")
        if isinstance(slots, dict):
            for lk in sorted([int(k) for k in slots.keys() if str(k).isdigit()]):
                sl = slots.get(str(lk))
                if isinstance(sl, dict) and sl.get("current", 0) < sl.get("max", 0):
                    sl["current"] += 1
                    note_extra = f" (+1 slot di {lk}° liv.)"
                    break
    elif code == "max_damage_next":
        caster.wild_magic_max_damage_next = True
    elif code == "spectral_shield":
        if hasattr(caster, "add_effect"):
            caster.add_effect({"id": "wild_spectral_shield", "name": "Scudo Spettrale Selvaggio (+2 CA)", "duration_rounds": 10})
    elif code == "mirror_image_self":
        caster.mirror_images = 3
    elif code == "invis_self":
        conds = getattr(caster, "conditions", None)
        if isinstance(conds, list) and "Invisibile" not in conds:
            conds.append("Invisibile")
    elif code == "resist_all":
        caster.wild_magic_resist_all = True
    elif code == "fireball_self" and game_state is not None:
        from server.rules.combat import apply_damage
        fb_dmg = roll_dice("8d6")["total"]
        dc_fb = 8 + entity_get_attr_mod(caster, "CAR") + ((entity_get_total_level(caster) - 1) // 4 + 2)
        dex_m = entity_get_attr_mod(caster, "DES")
        sr = roll_dice(f"1d20{'+' if dex_m >= 0 else ''}{dex_m}")["total"]
        raw = fb_dmg // 2 if sr >= dc_fb else fb_dmg
        fd, _, _, _ = apply_damage(caster, raw, damage_type="Fuoco", game_state=game_state, is_spell=True)
        note_extra = f" (TS DES {sr} vs CD {dc_fb}: {fd} danni da Fuoco!)"

    msg = (
        f"🌀 [MAGIA SELVAGGIA! d100={d100}] "
        f"({('Ondata di Caos scaricata' if tides_pending else f'd20={d20}')}) "
        f"{caster.name}: {desc}{note_extra}"
    )
    return {
        "triggered": True,
        "d20": d20,
        "d100": d100,
        "code": code,
        "desc": desc,
        "message": msg,
    }


# ==============================================================================
# 3. 20+ INCANTESIMI ICONICI PHB / XGtE (RUNTIME)
# ==============================================================================

ICONIC_SPELL_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("absorb_elements", ("assorbire elementi", "absorb elements")),
    ("hellish_rebuke", ("intimorire infernale", "hellish rebuke")),
    ("silvery_barbs", ("beffa argentea", "silvery barbs")),
    ("hunters_mark", ("marchio del cacciatore", "hunter's mark", "hunters mark")),
    ("hex", ("sortilegio", "maledizione (hex)", "hex")),
    ("mirror_image", ("immagine speculare", "mirror image")),
    ("blur", ("sfocatura", "blur")),
    ("sanctuary", ("santuario", "sanctuary")),
    ("armor_of_agathys", ("armatura di agathys", "armor of agathys")),
    ("aid", ("aiuto (aid)", "aiuto", "aid")),
    ("mage_armor", ("armatura magica", "mage armor")),
    ("shield_of_faith", ("scudo della fede", "shield of faith")),
    ("greater_invisibility", ("invisibilità superiore", "invisibilita superiore", "greater invisibility")),
    ("spiritual_weapon", ("arma spirituale", "spiritual weapon")),
    ("heat_metal", ("riscaldare il metallo", "heat metal")),
    ("hold_person", ("blocca persone", "hold person")),
    ("web", ("ragnatela", "web")),
    ("spike_growth", ("crescita di spine", "spike growth")),
    ("hunger_of_hadar", ("fame di hadar", "hunger of hadar")),
    ("wall_of_fire", ("muro di fuoco", "wall of fire")),
)


def identify_iconic_spell(spell_name: str) -> Optional[str]:
    low = str(spell_name or "").strip().lower()
    if not low:
        return None
    for key, aliases in ICONIC_SPELL_KEYWORDS:
        for a in aliases:
            if a == "aid" and low != "aid":
                continue
            if a == "aiuto" and low not in ("aiuto", "aiuto (aid)"):
                continue
            if a == "hex" and low not in ("hex", "sortilegio", "sortilegio (hex)"):
                continue
            if a == "web" and low not in ("web", "ragnatela"):
                continue
            if a in low:
                return key
    return None


def _entity_spell_dc(actor: Any) -> int:
    lvl = entity_get_total_level(actor)
    pb = ((lvl - 1) // 4) + 2
    mods = [entity_get_attr_mod(actor, s) for s in ("INT", "SAG", "CAR")]
    return 8 + pb + max(mods)


def _sync_player(entity: Any) -> None:
    fs = getattr(entity, "full_sheet", None)
    if isinstance(fs, dict):
        if hasattr(entity, "conditions"):
            fs["conditions"] = list(entity.conditions)
        if hasattr(entity, "temp_hp"):
            fs["temp_hp"] = getattr(entity, "temp_hp", 0)
        if hasattr(entity, "hp"):
            fs["hp_current"] = entity.hp
        if hasattr(entity, "max_hp"):
            fs["hp_max"] = entity.max_hp


def cast_iconic_spell(
    actor: Any,
    target: Any,
    spell_name: str,
    cast_level: int,
    game_state: Any = None,
    damage_type: str = "Fuoco",
    metamagic_key: str = "",
) -> Optional[str]:
    """
    Esegue gli effetti runtime di 20+ incantesimi iconici PHB/XGtE.
    Ritorna una stringa narrativa di sistema se l'incantesimo è riconosciuto, altrimenti None.
    """
    key = identify_iconic_spell(spell_name)
    if not key or not actor:
        return None
    tgt = target or actor
    dc = _entity_spell_dc(actor)
    lvl = max(1, int(cast_level or 1))
    dur_mult = 2 if normalize_metamagic_key(metamagic_key) == "extended" else 1
    heightened = (normalize_metamagic_key(metamagic_key) == "heightened")

    if key == "mage_armor":
        dex_m = entity_get_attr_mod(tgt, "DES")
        new_ac = 13 + dex_m
        tgt.mage_armor_active = True
        if getattr(tgt, "ac", 10) < new_ac:
            tgt.ac = new_ac
        if hasattr(tgt, "add_effect"):
            tgt.add_effect({"id": "mage_armor", "name": f"Armatura Magica (CA {new_ac})", "duration_rounds": 4800 * dur_mult})
        _sync_player(tgt)
        return f"🛡️ [ARMATURA MAGICA] {tgt.name} avvolto da forza protettiva (CA base 13+DES = {new_ac}, durata 8 ore)."

    if key == "shield_of_faith":
        tgt.ac = int(getattr(tgt, "ac", 10) or 10) + 2
        if hasattr(tgt, "add_effect"):
            tgt.add_effect({"id": "shield_of_faith", "name": "Scudo della Fede (+2 CA)", "duration_rounds": 100 * dur_mult, "source": actor.name})
        actor.concentrating_on = "Scudo della Fede"
        return f"✨ [SCUDO DELLA FEDE] {tgt.name} ottiene +2 alla CA (ora {tgt.ac}) finché {actor.name} mantiene Concentrazione!"

    if key == "aid":
        bonus_hp = 5 * max(1, lvl - 1) if lvl >= 2 else 5
        boosted = []
        party = [p for p in getattr(game_state, "players", [tgt]) if getattr(p, "is_party_member", True) == getattr(actor, "is_party_member", True)][:3]
        if tgt not in party:
            party = [tgt]
        for al in party:
            al.max_hp = int(getattr(al, "max_hp", 10) or 10) + bonus_hp
            al.hp = int(getattr(al, "hp", 10) or 10) + bonus_hp
            al.aid_bonus_hp = bonus_hp
            if hasattr(al, "add_effect"):
                al.add_effect({"id": "aid", "name": f"Aiuto (+{bonus_hp} PV max)", "duration_rounds": 4800 * dur_mult})
            _sync_player(al)
            boosted.append(al.name)
        return f"💛 [AIUTO Lv.{lvl}] {', '.join(boosted)} guadagnano +{bonus_hp} PV massimi e attuali per 8 ore!"

    if key == "armor_of_agathys":
        thp = 5 * lvl
        actor.temp_hp = max(int(getattr(actor, "temp_hp", 0) or 0), thp)
        actor.agathys_cold_dmg = thp
        if hasattr(actor, "add_effect"):
            actor.add_effect({"id": "armor_of_agathys", "name": f"Armatura di Agathys ({thp} PF Temp / {thp} Freddo)", "duration_rounds": 600 * dur_mult})
        _sync_player(actor)
        return f"❄️ [ARMATURA DI AGATHYS Lv.{lvl}] {actor.name} ottiene {actor.temp_hp} PF Temporanei: ogni attaccante in mischia subisce {thp} danni da Freddo finché resistono!"

    if key == "mirror_image":
        actor.mirror_images = 3
        if hasattr(actor, "add_effect"):
            actor.add_effect({"id": "mirror_image", "name": "Immagine Speculare (3 copie)", "duration_rounds": 10 * dur_mult})
        return f"🪞 [IMMAGINE SPECULARE] 3 duplicati illusori compaiono attorno a {actor.name} (CA copie: {10 + entity_get_attr_mod(actor, 'DES')})!"

    if key == "blur":
        actor.blur_active = True
        actor.concentrating_on = "Sfocatura"
        if hasattr(actor, "add_effect"):
            actor.add_effect({"id": "blur", "name": "Sfocatura (Svantaggio TpC nemici)", "duration_rounds": 10 * dur_mult})
        return f"🌫️ [SFOCATURA] I contorni di {actor.name} si fanno confusi: gli attacchi contro di lui hanno Svantaggio!"

    if key == "sanctuary":
        tgt.sanctuary_dc = dc
        if hasattr(tgt, "add_effect"):
            tgt.add_effect({"id": "sanctuary", "name": f"Santuario (CD {dc} SAG)", "duration_rounds": 10 * dur_mult})
        return f"🕊️ [SANTUARIO] {tgt.name} è protetto: chi vuole attaccarlo o bersagliarlo con incantesimo nocivo deve superare TS SAG CD {dc}!"

    if key == "greater_invisibility":
        tgt.greater_invisibility = True
        actor.concentrating_on = "Invisibilità Superiore"
        conds = getattr(tgt, "conditions", None)
        if isinstance(conds, list) and "Invisibile" not in conds:
            conds.append("Invisibile")
        if hasattr(tgt, "add_effect"):
            tgt.add_effect({"id": "greater_invisibility", "name": "Invisibilità Superiore", "duration_rounds": 10 * dur_mult, "source": actor.name})
        _sync_player(tgt)
        return f"👻 [INVISIBILITÀ SUPERIORE] {tgt.name} diventa Invisibile per 1 minuto anche mentre attacca o lancia incantesimi!"

    if key == "hunters_mark":
        actor.hunters_mark_target = tgt.name
        actor.concentrating_on = "Marchio del Cacciatore"
        if hasattr(tgt, "add_effect"):
            tgt.add_effect({"id": "hunters_mark", "name": f"Marchiato da {actor.name} (+1d6)", "duration_rounds": 600 * dur_mult, "source": actor.name})
        return f"🎯 [MARCHIO DEL CACCIATORE] {actor.name} marchia {tgt.name}: +1d6 danni aggiuntivi con attacchi con arma!"

    if key == "hex":
        actor.hex_target = tgt.name
        actor.concentrating_on = "Sortilegio (Hex)"
        if hasattr(tgt, "add_effect"):
            tgt.add_effect({"id": "hex", "name": f"Maledetto (Hex +1d6 Necrotico)", "duration_rounds": 600 * dur_mult, "source": actor.name})
        return f"🕯️ [SORTILEGIO (HEX)] {actor.name} maledice {tgt.name}: +1d6 danni Necrotici per ogni colpo a segno e svantaggio alle prove di caratteristica!"

    if key == "absorb_elements":
        actor.absorb_elements_type = damage_type
        actor.absorb_elements_dice = lvl
        actor.reaction_used_this_turn = True
        if hasattr(actor, "add_effect"):
            actor.add_effect({"id": "absorb_elements", "name": f"Assorbire Elementi ({damage_type}, +{lvl}d6)", "duration_rounds": 1})
        return f"🛡️ [ASSORBIRE ELEMENTI Lv.{lvl}] {actor.name} assorbe energia {damage_type} (Resistenza fino al prossimo turno e +{lvl}d6 al prossimo attacco in mischia)!"

    if key == "hellish_rebuke":
        actor.reaction_used_this_turn = True
        dice_cnt = lvl + 1
        dmg_r = roll_dice(f"{dice_cnt}d10")
        from common.item_modifiers import get_effective_save_bonus_from_dict
        dex_m = get_effective_save_bonus_from_dict(tgt, "DES")
        r1 = roll_dice(f"1d20{'+' if dex_m >= 0 else ''}{dex_m}")["total"]
        r2 = roll_dice(f"1d20{'+' if dex_m >= 0 else ''}{dex_m}")["total"] if heightened else r1
        sr = min(r1, r2) if heightened else r1
        raw = dmg_r["total"] // 2 if sr >= dc else dmg_r["total"]
        fd = raw
        if game_state is not None:
            from server.rules.combat import apply_damage
            fd, _, _, _ = apply_damage(tgt, raw, damage_type="Fuoco", game_state=game_state, is_spell=True)
        return f"🔥 [INTIMORIRE INFERNALE Lv.{lvl} - CD {dc} DES] {tgt.name} tira {sr} ({'1/2' if sr >= dc else 'pieno'}): subisce {fd} danni da Fuoco!"

    if key == "silvery_barbs":
        actor.reaction_used_this_turn = True
        tgt.silvery_barbs_disadvantage = True
        actor.silvery_advantage = True
        return f"✨ [BEFFA ARGENTEA (Reaction)] {actor.name} costringe {tgt.name} a ritirare il d20 (tenendo il risultato minore) e concede Vantaggio al prossimo d20!"

    if key == "spiritual_weapon":
        lvl_dice = 1 + max(0, (lvl - 2) // 2)
        mod_w = max(entity_get_attr_mod(actor, "SAG"), entity_get_attr_mod(actor, "CAR"), entity_get_attr_mod(actor, "INT"))
        pb = ((entity_get_total_level(actor) - 1) // 4) + 2
        atk_b = mod_w + pb
        atk_r = roll_dice(f"1d20{'+' if atk_b >= 0 else ''}{atk_b}")
        is_c = (atk_r.get("natural_roll") == 20)
        tgt_ac = getattr(tgt, "ac", 12)
        actor.spiritual_weapon_level = lvl
        actor.bonus_action_used_this_turn = True
        if is_c or (atk_r.get("natural_roll") != 1 and atk_r["total"] >= tgt_ac):
            d_r = roll_dice(f"{lvl_dice}d8+{mod_w}", is_crit=is_c)
            fd = d_r["total"]
            if game_state is not None and tgt is not actor:
                from server.rules.combat import apply_damage
                fd, _, _, _ = apply_damage(tgt, fd, damage_type="Forza", game_state=game_state, is_crit=is_c, is_spell=True)
            return f"⚔️ [ARMA SPIRITUALE Lv.{lvl}] TxC {atk_r['total']} vs CA {tgt_ac} -> COLPITO {tgt.name} per {fd} danni da Forza{' 🌟CRIT!' if is_c else ''}!"
        return f"⚔️ [ARMA SPIRITUALE Lv.{lvl}] TxC {atk_r['total']} vs CA {tgt_ac} -> MANCATO {tgt.name}."

    if key == "hold_person":
        actor.concentrating_on = "Blocca Persone"
        from common.item_modifiers import get_effective_save_bonus_from_dict
        wis_m = get_effective_save_bonus_from_dict(tgt, "SAG")
        r1 = roll_dice(f"1d20{'+' if wis_m >= 0 else ''}{wis_m}")["total"]
        r2 = roll_dice(f"1d20{'+' if wis_m >= 0 else ''}{wis_m}")["total"] if heightened else r1
        sr = min(r1, r2) if heightened else r1
        if sr >= dc:
            return f"⚡ [BLOCCA PERSONE - CD {dc} SAG] {tgt.name} resiste con TS {sr}!"
        conds = getattr(tgt, "conditions", None)
        if isinstance(conds, list) and "Paralizzato" not in conds:
            conds.append("Paralizzato")
        if hasattr(tgt, "add_effect"):
            tgt.add_effect({"id": "hold_person", "name": "Paralizzato (Blocca Persone)", "duration_rounds": 10 * dur_mult, "save_ends": {"stat": "SAG", "dc": dc, "timing": "end_of_turn"}, "source": actor.name})
        _sync_player(tgt)
        return f"🥶 [BLOCCA PERSONE - CD {dc} SAG] {tgt.name} fallisce il TS ({sr}) ed è PARALIZZATO (attacchi entro 1,5m sono Critici automatici)!"

    if key == "heat_metal":
        actor.concentrating_on = "Riscaldare il Metallo"
        dice_cnt = 2 + max(0, lvl - 2)
        d_r = roll_dice(f"{dice_cnt}d8")
        fd = d_r["total"]
        if game_state is not None:
            from server.rules.combat import apply_damage
            fd, _, _, _ = apply_damage(tgt, fd, damage_type="Fuoco", game_state=game_state, is_spell=True)
        from common.item_modifiers import get_effective_save_bonus_from_dict
        con_m = get_effective_save_bonus_from_dict(tgt, "COS")
        sr = roll_dice(f"1d20{'+' if con_m >= 0 else ''}{con_m}")["total"]
        if hasattr(tgt, "add_effect"):
            tgt.add_effect({"id": "heat_metal", "name": f"Metallo Incandescente ({dice_cnt}d8 Fuoco/turno)", "duration_rounds": 10 * dur_mult, "dot_damage": f"{dice_cnt}d8", "dot_type": "Fuoco", "source": actor.name})
        drop_txt = "lascia cadere l'oggetto o subisce Svantaggio ai TpC/prove!" if sr < dc else "mantiene la presa nonostante il dolore."
        return f"🔥 [RISCALDARE IL METALLO Lv.{lvl}] {tgt.name} subisce {fd} danni da Fuoco e (TS COS {sr} vs CD {dc}) {drop_txt}"

    if key in ("web", "spike_growth", "hunger_of_hadar", "wall_of_fire"):
        actor.concentrating_on = spell_name
        aoe_label = {
            "web": f"🕸️ Ragnatela (CD {dc} DES -> Trattenuto / Terreno Difficile)",
            "spike_growth": "🌿 Crescita di Spine (2d4 Perforanti ogni 5 ft di movimento)",
            "hunger_of_hadar": f"🌑 Fame di Hadar (2d6 Freddo inizio turno / CD {dc} DES 2d6 Acido fine turno)",
            "wall_of_fire": f"🔥 Muro di Fuoco ({5 + max(0, lvl - 4)}d8 Fuoco / CD {dc} DES)",
        }[key]
        if game_state is not None and isinstance(getattr(game_state, "active_aoes", None), list):
            pos = getattr(tgt, "position", None) or getattr(actor, "position", (0, 0))
            game_state.active_aoes.append({
                "name": spell_name,
                "spell_key": key,
                "caster": actor.name,
                "center": list(pos),
                "radius_hex": 4 if key != "wall_of_fire" else 5,
                "dc": dc,
                "cast_level": lvl,
                "rounds": 10 * dur_mult,
            })
        if key == "wall_of_fire" and tgt is not actor and game_state is not None:
            dice_cnt = 5 + max(0, lvl - 4)
            d_r = roll_dice(f"{dice_cnt}d8")
            from common.item_modifiers import get_effective_save_bonus_from_dict
            dex_m = get_effective_save_bonus_from_dict(tgt, "DES")
            sr = roll_dice(f"1d20{'+' if dex_m >= 0 else ''}{dex_m}")["total"]
            raw = d_r["total"] // 2 if sr >= dc else d_r["total"]
            from server.rules.combat import apply_damage
            fd, _, _, _ = apply_damage(tgt, raw, damage_type="Fuoco", game_state=game_state, is_spell=True)
            return f"{aoe_label} -> {tgt.name} TS DES {sr}: subisce {fd} danni da Fuoco!"
        if key == "web" and tgt is not actor:
            from common.item_modifiers import get_effective_save_bonus_from_dict
            dex_m = get_effective_save_bonus_from_dict(tgt, "DES")
            sr = roll_dice(f"1d20{'+' if dex_m >= 0 else ''}{dex_m}")["total"]
            if sr < dc:
                conds = getattr(tgt, "conditions", None)
                if isinstance(conds, list) and "Trattenuto" not in conds:
                    conds.append("Trattenuto")
                _sync_player(tgt)
                return f"{aoe_label} -> {tgt.name} fallisce TS DES ({sr}) ed è TRATTENUTO dalle ragnatele!"
        return f"✨ [{spell_name.upper()}] Zona attiva sul campo di battaglia: {aoe_label}."

    return None


def compute_combat_spell_modifiers(attacker: Any, target: Any, is_melee: bool = True, base_disadv: bool = False, base_adv: bool = False) -> Dict[str, Any]:
    """
    Calcola i modificatori difensivi/offensivi derivanti da incantesimi iconici attivi:
    - Blur / Greater Invisibility: vantaggio/svantaggio attacco
    - Mirror Image: intercettazione d20 sui duplicati
    - Hunter's Mark / Hex / Absorb Elements: dadi bonus danni
    """
    res: Dict[str, Any] = {
        "adv": base_adv,
        "disadv": base_disadv,
        "bonus_dmg_dice": [],
        "mirror_intercepted": False,
        "sanctuary_blocked": False,
        "notes": [],
    }
    if not attacker or not target:
        return res

    # Attacker buffs
    if getattr(attacker, "greater_invisibility", False) or any("invisibil" in str(c).lower() for c in getattr(attacker, "conditions", [])):
        res["adv"] = True
        res["notes"].append("Invisibile (Vantaggio)")
    if getattr(attacker, "hunters_mark_target", None) == getattr(target, "name", None):
        res["bonus_dmg_dice"].append(("1d6", "Perforante", "Marchio del Cacciatore"))
    if getattr(attacker, "hex_target", None) == getattr(target, "name", None):
        res["bonus_dmg_dice"].append(("1d6", "Necrotico", "Sortilegio (Hex)"))
    if is_melee and int(getattr(attacker, "absorb_elements_dice", 0) or 0) > 0:
        d_n = int(attacker.absorb_elements_dice)
        d_t = getattr(attacker, "absorb_elements_type", "Fuoco") or "Fuoco"
        res["bonus_dmg_dice"].append((f"{d_n}d6", d_t, "Assorbire Elementi"))
        attacker.absorb_elements_dice = 0

    # Target buffs
    if getattr(target, "blur_active", False) or getattr(target, "greater_invisibility", False):
        res["disadv"] = True
        res["notes"].append("Sfocatura/Invisibilità bersaglio (Svantaggio)")

    san_dc = int(getattr(target, "sanctuary_dc", 0) or 0)
    if san_dc > 0:
        from common.item_modifiers import get_effective_save_bonus_from_dict
        wis_m = get_effective_save_bonus_from_dict(attacker, "SAG")
        sr = roll_dice(f"1d20{'+' if wis_m >= 0 else ''}{wis_m}")["total"]
        if sr < san_dc:
            res["sanctuary_blocked"] = True
            res["notes"].append(f"🕊️ Santuario blocca l'attacco (TS SAG {sr} < CD {san_dc})!")
            return res

    imgs = int(getattr(target, "mirror_images", 0) or 0)
    if imgs > 0:
        thresh = 6 if imgs >= 3 else (8 if imgs == 2 else 11)
        m_roll = random.randint(1, 20)
        if m_roll >= thresh:
            copy_ac = 10 + entity_get_attr_mod(target, "DES")
            res["mirror_intercepted"] = True
            res["mirror_copy_ac"] = copy_ac
            res["mirror_roll"] = m_roll
            res["notes"].append(f"🪞 Colpisce un duplicato di Immagine Speculare (d20={m_roll} >= {thresh}, CA copia {copy_ac})!")
    return res


def apply_spell_movement_hazards(entity: Any, from_pos: Any, to_pos: Any, game_state: Any) -> List[str]:
    """
    PHB p. 277 Crescita di Spine (Spike Growth): 2d4 Perforanti per ogni 5 ft (1 cella) percorsa dentro l'area.
    """
    if not entity or not game_state or not to_pos or getattr(entity, "hp", 0) <= 0:
        return []
    aoes = getattr(game_state, "active_aoes", None) or []
    if not aoes:
        return []
    from common.hex_utils import Hex, grid_distance
    gtype = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
    msgs: List[str] = []
    steps = max(1, int(round(grid_distance(Hex(from_pos[0], from_pos[1]), Hex(to_pos[0], to_pos[1]), grid_type=gtype)))) if from_pos else 1

    for aoe in list(aoes):
        if aoe.get("spell_key") != "spike_growth":
            continue
        ctr = aoe.get("center") or (0, 0)
        rad = float(aoe.get("radius_hex", 4) or 4)
        d_to = grid_distance(Hex(to_pos[0], to_pos[1]), Hex(ctr[0], ctr[1]), grid_type=gtype)
        d_from = grid_distance(Hex(from_pos[0], from_pos[1]), Hex(ctr[0], ctr[1]), grid_type=gtype) if from_pos else 999
        if d_to <= rad or d_from <= rad:
            dice_cnt = max(2, 2 * steps)
            dmg_r = roll_dice(f"{dice_cnt}d4")
            from server.rules.combat import apply_damage
            fd, _, _, _ = apply_damage(entity, dmg_r["total"], damage_type="Perforante", game_state=game_state, is_spell=True)
            msgs.append(f"🌿 [CRESCITA DI SPINE] {entity.name} si muove tra le spine ({steps * 5} ft) e subisce {fd} danni Perforanti!")
    return msgs


def tick_active_spell_aoes_for_entity(entity: Any, timing: str, game_state: Any) -> List[str]:
    """
    Risolve a inizio/fine turno i pericoli delle aree attive: Fame di Hadar, Ragnatela, Muro di Fuoco, Metallo Incandescente.
    """
    if not entity or not game_state or getattr(entity, "hp", 0) <= 0:
        return []
    msgs: List[str] = []
    pos = getattr(entity, "position", None)
    gtype = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
    from common.hex_utils import Hex, grid_distance
    from common.item_modifiers import get_effective_save_bonus_from_dict
    from server.rules.combat import apply_damage

    # Heat Metal DoT at start of target turn
    if timing == "start_of_turn":
        for fx in list(getattr(entity, "active_effects", []) or []):
            if isinstance(fx, dict) and fx.get("id") == "heat_metal" and fx.get("dot_damage"):
                dmg_r = roll_dice(str(fx["dot_damage"]))
                fd, _, _, _ = apply_damage(entity, dmg_r["total"], damage_type=str(fx.get("dot_type", "Fuoco")), game_state=game_state, is_spell=True)
                msgs.append(f"🔥 [RISCALDARE IL METALLO] {entity.name} brucia a inizio turno per {fd} danni da Fuoco!")

    if not pos:
        return msgs

    for aoe in list(getattr(game_state, "active_aoes", []) or []):
        skey = aoe.get("spell_key")
        if not skey:
            continue
        ctr = aoe.get("center") or (0, 0)
        rad = float(aoe.get("radius_hex", 4) or 4)
        dc = int(aoe.get("dc", 13) or 13)
        if grid_distance(Hex(pos[0], pos[1]), Hex(ctr[0], ctr[1]), grid_type=gtype) > rad:
            continue

        if skey == "hunger_of_hadar" and timing == "start_of_turn":
            fd, _, _, _ = apply_damage(entity, roll_dice("2d6")["total"], damage_type="Freddo", game_state=game_state, is_spell=True)
            msgs.append(f"🌑 [FAME DI HADAR] {entity.name} inizia il turno nel vuoto gelido: {fd} danni da Freddo!")
        elif skey == "hunger_of_hadar" and timing == "end_of_turn":
            dex_m = get_effective_save_bonus_from_dict(entity, "DES")
            sr = roll_dice(f"1d20{'+' if dex_m >= 0 else ''}{dex_m}")["total"]
            if sr < dc:
                fd, _, _, _ = apply_damage(entity, roll_dice("2d6")["total"], damage_type="Acido", game_state=game_state, is_spell=True)
                msgs.append(f"🌑 [FAME DI HADAR - CD {dc} DES] {entity.name} (TS {sr}) subisce {fd} danni da Acido a fine turno!")
        elif skey == "web" and timing == "start_of_turn":
            if "Trattenuto" not in getattr(entity, "conditions", []):
                dex_m = get_effective_save_bonus_from_dict(entity, "DES")
                sr = roll_dice(f"1d20{'+' if dex_m >= 0 else ''}{dex_m}")["total"]
                if sr < dc:
                    entity.conditions.append("Trattenuto")
                    msgs.append(f"🕸️ [RAGNATELA - CD {dc} DES] {entity.name} (TS {sr}) rimane TRATTENUTO!")
        elif skey == "wall_of_fire" and timing == "end_of_turn":
            lvl = int(aoe.get("cast_level", 4) or 4)
            dice_cnt = 5 + max(0, lvl - 4)
            d_tot = roll_dice(f"{dice_cnt}d8")["total"]
            dex_m = get_effective_save_bonus_from_dict(entity, "DES")
            sr = roll_dice(f"1d20{'+' if dex_m >= 0 else ''}{dex_m}")["total"]
            raw = d_tot // 2 if sr >= dc else d_tot
            fd, _, _, _ = apply_damage(entity, raw, damage_type="Fuoco", game_state=game_state, is_spell=True)
            msgs.append(f"🔥 [MURO DI FUOCO - CD {dc} DES] {entity.name} (TS {sr}): {fd} danni da Fuoco a fine turno!")
    return msgs

