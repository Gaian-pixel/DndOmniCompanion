# server/dm_journal_dialog.py
"""
Dialogo per la gestione del Diario Narrativo Continuativo di Campagna (DM).
Permette di consultare e modificare tutte le sessioni svolte,
avviare nuove sessioni, sintetizzare la prosa narrativa, inserire note riservate del DM,
sincronizzare il diario con i client dei giocatori ed esportare in Markdown, HTML e Discord.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from common.messagebox import messagebox
from typing import Optional, Any

from common.theme import (
    apply_modern_window_style,
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT, BORDER_COLOR,
    TEXT_COLOR, TEXT_MUTED, TEXT_DARK, TEXT_GOLD,
    ACCENT_GOLD, ACCENT_GREEN, ACCENT_BLUE, ACCENT_PURPLE,
    FONT_TITLE, FONT_HEADER, FONT_BOLD, FONT_MAIN, FONT_SMALL
)
from common.i18n import _t, get_language
from common.campaign_journal import CampaignJournal, JournalSession, format_game_date
from common.network_utils import broadcast
from common.protocol import make_journal_sync, make_chat_broadcast
from components.ui_components import show_toast


class DMJournalDialog(tk.Toplevel):
    def __init__(self, master_gui, game_state: Any):
        super().__init__(master_gui.master)
        self.master_gui = master_gui
        self.game_state = game_state

        if not hasattr(game_state, "campaign_journal") or not game_state.campaign_journal:
            camp_name = getattr(game_state.active_campaign, "name", "Campagna") if getattr(game_state, "active_campaign", None) else "Campagna"
            game_state.campaign_journal = CampaignJournal(campaign_name=camp_name)

        self.journal: CampaignJournal = game_state.campaign_journal
        self.active_session = self.journal.get_active_session()
        self.selected_index: int = self.journal.active_session_index

        self.title(_t("journal_window_title", default="📖 Libro del Diario di Campagna"))
        self.geometry("980x680")
        self.minsize(840, 560)
        self.transient(master_gui.master)
        apply_modern_window_style(self, bind_escape=False)
        self.configure(bg=BG_COLOR)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())

        self._build_ui()
        self._populate_sessions_list()
        self._load_session_data(self.selected_index)

    def _build_ui(self):
        main_box = tk.Frame(self, bg=BG_COLOR, padx=14, pady=12)
        main_box.pack(fill=tk.BOTH, expand=True)

        # Header superiore
        top_hdr = tk.Frame(main_box, bg=BG_COLOR)
        top_hdr.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            top_hdr,
            text=f"📖 {self.journal.campaign_name} — " + _t("journal_chronicles_title", default="Cronache di Campagna"),
            font=FONT_TITLE, bg=BG_COLOR, fg=ACCENT_GOLD
        ).pack(side=tk.LEFT)

        btn_share = ttk.Button(
            top_hdr,
            text=_t("btn_share_with_party", default="📢 Trasmetti ai Giocatori"),
            command=self._on_share_with_party,
            style="Accent.TButton"
        )
        btn_share.pack(side=tk.RIGHT, padx=4)

        # Split orizzontale: Sinistra (Indice Sessioni), Destra (Dettaglio Sessione)
        split_frame = tk.Frame(main_box, bg=BG_COLOR)
        split_frame.pack(fill=tk.BOTH, expand=True)

        # ------------------ PANNELLO SINISTRO (Indice Sessioni) ------------------
        left_panel = tk.Frame(split_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, width=280, padx=10, pady=10)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        tk.Label(
            left_panel,
            text=_t("journal_session_index", default="📜 Indice delle Sessioni"),
            font=FONT_HEADER, bg=SURFACE_COLOR, fg=TEXT_GOLD
        ).pack(anchor="w", pady=(0, 6))

        # Listbox sessioni
        list_frame = tk.Frame(left_panel, bg=SURFACE_COLOR)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.session_listbox = tk.Listbox(
            list_frame,
            bg=SURFACE_COLOR_ALT,
            fg=TEXT_COLOR,
            selectbackground=ACCENT_GOLD,
            selectforeground=TEXT_DARK,
            font=FONT_MAIN,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_COLOR
        )
        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.session_listbox.yview)
        self.session_listbox.configure(yscrollcommand=sb.set)
        self.session_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.session_listbox.bind("<<ListboxSelect>>", self._on_session_selected)

        # Pulsanti gestione sessioni
        btn_box_left = tk.Frame(left_panel, bg=SURFACE_COLOR)
        btn_box_left.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(
            btn_box_left,
            text=_t("btn_new_session", default="➕ Nuova Sessione"),
            command=self._on_new_session
        ).pack(fill=tk.X, pady=(0, 4))

        self.btn_conclude = ttk.Button(
            btn_box_left,
            text=_t("btn_conclude_session", default="🏁 Concludi Sessione"),
            command=self._on_conclude_session
        )
        self.btn_conclude.pack(fill=tk.X)

        # ------------------ PANNELLO DESTRO (Dettagli Sessione) ------------------
        right_panel = tk.Frame(split_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Titolo e Metadati della sessione selezionata
        meta_frame = tk.Frame(right_panel, bg=SURFACE_COLOR)
        meta_frame.pack(fill=tk.X, pady=(0, 8))

        row_title = tk.Frame(meta_frame, bg=SURFACE_COLOR)
        row_title.pack(fill=tk.X, pady=(0, 4))

        tk.Label(row_title, text=_t("lbl_session_title", default="Titolo:"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 6))
        self.var_title = tk.StringVar()
        self.ent_title = ttk.Entry(row_title, textvariable=self.var_title, font=FONT_BOLD)
        self.ent_title.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.lbl_status_badge = tk.Label(row_title, text="[In Corso]", font=FONT_SMALL, bg="#1E3A8A", fg="#93C5FD", padx=6, pady=2)
        self.lbl_status_badge.pack(side=tk.RIGHT)

        self.lbl_meta_strip = tk.Label(
            meta_frame,
            text="🗓️ Data Reale: 2026-10-29 | ⏳ Harptos: 1 Ches, 1492 CV | 🌤️ Meteo: Sereno | 🧭 Faerûn",
            font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED
        )
        self.lbl_meta_strip.pack(anchor="w")

        # Notebook tabs
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Tab 1: Prosa Narrativa
        tab_prose = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab_prose, text=_t("tab_narrative_prose", default="📖 Resoconto Narrativo"))

        prose_ctrls = tk.Frame(tab_prose, bg=BG_COLOR)
        prose_ctrls.pack(fill=tk.X, pady=(0, 4))

        ttk.Button(
            prose_ctrls,
            text=_t("btn_regenerate_prose", default="↺ Rigenera Sintesi Narrativa"),
            command=self._on_regenerate_prose
        ).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(
            prose_ctrls,
            text=_t("btn_save_prose", default="💾 Salva Modifiche"),
            command=self._on_save_edits
        ).pack(side=tk.LEFT)

        self.txt_prose = scrolledtext.ScrolledText(
            tab_prose,
            wrap=tk.WORD,
            bg=SURFACE_COLOR_ALT,
            fg=TEXT_COLOR,
            font=("Consolas", 10),
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_COLOR
        )
        self.txt_prose.pack(fill=tk.BOTH, expand=True)

        # Tab 2: Note Riservate del Master
        tab_notes = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab_notes, text=_t("tab_dm_notes", default="🔒 Note Private DM"))

        tk.Label(
            tab_notes,
            text=_t("dm_notes_disclaimer", default="Queste note sono confidenziali e visibili esclusivamente al Dungeon Master (non inviate ai giocatori)."),
            font=FONT_SMALL, fg=ACCENT_PURPLE, bg=BG_COLOR
        ).pack(anchor="w", pady=(0, 4))

        self.txt_dm_notes = scrolledtext.ScrolledText(
            tab_notes,
            wrap=tk.WORD,
            bg=SURFACE_COLOR_ALT,
            fg=TEXT_COLOR,
            font=("Consolas", 10),
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_COLOR
        )
        self.txt_dm_notes.pack(fill=tk.BOTH, expand=True)

        # Tab 3: Timeline Eventi Dettagliata
        tab_events = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab_events, text=_t("tab_timeline_events", default="⏱️ Eventi Registrati"))

        self.txt_events = scrolledtext.ScrolledText(
            tab_events,
            wrap=tk.WORD,
            bg=SURFACE_COLOR_ALT,
            fg=TEXT_COLOR,
            font=("Consolas", 9),
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_COLOR
        )
        self.txt_events.pack(fill=tk.BOTH, expand=True)

        # Barra inferiore azioni ed esportazione
        bbar = tk.Frame(right_panel, bg=SURFACE_COLOR)
        bbar.pack(fill=tk.X)

        ttk.Button(
            bbar,
            text=_t("btn_copy_discord", default="📋 Copia per Discord"),
            command=self._on_copy_discord
        ).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(
            bbar,
            text=_t("btn_export_html", default="📄 Esporta HTML Pergamena"),
            command=self._on_export_html
        ).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(
            bbar,
            text=_t("btn_export_markdown", default="📥 Esporta Markdown Campagna"),
            command=self._on_export_markdown
        ).pack(side=tk.LEFT)

        ttk.Button(
            bbar,
            text=_t("btn_close", default="Chiudi"),
            command=self._on_close
        ).pack(side=tk.RIGHT)

    def _populate_sessions_list(self):
        self.session_listbox.delete(0, tk.END)
        for idx, sess in enumerate(self.journal.sessions):
            status = "✓" if sess.is_concluded else "●"
            self.session_listbox.insert(tk.END, f"{status} #{sess.session_number}: {sess.title}")

        if 0 <= self.selected_index < self.session_listbox.size():
            self.session_listbox.select_set(self.selected_index)
            self.session_listbox.see(self.selected_index)

    def _on_session_selected(self, event=None):
        sel = self.session_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        # Salva le modifiche pendenti prima di cambiare
        self._save_current_ui_into_session()
        self.selected_index = idx
        self._load_session_data(idx)

    def _load_session_data(self, idx: int):
        if idx < 0 or idx >= len(self.journal.sessions):
            return
        sess = self.journal.sessions[idx]

        self.var_title.set(sess.title)
        
        # Aggiorna lo stato visivo
        if sess.is_concluded:
            self.lbl_status_badge.config(text="[Conclusa]", bg="#064E3B", fg="#A7F3D0")
            self.btn_conclude.config(state="disabled")
        else:
            self.lbl_status_badge.config(text="[In Corso]", bg="#1E3A8A", fg="#93C5FD")
            self.btn_conclude.config(state="normal")

        # Meta strip
        game_dt_str = format_game_date(sess.game_date, language=get_language())
        self.lbl_meta_strip.config(
            text=f"🗓️ {sess.real_date} | ⏳ {game_dt_str} | 🌤️ {sess.weather} | 🧭 {sess.location}"
        )

        # Prosa narrativa
        self.txt_prose.delete("1.0", tk.END)
        prose_text = sess.prose.strip()
        if not prose_text:
            prose_text = self.journal.synthesize_prose(idx, language=get_language())
            sess.prose = prose_text
        self.txt_prose.insert("1.0", prose_text)

        # Note DM
        self.txt_dm_notes.delete("1.0", tk.END)
        self.txt_dm_notes.insert("1.0", sess.dm_notes)

        # Eventi registrati
        self.txt_events.delete("1.0", tk.END)
        category_icons = {
            "combat": "⚔️", "door": "🚪", "trap": "⚠️", "discovery": "🔍",
            "loot": "💰", "rest": "🏕️", "death": "💀", "note": "📜"
        }
        if not sess.events:
            self.txt_events.insert("1.0", "*Nessun evento ancora registrato in questa sessione.*")
        else:
            for e in sess.events:
                ico = category_icons.get(e.category, "●")
                self.txt_events.insert(tk.END, f"[{e.timestamp}] {ico} {e.title}\n")
                if e.description:
                    self.txt_events.insert(tk.END, f"    {e.description}\n")

    def _persist_to_disk(self):
        camp = getattr(self.game_state, "active_campaign", None)
        if camp:
            camp.journal = self.journal
            if getattr(camp, "folder_path", None):
                try:
                    camp.save()
                except Exception:
                    pass

    def _on_close(self):
        try:
            self._save_current_ui_into_session()
            self._persist_to_disk()
        except Exception:
            pass
        self.destroy()

    def _save_current_ui_into_session(self):
        if 0 <= self.selected_index < len(self.journal.sessions):
            sess = self.journal.sessions[self.selected_index]
            sess.title = self.var_title.get().strip() or f"Sessione {sess.session_number}"
            sess.prose = self.txt_prose.get("1.0", tk.END).strip()
            sess.dm_notes = self.txt_dm_notes.get("1.0", tk.END).strip()
            self._persist_to_disk()

    def _on_save_edits(self):
        self._save_current_ui_into_session()
        self._populate_sessions_list()
        show_toast(self, _t("toast_journal_saved", default="💾 Modifiche salvate nel Diario!"), color=ACCENT_GREEN)

    def _on_regenerate_prose(self):
        if 0 <= self.selected_index < len(self.journal.sessions):
            new_prose = self.journal.synthesize_prose(self.selected_index, language=get_language())
            self.txt_prose.delete("1.0", tk.END)
            self.txt_prose.insert("1.0", new_prose)
            self.journal.sessions[self.selected_index].prose = new_prose
            show_toast(self, _t("toast_prose_regenerated", default="↺ Prosa rigenerata!"), color=ACCENT_BLUE)

    def _on_new_session(self):
        self._save_current_ui_into_session()
        num = len(self.journal.sessions) + 1
        new_sess = self.journal.start_new_session(
            title=f"Sessione {num}",
            weather=getattr(self.game_state, "weather", "Sereno"),
            location=getattr(self.game_state.current_map, "get", lambda k, d: d)("name", "Mappa Tattica") if getattr(self.game_state, "current_map", None) else "Faerûn"
        )
        self.selected_index = len(self.journal.sessions) - 1
        self._populate_sessions_list()
        self._load_session_data(self.selected_index)
        show_toast(self, _t("toast_new_session_started", default="➕ Nuova sessione avviata!"), color=ACCENT_GOLD)

    def _on_conclude_session(self):
        self._save_current_ui_into_session()
        if 0 <= self.selected_index < len(self.journal.sessions):
            sess = self.journal.sessions[self.selected_index]
            sess.is_concluded = True
            if not sess.prose.strip():
                sess.prose = self.journal.synthesize_prose(self.selected_index, language=get_language())
            self._load_session_data(self.selected_index)
            self._populate_sessions_list()
            show_toast(self, _t("toast_session_concluded", default="🏁 Sessione conclusa ed archiviata!"), color=ACCENT_GREEN)

    def _on_share_with_party(self):
        self._save_current_ui_into_session()
        sanitized = self.journal.sanitize_for_players()
        broadcast(self.game_state, make_journal_sync(sanitized))
        active_title = self.journal.sessions[self.selected_index].title if self.journal.sessions else "Diario"
        broadcast(self.game_state, make_chat_broadcast("Sistema", f"📖 Il Dungeon Master ha condiviso la Cronaca: {active_title}!"))
        show_toast(self, _t("toast_journal_shared", default="📢 Diario sincronizzato con tutti i giocatori!"), color=ACCENT_GOLD)

    def _on_copy_discord(self):
        self._save_current_ui_into_session()
        text = self.journal.export_discord(self.selected_index, language=get_language())
        self.clipboard_clear()
        self.clipboard_append(text)
        show_toast(self, _t("toast_copied_discord", default="📋 Copiato negli appunti per Discord/WhatsApp!"), color=ACCENT_BLUE)

    def _on_export_markdown(self):
        self._save_current_ui_into_session()
        fpath = filedialog.asksaveasfilename(
            parent=self,
            title=_t("export_markdown_title", default="Esporta Cronache in Markdown"),
            defaultextension=".md",
            filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if fpath:
            md_content = self.journal.export_full_markdown(language=get_language(), include_dm_notes=True)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(md_content)
            show_toast(self, _t("toast_exported_success", default="📥 Cronache esportate con successo!"), color=ACCENT_GREEN)

    def _on_export_html(self):
        self._save_current_ui_into_session()
        fpath = filedialog.asksaveasfilename(
            parent=self,
            title=_t("export_html_title", default="Esporta Pergamena HTML"),
            defaultextension=".html",
            filetypes=[("HTML Files", "*.html"), ("All Files", "*.*")]
        )
        if fpath:
            html_content = self.journal.export_html(session_index=None, language=get_language(), include_dm_notes=True)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(html_content)
            show_toast(self, _t("toast_exported_html_success", default="📄 Pergamena HTML generata con successo!"), color=ACCENT_GREEN)

