"""
client/sheet_panels/vitals_panel.py - Gestione Vitals, Punti Ferita, Dadi Vita, TS Morte e Riposi (5e RAW).
Modulo estratto da CharacterSheetFrame per separazione di responsabilità e testabilità.
"""

import tkinter as tk
from tkinter import ttk
import random
from common.messagebox import messagebox
from common.theme import (
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT, BORDER_COLOR,
    TEXT_COLOR, TEXT_MUTED, ACCENT_GOLD, ACCENT_RED, ACCENT_GREEN,
    FONT_HEADER, FONT_BOLD, FONT_SMALL, apply_modern_window_style
)
from common.i18n import _t


class VitalsPanel:
    """Gestisce la logica dei parametri vitali (PF, Dadi Vita, Riposi, TS Morte) di un personaggio."""

    @staticmethod
    def short_rest(sheet):
        """Apre il dialogo di riposo breve e spesa dadi vita conforme a D&D 5e RAW."""
        win = tk.Toplevel(sheet)
        win.transient(sheet)
        win.grab_set()
        apply_modern_window_style(win)
        win.title("❤️ Riposo Breve - Spesa Dadi Vita 5e")
        win.minsize(440, 480)

        container = tk.Frame(win, bg=BG_COLOR, padx=16, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text=f"❤️ {_t('sheet_short_rest')} (5e)", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
        tk.Label(container, text=_t("sheet_short_rest_subtitle"), font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 10))

        st_frame = tk.Frame(container, bg=SURFACE_COLOR, padx=12, pady=10, highlightbackground=BORDER_COLOR, highlightthickness=1)
        st_frame.pack(fill=tk.X, pady=(0, 10))

        lbl_hp = tk.Label(st_frame, text=f"Punti Ferita: {sheet.character.hp_current} / {sheet.character.hp_max}", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR)
        lbl_hp.pack(anchor="w")

        bar_bg = tk.Frame(st_frame, bg="#111827", height=12)
        bar_bg.pack(fill=tk.X, pady=(4, 8))
        ratio = max(0.0, min(1.0, sheet.character.hp_current / max(1, sheet.character.hp_max)))
        bar_fill = tk.Frame(bar_bg, bg=ACCENT_GREEN if ratio > 0.5 else ("#F59E0B" if ratio > 0.25 else ACCENT_RED), height=12)
        bar_fill.place(x=0, y=0, relwidth=ratio, relheight=1.0)

        if hasattr(sheet.character, "get_modifier"):
            cos_mod = sheet.character.get_modifier("COS")
        else:
            cos_mod = (int(sheet.character.attributes.get("COS", 10)) - 10) // 2
        cos_str = f"+{cos_mod}" if cos_mod >= 0 else str(cos_mod)
        lbl_hd = tk.Label(
            st_frame,
            text=f"🎲 Dadi Vita: {sheet.character.hit_dice_current} / {sheet.character.hit_dice_total} ({sheet.character.hit_dice_type})  |  COS: {cos_str}",
            font=FONT_SMALL, bg=SURFACE_COLOR, fg=ACCENT_GOLD
        )
        lbl_hd.pack(anchor="w")

        tk.Label(container, text=_t("sheet_short_rest_log"), font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(4, 2))
        log_box = tk.Text(container, height=8, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=("Consolas", 9), relief=tk.FLAT, padx=8, pady=6)
        log_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        log_box.insert(tk.END, "Inizio riposo breve. Clicca su 'Tira 1 Dado Vita' per curarti.\n")
        log_box.config(state=tk.DISABLED)

        spent_dice = []

        def update_dialog_ui():
            lbl_hp.config(text=f"Punti Ferita: {sheet.character.hp_current} / {sheet.character.hp_max}")
            r = max(0.0, min(1.0, sheet.character.hp_current / max(1, sheet.character.hp_max)))
            c = ACCENT_GREEN if r > 0.5 else ("#F59E0B" if r > 0.25 else ACCENT_RED)
            bar_fill.config(bg=c)
            bar_fill.place(x=0, y=0, relwidth=r, relheight=1.0)
            lbl_hd.config(text=f"🎲 Dadi Vita: {sheet.character.hit_dice_current} / {sheet.character.hit_dice_total} ({sheet.character.hit_dice_type})  |  COS: {cos_str}")
            sheet.hp_cur_var.set(sheet.character.hp_current)
            if sheet.character.hit_dice_current <= 0 or sheet.character.hp_current >= sheet.character.hp_max:
                btn_roll_one.config(state=tk.DISABLED)
                btn_roll_all.config(state=tk.DISABLED)

        def log_msg(msg_text):
            log_box.config(state=tk.NORMAL)
            log_box.insert(tk.END, msg_text + "\n")
            log_box.see(tk.END)
            log_box.config(state=tk.DISABLED)

        def roll_one():
            if sheet.character.hit_dice_current <= 0:
                messagebox.showinfo("Dadi Esauriti", "Non hai più Dadi Vita da spendere.", parent=win)
                return
            if sheet.character.hp_current >= sheet.character.hp_max:
                messagebox.showinfo("PF al Massimo", "I tuoi Punti Ferita sono già al massimo!", parent=win)
                return
            res = sheet.character.spend_hit_die_single()
            if res.get("success"):
                spent_dice.append(res)
                log_msg(f"• Tiro {len(spent_dice)}: {res['die']} ({res['roll']}) {cos_str} COS = +{res['healed']} PF (PF: {res['hp_current']}/{res['hp_max']})")
                update_dialog_ui()

        def roll_all():
            while sheet.character.hit_dice_current > 0 and sheet.character.hp_current < sheet.character.hp_max:
                res = sheet.character.spend_hit_die_single()
                if res.get("success"):
                    spent_dice.append(res)
                    log_msg(f"• Tiro {len(spent_dice)}: {res['die']} ({res['roll']}) {cos_str} COS = +{res['healed']} PF (PF: {res['hp_current']}/{res['hp_max']})")
            update_dialog_ui()

        def finish_rest():
            if not hasattr(sheet.character, "class_resources") or not isinstance(sheet.character.class_resources, dict):
                sheet.character.class_resources = {}
            sheet.character.class_resources["second_wind"] = True
            sheet.character.class_resources["action_surge"] = True
            for res in getattr(sheet.character, "custom_resources", []):
                if isinstance(res, dict) and res.get("reset_on") == "short":
                    res["current"] = res.get("max", 0)
            if hasattr(sheet, "refresh_custom_resources_ui"):
                try: sheet.refresh_custom_resources_ui()
                except Exception: pass
            c_class = str(getattr(sheet.character, "char_class", "")).strip().lower()
            if "warlock" in c_class:
                for lvl, slot in getattr(sheet.character, "spell_slots", {}).items():
                    if isinstance(slot, dict) and "current" in slot:
                        slot["current"] = slot.get("max", 0)
                        if hasattr(sheet, "slot_vars") and str(lvl) in sheet.slot_vars:
                            v = sheet.slot_vars[str(lvl)]
                            if isinstance(v, dict) and "current" in v:
                                v["current"].set(slot["current"])
                            elif hasattr(v, "set"):
                                v.set(slot["current"])
            
            if sheet.manager:
                sheet.manager.update_character(sheet.character)
            if hasattr(sheet, "on_save_callback") and sheet.on_save_callback:
                try: sheet.on_save_callback(sheet.character)
                except Exception: pass
                
            tot_healed = sum(d.get("healed", 0) for d in spent_dice)
            if sheet.roll_callback:
                chat_msg = f"[RIPOSO BREVE] {sheet.character.name} conclude il riposo breve. Dadi spesi: {len(spent_dice)}. PF recuperati: +{tot_healed} (PF attuali: {sheet.character.hp_current}/{sheet.character.hp_max}, Dadi rimasti: {sheet.character.hit_dice_current}/{sheet.character.hit_dice_total})."
                sheet.roll_callback("0d0", chat_msg)
            win.destroy()

        btn_row = tk.Frame(container, bg=BG_COLOR)
        btn_row.pack(fill=tk.X, pady=(4, 0))

        btn_roll_one = ttk.Button(btn_row, text=_t("sheet_short_rest_roll_hd"), command=roll_one, style="Gold.TButton")
        btn_roll_one.pack(side=tk.LEFT, padx=(0, 6))

        btn_roll_all = ttk.Button(btn_row, text=_t("sheet_short_rest_spend_all"), command=roll_all)
        btn_roll_all.pack(side=tk.LEFT, padx=(0, 6))

        char_cls = str(getattr(sheet.character, "char_class", "")).lower()
        if any(k in char_cls for k in ("mago", "wizard")) and not getattr(sheet.character, "arcane_recovery_used", False):
            def do_arcane_rec():
                import math
                lvl = int(getattr(sheet.character, "level", 1) or 1)
                max_rec = math.ceil(lvl / 2)
                rec_dict = {}
                remaining = max_rec
                for s_i in range(1, 6):
                    s_str = str(s_i)
                    slot = sheet.character.spell_slots.get(s_str, {})
                    cur = slot.get("current", 0) if isinstance(slot, dict) else (slot[0] if isinstance(slot, list) and len(slot) >= 2 else 0)
                    mx = slot.get("max", 0) if isinstance(slot, dict) else (slot[1] if isinstance(slot, list) and len(slot) >= 2 else 0)
                    missing = max(0, mx - cur)
                    while missing > 0 and remaining >= s_i:
                        rec_dict[s_i] = rec_dict.get(s_i, 0) + 1
                        missing -= 1
                        remaining -= s_i
                if rec_dict:
                    ok, msg = sheet.character.arcane_recovery(rec_dict)
                    if ok:
                        log_msg(f"✨ {msg}")
                        btn_arcane.config(state=tk.DISABLED)
                else:
                    messagebox.showinfo("Recupero Arcano", f"Nessuno slot incantesimo (1°-5°) da recuperare (Max recuperabile: {max_rec} livelli).", parent=win)

            btn_arcane = ttk.Button(btn_row, text="✨ Recupero Arcano", command=do_arcane_rec, style="Gold.TButton")
            btn_arcane.pack(side=tk.LEFT, padx=(0, 6))

        btn_finish = ttk.Button(btn_row, text=_t("sheet_short_rest_finish"), command=finish_rest)
        btn_finish.pack(side=tk.RIGHT)
        win.protocol("WM_DELETE_WINDOW", finish_rest)

    @staticmethod
    def long_rest(sheet):
        """Esegue il riposo lungo conforme a D&D 5e RAW."""
        if hasattr(sheet, 'long_rest_callback') and sheet.long_rest_callback:
            sheet.long_rest_callback()
        else:
            if messagebox.askyesno("Riposo Lungo", "Effettuare un riposo lungo?"):
                sheet.character.long_rest()
                sheet.load_data()
                if sheet.manager:
                    sheet.manager.update_character(sheet.character)
                if hasattr(sheet, "on_save_callback") and sheet.on_save_callback:
                    try: sheet.on_save_callback(sheet.character)
                    except Exception: pass
                messagebox.showinfo("Riposo Lungo", "Hai effettuato un riposo lungo! HP, Dadi Vita, Tiri contro la Morte e Slot Incantesimo sono stati recuperati.")

    @staticmethod
    def roll_death_save(sheet):
        """Effettua un tiro salvezza su morte conforme a D&D 5e RAW."""
        roll = random.randint(1, 20)
        if not hasattr(sheet.character, "death_saves"):
            sheet.character.death_saves = {"successes": 0, "failures": 0}
            
        succ = sheet.character.death_saves.get("successes", 0)
        fail = sheet.character.death_saves.get("failures", 0)
        conds = getattr(sheet.character, "conditions", [])
        
        flavor = ""
        if roll == 1:
            fail += 2
            flavor = "💀 FALLIMENTO CRITICO (1 Naturale)! (2 fallimenti)"
        elif roll <= 9:
            fail += 1
            flavor = "❌ Fallimento."
        elif roll <= 19:
            succ += 1
            flavor = "✅ Successo."
        elif roll == 20:
            sheet.character.hp_current = 1
            sheet.hp_cur_var.set(1)
            succ = 0
            fail = 0
            if "Incosciente" in conds:
                conds.remove("Incosciente")
            flavor = "🌟 SUCCESSO CRITICO (20 Naturale)! Ti risvegli con 1 HP."

        if roll != 20:
            succ = min(3, succ)
            fail = min(3, fail)
            if fail >= 3:
                if "Morto" not in conds:
                    conds.append("Morto")
                flavor += " 💀 Sei MORTO!"
            elif succ >= 3:
                if "Stabilizzato" not in conds:
                    conds.append("Stabilizzato")
                flavor += " 🩹 Ti sei STABILIZZATO!"

        sheet.character.conditions = conds
        sheet.character.death_saves["successes"] = succ
        sheet.character.death_saves["failures"] = fail
        sheet.update_death_saves_ui()
        if sheet.manager:
            sheet.manager.update_character(sheet.character)
        if hasattr(sheet, "on_save_callback") and sheet.on_save_callback:
            try: sheet.on_save_callback(sheet.character)
            except Exception: pass

        if sheet.roll_callback:
            chat_msg = f"[TS MORTE] {sheet.character.name} ottiene {roll}. {flavor} (Successi: {succ}/3, Fallimenti: {fail}/3)"
            sheet.roll_callback(f"1d20={roll}", chat_msg)
        else:
            messagebox.showinfo("Tiro Salvezza Morte", f"Hai tirato: {roll}\n{flavor}\n\nSuccessi: {succ}/3\nFallimenti: {fail}/3", parent=sheet)

