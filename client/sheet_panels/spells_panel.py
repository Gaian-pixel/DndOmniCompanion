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

