"""
client/sheet_panels/combat_panel.py - Gestione Armi, Attacchi, TxC e Calcoli dei Danni (5e RAW).
Modulo estratto da CharacterSheetFrame per separazione di responsabilità e testabilità.
"""

import tkinter as tk
from tkinter import ttk
from common.theme import (
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT, BORDER_COLOR,
    TEXT_COLOR, TEXT_MUTED, ACCENT_GOLD,
    FONT_BOLD, FONT_SMALL, FONT_MAIN
)
from common.i18n import _t, get_language


class CombatPanel:
    """Gestisce la logica di calcolo dei tiri per colpire, danni e rendering della scheda armi."""

    @staticmethod
    def calculate_weapon_txc(character, weapon, power_attack: bool = False):
        """Calcola il bonus di attacco (TxC) totale per un'arma secondo D&D 5e RAW considerando attributi, bonus magici e Attacco Poderoso (-5/+10)."""
        stat_key = weapon.get("ability", "FOR")
        prop_str = f"{weapon.get('properties', '')} {weapon.get('type', '')} {weapon.get('desc', '')}".lower()
        name_str = str(weapon.get("name", "")).lower()
        is_finesse = (
            "accurat" in prop_str or "finesse" in prop_str or
            any(fn in name_str for fn in [
                "stocco", "rapier", "pugnale", "dagger", "scimitarra", "scimitar",
                "frusta", "whip", "spada corta", "shortsword", "spada del sole", "sun blade"
            ])
        )
        is_ranged = (
            any(k in prop_str for k in ["distanza", "ranged", "munizioni", "ammunition"]) or
            any(rn in name_str for rn in ["arco", "bow", "balestra", "crossbow", "fionda", "sling", "cerbottana", "blowgun"])
        ) and not ("lancio" in prop_str or "thrown" in prop_str)

        char_cls = str(getattr(character, "char_class", "") or "").lower()
        is_monk_martial = ("monaco" in char_cls or "monk" in char_cls) and any(
            mw in name_str for mw in [
                "colpo senz'armi", "unarmed", "spada corta", "shortsword", "bastone ferrato", "quarterstaff",
                "lancia", "spear", "mazza", "mace", "randello", "club", "pugnale", "dagger",
                "ascia", "handaxe", "giavellotto", "javelin", "martello leggero", "light hammer", "falcetto", "sickle"
            ]
        ) and not any(hw in name_str for hw in ["bipenne", "greataxe", "spadone", "greatsword", "maglio", "maul", "alabarda", "halberd", "picca", "pike", "falcione", "glaive"])

        get_attr = getattr(character, "get_effective_attribute", lambda s: getattr(character, "attributes", {}).get(s, 10))
        if is_ranged:
            stat_key = "DES"
        elif (is_finesse or is_monk_martial) and stat_key in ("FOR", "DES"):
            for_val = get_attr("FOR")
            des_val = get_attr("DES")
            stat_key = "DES" if des_val >= for_val else "FOR"

        stat_val = get_attr(stat_key)
        mod = (stat_val - 10) // 2
        char_lvl = getattr(character, "level", 1) or 1
        calc_pb = ((max(1, int(char_lvl)) - 1) // 4) + 2
        if "proficient" in weapon:
            prof_bonus = calc_pb if weapon.get("proficient") else 0
        else:
            from common.feats_and_classes import is_proficient_with_weapon
            w_props = [p.strip() for p in str(weapon.get("properties", "")).split(",") if p.strip()]
            prof_bonus = calc_pb if is_proficient_with_weapon(character, weapon.get("name", ""), w_props) else 0

        # Bonus magico dell'arma (esplicito o dedotto automaticamente dal nome/descrizione)
        w_bonus = 0
        if "bonus" in weapon and weapon["bonus"] is not None:
            try: w_bonus = int(weapon["bonus"])
            except Exception: pass
        elif "bonus_attack" in weapon and weapon["bonus_attack"] is not None:
            try: w_bonus = int(weapon["bonus_attack"])
            except Exception: pass

        if w_bonus == 0:
            from common.item_modifiers import extract_magic_bonus
            w_bonus = extract_magic_bonus(name_str) or extract_magic_bonus(str(weapon.get("desc", "")))
            if w_bonus == 0:
                if any(k in name_str for k in ["spada del sole", "sun blade"]):
                    w_bonus = 2
                elif any(k in name_str for k in ["vendicatrice sacra", "holy avenger", "vorpal", "difensore", "defender"]):
                    w_bonus = 3

        # DMG p. 150: Munizioni magiche (+1/+2/+3) si cumulano con armi a distanza magiche
        is_ammo_ranged = any(k in name_str or k in prop_str for k in ("arco", "bow", "balestra", "crossbow", "fionda", "sling", "cerbottana", "blowgun"))
        if is_ammo_ranged and hasattr(character, "find_ammunition"):
            try:
                ammo_it, _ = character.find_ammunition(name_str)
                if isinstance(ammo_it, dict):
                    from common.item_modifiers import extract_magic_bonus as _ext_mb
                    ammo_b = int(ammo_it.get("bonus") or ammo_it.get("bonus_attack") or 0)
                    if ammo_b == 0:
                        ammo_b = _ext_mb(str(ammo_it.get("name", ""))) or _ext_mb(str(ammo_it.get("desc", "")))
                    w_bonus += ammo_b
            except Exception:
                pass

        total_txc = mod + prof_bonus + w_bonus - (5 if power_attack else 0)
        return total_txc, mod, prof_bonus, w_bonus, stat_key

    @staticmethod
    def calculate_weapon_damage(character, weapon, mod=None, w_bonus=None, power_attack: bool = False, is_offhand: bool = False):
        """
        Calcola la formula del danno e la stringa leggibile per un'arma:
        - power_attack=True: aggiunge +10 ai danni (Maestro d'Armi Possenti / Tiratore Scelto).
        - is_offhand=True: Combattere con Due Armi (PHB p. 195): non somma il modificatore di caratteristica
          positivo al danno a meno che il personaggio possieda lo Stile di Combattimento: Combattere con Due Armi.
        """
        if mod is None or w_bonus is None:
            _, mod, _, w_bonus, _ = CombatPanel.calculate_weapon_txc(character, weapon, power_attack=power_attack)
        eff_mod = mod
        if is_offhand and mod > 0:
            has_twf = getattr(character, "has_two_weapon_fighting_style", lambda: False)()
            if not has_twf:
                eff_mod = 0
        dmg_mod = eff_mod + w_bonus + (10 if power_attack else 0)
        dmg_mod_str = f"+{dmg_mod}" if dmg_mod > 0 else (str(dmg_mod) if dmg_mod < 0 else "")
        dice = weapon.get("damage_dice", "1d8")
        dmg_formula = f"{dice}{dmg_mod_str}"
        dmg_str = f"{dmg_formula} {weapon.get('damage_type', '')}"
        return dmg_formula, dmg_str, dmg_mod

    @staticmethod
    def refresh_weapons_list(sheet):
        """Rigenera le schede grafiche per tutte le armi del personaggio."""
        if not hasattr(sheet, 'weapons_cards_frame'):
            return
        if hasattr(sheet, "character") and hasattr(sheet.character, "sync_weapons_from_inventory"):
            sheet.character.sync_weapons_from_inventory()
        for child in sheet.weapons_cards_frame.winfo_children():
            child.destroy()

        weapons = getattr(sheet.character, "weapons", [])
        if not weapons:
            empty_lbl = tk.Label(
                sheet.weapons_cards_frame,
                text=_t("sheet_weapons_empty"),
                font=FONT_MAIN, bg=BG_COLOR, fg=TEXT_MUTED, pady=25
            )
            empty_lbl.pack(fill=tk.X)
            return

        if not hasattr(sheet, "_power_attack_var"):
            sheet._power_attack_var = tk.BooleanVar(value=False)

        power_bar = tk.Frame(sheet.weapons_cards_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=4)
        power_bar.pack(fill=tk.X, pady=(0, 6), padx=4)
        chk_pwr = ttk.Checkbutton(
            power_bar,
            text="⚡ Attacco Poderoso (-5 TxC / +10 Danni)",
            variable=sheet._power_attack_var,
            command=lambda: CombatPanel.refresh_weapons_list(sheet)
        )
        chk_pwr.pack(side=tk.LEFT)

        char_cls = str(getattr(sheet.character, "char_class", "")).lower()
        if any(k in char_cls for k in ("paladino", "paladin")):
            if not hasattr(sheet, "_divine_smite_var"):
                sheet._divine_smite_var = tk.StringVar(value="0")
            smite_f = tk.Frame(power_bar, bg=SURFACE_COLOR_ALT)
            smite_f.pack(side=tk.RIGHT, padx=4)
            tk.Label(smite_f, text="⚡ Punizione:", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(side=tk.LEFT, padx=(2, 2))
            cb_smite = ttk.Combobox(
                smite_f, textvariable=sheet._divine_smite_var,
                values=["0", "1 (+2d8)", "2 (+3d8)", "3 (+4d8)", "4 (+5d8)", "5 (+5d8)"],
                width=10, state="readonly"
            )
            cb_smite.pack(side=tk.LEFT)

        if any(k in char_cls for k in ("monaco", "monk")) and getattr(sheet.character, "level", 1) >= 5:
            if not hasattr(sheet, "_stunning_strike_var"):
                sheet._stunning_strike_var = tk.BooleanVar(value=False)
            chk_stun = ttk.Checkbutton(
                power_bar,
                text="🥋 Stordente",
                variable=sheet._stunning_strike_var
            )
            chk_stun.pack(side=tk.RIGHT, padx=4)

        is_pwr = bool(sheet._power_attack_var.get())

        for i, w in enumerate(weapons):
            card = tk.Frame(sheet.weapons_cards_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=8)
            card.pack(fill=tk.X, pady=4, padx=4)

            total_txc, mod, prof_bonus, w_bonus, stat_key = CombatPanel.calculate_weapon_txc(sheet.character, w, power_attack=is_pwr)
            txc_str = f"+{total_txc}" if total_txc >= 0 else str(total_txc)
            dmg_formula, dmg_str, dmg_mod = CombatPanel.calculate_weapon_damage(sheet.character, w, mod, w_bonus, power_attack=is_pwr)
            off_formula, off_str, off_mod = CombatPanel.calculate_weapon_damage(sheet.character, w, mod, w_bonus, power_attack=is_pwr, is_offhand=True)

            r1 = tk.Frame(card, bg=SURFACE_COLOR)
            r1.pack(fill=tk.X)
            tk.Label(r1, text=w.get("name", "Arma"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)
            tk.Label(r1, text=f"• {w.get('type', '')}", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=6)

            prof_badge = "Competente" if w.get("proficient", True) else "Non Comp."
            r2 = tk.Frame(card, bg=SURFACE_COLOR)
            r2.pack(fill=tk.X, pady=(2, 4))
            tk.Label(
                r2,
                text=f"Modificatore: {stat_key} ({mod:+d}) | {prof_badge} (+{prof_bonus}) | Magico: +{w_bonus}",
                font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_COLOR
            ).pack(side=tk.LEFT)

            r3 = tk.Frame(card, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=4)
            r3.pack(fill=tk.X, pady=(2, 6))
            tk.Label(r3, text=f"TxC: {txc_str}", font=("Georgia", 11, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(side=tk.LEFT, padx=(0, 15))
            tk.Label(r3, text=f"Danno: {dmg_str}", font=("Georgia", 11, "bold"), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).pack(side=tk.LEFT)

            ammo_item, ammo_idx = sheet.character.find_ammunition(w.get("name", ""))
            if ammo_item:
                ammo_lbl = tk.Label(r3, text=f"🏹 Munizioni: {ammo_item.get('qty', 0)}x {ammo_item.get('name')}", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD)
                ammo_lbl.pack(side=tk.RIGHT, padx=4)

            r4 = tk.Frame(card, bg=SURFACE_COLOR)
            r4.pack(fill=tk.X)

            if ammo_item:
                btn_ammo = ttk.Button(r4, text=f"🏹 -1 {ammo_item.get('name')}", command=lambda a_idx=ammo_idx: sheet.spend_consumable(a_idx, 1), style="Gold.TButton")
                btn_ammo.pack(side=tk.LEFT, padx=(0, 4))

            if getattr(sheet, "attack_callback", None):
                btn_target = ttk.Button(r4, text=f"🎯 Bersaglio ({txc_str})", command=lambda weapon=w, txc=total_txc, dmg=dmg_formula: sheet.execute_targeted_attack(weapon, txc, dmg), style="Gold.TButton")
                btn_target.pack(side=tk.LEFT, padx=(0, 4))
                btn_attack = ttk.Button(r4, text="🎲 Tira TxC", command=lambda weapon=w, txc=total_txc: sheet.execute_weapon_attack(weapon, txc), style="Primary.TButton")
                btn_attack.pack(side=tk.LEFT, padx=(0, 4))
            else:
                btn_attack = ttk.Button(r4, text=f"🎯 Colpisci ({txc_str})", command=lambda weapon=w, txc=total_txc: sheet.execute_weapon_attack(weapon, txc), style="Gold.TButton")
                btn_attack.pack(side=tk.LEFT, padx=(0, 4))

            btn_damage = ttk.Button(r4, text="💥 Danno", command=lambda weapon=w, dmod=dmg_mod: sheet.execute_weapon_damage(weapon, dmod), style="Primary.TButton")
            btn_damage.pack(side=tk.LEFT, padx=(0, 4))

            if "distanza" not in str(w.get("type", "")).lower():
                if getattr(sheet, "attack_callback", None):
                    btn_offhand = ttk.Button(
                        r4,
                        text=f"🗡️ 2ª Mano ({off_formula})",
                        command=lambda weapon=w, txc=total_txc, dmg=off_formula: sheet.execute_targeted_attack(weapon, txc, dmg),
                        style="Tool.TButton"
                    )
                else:
                    btn_offhand = ttk.Button(
                        r4,
                        text=f"🗡️ 2ª Mano ({off_formula})",
                        command=lambda weapon=w, dmod=off_mod: sheet.execute_weapon_damage(weapon, dmod),
                        style="Tool.TButton"
                    )
                btn_offhand.pack(side=tk.LEFT, padx=(0, 4))

            btn_del = ttk.Button(r4, text="🗑️", width=3, command=lambda idx=i: sheet.remove_weapon(idx))
            btn_del.pack(side=tk.RIGHT)

            btn_edit = ttk.Button(r4, text="✏️", width=3, command=lambda weapon=w, idx=i: sheet.open_edit_weapon_dialog(weapon, idx))
            btn_edit.pack(side=tk.RIGHT, padx=(0, 4))

