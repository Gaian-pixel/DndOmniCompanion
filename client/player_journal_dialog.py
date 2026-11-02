# client/player_journal_dialog.py
"""
Dialogo di consultazione del Diario di Campagna per i Giocatori (Player Client).
Permette a ciascun giocatore di sfogliare la cronistoria delle sessioni svolte,
leggere la prosa narrativa, consultare gli eventi salienti, annotare memorie personali dell'eroe
ed esportare la cronaca in HTML, Markdown o per Discord/WhatsApp.
"""

import os
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from typing import Optional, Any

from common.theme import (
    apply_modern_window_style,
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT, BORDER_COLOR,
    TEXT_COLOR, TEXT_MUTED, TEXT_DARK, TEXT_GOLD,
    ACCENT_GOLD, ACCENT_GREEN, ACCENT_BLUE,
    FONT_TITLE, FONT_HEADER, FONT_BOLD, FONT_MAIN, FONT_SMALL
)
from common.file_utils import get_writable_dir
from common.i18n import _t, get_language
from common.campaign_journal import CampaignJournal, format_game_date
from components.ui_components import show_toast


class PlayerJournalDialog(tk.Toplevel):
    def __init__(self, master_gui, campaign_journal: Optional[CampaignJournal] = None, character_name: str = "Avventuriero"):
        super().__init__(master_gui.root if hasattr(master_gui, "root") else master_gui)
        self.master_gui = master_gui
        self.character_name = character_name
        self.journal = campaign_journal or CampaignJournal(campaign_name="Campagna")
        self.selected_index: int = max(0, len(self.journal.sessions) - 1)

        self.title(_t("player_journal_title", default="📖 Diario di Campagna — Cronache dell'Avventura"))
        self.geometry("920x640")
        self.minsize(780, 520)
        apply_modern_window_style(self, bind_escape=True)
        self.configure(bg=BG_COLOR)

        self._build_ui()
        self._populate_sessions_list()
        self._load_session_data(self.selected_index)

    def _build_ui(self):
        main_box = tk.Frame(self, bg=BG_COLOR, padx=14, pady=12)
        main_box.pack(fill=tk.BOTH, expand=True)

        # Header
        top_hdr = tk.Frame(main_box, bg=BG_COLOR)
        top_hdr.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            top_hdr,
            text=f"📖 {self.journal.campaign_name} — " + _t("journal_chronicles_title", default="Cronache di Campagna"),
            font=FONT_TITLE, bg=BG_COLOR, fg=ACCENT_GOLD
        ).pack(side=tk.LEFT)

        # Split frame
        split_frame = tk.Frame(main_box, bg=BG_COLOR)
        split_frame.pack(fill=tk.BOTH, expand=True)

        # ------------------ PANNELLO SINISTRO (Indice Sessioni) ------------------
        left_panel = tk.Frame(split_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, width=260, padx=10, pady=10)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        tk.Label(
            left_panel,
            text=_t("journal_session_index", default="📜 Indice delle Sessioni"),
            font=FONT_HEADER, bg=SURFACE_COLOR, fg=TEXT_GOLD
        ).pack(anchor="w", pady=(0, 6))

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

        # ------------------ PANNELLO DESTRO (Dettagli Sessione) ------------------
        right_panel = tk.Frame(split_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Intestazione sessione
        meta_frame = tk.Frame(right_panel, bg=SURFACE_COLOR)
        meta_frame.pack(fill=tk.X, pady=(0, 8))

        self.lbl_title = tk.Label(meta_frame, text="", font=FONT_HEADER, bg=SURFACE_COLOR, fg=ACCENT_GOLD)
        self.lbl_title.pack(anchor="w")

        self.lbl_meta_strip = tk.Label(
            meta_frame,
            text="",
            font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED
        )
        self.lbl_meta_strip.pack(anchor="w", pady=(2, 0))

        # Notebook tabs
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Tab 1: Prosa Narrativa
        tab_prose = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab_prose, text=_t("tab_narrative_prose", default="📖 Resoconto dell'Avventura"))

        self.txt_prose = scrolledtext.ScrolledText(
            tab_prose,
            wrap=tk.WORD,
            bg=SURFACE_COLOR_ALT,
            fg=TEXT_COLOR,
            font=("Georgia", 11),
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_COLOR
        )
        self.txt_prose.pack(fill=tk.BOTH, expand=True)
        self.txt_prose.configure(state="disabled")

        # Tab 2: Note Personali dell'Eroe
        tab_personal = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab_personal, text=_t("tab_personal_notes", default="✏️ Memorie Personali"))

        hdr_personal = tk.Frame(tab_personal, bg=BG_COLOR)
        hdr_personal.pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            hdr_personal,
            text=_t("personal_notes_desc", default="Le tue riflessioni personali di gioco relative a questa sessione."),
            font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_COLOR
        ).pack(side=tk.LEFT)

        ttk.Button(
            hdr_personal,
            text=_t("btn_save_my_notes", default="💾 Salva Memorie"),
            command=self._save_personal_notes
        ).pack(side=tk.RIGHT)

        self.txt_personal = scrolledtext.ScrolledText(
            tab_personal,
            wrap=tk.WORD,
            bg=SURFACE_COLOR_ALT,
            fg=TEXT_COLOR,
            font=("Consolas", 10),
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_COLOR
        )
        self.txt_personal.pack(fill=tk.BOTH, expand=True)

        # Tab 3: Timeline Eventi Salienti
        tab_events = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab_events, text=_t("tab_timeline_events", default="⏱️ Eventi Salienti"))

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
        self.txt_events.configure(state="disabled")

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
            text=_t("btn_export_markdown", default="📥 Esporta Markdown"),
            command=self._on_export_markdown
        ).pack(side=tk.LEFT)

        ttk.Button(
            bbar,
            text=_t("btn_close", default="Chiudi"),
            command=self.destroy
        ).pack(side=tk.RIGHT)

    def destroy(self):
        self._save_personal_notes_silent()
        super().destroy()

    def update_journal(self, new_journal: CampaignJournal):
        self._save_personal_notes_silent()
        self.journal = new_journal
        self._populate_sessions_list()
        self._load_session_data(self.selected_index)

    def _populate_sessions_list(self):
        self.session_listbox.delete(0, tk.END)
        for idx, sess in enumerate(self.journal.sessions):
            self.session_listbox.insert(tk.END, f"#{sess.session_number}: {sess.title}")

        if 0 <= self.selected_index < self.session_listbox.size():
            self.session_listbox.select_set(self.selected_index)
            self.session_listbox.see(self.selected_index)

    def _on_session_selected(self, event=None):
        sel = self.session_listbox.curselection()
        if not sel:
            return
        self._save_personal_notes_silent()
        self.selected_index = sel[0]
        self._load_session_data(self.selected_index)

    def _load_session_data(self, idx: int):
        if idx < 0 or idx >= len(self.journal.sessions):
            return
        sess = self.journal.sessions[idx]

        self.lbl_title.config(text=f"#{sess.session_number}: {sess.title}")

        game_dt_str = format_game_date(sess.game_date, language=get_language())
        self.lbl_meta_strip.config(
            text=f"🗓️ {sess.real_date} | ⏳ {game_dt_str} | 🌤️ {sess.weather} | 🧭 {sess.location}"
        )

        # Prosa
        self.txt_prose.configure(state="normal")
        self.txt_prose.delete("1.0", tk.END)
        prose_text = sess.prose.strip() or self.journal.synthesize_prose(idx, language=get_language())
        self.txt_prose.insert("1.0", prose_text)
        self.txt_prose.configure(state="disabled")

        # Eventi
        self.txt_events.configure(state="normal")
        self.txt_events.delete("1.0", tk.END)
        category_icons = {
            "combat": "⚔️", "door": "🚪", "trap": "⚠️", "discovery": "🔍",
            "loot": "💰", "rest": "🏕️", "death": "💀", "note": "📜"
        }
        if not sess.events:
            self.txt_events.insert("1.0", "*Nessun evento registrato in questa sessione.*")
        else:
            for e in sess.events:
                ico = category_icons.get(e.category, "●")
                self.txt_events.insert(tk.END, f"[{e.timestamp}] {ico} {e.title}\n")
                if e.description:
                    self.txt_events.insert(tk.END, f"    {e.description}\n")
        self.txt_events.configure(state="disabled")

        # Note personali
        notes_path = self._get_notes_file_path()
        personal_notes = ""
        if os.path.exists(notes_path):
            try:
                with open(notes_path, "r", encoding="utf-8") as f:
                    all_notes = json.load(f)
                    personal_notes = all_notes.get(str(sess.session_number), "")
            except Exception:
                personal_notes = ""
        self.txt_personal.delete("1.0", tk.END)
        self.txt_personal.insert("1.0", personal_notes)

    def _get_notes_file_path(self) -> str:
        safe_char = "".join(c for c in self.character_name if c.isalnum() or c in ("_", "-")).strip() or "hero"
        camp_name = getattr(self.journal, "campaign_name", "campaign")
        safe_camp = "".join(c for c in camp_name if c.isalnum() or c in ("_", "-")).strip() or "default"
        return os.path.join(get_writable_dir(), "client_data", f"journal_notes_{safe_char}_{safe_camp}.json")

    def _save_personal_notes_silent(self):
        if not hasattr(self, "selected_index") or self.selected_index < 0 or self.selected_index >= len(self.journal.sessions):
            return
        try:
            sess = self.journal.sessions[self.selected_index]
            notes_path = self._get_notes_file_path()
            all_notes = {}
            if os.path.exists(notes_path):
                try:
                    with open(notes_path, "r", encoding="utf-8") as f:
                        all_notes = json.load(f)
                except Exception:
                    all_notes = {}
            text = self.txt_personal.get("1.0", tk.END).strip()
            all_notes[str(sess.session_number)] = text
            os.makedirs(os.path.dirname(notes_path), exist_ok=True)
            with open(notes_path, "w", encoding="utf-8") as f:
                json.dump(all_notes, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _save_personal_notes(self):
        self._save_personal_notes_silent()
        show_toast(self, _t("toast_notes_saved", default="💾 Memorie personali salvate con successo!"), color=ACCENT_GREEN)

    def _on_copy_discord(self):
        text = self.journal.export_discord(self.selected_index, language=get_language())
        self.clipboard_clear()
        self.clipboard_append(text)
        show_toast(self, _t("toast_copied_discord", default="📋 Copiato negli appunti per Discord/WhatsApp!"), color=ACCENT_BLUE)

    def _on_export_markdown(self):
        fpath = filedialog.asksaveasfilename(
            parent=self,
            title=_t("export_markdown_title", default="Esporta Cronache in Markdown"),
            defaultextension=".md",
            filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if fpath:
            md_content = self.journal.export_full_markdown(language=get_language(), include_dm_notes=False)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(md_content)
            show_toast(self, _t("toast_exported_success", default="📥 Cronache esportate con successo!"), color=ACCENT_GREEN)

    def _on_export_html(self):
        fpath = filedialog.asksaveasfilename(
            parent=self,
            title=_t("export_html_title", default="Esporta Pergamena HTML"),
            defaultextension=".html",
            filetypes=[("HTML Files", "*.html"), ("All Files", "*.*")]
        )
        if fpath:
            html_content = self.journal.export_html(session_index=None, language=get_language(), include_dm_notes=False)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(html_content)
            show_toast(self, _t("toast_exported_html_success", default="📄 Pergamena HTML generata con successo!"), color=ACCENT_GREEN)
