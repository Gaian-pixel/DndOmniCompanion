"""DM_GUI campaign, session persistence, scene audio, and player approval dialogs mixin."""

import base64
import copy
import json
import os
import tkinter as tk
from tkinter import filedialog, scrolledtext, simpledialog, ttk

from common.i18n import _t
from common.messagebox import messagebox
from common.network_utils import broadcast
from common.protocol import make_chat_broadcast, make_game_state
from common.theme import (
    ACCENT_GOLD,
    ACCENT_GREEN,
    BG_COLOR,
    BORDER_COLOR,
    FONT_BOLD,
    FONT_HEADER,
    FONT_MAIN,
    FONT_SMALL,
    SURFACE_COLOR,
    TEXT_COLOR,
    TEXT_DARK,
    TEXT_MUTED,
    apply_modern_window_style,
)


def _safe_import_int(val, default=0) -> int:
    try:
        if val is None or isinstance(val, bool):
            return int(default)
        if isinstance(val, str):
            val = val.strip()
            if not val:
                return int(default)
        return int(float(val))
    except (ValueError, TypeError):
        return int(default)


def find_free_spawn_hex(game_state, anchor_hex=None, exclude_name=None) -> list:
    """Return the first unoccupied non-wall hex near anchor_hex, map spawn, or origin within bounds."""
    cur_map = getattr(game_state, "current_map", None) or {}
    if anchor_hex is not None:
        if hasattr(anchor_hex, "q") and hasattr(anchor_hex, "r"):
            base_q, base_r = _safe_import_int(anchor_hex.q, 0), _safe_import_int(anchor_hex.r, 0)
        elif isinstance(anchor_hex, (list, tuple)) and len(anchor_hex) >= 2:
            base_q, base_r = _safe_import_int(anchor_hex[0], 0), _safe_import_int(anchor_hex[1], 0)
        else:
            base_q, base_r = 0, 0
    else:
        raw_spawn = cur_map.get("spawn_point") if isinstance(cur_map, dict) else None
        base_q, base_r = (
            (_safe_import_int(raw_spawn[0], 0), _safe_import_int(raw_spawn[1], 0))
            if isinstance(raw_spawn, (list, tuple)) and len(raw_spawn) >= 2
            else (0, 0)
        )
    raw_w = _safe_import_int(cur_map.get("width") if isinstance(cur_map, dict) else None, 0)
    raw_h = _safe_import_int(cur_map.get("height") if isinstance(cur_map, dict) else None, 0)
    has_bounds = (raw_w > 0 and raw_h > 0)

    occupied = {
        (_safe_import_int(p.position[0], 0), _safe_import_int(p.position[1], 0))
        for p in getattr(game_state, "players", [])
        if p.name != exclude_name
        and isinstance(getattr(p, "position", None), (list, tuple))
        and len(p.position) >= 2
    }
    walls = {
        (_safe_import_int(w[0], 0), _safe_import_int(w[1], 0))
        for w in (cur_map.get("walls", []) if isinstance(cur_map, dict) else [])
        if isinstance(w, (list, tuple)) and len(w) >= 2
    }
    max_radius = max(12, raw_w, raw_h)
    offsets = [(0, 0)]
    for radius in range(1, min(max_radius, 30) + 1):
        for dq in range(-radius, radius + 1):
            for dr in range(-radius, radius + 1):
                if max(abs(dq), abs(dr), abs(-dq - dr)) == radius:
                    offsets.append((dq, dr))

    fallback = None
    for dq, dr in offsets:
        cand = (base_q + dq, base_r + dr)
        if cand in occupied or cand in walls:
            continue
        if has_bounds and not (0 <= cand[0] < raw_w and 0 <= cand[1] < raw_h):
            if fallback is None:
                fallback = [cand[0], cand[1]]
            continue
        return [cand[0], cand[1]]
    return fallback if fallback is not None else [base_q, base_r]


def _find_free_party_spawn_hex(game_state, exclude_name=None) -> list:
    """Return the first unoccupied non-wall hex near map spawn or origin within map bounds for tabletop PC placement."""
    return find_free_spawn_hex(game_state, anchor_hex=None, exclude_name=exclude_name)


def import_party_character_to_game_state(game_state, char_dict, spawn_pos=None):
    """Spawn or refresh a saved local Character dict/instance as an active party token in GameState."""
    from common.game_state import Player
    from common.item_modifiers import compute_effective_ac
    from common.character_schema import normalize_character_dict

    raw_orig = char_dict.to_dict() if hasattr(char_dict, "to_dict") else copy.deepcopy(char_dict)
    if not isinstance(raw_orig, dict):
        raise ValueError("Dati personaggio non validi.")
    raw = normalize_character_dict(copy.deepcopy(raw_orig))
    if isinstance(raw, dict):
        for k, v in raw_orig.items():
            raw.setdefault(k, copy.deepcopy(v))
    name = str(raw.get("name", "") or "").strip()
    if not name:
        raise ValueError("Nome personaggio mancante.")

    attrs = raw.get("attributes", {}) if isinstance(raw.get("attributes"), dict) else {}
    dex_val = _safe_import_int(attrs.get("DES", attrs.get("DEX", 10)), 10)
    dex_mod = (dex_val - 10) // 2
    raw_init = raw.get("initiative")
    init_bonus = _safe_import_int(raw_init, dex_mod)
    if raw_init is None or _safe_import_int(raw_init, 0) == 0:
        init_bonus = dex_mod

    try:
        eff_ac = _safe_import_int(compute_effective_ac(raw), 10)
    except Exception:
        eff_ac = _safe_import_int(raw.get("ac", 10), 10)

    max_hp = max(1, _safe_import_int(raw.get("hp_max", raw.get("max_hp", 10)), 10))
    raw_cur_hp = raw.get("hp_current", raw.get("hp", max_hp))
    hp = _safe_import_int(raw_cur_hp, max_hp) if raw_cur_hp is not None else max_hp
    temp_hp = max(0, _safe_import_int(raw.get("temp_hp", 0), 0))
    speed = max(0, _safe_import_int(raw.get("speed", 30), 30))
    speed_unit = raw.get("speed_unit", None)
    avatar_b64 = raw.get("avatar_b64", None)
    pact = raw.get("pact_slots", {}) if isinstance(raw.get("pact_slots"), dict) else {}

    with game_state.lock:
        existing = game_state.find_player(name)
        player = existing or Player(name)
        player.role = "player"
        player.is_party_member = True
        player.is_npc = False
        player.layer = "token"
        player.is_hidden = False
        player._preserve_server_state_on_join = True
        player._preserve_stats_on_join = True
        player.hp = hp
        player.max_hp = max_hp
        player.temp_hp = temp_hp
        player.ac = eff_ac
        player.speed = speed
        player.speed_unit = speed_unit
        player.initiative_bonus = init_bonus
        player.avatar_b64 = avatar_b64
        player.full_sheet = raw
        player.conditions = list(raw.get("conditions", []) or [])
        player.damage_resistances = list(raw.get("damage_resistances", []) or [])
        player.damage_immunities = list(raw.get("damage_immunities", []) or [])
        player.damage_vulnerabilities = list(raw.get("damage_vulnerabilities", []) or [])
        player.exhaustion_level = max(0, _safe_import_int(raw.get("exhaustion_level", 0), 0))
        player.hit_dice_max = max(0, _safe_import_int(raw.get("hit_dice_max", raw.get("hit_dice_total", raw.get("level", 1))), 1))
        player.hit_dice_current = max(0, _safe_import_int(raw.get("hit_dice_current", player.hit_dice_max), player.hit_dice_max))
        player.spell_points_max = max(0, _safe_import_int(raw.get("spell_points_max", 0), 0))
        player.spell_points_current = max(0, _safe_import_int(raw.get("spell_points_current", 0), 0))
        player.inspiration = bool(raw.get("inspiration", False))
        player.size = str(raw.get("size", getattr(player, "size", "Medium")) or "Medium")
        player.creature_type = str(raw.get("creature_type", getattr(player, "creature_type", "Humanoid")) or "Humanoid")
        player.pact_slots_max = max(0, _safe_import_int(pact.get("max", 0), 0))
        player.pact_slots_current = max(0, _safe_import_int(pact.get("current", 0), 0))
        player.pact_slot_level = max(0, _safe_import_int(pact.get("level", 0), 0))
        cur_map = getattr(game_state, "current_map", None) or {}
        walls = {
            (_safe_import_int(w[0], 0), _safe_import_int(w[1], 0))
            for w in (cur_map.get("walls", []) if isinstance(cur_map, dict) else [])
            if isinstance(w, (list, tuple)) and len(w) >= 2
        }
        occupied = {
            (_safe_import_int(p.position[0], 0), _safe_import_int(p.position[1], 0))
            for p in getattr(game_state, "players", [])
            if p.name != name
            and isinstance(getattr(p, "position", None), (list, tuple))
            and len(p.position) >= 2
        }
        if spawn_pos is not None and isinstance(spawn_pos, (list, tuple)) and len(spawn_pos) >= 2:
            cand_pos = (_safe_import_int(spawn_pos[0], 0), _safe_import_int(spawn_pos[1], 0))
            if cand_pos not in walls and cand_pos not in occupied:
                player.position = [cand_pos[0], cand_pos[1]]
            else:
                player.position = _find_free_party_spawn_hex(game_state, exclude_name=name)
        elif not existing:
            player.position = _find_free_party_spawn_hex(game_state, exclude_name=name)
        if not existing:
            game_state.add_player(player)
        if player.check_has_darkvision():
            player.has_darkvision = True
            player.vision_radius = max(12, _safe_import_int(getattr(player, "vision_radius", 6), 6))
    return player


