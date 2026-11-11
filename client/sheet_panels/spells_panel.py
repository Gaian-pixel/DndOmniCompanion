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
        sheet.lbl_spell_pb.config(text=f"⭐ Competenza: +{pb}")

    @staticmethod
    def refresh_spell_list(sheet):
        """Aggiorna la vista ad albero (Treeview) con la lista degli incantesimi."""
        if not hasattr(sheet, 'spell_tree'):
            return
        for item in sheet.spell_tree.get_children():
            sheet.spell_tree.delete(item)
        for i, s in enumerate(getattr(sheet.character, "spellbook", [])):
            lvl = s.get("level", 0)
            lvl_str = _t("cantrip") if lvl == 0 else str(lvl)
            sheet.spell_tree.insert("", tk.END, iid=str(i), values=(lvl_str, s.get("name", ""), s.get("time", ""), s.get("range", "")))

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


