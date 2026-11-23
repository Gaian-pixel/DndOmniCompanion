"""ClientGUI reaction & saving-throw prompt dialog mixin."""

import tkinter as tk
from tkinter import ttk

from common.protocol import (
    make_reaction_response,
    make_save_result,
    make_update_full_sheet_request,
)
from common.theme import (
    apply_modern_window_style,
    BG_COLOR,
    TEXT_COLOR,
    FONT_REGULAR,
)


class ClientReactionPromptsMixin:
    """Mixin encapsulating interactive reaction and saving-throw prompt windows on ClientGUI."""

    def _get_available_reaction_slots(self, min_level: int = 1):
        """Ritorna la lista ordinata di livelli di slot disponibili >= min_level (inclusi Patti Warlock)."""
        choices = []
        char = getattr(self, "active_character", None)
        if not char:
            return choices
        slots = getattr(char, "spell_slots", None)
        if isinstance(slots, dict):
            for s_lvl in range(max(1, int(min_level)), 10):
                sl_d = slots.get(str(s_lvl), {})
                cv = sl_d.get("current", 0) if isinstance(sl_d, dict) else (sl_d[0] if isinstance(sl_d, list) and sl_d else 0)
                if cv > 0:
                    choices.append(s_lvl)
        pact = getattr(char, "pact_slots", None)
        if isinstance(pact, dict) and pact.get("current", 0) > 0 and int(pact.get("level", 0) or 0) >= int(min_level):
            p_lvl = int(pact["level"])
            if p_lvl not in choices:
                choices.append(p_lvl)
        choices.sort()
        return choices

    def _consume_reaction_slot_local(self, min_level: int = 1, prefer_level: int = None) -> bool:
        """Consuma localmente uno slot (Patto o standard) >= min_level e sincronizza la scheda sul server."""
        char = getattr(self, "active_character", None)
        if not char:
            return False
        choices = self._get_available_reaction_slots(min_level=min_level)
        if not choices:
            return False
        target_lvl = int(prefer_level) if (prefer_level and int(prefer_level) in choices) else choices[0]
        consumed = False
        pact = getattr(char, "pact_slots", None)
        if isinstance(pact, dict) and pact.get("current", 0) > 0 and int(pact.get("level", 0) or 0) == target_lvl:
            pact["current"] = max(0, pact.get("current", 1) - 1)
            consumed = True
        elif hasattr(char, "spell_slots") and isinstance(char.spell_slots, dict):
            sl = char.spell_slots.get(str(target_lvl))
            if isinstance(sl, dict) and sl.get("current", 0) > 0:
                sl["current"] = max(0, sl.get("current", 1) - 1)
                consumed = True
            elif isinstance(sl, list) and sl and sl[0] > 0:
                sl[0] = max(0, sl[0] - 1)
                consumed = True
        if consumed:
            if hasattr(self, "character_manager") and self.character_manager:
                self.character_manager.save_characters()
            if getattr(self, "network", None):
                self.network.send(make_update_full_sheet_request(char.to_dict()))
        return consumed

    def handle_prompt_reaction(self, data):
        reaction_type = data.get("reaction_type")
        source_name = data.get("source_name", "Un'entità")
        details = data.get("details", {})

        if reaction_type == "OPPORTUNITY_ATTACK":
            win = tk.Toplevel(self.master)
            win.transient(self.master)
            win.grab_set()
            apply_modern_window_style(win)
            win.title("⚔️ Attacco d'Opportunità (Reazione)")
            win.minsize(420, 200)

            w_lbl = details.get("weapon_name") or "arma da mischia"
            tk.Label(win, text="⚔️ REAZIONE: ATTACCO D'OPPORTUNITÀ", font=("Georgia", 13, "bold"), fg="#F59E0B", bg="#1E2024").pack(fill=tk.X, pady=8)
            msg = f"{source_name} sta uscendo dalla tua portata di mischia senza disimpegnarsi!\n\nVuoi spendere la tua REAZIONE per sferrare un Attacco d'Opportunità ({w_lbl})?"
            tk.Label(win, text=msg, font=FONT_REGULAR, fg=TEXT_COLOR, bg=BG_COLOR, justify="center").pack(padx=16, pady=10)

            btn_frame = tk.Frame(win, bg=BG_COLOR)
            btn_frame.pack(pady=12)

            def accept():
                self.reaction_spent = True
                if hasattr(self, "update_action_economy_ui"):
                    self.update_action_economy_ui()
                self.network.send(make_reaction_response("OPPORTUNITY_ATTACK", True, self.name, source_name, details))
                self.show_toast(f"Attacco d'Opportunità sferrato contro {source_name}!", title="⚔️ Reazione Usata", toast_type="success")
                win.destroy()

            def decline():
                self.network.send(make_reaction_response("OPPORTUNITY_ATTACK", False, self.name, source_name, details))
                win.destroy()

            win.protocol("WM_DELETE_WINDOW", decline)
            win.bind("<Escape>", lambda e: decline())
            ttk.Button(btn_frame, text="⚔️ Sferra Attacco (Spendi Reazione)", command=accept, style="Gold.TButton").pack(side=tk.LEFT, padx=6)
            ttk.Button(btn_frame, text="Ignora", command=decline).pack(side=tk.LEFT, padx=6)

        elif reaction_type == "SHIELD_SPELL":
            win = tk.Toplevel(self.master)
            win.transient(self.master)
            win.grab_set()
            apply_modern_window_style(win)
            win.title("🛡️ Reazione: Incantesimo Scudo")
            win.minsize(440, 220)

            hit_roll = details.get("hit_roll", 15)
            atk_weapon = details.get("weapon_name", "un attacco")
            current_ac = details.get("current_ac", 12)

            tk.Label(win, text="🛡️ REAZIONE: INCANTESIMO SCUDO", font=("Georgia", 13, "bold"), fg="#60A5FA", bg="#1E2024").pack(fill=tk.X, pady=8)
            msg = f"{source_name} ti sta colpendo con {atk_weapon}!\n(Tiro per Colpire: {hit_roll} vs la tua CA {current_ac})\n\nVuoi spendere uno slot di 1° livello per lanciare SCUDO?\nOttieni +5 CA (totale {current_ac + 5}), che farà fallire l'attacco!"
            tk.Label(win, text=msg, font=FONT_REGULAR, fg=TEXT_COLOR, bg=BG_COLOR, justify="center").pack(padx=16, pady=8)

            btn_frame = tk.Frame(win, bg=BG_COLOR)
            btn_frame.pack(pady=12)

            avail_shield = self._get_available_reaction_slots(min_level=1)

            def accept():
                send_details = dict(details) if isinstance(details, dict) else {}
                if avail_shield:
                    send_details["slot_level"] = avail_shield[0]
                    if self._consume_reaction_slot_local(min_level=1, prefer_level=avail_shield[0]):
                        send_details["slot_consumed"] = True
                self.reaction_spent = True
                if hasattr(self, "update_action_economy_ui"):
                    self.update_action_economy_ui()
                self.network.send(make_reaction_response("SHIELD_SPELL", True, self.name, source_name, send_details))
                self.show_toast("Incantesimo Scudo attivato! (+5 CA)", title="🛡️ Scudo", toast_type="success")
                win.destroy()

            def decline():
                self.network.send(make_reaction_response("SHIELD_SPELL", False, self.name, source_name, details))
                win.destroy()

            win.protocol("WM_DELETE_WINDOW", decline)
            win.bind("<Escape>", lambda e: decline())
            shield_btn_state = "normal" if (avail_shield or not self.active_character) else "disabled"
            ttk.Button(btn_frame, text="🛡️ Lancia Scudo (+5 CA)", command=accept, style="Primary.TButton", state=shield_btn_state).pack(side=tk.LEFT, padx=6)
            ttk.Button(btn_frame, text="Subisci Attacco", command=decline).pack(side=tk.LEFT, padx=6)

        elif reaction_type == "UNCANNY_DODGE":
            dmg_taken = int(details.get("damage_taken", 0) or 0)
            wep_name = details.get("weapon_name", "Attacco")
            win = tk.Toplevel(self.master)
            win.title("🗡️ Schivata Prodigiosa (Reazione)")
            win.geometry("420x210")
            win.transient(self.master)
            win.grab_set()
            apply_modern_window_style(win)
            ttk.Label(
                win,
                text=f"{source_name} ti ha colpito con {wep_name} infliggendo {dmg_taken} danni!\nVuoi usare la tua Reazione per Schivata Prodigiosa (danni dimezzati a {dmg_taken // 2})?",
                wraplength=390,
                justify="center"
            ).pack(pady=16, padx=14)
            btn_frame = ttk.Frame(win)
            btn_frame.pack(pady=8)
            def accept_ud():
                self.reaction_spent = True
                self.update_action_economy_ui()
                self.network.send(make_reaction_response("UNCANNY_DODGE", True, self.name, source_name, details))
                win.destroy()
            def decline_ud():
                self.network.send(make_reaction_response("UNCANNY_DODGE", False, self.name, source_name, details))
                win.destroy()
            win.protocol("WM_DELETE_WINDOW", decline_ud)
            win.bind("<Escape>", lambda e: decline_ud())
            ttk.Button(btn_frame, text="🗡️ Dimezza Danni (Reazione)", command=accept_ud, style="Primary.TButton").pack(side=tk.LEFT, padx=6)
            ttk.Button(btn_frame, text="Subisci Tutti i Danni", command=decline_ud).pack(side=tk.LEFT, padx=6)

        elif reaction_type == "COUNTERSPELL":
            spell_name_cs = details.get("spell_name", "Incantesimo")
            spell_lvl_cs = int(details.get("spell_level", 3) or 3)
            win = tk.Toplevel(self.master)
            win.title("✋ Reazione: Controincantesimo")
            win.geometry("450x255")
            win.transient(self.master)
            win.grab_set()
            apply_modern_window_style(win)
            ttk.Label(
                win,
                text=f"{source_name} sta lanciando {spell_name_cs} (Liv. {spell_lvl_cs})!\nVuoi usare la tua Reazione per lanciare Controincantesimo?",
                wraplength=410,
                justify="center"
            ).pack(pady=(14, 8), padx=14)
            slot_choices = self._get_available_reaction_slots(min_level=3)
            slot_var = tk.StringVar(value=str(slot_choices[0] if slot_choices else 3))
            if slot_choices:
                slot_row = ttk.Frame(win)
                slot_row.pack(pady=4)
                ttk.Label(slot_row, text="Slot incantesimo:").pack(side=tk.LEFT, padx=4)
                slot_cb = ttk.Combobox(slot_row, textvariable=slot_var, values=[str(s) for s in slot_choices], state="readonly", width=6)
                slot_cb.pack(side=tk.LEFT, padx=4)
            btn_frame = ttk.Frame(win)
            btn_frame.pack(pady=10)
            def accept_cs():
                try:
                    use_lvl = int(slot_var.get() or 3)
                except (TypeError, ValueError):
                    use_lvl = 3
                cs_details = dict(details) if isinstance(details, dict) else {}
                cs_details["slot_level"] = use_lvl
                if self._consume_reaction_slot_local(min_level=3, prefer_level=use_lvl):
                    cs_details["slot_consumed"] = True
                self.reaction_spent = True
                self.update_action_economy_ui()
                self.network.send(make_reaction_response("COUNTERSPELL", True, self.name, source_name, cs_details))
                win.destroy()
            def decline_cs():
                self.network.send(make_reaction_response("COUNTERSPELL", False, self.name, source_name, details))
                win.destroy()
            win.protocol("WM_DELETE_WINDOW", decline_cs)
            win.bind("<Escape>", lambda e: decline_cs())
            cs_btn = ttk.Button(
                btn_frame,
                text=f"✋ Lancia Controincantesimo (Liv. {slot_var.get()})",
                command=accept_cs,
                style="Primary.TButton",
                state=("normal" if (slot_choices or not self.active_character) else "disabled"),
            )
            cs_btn.pack(side=tk.LEFT, padx=6)
            def _update_cs_lbl(*_a):
                if cs_btn.winfo_exists():
                    cs_btn.config(text=f"✋ Lancia Controincantesimo (Liv. {slot_var.get()})")
            slot_var.trace_add("write", _update_cs_lbl)
            ttk.Button(btn_frame, text="Lascia Lanciare", command=decline_cs).pack(side=tk.LEFT, padx=6)

        elif reaction_type in ("ABSORB_ELEMENTS", "HELLISH_REBUKE", "SILVERY_BARBS"):
            slot_choices = self._get_available_reaction_slots(min_level=1)
            win = tk.Toplevel(self.master)
            win.geometry("450x255")
            win.transient(self.master)
            win.grab_set()
            apply_modern_window_style(win)
            slot_var = tk.StringVar(value=str(slot_choices[0] if slot_choices else 1))
            dmg_tp = details.get("damage_type", "Fuoco")
            dmg_inc = int(details.get("dmg_to_hp", details.get("dmg_dealt", 0)) or 0)
            if reaction_type == "ABSORB_ELEMENTS":
                win.title("🔥 Reazione: Assorbire Elementi")
                prompt_txt = (
                    f"{source_name} ti ha inflitto {dmg_inc} danni da {dmg_tp}!\n"
                    f"Vuoi usare la tua Reazione per Assorbire Elementi (Resistenza a {dmg_tp}, danni dimezzati + d6 bonus al prossimo colpo in mischia)?"
                )
                btn_lbl = "🔥 Assorbi Elementi"
            elif reaction_type == "HELLISH_REBUKE":
                win.title("🔥 Reazione: Intimorire Infernale")
                prompt_txt = (
                    f"{source_name} ti ha appena colpito infliggendo {dmg_inc} danni!\n"
                    f"Vuoi usare la tua Reazione per scagliare Intimorire Infernale (2d10 Fuoco base, TS DES)? "
                )
                btn_lbl = "🔥 Intimorire Infernale"
            else:
                win.title("✨ Reazione: Beffa Argentea")
                prompt_txt = (
                    f"{source_name} ha ottenuto un tiro favorevole!\n"
                    f"Vuoi usare Beffa Argentea (Slot Liv. 1) per imporgli di ritirare e dare Vantaggio a un alleato?"
                )
                btn_lbl = "✨ Lancia Beffa Argentea"

            ttk.Label(win, text=prompt_txt, wraplength=410, justify="center").pack(pady=(14, 8), padx=14)
            if slot_choices and reaction_type in ("ABSORB_ELEMENTS", "HELLISH_REBUKE"):
                slot_row = ttk.Frame(win)
                slot_row.pack(pady=4)
                ttk.Label(slot_row, text="Slot incantesimo:").pack(side=tk.LEFT, padx=4)
                ttk.Combobox(slot_row, textvariable=slot_var, values=[str(s) for s in slot_choices], state="readonly", width=6).pack(side=tk.LEFT, padx=4)

            btn_frame = ttk.Frame(win)
            btn_frame.pack(pady=10)
            def accept_rx():
                try:
                    use_lvl = int(slot_var.get() or 1)
                except (TypeError, ValueError):
                    use_lvl = 1
                rx_details = dict(details) if isinstance(details, dict) else {}
                rx_details["slot_level"] = use_lvl if reaction_type != "SILVERY_BARBS" else (slot_choices[0] if slot_choices else 1)
                if self._consume_reaction_slot_local(min_level=1, prefer_level=rx_details["slot_level"]):
                    rx_details["slot_consumed"] = True
                self.reaction_spent = True
                if hasattr(self, "update_action_economy_ui"):
                    self.update_action_economy_ui()
                self.network.send(make_reaction_response(reaction_type, True, self.name, source_name, rx_details))
                win.destroy()

            def decline_rx():
                self.network.send(make_reaction_response(reaction_type, False, self.name, source_name, details))
                win.destroy()

            win.protocol("WM_DELETE_WINDOW", decline_rx)
            win.bind("<Escape>", lambda e: decline_rx())
            rx_btn = ttk.Button(
                btn_frame,
                text=f"{btn_lbl} (Liv. {slot_var.get()})",
                command=accept_rx,
                style="Primary.TButton",
                state=("normal" if (slot_choices or not self.active_character) else "disabled"),
            )
            rx_btn.pack(side=tk.LEFT, padx=6)
            if reaction_type in ("ABSORB_ELEMENTS", "HELLISH_REBUKE"):
                def _upd_rx_lbl(*_a):
                    if rx_btn.winfo_exists():
                        rx_btn.config(text=f"{btn_lbl} (Liv. {slot_var.get()})")
                slot_var.trace_add("write", _upd_rx_lbl)
            ttk.Button(btn_frame, text="Ignora", command=decline_rx).pack(side=tk.LEFT, padx=6)

        elif reaction_type == "DEFLECT_MISSILES":
            inc_dmg = int(details.get("incoming_damage", 0) or 0)
            win = tk.Toplevel(self.master)
            win.title("🥋 Reazione: Deflettere Missili")
            win.geometry("420x210")
            win.transient(self.master)
            win.grab_set()
            apply_modern_window_style(win)
            ttk.Label(
                win,
                text=f"{source_name} ti ha colpito a distanza infliggendo {inc_dmg} danni!\nVuoi usare la tua Reazione per Deflettere Missili (1d10 + DES + Liv. Monaco)?",
                wraplength=390,
                justify="center"
            ).pack(pady=16, padx=14)
            btn_frame = ttk.Frame(win)
            btn_frame.pack(pady=8)
            def accept_dm():
                self.reaction_spent = True
                self.update_action_economy_ui()
                self.network.send(make_reaction_response("DEFLECT_MISSILES", True, self.name, source_name, details))
                win.destroy()
            def decline_dm():
                self.network.send(make_reaction_response("DEFLECT_MISSILES", False, self.name, source_name, details))
                win.destroy()
            win.protocol("WM_DELETE_WINDOW", decline_dm)
            win.bind("<Escape>", lambda e: decline_dm())
            ttk.Button(btn_frame, text="🥋 Defletti Missile (Reazione)", command=accept_dm, style="Primary.TButton").pack(side=tk.LEFT, padx=6)
            ttk.Button(btn_frame, text="Subisci Danni", command=decline_dm).pack(side=tk.LEFT, padx=6)

        elif reaction_type in ("DEFENSIVE_DUELIST", "ILLUSORY_SELF", "DAMPEN_ELEMENTS"):
            title_map = {
                "DEFENSIVE_DUELIST": ("⚔️ Reazione: Duellante Difensivo", f"{source_name} ti sta per colpire ({details.get('hit_roll')} vs CA {details.get('current_ac')}).\nVuoi aggiungere +{details.get('bonus_ac', 2)} alla CA con arma accurata?", "⚔️ Para (+CA)"),
                "ILLUSORY_SELF": ("🎭 Reazione: Sé Illusorio", f"{source_name} ti ha colpito!\nVuoi interporre un duplicato illusorio per far mancare automaticamente l'attacco (1/riposo breve)?", "🎭 Sé Illusorio (Manca)"),
                "DAMPEN_ELEMENTS": ("🌿 Reazione: Smorzare Elementi", f"{source_name} infligge danni da {details.get('damage_type', 'elemento')}!\nVuoi dimezzare i danni con Resistenza in Reazione?", "🌿 Smorza (Dimezza)"),
            }
            dlg_t, dlg_msg, btn_txt = title_map[reaction_type]
            win = tk.Toplevel(self.master)
            win.title(dlg_t)
            win.geometry("430x210")
            win.transient(self.master)
            win.grab_set()
            apply_modern_window_style(win)
            ttk.Label(win, text=dlg_msg, wraplength=400, justify="center").pack(pady=16, padx=14)
            btn_frame = ttk.Frame(win)
            btn_frame.pack(pady=8)
            def accept_gen():
                self.reaction_spent = True
                self.update_action_economy_ui()
                self.network.send(make_reaction_response(reaction_type, True, self.name, source_name, details))
                win.destroy()
            def decline_gen():
                self.network.send(make_reaction_response(reaction_type, False, self.name, source_name, details))
                win.destroy()
            win.protocol("WM_DELETE_WINDOW", decline_gen)
            win.bind("<Escape>", lambda e: decline_gen())
            ttk.Button(btn_frame, text=btn_txt, command=accept_gen, style="Primary.TButton").pack(side=tk.LEFT, padx=6)
            ttk.Button(btn_frame, text="Ignora", command=decline_gen).pack(side=tk.LEFT, padx=6)

    def handle_prompt_save(self, data):
        stat = data.get("stat")
        dc = data.get("dc")
        damage_formula = data.get("damage_formula")
        half_on_success = data.get("half_on_success")
        source_name = data.get("source_name")
        damage_type = data.get("damage_type", "Fuoco")
        has_advantage = bool(data.get("has_advantage", False))
        has_disadvantage = bool(data.get("has_disadvantage", False))

        # Controllo locale Incantatore da Guerra (War Caster PHB p. 170) per TS di Concentrazione
        src_low = str(source_name or "").lower()
        if str(stat or "").upper() == "COS" and ("concentrazion" in src_low or "concentration" in src_low):
            if self.active_character:
                from common.dnd5e_tables import entity_has_keyword
                if entity_has_keyword(self.active_character, "incantatore da guerra", "war caster"):
                    has_advantage = True

        eff_adv = has_advantage and not has_disadvantage
        eff_dis = has_disadvantage and not has_advantage

        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        win.title("Tiro Salvezza Richiesto!")
        win.minsize(360, 260)
        apply_modern_window_style(win)

        ttk.Label(win, text=f"{source_name} richiede un TS!", font=("Georgia", 12, "bold"), foreground="#D4AF37").pack(pady=(10, 5))
        ttk.Label(win, text=f"Statistica: {stat} | CD: {dc}").pack(pady=5)
        if eff_adv:
            ttk.Label(win, text="🟢 Tiro con VANTAGGIO", foreground="#22C55E", font=("Segoe UI", 9, "bold")).pack()
        elif eff_dis:
            ttk.Label(win, text="🔴 Tiro con SVANTAGGIO", foreground="#EF4444", font=("Segoe UI", 9, "bold")).pack()

        if damage_formula:
            ttk.Label(win, text=f"Danno potenziale: {damage_formula}").pack()

        def do_roll():
            from common.dice import roll_dice
            mod = 0
            if self.active_character:
                if hasattr(self.active_character, "get_effective_save_bonus"):
                    mod = self.active_character.get_effective_save_bonus(stat)
                else:
                    attr = self.active_character.attributes
                    if stat in attr:
                        mod = (int(attr[stat]) - 10) // 2

            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            adv_tok = " adv" if eff_adv else (" dis" if eff_dis else "")
            res = roll_dice(f"1d20{mod_str}{adv_tok}")

            is_crit = res.get("is_crit", res["rolls"][0] == 20)
            is_fail = res.get("is_fumble", res["rolls"][0] == 1)

            if is_crit:
                self.show_toast(
                    f"20 NATURALE sul Tiro Salvezza su {stat}! (Totale: {res['total']})",
                    title="🌟 20 Naturale!",
                    toast_type="gold",
                )
            elif is_fail:
                self.show_toast(
                    f"1 NATURALE sul Tiro Salvezza su {stat}! (Totale: {res['total']})",
                    title="💀 1 Naturale!",
                    toast_type="danger",
                )

            self.network.send(make_save_result(stat, res["total"], is_crit, is_fail, dc, damage_formula, half_on_success, source_name, damage_type=damage_type))
            win.destroy()

        btn_suffix = " [Vantaggio]" if eff_adv else (" [Svantaggio]" if eff_dis else "")
        ttk.Button(win, text=f"Tira Salvezza ({stat}){btn_suffix}", command=do_roll, style="Danger.TButton").pack(pady=20)