class DMCampaignSessionMixin:
    """Mixin encapsulating DM campaign lifecycle, session save/load, scenes, and player approval prompts."""

    def _sync_gui_after_map_change(self, broadcast_state: bool = True):
        gs = self.server.game_state
        cur_map = getattr(gs, "current_map", None) or {}
        if hasattr(self, "fow_enabled_var"):
            self.fow_enabled_var.set(bool(cur_map.get("fow_enabled", False)))
        if hasattr(self, "top_status_env_lbl") and hasattr(self, "_apply_weather_change"):
            try:
                is_out = bool(cur_map.get("outdoor", True))
                self.top_status_env_lbl.config(
                    text=_t("map_env_outdoor") if is_out else _t("map_env_indoor"),
                    fg=ACCENT_GREEN if is_out else ACCENT_GOLD,
                )
            except Exception:
                pass
        if hasattr(self, "top_status_map_lbl"):
            try:
                m_title = str(cur_map.get("name") or getattr(gs, "active_map_id", "Mappa") or "Mappa")
                self.top_status_map_lbl.config(text=f"🗺️ {m_title[:20]}")
            except Exception:
                pass
        if hasattr(self, "top_status_grid_lbl"):
            try:
                gtype = cur_map.get("grid_type", "hex")
                g_key = {"hex": "grid_hex", "square": "grid_square", "none": "grid_none"}.get(gtype, "grid_hex")
                self.top_status_grid_lbl.config(text=f"🌐 {_t('grid_type_menu')}: {_t(g_key)}")
            except Exception:
                pass
        if hasattr(self, "redraw_map_and_players"):
            self.redraw_map_and_players()
        if hasattr(self, "_sync_player_display_window"):
            try:
                self._sync_player_display_window()
            except Exception:
                pass
        if broadcast_state:
            broadcast(gs, make_game_state(gs.get_state_dict(is_dm=False)))

    def load_map_from_file(self):
        maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
        file_path = filedialog.askopenfilename(initialdir=maps_dir, filetypes=[("Mappe D&D", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                map_data = json.load(f)
            from common.network_utils import resolve_map_image_data
            camp_folder = os.path.dirname(file_path)
            resolve_map_image_data(map_data, extra_dirs=[camp_folder])
            map_data.setdefault("name", os.path.splitext(os.path.basename(file_path))[0])

            self.server.game_state.load_map(map_data)
            self._sync_gui_after_map_change(broadcast_state=True)
            self.log_to_chat(f"[SISTEMA] Mappa '{os.path.basename(file_path)}' caricata.")
        except Exception as e:
            messagebox.showerror("Errore Caricamento", f"Impossibile caricare la mappa: {e}")

    def open_map_manager_dialog(self):
        """Finestra di gestione runtime delle mappe di sessione (Cambio, Creazione, Ridimensiona, Elimina)."""
        win = tk.Toplevel(self.master)
        win.title("🗺️ Gestione & Cambio Mappe Sessione")
        win.minsize(560, 420)
        win.transient(self.master)
        win.grab_set()
        apply_modern_window_style(win)

        gs = self.server.game_state
        if not getattr(gs, "maps", None):
            gs.maps = {}
        if getattr(gs, "current_map", None) and getattr(gs, "active_map_id", None) not in gs.maps:
            cur_id = str(gs.current_map.get("name") or getattr(gs, "active_map_id", None) or "default")
            gs.active_map_id = cur_id
            gs.maps[cur_id] = gs.current_map

        ttk.Label(win, text="Mappe disponibili nella sessione:", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        list_frame = tk.Frame(win, bg="#181B22")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)
        listbox = tk.Listbox(list_frame, bg="#121316", fg="#E5E7EB", selectbackground="#2563EB", font=("Segoe UI", 10))
        listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.config(yscrollcommand=sb.set)

        map_keys = []

        def refresh_list():
            nonlocal map_keys
            listbox.delete(0, tk.END)
            map_keys = list((getattr(gs, "maps", {}) or {}).keys())
            active_id = getattr(gs, "active_map_id", None)
            for k in map_keys:
                m = gs.maps[k]
                gtype = m.get("grid_type", "hex")
                cells = len(m.get("hexes", []))
                prefix = "★ [ATTIVA] " if k == active_id else "   "
                listbox.insert(tk.END, f"{prefix}{k}  ({gtype}, {cells} celle)")

        def get_selected_key():
            sel = listbox.curselection()
            if not sel:
                return None
            idx = sel[0]
            return map_keys[idx] if 0 <= idx < len(map_keys) else None

        def do_switch():
            key = get_selected_key()
            if not key:
                return
            gs.switch_map(key)
            self._sync_gui_after_map_change(broadcast_state=True)
            refresh_list()
            if hasattr(self, "show_toast"):
                self.show_toast(f"Mappa attiva cambiata in '{key}'", title="🗺️ Mappa Attiva", toast_type="success")

        def do_create():
            dlg = tk.Toplevel(win)
            dlg.title("Nuova Mappa Griglia")
            dlg.minsize(340, 260)
            dlg.transient(win)
            dlg.grab_set()
            apply_modern_window_style(dlg)

            name_var = tk.StringVar(value=f"Arena {len(gs.maps) + 1}")
            grid_var = tk.StringVar(value="square")
            cols_var = tk.IntVar(value=24)
            rows_var = tk.IntVar(value=18)
            outdoor_var = tk.BooleanVar(value=True)

            frm = ttk.Frame(dlg, padding=12)
            frm.pack(fill=tk.BOTH, expand=True)
            ttk.Label(frm, text="Nome Mappa:").grid(row=0, column=0, sticky="w", pady=3)
            ttk.Entry(frm, textvariable=name_var, width=22).grid(row=0, column=1, sticky="ew", pady=3)
            ttk.Label(frm, text="Griglia:").grid(row=1, column=0, sticky="w", pady=3)
            ttk.Combobox(frm, textvariable=grid_var, values=["hex", "square", "none"], state="readonly", width=19).grid(row=1, column=1, sticky="ew", pady=3)
            ttk.Label(frm, text="Colonne / Larghezza:").grid(row=2, column=0, sticky="w", pady=3)
            ttk.Spinbox(frm, from_=4, to=120, textvariable=cols_var, width=10).grid(row=2, column=1, sticky="w", pady=3)
            ttk.Label(frm, text="Righe / Altezza:").grid(row=3, column=0, sticky="w", pady=3)
            ttk.Spinbox(frm, from_=4, to=120, textvariable=rows_var, width=10).grid(row=3, column=1, sticky="w", pady=3)
            ttk.Checkbutton(frm, text="Ambiente Esterno (Ciclo Giorno/Notte)", variable=outdoor_var).grid(row=4, column=0, columnspan=2, sticky="w", pady=6)

            def confirm_create():
                created = gs.create_map(
                    name_var.get(),
                    cols=int(cols_var.get() or 20),
                    rows=int(rows_var.get() or 15),
                    grid_type=grid_var.get(),
                    outdoor=bool(outdoor_var.get()),
                    activate=True,
                )
                self._sync_gui_after_map_change(broadcast_state=True)
                dlg.destroy()
                refresh_list()
                self.log_to_chat(f"[SISTEMA] Creata e attivata mappa '{created.get('name')}'.")

            ttk.Button(frm, text="Crea e Attiva", command=confirm_create, style="Success.TButton").grid(row=5, column=0, columnspan=2, pady=10)

        def do_resize():
            cur = getattr(gs, "current_map", None)
            if not cur:
                return
            cols_s = simpledialog.askinteger("Ridimensiona Mappa Attuale", "Numero di colonne (q):", initialvalue=20, minvalue=2, maxvalue=120, parent=win)
            if not cols_s:
                return
            rows_s = simpledialog.askinteger("Ridimensiona Mappa Attuale", "Numero di righe (r):", initialvalue=15, minvalue=2, maxvalue=120, parent=win)
            if not rows_s:
                return
            gs.resize_current_map(cols_s, rows_s)
            self._sync_gui_after_map_change(broadcast_state=False)
            refresh_list()
            self.log_to_chat(f"[SISTEMA] Griglia ridimensionata a {cols_s}x{rows_s} celle.")

        def do_load_file():
            self.load_map_from_file()
            refresh_list()

        def do_delete():
            key = get_selected_key()
            if not key:
                return
            if len(getattr(gs, "maps", {}) or {}) <= 1:
                messagebox.showwarning("Attenzione", "Deve rimanere almeno una mappa nella sessione.", parent=win)
                return
            if messagebox.askyesno("Elimina Mappa", f"Eliminare la mappa '{key}' dalla sessione?", parent=win):
                if gs.delete_map(key):
                    self._sync_gui_after_map_change(broadcast_state=True)
                    refresh_list()

        btn_bar = ttk.Frame(win)
        btn_bar.pack(fill=tk.X, padx=12, pady=(6, 12))
        ttk.Button(btn_bar, text="✅ Attiva Selezionata", command=do_switch, style="Success.TButton").pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar, text="➕ Nuova Mappa", command=do_create, style="Primary.TButton").pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar, text="📐 Ridimensiona Attuale", command=do_resize).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar, text="📂 Carica File", command=do_load_file).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar, text="🗑️ Elimina", command=do_delete, style="Danger.TButton").pack(side=tk.RIGHT, padx=3)

        refresh_list()

    def save_session(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Sessione D&D", "*.json")])
        if not file_path: return
        try:
            self.server.game_state.save_session(file_path)
            messagebox.showinfo("Successo", "Sessione salvata correttamente.")
        except Exception as e:
            messagebox.showerror("Errore Salvataggio", f"Impossibile salvare la sessione: {e}")

    def load_session(self):
        file_path = filedialog.askopenfilename(filetypes=[("Sessione D&D", "*.json")])
        if not file_path: return
        try:
            self.server.game_state.load_session(file_path)
            if self.server.game_state.current_map:
                self.fow_enabled_var.set(self.server.game_state.current_map.get("fow_enabled", False))
            self.redraw_map_and_players()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            messagebox.showinfo("Successo", "Sessione caricata correttamente.")
        except Exception as e:
            messagebox.showerror("Errore Caricamento", f"Impossibile caricare la sessione: {e}")

    def open_session_password_dialog(self):
        """Permette al DM di impostare o rimuovere una password/PIN opzionale per i client in ingresso."""
        cur_pw = getattr(self.server, "session_password", "")
        new_pw = simpledialog.askstring(
            _t("menu_session_password", default="Password / PIN Sessione"),
            "Inserisci il PIN o la password richiesta ai giocatori al JOIN (lascia vuoto per rimuovere la protezione):",
            initialvalue=cur_pw,
            show="*",
            parent=self.master,
        )
        if new_pw is None:
            return
        self.server.set_session_password(new_pw)
        if getattr(self.server, "session_password", ""):
            self.log_to_chat("[SICUREZZA] Password/PIN della sessione impostata dal Dungeon Master.", "Sistema")
            if hasattr(self, "show_toast"):
                self.show_toast("Password / PIN sessione attivata!", title="Sicurezza Sessione", toast_type="success")
        else:
            self.log_to_chat("[SICUREZZA] Protezione password della sessione rimossa.", "Sistema")
            if hasattr(self, "show_toast"):
                self.show_toast("Password sessione rimossa (accesso libero).", title="Sicurezza Sessione", toast_type="info")

    def open_new_campaign_dialog(self):
        from server.campaign_editor_ui import CampaignEditorDialog
        from common.campaign import Campaign
        new_camp = Campaign(name="Nuova Campagna")
        def on_saved(camp):
            camp.apply_to_game_state(self.server.game_state)
            if self.server.game_state.current_map:
                self.fow_enabled_var.set(self.server.game_state.current_map.get("fow_enabled", False))
                self.redraw_map_and_players()
            if hasattr(self, 'lbl_campaign_name'):
                self.lbl_campaign_name.config(text=f"🏰 Campagna: {camp.name}")
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            self.log_to_chat(f"[SISTEMA] Nuova campagna '{camp.name}' creata e applicata.")
        CampaignEditorDialog(self.master, campaign=new_camp, game_state=self.server.game_state, on_save_callback=on_saved)

    def open_load_campaign_dialog(self):
        from server.campaign_editor_ui import CampaignSelectorDialog
        def on_selected(camp):
            camp.apply_to_game_state(self.server.game_state)
            if hasattr(self, "session_ledger") and self.session_ledger:
                self.session_ledger.campaign_name = camp.name
                if getattr(camp, "start_date", None):
                    self.session_ledger.start_game_date = dict(camp.start_date)
                    self.session_ledger.current_game_date = dict(camp.start_date)
                if getattr(camp, "start_weather", None):
                    self.session_ledger.current_weather = camp.start_weather
            if self.server.game_state.current_map:
                self.fow_enabled_var.set(self.server.game_state.current_map.get("fow_enabled", False))
                self.redraw_map_and_players()
            if hasattr(self, 'lbl_campaign_name'):
                self.lbl_campaign_name.config(text=f"🏰 Campagna: {camp.name}")
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            self.log_to_chat(f"[SISTEMA] Campagna '{camp.name}' caricata e attiva.")
            messagebox.showinfo("Campagna Caricata", f"Campagna '{camp.name}' caricata con successo!", parent=self.master)
        CampaignSelectorDialog(self.master, on_select_callback=on_selected)

    def open_campaign_editor_dialog(self):
        from server.campaign_editor_ui import CampaignEditorDialog
        active_camp = getattr(self.server.game_state, 'active_campaign', None)
        if active_camp:
            def on_saved(camp):
                camp.apply_to_game_state(self.server.game_state)
                broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
                self.log_to_chat(f"[SISTEMA] Campagna '{camp.name}' aggiornata.")
            CampaignEditorDialog(self.master, campaign=active_camp, game_state=self.server.game_state, on_save_callback=on_saved)
        else:
            choice = messagebox.askyesno(
                _t("campaign_none_title", default="Nessuna Campagna Attiva"),
                _t("campaign_none_prompt", default="Non c'è una campagna attualmente caricata.\n\nVuoi caricare una campagna esistente?\n(Scegli 'No' per creare una Nuova Campagna)"),
                parent=self.master
            )
            if choice:
                self.open_load_campaign_dialog()
            else:
                self.open_new_campaign_dialog()

    def open_campaign_from_custom_path(self):
        from common.campaign import Campaign
        target = filedialog.askopenfilename(
            title="Seleziona file manifesto 'campaign.json'",
            filetypes=[("Manifest Campagna", "campaign.json"), ("File JSON", "*.json"), ("Tutti i file", "*.*")],
            parent=self.master
        )
        if not target:
            if messagebox.askyesno("Scegli Cartella", "Vuoi selezionare una cartella di campagna invece di un singolo file?", parent=self.master):
                target = filedialog.askdirectory(title="Seleziona la cartella della campagna", parent=self.master)
        if not target:
            return
        try:
            camp = Campaign.load(target)
            camp.apply_to_game_state(self.server.game_state)
            if hasattr(self, "session_ledger") and self.session_ledger:
                self.session_ledger.campaign_name = camp.name
                if getattr(camp, "start_date", None):
                    self.session_ledger.start_game_date = dict(camp.start_date)
                    self.session_ledger.current_game_date = dict(camp.start_date)
                if getattr(camp, "start_weather", None):
                    self.session_ledger.current_weather = camp.start_weather
            if self.server.game_state.current_map:
                self.fow_enabled_var.set(self.server.game_state.current_map.get("fow_enabled", False))
                self.redraw_map_and_players()
            if hasattr(self, 'lbl_campaign_name'):
                self.lbl_campaign_name.config(text=f"🏰 Campagna: {camp.name}")
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            self.log_to_chat(f"[SISTEMA] Campagna '{camp.name}' caricata da {camp.folder_path} e attiva.")
            messagebox.showinfo("Campagna Caricata", f"Campagna '{camp.name}' caricata con successo da:\n{camp.folder_path}", parent=self.master)
        except Exception as e:
            messagebox.showerror("Errore Caricamento", f"Impossibile caricare la campagna: {e}", parent=self.master)

    def save_active_campaign(self):
        active_camp = getattr(self.server.game_state, 'active_campaign', None)
        if not active_camp:
            messagebox.showwarning("Nessuna Campagna", "Non c'è una campagna attiva da salvare.", parent=self.master)
            return
        if not getattr(active_camp, 'folder_path', None):
            return self.save_active_campaign_as()
        try:
            saved_dir = active_camp.save()
            self.log_to_chat(f"[SISTEMA] Campagna '{active_camp.name}' salvata in: {saved_dir}")
            if hasattr(self, "show_toast"):
                self.show_toast(f"Campagna '{active_camp.name}' salvata.", title="💾 Salva Campagna", toast_type="success")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare la campagna: {e}", parent=self.master)

    def save_active_campaign_as(self):
        active_camp = getattr(self.server.game_state, 'active_campaign', None)
        if not active_camp:
            messagebox.showwarning("Nessuna Campagna", "Non c'è una campagna attiva da salvare.", parent=self.master)
            return
        from common.campaign import DEFAULT_CAMPAIGNS_DIR
        initial_dir = active_camp.folder_path or DEFAULT_CAMPAIGNS_DIR
        if not os.path.exists(initial_dir):
            initial_dir = DEFAULT_CAMPAIGNS_DIR
        selected = filedialog.askdirectory(
            title="Salva Campagna Attiva Con Nome - Seleziona Cartella di Destinazione",
            initialdir=initial_dir,
            parent=self.master
        )
        if not selected:
            return
        try:
            manifest_path = os.path.join(selected, "campaign.json")
            if os.path.exists(manifest_path):
                if not messagebox.askyesno("Conferma Sovrascrittura", f"Nella cartella selezionata è già presente un file 'campaign.json':\n{selected}\n\nVuoi sovrascriverlo con questa campagna?", parent=self.master):
                    return
            folder = active_camp.save(target_folder=selected)
            self.log_to_chat(f"[SISTEMA] Campagna '{active_camp.name}' salvata in: {folder}")
            messagebox.showinfo("Campagna Salvata", f"Campagna '{active_camp.name}' salvata con successo in:\n{folder}", parent=self.master)
        except Exception as e:
            messagebox.showerror("Errore Salvataggio", f"Impossibile salvare la campagna: {e}", parent=self.master)

    def close_active_campaign(self):
        active_camp = getattr(self.server.game_state, 'active_campaign', None)
        if not active_camp:
            messagebox.showinfo(_t("campaign_none_title", default="Nessuna Campagna"), _t("msg_no_active_campaign", default="Nessuna campagna attiva da chiudere."), parent=self.master)
            return
        camp_name = active_camp.name
        self.server.game_state.active_campaign = None
        if hasattr(self, 'lbl_campaign_name'):
            self.lbl_campaign_name.config(text=_t("campaign_none"))
        self.log_to_chat(f"[SISTEMA] Campagna '{camp_name}' chiusa. Modalità sessione libera attiva.")
        self.show_toast(f"Campagna '{camp_name}' chiusa.", title="Campagna", toast_type="info")

    def open_live_flow_controller(self):
        from server.dm_live_flow import DMLiveFlowDialog
        DMLiveFlowDialog(self, self.server.game_state, self.session_ledger)

    def open_session_chronicle_dialog(self):
        from server.dm_live_flow import SessionChronicleDialog
        active_camp = getattr(self.server.game_state, 'active_campaign', None)
        SessionChronicleDialog(self, self.session_ledger, campaign=active_camp)

    def open_campaign_journal_dialog(self):
        from server.dm_journal_dialog import DMJournalDialog
        DMJournalDialog(self, self.server.game_state)

    def deploy_campaign_encounter_dialog(self):
        active_camp = getattr(self.server.game_state, 'active_campaign', None)
        if not active_camp or not active_camp.encounters:
            if messagebox.askyesno(_t("msg_no_encounter_title", default="Nessun Incontro"), _t("msg_no_encounter_desc", default="Nessuna campagna attiva con incontri preparati. Vuoi aprire l'Editor Campagna?"), parent=self.master):
                self.open_campaign_editor_dialog()
            return
            
        dlg = tk.Toplevel(self.master)
        dlg.title(_t("deploy_encounter_title", default="Schiera Incontro della Campagna"))
        dlg.minsize(520, 360)
        dlg.transient(self.master)
        dlg.grab_set()
        apply_modern_window_style(dlg)
        dlg.configure(bg=BG_COLOR)
        
        container = tk.Frame(dlg, bg=BG_COLOR, padx=15, pady=12)
        container.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(container, text=_t("deploy_encounter_header", default="⚔️ Incontri Preparati della Campagna"), font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 4))
        tk.Label(container, text=_t("deploy_encounter_subtitle", default="Seleziona l'incontro da schierare sulla mappa corrente:"), font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 8))
        
        tree_frame = tk.Frame(container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        cols = ("Nome", "Atto", "Mostri", "Descrizione")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=6)
        tree.heading("Nome", text=_t("col_encounter_name", default="Nome Incontro"))
        tree.heading("Atto", text=_t("col_act", default="Atto"))
        tree.heading("Mostri", text=_t("col_monsters", default="Mostri"))
        tree.heading("Descrizione", text=_t("col_notes", default="Note"))
        tree.column("Nome", width=160)
        tree.column("Atto", width=90)
        tree.column("Mostri", width=60, anchor="center")
        tree.column("Descrizione", width=180)
        
        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        for idx, enc in enumerate(active_camp.encounters):
            m_cnt = sum(int(m.get("qty", m.get("count", m.get("quantity", 1))) or 1) for m in enc.get("monsters", []))
            tree.insert("", tk.END, iid=str(idx), values=(
                enc.get("name", "Incontro"),
                enc.get("act", "Atto 1"),
                str(m_cnt),
                enc.get("description", "")
            ))
        if active_camp.encounters:
            tree.selection_set("0")
            
        def do_deploy():
            sel = tree.selection()
            if not sel: return
            idx = int(sel[0])
            enc = active_camp.encounters[idx]
            monsters = enc.get("monsters", [])
            self.handle_encounter_start(monsters)
            self.log_to_chat(f"[SISTEMA] Incontro '{enc.get('name')}' schierato dal piano di campagna.")
            dlg.destroy()
            
        btn_box = tk.Frame(container, bg=BG_COLOR)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text=_t("btn_deploy_on_map", default="⚡ Schiera sulla Mappa"), command=do_deploy, style="Gold.TButton").pack(side=tk.RIGHT)
        ttk.Button(btn_box, text=_t("cancel", default="Annulla"), command=dlg.destroy).pack(side=tk.RIGHT, padx=6)

    def _play_track_by_name_or_url(self, track_ref):
        """Riproduce una traccia dalla libreria audio DM o da URL diretto."""
        ref = str(track_ref or "").strip()
        if not ref or not hasattr(self, "server") or not hasattr(self.server, "game_state"):
            return
        if ref.lower().startswith(("http://", "https://")):
            self.play_audio(ref)
            return
        gs = self.server.game_state
        lib = getattr(gs, "audio_library", None)
        if not lib or not getattr(lib, "tracks", None):
            return
        ref_low = ref.lower()
        found = next(
            (t for t in lib.tracks if t.get("id") == ref or str(t.get("name", "")).strip().lower() == ref_low),
            None
        )
        if not found:
            found = next((t for t in lib.tracks if ref_low in str(t.get("name", "")).strip().lower()), None)
        if not found:
            return
        from common.protocol import make_audio_track_play
        is_music = found.get("category") == "Musica"
        channel = "music" if is_music else "sfx"
        loop = True if is_music else False
        vol = (self.audio_volume_var.get() / 100.0) if hasattr(self, "audio_volume_var") else 0.7
        msg = make_audio_track_play(found["id"], found["name"], found.get("ext", ".mp3"), found.get("size", 0), channel=channel, loop=loop, volume=vol)
        if is_music:
            gs.current_music = msg
        broadcast(gs, msg)
        if hasattr(self, "audio_dm_listen_var") and self.audio_dm_listen_var.get() and hasattr(self, "audio_manager"):
            self.audio_manager.play(lib.get_path(found["id"]), channel=channel, loop=loop, volume=vol, name=found["name"])
        if is_music and hasattr(self, "audio_now_playing"):
            self.audio_now_playing.config(text=f"In riproduzione: 🎵 {found['name']} (loop)")

    def _apply_scene_atmosphere(self, scene_data):
        """Applica meteo, illuminazione e tema musicale associati a una scena."""
        if not isinstance(scene_data, dict):
            return
        weather = str(scene_data.get("weather") or "").strip()
        light = str(scene_data.get("light") or "").strip()
        if not weather and light.lower() in ("buio", "notte", "oscurità", "oscurita", "darkness"):
            weather = "Oscurità"
        elif not weather and light:
            # Mantieni meteo attuale se solo illuminazione non oscura
            pass
        if weather:
            self._apply_weather_change(weather, trigger_redraw=False)
        music_ref = str(scene_data.get("music") or "").strip()
        if music_ref:
            self._play_track_by_name_or_url(music_ref)

    def switch_campaign_scene_dialog(self):
        active_camp = getattr(self.server.game_state, 'active_campaign', None)
        if not active_camp or not active_camp.scenes:
            messagebox.showinfo(_t("msg_no_scene_title", default="Nessuna Scena"), _t("msg_no_scene_desc", default="Nessuna campagna attiva con scene collegate."), parent=self.master)
            return
            
        dlg = tk.Toplevel(self.master)
        dlg.title(_t("switch_scene_title", default="Passa a Scena della Campagna"))
        dlg.minsize(480, 320)
        dlg.transient(self.master)
        dlg.grab_set()
        apply_modern_window_style(dlg)
        dlg.configure(bg=BG_COLOR)
        
        container = tk.Frame(dlg, bg=BG_COLOR, padx=15, pady=12)
        container.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(container, text=_t("switch_scene_header", default="🗺️ Scene della Campagna"), font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 6))
        
        lb_scenes = tk.Listbox(container, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=FONT_MAIN,
                               selectbackground=ACCENT_GOLD, selectforeground=TEXT_DARK,
                               highlightthickness=1, highlightbackground=BORDER_COLOR)
        lb_scenes.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        for sc in active_camp.scenes:
            lb_scenes.insert(tk.END, f"{sc.get('name', 'Scena')}  [{sc.get('map_file', '')}]")
        if active_camp.scenes:
            lb_scenes.selection_set(0)
            
        def do_switch():
            sel = lb_scenes.curselection()
            if not sel: return
            sc = active_camp.scenes[sel[0]]
            # Recupera anche eventuali metadati dal nodo scena macro (weather, light, music)
            scene_meta = dict(sc)
            raw_fg = getattr(active_camp, "flow_graph", None)
            if isinstance(raw_fg, dict) and isinstance(raw_fg.get("nodes"), dict):
                sc_low = str(sc.get("name", "")).strip().lower()
                for n_raw in raw_fg["nodes"].values():
                    if isinstance(n_raw, dict) and n_raw.get("node_type") == "scene" and str(n_raw.get("title", "")).strip().lower() == sc_low:
                        for k in ("weather", "light", "music"):
                            if not scene_meta.get(k) and isinstance(n_raw.get("data"), dict) and n_raw["data"].get(k):
                                scene_meta[k] = n_raw["data"][k]
                        break

            map_file = sc.get("map_file")
            if map_file:
                map_path = map_file
                if not os.path.isabs(map_path) and active_camp.folder_path:
                    cand = os.path.join(active_camp.folder_path, map_path)
                    if os.path.exists(cand): map_path = cand
                if not os.path.exists(map_path):
                    cand_global = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), map_file)
                    if os.path.exists(cand_global): map_path = cand_global
                if os.path.exists(map_path):
                    try:
                        with open(map_path, 'r', encoding="utf-8") as f:
                            map_data = json.load(f)
                        if 'base_image_path' in map_data and map_data['base_image_path']:
                            img_path = map_data['base_image_path']
                            if not os.path.isabs(img_path):
                                img_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), img_path)
                            if os.path.exists(img_path):
                                with open(img_path, "rb") as image_file:
                                    map_data['bg_image_data'] = base64.b64encode(image_file.read()).decode('utf-8')
                        self.server.game_state.load_map(map_data)
                        self.fow_enabled_var.set(self.server.game_state.current_map.get("fow_enabled", False))
                    except Exception as e:
                        messagebox.showerror(_t("error", default="Errore"), f"Impossibile caricare la mappa: {e}", parent=dlg)
                        return

            self._apply_scene_atmosphere(scene_meta)
            self.redraw_map_and_players()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            broadcast(self.server.game_state, make_chat_broadcast("DM", f"Il DM ha spostato il gruppo nella scena: {sc.get('name')}"))
            self.log_to_chat(f"[SISTEMA] Scena cambiata in: '{sc.get('name')}'.")
            dlg.destroy()
            
        btn_box = tk.Frame(container, bg=BG_COLOR)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text=_t("btn_switch_scene", default="Passa a Questa Scena"), command=do_switch, style="Gold.TButton").pack(side=tk.RIGHT)
        ttk.Button(btn_box, text=_t("cancel", default="Annulla"), command=dlg.destroy).pack(side=tk.RIGHT, padx=6)

    def prompt_currency_approval(self, player, coin, amount, reason):
        if not player or amount <= 0: return
        p_name = getattr(player, "name", "Giocatore")
        coin_labels = {
            "MO": "Monete d'Oro (MO / gp)", "gp": "Monete d'Oro (MO / gp)",
            "MA": "Monete d'Argento (MA / sp)", "sp": "Monete d'Argento (MA / sp)",
            "MR": "Monete di Rame (MR / cp)", "cp": "Monete di Rame (MR / cp)",
            "ME": "Monete d'Electrum (ME / ep)", "ep": "Monete d'Electrum (ME / ep)",
            "MP": "Monete di Platino (MP / pp)", "pp": "Monete di Platino (MP / pp)"
        }
        coin_display = coin_labels.get(coin, coin)
        reason_display = reason if reason else "Nessuna motivazione specificata"
        prompt_text = (
            f"Il giocatore '{p_name}' richiede di ricevere valuta:\n\n"
            f"• Quantità: +{amount} {coin_display}\n"
            f"• Motivazione: {reason_display}\n\n"
            f"Vuoi approvare la richiesta e accreditare le monete a {p_name}?"
        )
        approved = messagebox.askyesno("Richiesta Valuta Giocatore", prompt_text, parent=self.master)
        
        from common.protocol import make_currency_response, make_chat_broadcast, make_game_state
        from common.network_utils import send_message, broadcast
        if approved:
            sheet = getattr(player, "full_sheet", None)
            if sheet:
                if not isinstance(sheet.get("currency"), dict):
                    sheet["currency"] = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
                sheet["currency"][coin] = sheet["currency"].get(coin, 0) + amount
                if not isinstance(sheet.get("wallet"), dict):
                    sheet["wallet"] = dict(sheet["currency"])
                else:
                    sheet["wallet"][coin] = sheet["currency"][coin]
                if coin in ["MO", "gp"]:
                    sheet["gp"] = sheet["currency"].get("MO", 0)
            if player.conn:
                send_message(player.conn, make_currency_response(p_name, coin, amount, approved=True, reason=reason))
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", f"[VALUTA] Il Master ha APPROVATO e concesso +{amount} {coin_display} a {p_name}!"))
            self.log_to_chat(f"[SISTEMA] Concessi +{amount} {coin_display} a {p_name}.")
            self.server.game_state._trigger_gui_update()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
        else:
            if player.conn:
                send_message(player.conn, make_currency_response(p_name, coin, amount, approved=False, reason="Richiesta respinta dal Dungeon Master."))
            self.log_to_chat(f"[SISTEMA] Respinta richiesta valuta da {p_name} (+{amount} {coin_display}).")

    def prompt_item_approval(self, player, item, slot_idx):
        if not player or not item: return
        p_name = getattr(player, "name", "Giocatore")
        it_name = item.get("name", "Oggetto Sconosciuto")
        it_type = item.get("type", "Equipaggiamento")
        it_qty = item.get("qty", 1)
        it_weight = item.get("weight", 0.0)
        it_attuned = "Sì" if item.get("attuned") else "No"
        it_desc = item.get("desc", "")
        is_remove = item.get("action") == "remove"
        
        if is_remove:
            prompt_text = (
                f"Il giocatore '{p_name}' richiede di RIMUOVERE un oggetto dallo zaino:\n\n"
                f"• Oggetto: {it_name} (Slot #{slot_idx+1 if slot_idx is not None else '?'})\n\n"
                f"Vuoi approvare la rimozione di questo oggetto dall'inventario di {p_name}?"
            )
            dialog_title = "Approvazione Rimozione Oggetto"
        else:
            prompt_text = (
                f"Il giocatore '{p_name}' richiede di aggiungere un oggetto allo zaino:\n\n"
                f"• Oggetto: {it_name}\n"
                f"• Categoria: {it_type} (Quantità: {it_qty}, Peso: {it_weight} lbs)\n"
                f"• Richiede Sintonia: {it_attuned}\n\n"
                f"Descrizione:\n{it_desc}\n\n"
                f"Vuoi approvare questo oggetto per l'inventario di {p_name}?"
            )
            dialog_title = "Approvazione Oggetto Inventario"
        approved = messagebox.askyesno(dialog_title, prompt_text, parent=self.master)
        
        from common.protocol import make_item_approval_response, make_chat_broadcast, make_game_state
        from common.network_utils import send_message, broadcast
        if approved:
            sheet = getattr(player, "full_sheet", None)
            is_weapon_req = (item.get("target_collection") == "weapons")
            if sheet:
                if is_weapon_req:
                    if not isinstance(sheet.get("weapons"), list):
                        sheet["weapons"] = []
                    if is_remove:
                        if slot_idx is not None and 0 <= slot_idx < len(sheet["weapons"]):
                            sheet["weapons"].pop(slot_idx)
                        else:
                            for w_i, w_obj in enumerate(sheet["weapons"]):
                                if isinstance(w_obj, dict) and w_obj.get("name") == it_name:
                                    sheet["weapons"].pop(w_i)
                                    break
                    else:
                        clean_weapon = {k: v for k, v in item.items() if k not in ("action", "target_collection")}
                        sheet["weapons"].append(clean_weapon)
                else:
                    if not isinstance(sheet.get("inventory_grid"), list):
                        sheet["inventory_grid"] = [None] * 25
                    grid = sheet["inventory_grid"]
                    target_slot = slot_idx if (slot_idx is not None and 0 <= slot_idx < len(grid)) else None
                    if is_remove:
                        if target_slot is not None:
                            grid[target_slot] = None
                        else:
                            for s_i in range(len(grid)):
                                if grid[s_i] and grid[s_i].get("name") == it_name:
                                    grid[s_i] = None
                                    break
                    else:
                        clean_item = {k: v for k, v in item.items() if k not in ("action", "target_collection")}
                        if target_slot is None or grid[target_slot] is not None:
                            target_slot = None
                            for s_i in range(len(grid)):
                                if grid[s_i] is None:
                                    target_slot = s_i
                                    break
                        if target_slot is not None and 0 <= target_slot < len(grid):
                            grid[target_slot] = clean_item
                            slot_idx = target_slot
                        else:
                            grid.append(clean_item)
                            slot_idx = len(grid) - 1
                    try:
                        from common.item_modifiers import compute_effective_ac, calculate_character_item_modifiers
                        mods = calculate_character_item_modifiers(sheet)
                        if (
                            is_remove or
                            mods.get("equipped_armor") is not None or
                            mods.get("has_shield", False) or
                            mods.get("bonus_ac", 0) != 0 or
                            mods.get("special_ac_base") is not None
                        ):
                            new_ac = compute_effective_ac(sheet, mods)
                            sheet["ac"] = new_ac
                            player.ac = new_ac
                    except Exception:
                        pass
            if player.conn:
                send_message(player.conn, make_item_approval_response(p_name, item, slot_idx, approved=True))
            action_desc = "la rimozione di" if is_remove else "l'assegnazione di"
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", f"[INVENTARIO] Il Master ha APPROVATO {action_desc} '{it_name}' per {p_name}!"))
            self.log_to_chat(f"[SISTEMA] Approvata richiesta {action_desc} '{it_name}' per {p_name}.")
            self.server.game_state._trigger_gui_update()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
        else:
            if player.conn:
                send_message(player.conn, make_item_approval_response(p_name, item, slot_idx, approved=False, reason="Il Master ha respinto la richiesta."))
            self.log_to_chat(f"[SISTEMA] Respinta richiesta per '{it_name}' di {p_name}.")

    def prompt_journal_approval(self, player, field_name, content, title):
        if not player: return
        p_name = getattr(player, "name", "Giocatore")
        field_disp = "Biografia & Diario" if "journal" in str(field_name) else ("Privilegi & Tratti" if "features" in str(field_name) else "Appunti / Note")
        
        dlg = tk.Toplevel(self.master)
        dlg.title(f"Approvazione Modifiche - {field_disp}")
        dlg.geometry("560x520")
        dlg.minsize(480, 420)
        dlg.transient(self.master)
        dlg.grab_set()
        apply_modern_window_style(dlg)
        
        main_box = ttk.Frame(dlg, padding="14")
        main_box.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_box, text=f"📜 Richiesta di Modifica da {p_name}", font=FONT_BOLD).pack(anchor="w", pady=(0, 2))
        ttk.Label(main_box, text=f"Il giocatore richiede di aggiornare la sezione '{field_disp}':", style="Muted.TLabel").pack(anchor="w", pady=(0, 8))
        
        txt_prev = scrolledtext.ScrolledText(main_box, wrap=tk.WORD, font=FONT_MAIN, bg=SURFACE_COLOR, fg=TEXT_COLOR, padx=6, pady=6)
        txt_prev.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        txt_prev.insert(tk.END, content)
        txt_prev.config(state=tk.DISABLED)
        
        btn_box = ttk.Frame(main_box)
        btn_box.pack(fill=tk.X)
        
        from common.protocol import make_journal_approval_response, make_chat_broadcast, make_game_state
        from common.network_utils import send_message, broadcast
        
        def on_approve():
            sheet = getattr(player, "full_sheet", None)
            if sheet and isinstance(sheet, dict):
                sheet[field_name] = content
            if player.conn:
                send_message(player.conn, make_journal_approval_response(p_name, field_name, content, approved=True))
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", f"[DIARIO] Il Master ha APPROVATO le modifiche a {field_disp} per {p_name}!"))
            self.log_to_chat(f"[SISTEMA] Approvate modifiche a {field_disp} per {p_name}.")
            self.server.game_state._trigger_gui_update()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            dlg.destroy()
            
        def on_reject():
            if player.conn:
                send_message(player.conn, make_journal_approval_response(p_name, field_name, content, approved=False, reason="Il Master ha respinto le modifiche proposte."))
            self.log_to_chat(f"[SISTEMA] Respinte modifiche a {field_disp} per {p_name}.")
            dlg.destroy()
            
        ttk.Button(btn_box, text="✅ Approva Modifiche", command=on_approve, style="Success.TButton").pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_box, text="❌ Respingi", command=on_reject, style="Danger.TButton").pack(side=tk.RIGHT, padx=4)

    def prompt_custom_spell_approval(self, player, spell):
        if not player or not spell: return
        p_name = getattr(player, "name", "Giocatore")
        s_name = spell.get("name", "Incantesimo Sconosciuto")
        s_lvl = spell.get("level", 0)
        s_time = spell.get("time", "1 Azione")
        s_rng = spell.get("range", "Contatto")
        s_desc = spell.get("desc", "")
        is_remove = spell.get("action") == "remove"
        
        lvl_str = "Trucchetto (Lvl 0)" if s_lvl == 0 else f"Livello {s_lvl}"
        if is_remove:
            prompt_text = (
                f"Il giocatore '{p_name}' richiede di RIMUOVERE il seguente incantesimo dal proprio Grimorio:\n\n"
                f"• Nome: {s_name}\n"
                f"• Livello: {lvl_str}\n\n"
                f"Vuoi approvare la rimozione di questo incantesimo?"
            )
            dialog_title = "Approvazione Rimozione Incantesimo"
        else:
            prompt_text = (
                f"Il giocatore '{p_name}' richiede il permesso di aggiungere il seguente incantesimo al proprio Grimorio:\n\n"
                f"• Nome: {s_name}\n"
                f"• Livello: {lvl_str}\n"
                f"• Tempo di Lancio: {s_time}\n"
                f"• Raggio / Gittata: {s_rng}\n\n"
                f"Descrizione:\n{s_desc}\n\n"
                f"Vuoi approvare questo incantesimo e permetterne l'aggiunta al suo Grimorio?"
            )
            dialog_title = "Richiesta Approvazione Incantesimo"
        approved = messagebox.askyesno(dialog_title, prompt_text, parent=self.master)
        
        from common.protocol import make_custom_spell_response, make_chat_broadcast, make_game_state
        from common.network_utils import send_message, broadcast
        if approved:
            sheet = getattr(player, "full_sheet", None)
            if sheet and isinstance(sheet, dict):
                if not isinstance(sheet.get("spellbook"), list):
                    sheet["spellbook"] = []
                if is_remove:
                    sheet["spellbook"] = [s for s in sheet["spellbook"] if s.get("name") != s_name]
                else:
                    if not any(s.get("name") == s_name for s in sheet["spellbook"]):
                        sheet["spellbook"].append(spell)
            if player.conn:
                send_message(player.conn, make_custom_spell_response(p_name, spell, approved=True))
            action_desc = "la rimozione di" if is_remove else "l'incantesimo"
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", f"[MAGIA] Il Master ha APPROVATO {action_desc} '{s_name}' per {p_name}!"))
            self.log_to_chat(f"[SISTEMA] Approvata richiesta {action_desc} '{s_name}' per {p_name}.")
            self.server.game_state._trigger_gui_update()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
        else:
            if player.conn:
                send_message(player.conn, make_custom_spell_response(p_name, spell, approved=False, reason="Il Master ha respinto la richiesta."))
            self.log_to_chat(f"[SISTEMA] Respinta richiesta per '{s_name}' di {p_name}.")

    def import_party_character_data(self, char_dict, spawn_pos=None):
        """Importa un PG locale nel GameState e notifica tutti i client connessi."""
        player = import_party_character_to_game_state(self.server.game_state, char_dict, spawn_pos=spawn_pos)
        broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
        self.log_to_chat(
            f"[TAVOLO LOCALE] PG '{player.name}' importato sulla mappa (PF {player.hp}/{player.max_hp}, CA {player.ac})."
        )
        self.server.game_state._trigger_gui_update()
        return player

    def sync_local_party_characters_to_manager(self, target_name=None):
        """Sincronizza PF, CA, risorse, slot, dadi vita, tiri morte e XP dei PG locali su CharacterManager."""
        server = getattr(self, "server", None)
        gs = getattr(server, "game_state", None) if server else None
        if not gs:
            return 0
        party_players = [
            p for p in getattr(gs, "players", [])
            if getattr(p, "is_party_member", False)
            and (target_name is None or getattr(p, "name", None) == target_name)
        ]
        if not party_players:
            return 0

        from client.character_manager import CharacterManager

        mgr = CharacterManager()
        updated = 0
        for p in party_players:
            sheet = getattr(p, "full_sheet", None)
            if not isinstance(sheet, dict):
                sheet = {}
            char = None
            char_id = sheet.get("id") or sheet.get("character_id")
            if char_id:
                char = mgr.get_character_by_id(char_id)
            if char is None and getattr(p, "name", None):
                char = mgr.get_character_by_name(p.name)
            if char is None:
                continue

            char.hp_current = int(getattr(p, "hp", sheet.get("hp_current", char.hp_current)) or 0)
            char.hp_max = int(getattr(p, "max_hp", sheet.get("hp_max", char.hp_max)) or 1)
            char.temp_hp = int(getattr(p, "temp_hp", sheet.get("temp_hp", getattr(char, "temp_hp", 0))) or 0)
            char.ac = int(getattr(p, "ac", sheet.get("ac", char.ac)) or 10)
            char.conditions = list(getattr(p, "conditions", None) if getattr(p, "conditions", None) is not None else sheet.get("conditions", []))
            ds_src = getattr(p, "death_saves", None) or sheet.get("death_saves") or {"successes": 0, "failures": 0}
            char.death_saves = copy.deepcopy(ds_src) if isinstance(ds_src, dict) else {"successes": 0, "failures": 0}
            char.exhaustion_level = int(getattr(p, "exhaustion_level", sheet.get("exhaustion_level", 0)) or 0)

            for int_field in ("hit_dice_current", "hit_dice_total", "level", "lucky_points", "arcane_ward_hp", "wild_shape_uses", "wild_shape_max", "bardic_inspiration_current", "lay_on_hands_pool"):
                if int_field in sheet and sheet.get(int_field) is not None:
                    try:
                        setattr(char, int_field, int(sheet[int_field]))
                    except (ValueError, TypeError):
                        pass

            exp_val = sheet.get("exp") if sheet.get("exp") is not None else sheet.get("xp")
            if exp_val is not None:
                try:
                    char.exp = int(exp_val)
                except (ValueError, TypeError):
                    pass

            if "has_inspiration" in sheet:
                char.has_inspiration = bool(sheet["has_inspiration"])
                char.inspiration = bool(sheet["has_inspiration"])
            elif "inspiration" in sheet:
                char.has_inspiration = bool(sheet["inspiration"])
                char.inspiration = bool(sheet["inspiration"])

            for bool_field in ("arcane_recovery_used", "relentless_endurance_used"):
                if bool_field in sheet:
                    setattr(char, bool_field, bool(sheet[bool_field]))

            for dict_field in ("spell_slots", "pact_slots", "class_resources", "hit_dice_pools", "currency", "attributes", "skills", "classes", "subclasses"):
                val = sheet.get(dict_field)
                if isinstance(val, dict):
                    setattr(char, dict_field, copy.deepcopy(val))
            if not isinstance(sheet.get("classes"), dict) and "level" in sheet and sheet.get("level") is not None:
                if isinstance(getattr(char, "classes", None), dict) and len(char.classes) == 1:
                    only_cls = next(iter(char.classes))
                    char.classes[only_cls] = int(getattr(char, "level", 1) or 1)
            if not isinstance(sheet.get("currency"), dict) and isinstance(sheet.get("wallet"), dict):
                char.currency = copy.deepcopy(sheet["wallet"])

            for list_field in ("custom_resources", "spells", "inventory_grid", "weapons", "portent_dice", "saving_throw_proficiencies", "armor_proficiencies", "weapon_proficiencies", "tool_proficiencies"):
                val = sheet.get(list_field)
                if isinstance(val, list):
                    setattr(char, list_field, copy.deepcopy(val))

            sb_val = sheet.get("spellbook")
            if isinstance(sb_val, list):
                char.spellbook = copy.deepcopy(sb_val)
            elif isinstance(sheet.get("spells"), list) and not getattr(char, "spellbook", None):
                char.spellbook = copy.deepcopy(sheet["spells"])

            if isinstance(getattr(char, "hit_dice_pools", None), dict) and char.hit_dice_pools:
                from common.character_schema import sync_hit_dice_pools
                sync_hit_dice_pools(char, allow_scalar_override=False)

            updated += 1

        if updated > 0:
            mgr.save_characters()
        return updated

    def open_import_party_character_dialog(self):
        """Apre il selettore per importare Personaggi Giocanti locali (Sessione dal Vivo / Ibrida)."""
        from client.character_manager import CharacterManager

        mgr = CharacterManager()
        mgr.load_characters()
        chars = list(getattr(mgr, "characters", []) or [])
        if not chars:
            messagebox.showinfo(
                _t("dlg_import_local_pc_title", default="Importa PG Locale"),
                "Nessun personaggio salvato trovato nell'archivio locale.\nCrea prima un PG dalla finestra Giocatore/Scheda.",
                parent=self.master,
            )
            return

        dlg = tk.Toplevel(self.master)
        dlg.title(_t("dlg_import_local_pc_title", default="Importa PG Locali sul Tavolo"))
        dlg.geometry("460x380")
        dlg.transient(self.master)
        dlg.grab_set()
        apply_modern_window_style(dlg)

        tk.Label(
            dlg,
            text="Seleziona uno o più Eroi locali da schierare sul tavolo:",
            font=FONT_BOLD,
            bg=BG_COLOR,
            fg=ACCENT_GOLD,
            pady=8,
        ).pack(fill=tk.X, padx=10)

        lb_frame = tk.Frame(dlg, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        lb_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        lb = tk.Listbox(
            lb_frame,
            selectmode=tk.EXTENDED,
            bg=SURFACE_COLOR,
            fg=TEXT_COLOR,
            font=FONT_MAIN,
            activestyle="none",
        )
        lb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        for c in chars:
            c_cls = getattr(c, "char_class", "") or "Avventuriero"
            c_lvl = int(getattr(c, "level", 1) or 1)
            c_hp = int(getattr(c, "hp_current", getattr(c, "hp_max", 10)) or 0)
            c_max = int(getattr(c, "hp_max", 10) or 10)
            lb.insert(tk.END, f"{c.name} — {c_cls} Lv.{c_lvl} (PF {c_hp}/{c_max})")

        btn_row = tk.Frame(dlg, bg=BG_COLOR)
        btn_row.pack(fill=tk.X, padx=10, pady=10)

        def _do_import(indices):
            if not indices:
                messagebox.showwarning("Selezione Vuota", "Seleziona almeno un personaggio.", parent=dlg)
                return
            imported = []
            for idx in indices:
                if 0 <= idx < len(chars):
                    p_obj = self.import_party_character_data(chars[idx])
                    imported.append(p_obj.name)
            dlg.destroy()
            if imported and hasattr(self, "show_toast"):
                self.show_toast(
                    f"PG importati sul tavolo: {', '.join(imported)}",
                    title="🧙 Tavolo Locale",
                    toast_type="success",
                )

        ttk.Button(btn_row, text="🧙 Importa Selezionati", command=lambda: _do_import(lb.curselection()), style="Gold.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="👥 Importa Tutti", command=lambda: _do_import(list(range(len(chars)))), style="Primary.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Chiudi", command=dlg.destroy).pack(side=tk.RIGHT, padx=4)

