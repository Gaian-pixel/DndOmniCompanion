"""
client/sheet_panels/spells_panel.py - Gestione Incantesimi, Slot, CD Salvezza e Grimorio (5e RAW).
Modulo estratto da CharacterSheetFrame per separazione di responsabilità e testabilità.
"""

import tkinter as tk
from tkinter import ttk
from common.theme import (
    SURFACE_COLOR, BORDER_COLOR, TEXT_MUTED,
    ACCENT_GOLD, ACCENT_BLUE, ACCENT_GREEN,
    FONT_BOLD, FONT_SMALL
)
from common.i18n import _t


class SpellsPanel:
    """Gestisce il Grimorio, gli Slot Incantesimo (1-9) e le statistiche magiche D&D 5e RAW."""

    @staticmethod
    def get_spellcasting_ability(char_class: str, subclass: str = "") -> str:
        """Determina la caratteristica da incantatore principale secondo D&D 5e RAW."""
        c = (char_class or "").lower()
        sub = (subclass or "").lower()
        if any(k in c for k in ["chierico", "cleric", "druido", "druid", "ranger"]):
            return "SAG"
        if any(k in c for k in ["bardo", "bard", "paladino", "paladin", "stregone", "sorcerer", "warlock"]):
            return "CAR"
        if any(k in c for k in ["mago", "wizard", "artefice", "artificer"]) or any(k in sub for k in ["mistico", "eldritch", "arcane"]):
            return "INT"
        return "INT"

    @staticmethod
    def calculate_spell_stats(character):
        """Calcola Competenza (PB), Modificatore Incantatore, CD Salvezza e Bonus Attacco Incantesimi."""
        char_lvl = max(1, int(getattr(character, "level", 1) or 1))
        pb = ((char_lvl - 1) // 4) + 2
        char_class = getattr(character, "char_class", "")
        subclass = getattr(character, "subclass", "")
        stat = SpellsPanel.get_spellcasting_ability(char_class, subclass)

        if hasattr(character, "get_modifier"):
            mod = character.get_modifier(stat)
        else:
            val = 10
            if hasattr(character, "attributes") and isinstance(character.attributes, dict):
                val = character.attributes.get(stat, 10)
            mod = (val - 10) // 2

        spell_dc_bonus = getattr(character, "get_spell_dc_bonus", lambda: 0)()
        spell_atk_bonus = getattr(character, "get_spell_attack_bonus", lambda: 0)()

        dc = 8 + pb + mod + spell_dc_bonus
        atk_bonus = pb + mod + spell_atk_bonus
        return {
            "ability": stat,
            "mod": mod,
            "pb": pb,
            "dc": dc,
            "attack_bonus": atk_bonus,
            "attack_str": f"+{atk_bonus}" if atk_bonus >= 0 else str(atk_bonus)
        }

    @staticmethod
    def update_spell_stats(sheet):
        """Aggiorna le etichette grafiche nella scheda con i dati calcolati."""
        if not hasattr(sheet, "lbl_spell_dc"):
            return
        stats = SpellsPanel.calculate_spell_stats(sheet.character)
        stat = stats["ability"]
        mod = stats["mod"]
        dc = stats["dc"]
        atk_str = stats["attack_str"]
        pb = stats["pb"]

        sheet.lbl_spell_stat.config(text=f"🔮 Caratteristica: {stat} ({'+' if mod >= 0 else ''}{mod})")
        sheet.lbl_spell_dc.config(text=f"🎯 CD Salvezza: {dc}")
        sheet.lbl_spell_atk.config(text=f"⚔️ Attacco Magico: {atk_str}")
        max_prep = SpellsPanel.get_max_prepared_spells(sheet.character)
        if max_prep > 0:
            cur_prep = SpellsPanel.count_prepared_spells(sheet.character)
            prep_txt = f" | 📖 Prep: {cur_prep}/{max_prep}"
        else:
            prep_txt = ""
        sp_cur = getattr(sheet.character, "sorcery_points_current", 0)
        sp_max = getattr(sheet.character, "sorcery_points_max", 0)
        sorc_txt = f" | PS: {sp_cur}/{sp_max}" if sp_max > 0 else ""
        pact = getattr(sheet.character, "pact_slots", None)
        pact_txt = f" | 🟣 Patto: {pact.get('current', 0)}/{pact.get('max', 0)} ({pact.get('level', 1)}°)" if isinstance(pact, dict) and pact.get("max", 0) > 0 else ""
        _ch_sp = getattr(sheet, "character", None)
        mag_max = int(getattr(_ch_sp, "spell_points_max", 0) or 0) if _ch_sp else 0
        mag_cur = int(getattr(_ch_sp, "spell_points_current", 0) or 0) if _ch_sp else 0
        sp_txt = f" | ⚡ Punti Magia: {mag_cur}/{mag_max}" if mag_max > 0 else ""
        sheet.lbl_spell_pb.config(text=f"⭐ PB: +{pb}{prep_txt}{pact_txt}{sorc_txt}{sp_txt}")

    @staticmethod
    def refresh_spell_list(sheet):
        """Aggiorna la vista ad albero (Treeview) con la lista degli incantesimi."""
        if not hasattr(sheet, 'spell_tree'):
            return
        for item in sheet.spell_tree.get_children():
            sheet.spell_tree.delete(item)
        req_prep = SpellsPanel.spell_preparation_required(sheet.character)
        for i, s in enumerate(getattr(sheet.character, "spellbook", [])):
            lvl = int(s.get("level", 0) or 0)
            lvl_str = _t("cantrip") if lvl == 0 else str(lvl)
            name = s.get("name", "")
            if req_prep and lvl > 0:
                mark = "✓ " if s.get("prepared", True) else "○ "
                display_name = f"{mark}{name}"
            else:
                display_name = name
            sheet.spell_tree.insert("", tk.END, iid=str(i), values=(lvl_str, display_name, s.get("time", ""), s.get("range", "")))

    @staticmethod
    def can_cast_as_ritual(character) -> bool:
        """Verifica se il personaggio possiede il privilegio Lancio Rituale (PHB p. 201)."""
        if not character:
            return False
        classes_dict = getattr(character, "classes", {}) or {}
        c_blob = " ".join(
            [str(getattr(character, "char_class", "") or ""), str(getattr(character, "subclass", "") or "")]
            + [str(k) for k in classes_dict.keys()]
        ).lower()
        if any(k in c_blob for k in ("bardo", "bard", "chierico", "cleric", "druido", "druid", "mago", "wizard", "artefice", "artificer")):
            return True
        if hasattr(character, "_get_all_features_text"):
            ft = character._get_all_features_text()
        else:
            ft = str(getattr(character, "features", "") or "").lower()
        return any(k in ft for k in (
            "incantatore rituale", "ritual caster",
            "libro degli antichi segreti", "book of ancient secrets",
            "patto del tomo", "pact of the tome",
        ))

    @staticmethod
    def spell_preparation_required(character) -> bool:
        """True se almeno una classe del PG prepara giornalmente gli incantesimi (Chierico/Druido/Mago/Paladino/Artefice)."""
        return SpellsPanel.get_max_prepared_spells(character) > 0

    @staticmethod
    def count_prepared_spells(character) -> int:
        if not character:
            return 0
        return sum(1 for s in getattr(character, "spellbook", []) if int(s.get("level", 0) or 0) > 0 and s.get("prepared", True))

    @staticmethod
    def toggle_spell_prepared(sheet):
        """Alterna lo stato Preparato/Non Preparato sull'incantesimo selezionato in scheda."""
        if not hasattr(sheet, "spell_tree"):
            return
        sel = sheet.spell_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        sb = getattr(sheet.character, "spellbook", [])
        if idx < 0 or idx >= len(sb):
            return
        sp = sb[idx]
        if int(sp.get("level", 0) or 0) <= 0:
            return
        sp["prepared"] = not bool(sp.get("prepared", True))
        if hasattr(sheet, "manager") and hasattr(sheet.manager, "update_character"):
            sheet.manager.update_character(sheet.character)
            if hasattr(sheet.manager, "save_characters"):
                sheet.manager.save_characters()
        SpellsPanel.refresh_spell_list(sheet)
        SpellsPanel.update_spell_stats(sheet)

    @staticmethod
    def sort_spells(sheet, col):
        """Ordina gli incantesimi per livello crescente."""
        if not hasattr(sheet.character, "spellbook"):
            return
        sheet.character.spellbook.sort(key=lambda s: int(s.get("level", 0)))
        SpellsPanel.refresh_spell_list(sheet)

    @staticmethod
    def scale_spell_formula_for_upcast(base_formula: str, base_level: int, cast_level: int, spell_name: str = "") -> str:
        """
        Scala automaticamente la formula di danno o cura di un incantesimo quando viene lanciato
        con uno slot di livello superiore (Upcasting D&D 5e RAW):
        - Dardo Incantato (Magic Missile): +1d4+1 per ogni livello sopra il 1°
        - Raggio Rovente (Scorching Ray) / Sfera Infuocata: +2d6 o +1d6 per livello superiore
        - Standard (Palla di Fuoco, Cura Ferite, Dardo Guida, Mani Brucianti, Onda Tonante, Ferire, ecc.):
          +1 dado per ogni livello dello slot superiore al livello base dell'incantesimo.
        """
        import re
        f_clean = str(base_formula or "").strip()
        if not f_clean:
            return f_clean
        try:
            b_lvl = int(base_level)
            c_lvl = int(cast_level)
        except (ValueError, TypeError):
            return f_clean
        if b_lvl < 1 or c_lvl <= b_lvl:
            return f_clean

        diff = c_lvl - b_lvl
        s_low = str(spell_name or "").strip().lower()

        # Caso speciale: Dardo Incantato (Magic Missile) -> +1 dardo (1d4+1) per slot sopra il 1°
        if any(k in s_low for k in ("dardo incantato", "magic missile")):
            m = re.match(r'^(\d+)d4\s*\+\s*(\d+)(.*)$', f_clean, re.IGNORECASE)
            if m:
                new_cnt = int(m.group(1)) + diff
                new_mod = int(m.group(2)) + diff
                return f"{new_cnt}d4+{new_mod}{m.group(3)}"

        # Caso speciale: Raggio Rovente (Scorching Ray) / Evoca Animali / Spiriti Guardiani
        dice_per_level = 2 if any(k in s_low for k in ("raggio rovente", "scorching ray")) else 1

        def _repl(match):
            cnt_str = match.group(1)
            sides_str = match.group(2)
            cnt = int(cnt_str) if cnt_str else 1
            return f"{cnt + diff * dice_per_level}d{sides_str}"

        return re.sub(r'(\d*)d(\d+)', _repl, f_clean, count=1)

    @staticmethod
    def is_ritual_spell(spell_data_or_name) -> bool:
        """
        Determina se un incantesimo possiede il tag Rituale secondo D&D 5e RAW
        (può essere lanciato aggiungendo 10 minuti senza spendere uno slot incantesimo).
        """
        if isinstance(spell_data_or_name, dict):
            if spell_data_or_name.get("ritual") is True:
                return True
            txt = f"{spell_data_or_name.get('name', '')} {spell_data_or_name.get('time', '')} {spell_data_or_name.get('desc', '')}".lower()
        else:
            txt = str(spell_data_or_name or "").lower()

        if "rituale" in txt or "ritual" in txt:
            return True

        ritual_names = (
            "allarme", "alarm",
            "comprensione dei linguaggi", "comprehend languages",
            "individuazione del magico", "detect magic",
            "individuazione del veleno", "detect poison and disease",
            "identificare", "identify",
            "passo velato", "floating disk", "disco fluttuante",
            "servitore inosservato", "unseen servant",
            "trova famiglio", "find familiar",
            "augurio", "augury",
            "bocca magica", "magic mouth",
            "silenzio", "silence",
            "capanna di leomund", "leomund's tiny hut", "tiny hut",
            "camminare sull'acqua", "water walk",
            "respirare sott'acqua", "water breathing",
            "fondere nella pietra", "meld into stone",
            "divinazione", "divination",
            "comunione", "commune",
            "contatto con altri piani", "contact other plane",
            "legame telepatico", "telepathic bond",
            "forbiddance", "proibizione"
        )
        return any(rn in txt for rn in ritual_names)

    @staticmethod
    def scale_cantrip_formula(base_formula: str, total_level: int, spell_name: str = "") -> str:
        """
        Scala automaticamente i dadi di danno dei Trucchetti (Cantrips) secondo D&D 5e RAW (PHB p. 201):
        - Livello 1-4: 1 dado (formula base)
        - Livello 5-10: 2 dadi
        - Livello 11-16: 3 dadi
        - Livello 17-20: 4 dadi
        """
        import re
        f_clean = str(base_formula or "").strip()
        if not f_clean:
            return f_clean
        try:
            lvl = int(total_level)
        except (ValueError, TypeError):
            lvl = 1

        if lvl >= 17:
            mult = 4
        elif lvl >= 11:
            mult = 3
        elif lvl >= 5:
            mult = 2
        else:
            mult = 1

        if mult == 1:
            return f_clean

        def _repl(match):
            cnt_str = match.group(1)
            sides_str = match.group(2)
            cnt = int(cnt_str) if cnt_str else 1
            return f"{cnt * mult}d{sides_str}"

        return re.sub(r'(\d*)d(\d+)', _repl, f_clean, count=1)

    @staticmethod
    def get_max_prepared_spells(character) -> int:
        """
        Calcola il numero massimo di incantesimi preparabili giornalmente (D&D 5e RAW PHB p. 201):
        - Chierico / Druido: Livello + Mod SAG (minimo 1)
        - Mago: Livello + Mod INT (minimo 1)
        - Paladino: max(1, Livello // 2 + Mod CAR)
        - Artefice: max(1, Livello // 2 + Mod INT)
        - Bardi, Stregoni, Ranger, Warlock: 0 (gestiti con Spells Known fissi).
        """
        c_class = str(getattr(character, "char_class", "")).lower()
        classes = getattr(character, "classes", {})
        get_mod = getattr(character, "get_modifier", lambda s: 0)

        # Controlla classi singole o multiclasse
        for ck, cv in classes.items():
            ck_l = str(ck).lower()
            lvl = int(cv)
            if "chierico" in ck_l or "cleric" in ck_l or "druido" in ck_l or "druid" in ck_l:
                return max(1, lvl + get_mod("SAG"))
            if "mago" in ck_l or "wizard" in ck_l:
                return max(1, lvl + get_mod("INT"))
            if "paladino" in ck_l or "paladin" in ck_l:
                return max(1, (lvl // 2) + get_mod("CAR"))
            if "artefice" in ck_l or "artificer" in ck_l:
                return max(1, (lvl // 2) + get_mod("INT"))

        lvl = max(1, int(getattr(character, "level", 1) or 1))
        if "chierico" in c_class or "cleric" in c_class or "druido" in c_class or "druid" in c_class:
            return max(1, lvl + get_mod("SAG"))
        if "mago" in c_class or "wizard" in c_class:
            return max(1, lvl + get_mod("INT"))
        if "paladino" in c_class or "paladin" in c_class:
            return max(1, (lvl // 2) + get_mod("CAR"))
        if "artefice" in c_class or "artificer" in c_class:
            return max(1, (lvl // 2) + get_mod("INT"))
        return 0

    @staticmethod
    def consume_material_component(character, spell: dict, mat_gp: float) -> str:
        """
        Consuma dall'inventario (o dall'oro equivalente se assente) la componente materiale
        consumata al lancio dell'incantesimo (PHB p. 203).
        """
        if not character or float(mat_gp or 0) <= 0:
            return ""
        inv = getattr(character, "inventory_grid", None)
        comp_txt = f"{spell.get('components', '')} {spell.get('material', '')} {spell.get('desc', '')}".lower()
        mat_keywords = [w for w in ("diamante", "diamond", "perla", "pearl", "rubino", "ruby", "zaffiro", "sapphire", "incenso", "incense", "polvere d'oro", "polvere d'argento", "onice", "onyx", "opale", "erbe") if w in comp_txt]
        if isinstance(inv, list):
            for idx, it in enumerate(inv):
                if not isinstance(it, dict):
                    continue
                nm = str(it.get("name", "")).lower()
                if mat_keywords and any(k in nm for k in mat_keywords):
                    qty = int(it.get("qty", 1) or 1)
                    if qty > 1:
                        it["qty"] = qty - 1
                    else:
                        inv[idx] = None
                    return f" [💎 Consumato: {it.get('name', 'Componente Materiale')}]"
        curr = getattr(character, "currency", None)
        if isinstance(curr, dict):
            gp_need = int(round(float(mat_gp)))
            if int(curr.get("MO", 0) or 0) >= gp_need:
                curr["MO"] -= gp_need
                return f" [💰 Componenti consumate: -{gp_need} MO]"
        return f" [💎 Nota: componente da {int(round(float(mat_gp)))} mo consumato]"

    @staticmethod
    def execute_spell_resource_cost(
        character,
        spell: dict,
        cast_level: int,
        is_ritual: bool = False,
        use_pact: bool = False,
        use_spell_points: bool = False,
        metamagic_key: str = "",
    ) -> tuple:
        """
        Consuma in modo unificato e conforme alle regole 5e RAW:
        - Slot Patto Warlock (preferibile su richiesta o quando gli slot base mancano)
        - Punti Magia / Spell Points (DMG p. 288)
        - Slot Incantesimo standard (1-9)
        - Punti Stregoneria (Metamagia) e Impulso Magia Selvaggia
        Ritorna: (ok: bool, summary_tags: list[str], error_msg: str)
        """
        lvl = int(spell.get("level", 0) or 0)
        eff_lvl = max(lvl, int(cast_level or lvl))
        tags = []

        # 1. Verifica Lancio Rituale (PHB p. 201)
        if lvl > 0 and is_ritual:
            if not SpellsPanel.is_ritual_spell(spell):
                return False, [], "Questo incantesimo non possiede il tag Rituale."
            if not SpellsPanel.can_cast_as_ritual(character):
                return False, [], "La tua classe/talento non consente il Lancio Rituale."
            tags.append("🕯️ Rituale (+10 min, 0 slot)")

        # 2. Consumo risorsa lancio per incantesimi lv 1+ non rituali
        elif lvl > 0:
            if use_spell_points and hasattr(character, "spend_spell_points"):
                # DMG p. 288: max 1 incantesimo per ciascun livello 6-9 con Spell Points per Riposo Lungo
                used_high = getattr(character, "_spell_points_high_used", None)
                if not isinstance(used_high, set):
                    used_high = set(used_high or [])
                if eff_lvl >= 6 and eff_lvl in used_high:
                    return False, [], f"DMG p. 288: con i Punti Incantesimo puoi lanciare un solo incantesimo di {eff_lvl}° livello per Riposo Lungo."
                ok_sp, msg_sp = character.spend_spell_points(eff_lvl)
                if not ok_sp:
                    return False, [], msg_sp
                if eff_lvl >= 6:
                    used_high.add(eff_lvl)
                    character._spell_points_high_used = used_high
                tags.append(f"⚡ {msg_sp}")
            else:
                pact = getattr(character, "pact_slots", None)
                pact_ok = (
                    isinstance(pact, dict)
                    and int(pact.get("current", 0) or 0) > 0
                    and int(pact.get("level", 0) or 0) >= lvl
                )
                slots = getattr(character, "spell_slots", {}) or {}
                sl_entry = slots.get(str(eff_lvl), {"max": 0, "current": 0})
                std_cur = int(sl_entry.get("current", 0)) if isinstance(sl_entry, dict) else (int(sl_entry[0]) if isinstance(sl_entry, list) and sl_entry else 0)
                if (use_pact and pact_ok) or (std_cur <= 0 and pact_ok):
                    pact["current"] = int(pact["current"]) - 1
                    eff_lvl = max(lvl, int(pact.get("level", eff_lvl) or eff_lvl))
                    tags.append(f"🟣 Slot Patto Lv {eff_lvl}° ({pact['current']}/{pact.get('max', 0)})")
                else:
                    if std_cur <= 0:
                        return False, [], f"SLOT_EXHAUSTED:{eff_lvl}"
                    if isinstance(sl_entry, dict):
                        sl_entry["current"] = std_cur - 1
                    elif isinstance(sl_entry, list) and sl_entry:
                        sl_entry[0] = std_cur - 1
                    if eff_lvl > lvl:
                        tags.append(f"⬆️ Potenziato {eff_lvl}°")

        # 3. Metamagia (Stregone / Adepto della Metamagia)
        from common.spell_effects_engine import (
            apply_metamagic_to_cast,
            maybe_trigger_wild_magic_surge,
            normalize_metamagic_key,
            spend_metamagic_points,
        )
        m_key = normalize_metamagic_key(metamagic_key)
        if m_key:
            ok_m, _rem, msg_m = spend_metamagic_points(character, m_key, eff_lvl)
            if not ok_m:
                return False, [], msg_m
            meta_fx = apply_metamagic_to_cast(character, spell, m_key, eff_lvl)
            tags.append(meta_fx["note"])

        # 4. Magia Selvaggia (Stregone PHB p. 103)
        if lvl > 0:
            wm = maybe_trigger_wild_magic_surge(character, eff_lvl)
            if wm and wm.get("triggered"):
                tags.append(wm["message"])

        return True, tags, ""



