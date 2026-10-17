# server/dm_soundboard_panel.py
"""
Pannello Audio e Soundboard per il Dungeon Master.
Gestisce la libreria tracce (musica d'atmosfera, effetti sonori/SFX),
la riproduzione sincrona verso i client connessi, il looping e lo streaming YouTube.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog
from common.messagebox import messagebox
from common.i18n import _t
from common.theme import FONT_MAIN, FONT_SMALL, FONT_BOLD, SURFACE_COLOR, SURFACE_COLOR_ALT, BORDER_COLOR, TEXT_COLOR
from components.ui_components import ToolTip
from common.protocol import make_audio_track_play, make_audio_stop, make_audio_play_broadcast
from common.network_utils import broadcast


class DMSoundboardPanel(ttk.Frame):
    """Pannello modulare per la gestione dell'audio e soundboard del Master."""

    def __init__(self, parent, dm_gui):
        super().__init__(parent, padding=5)
        self.dm_gui = dm_gui
        self.server = getattr(dm_gui, "server", None)
        self.setup_ui()

    def setup_ui(self):
        self.lbl_audio_lib = ttk.Label(self, text=_t("audio_library_header"), font=("Arial", 12, "bold"))
        self.lbl_audio_lib.pack(anchor="w", pady=(0, 2))
        self.lbl_audio_desc = ttk.Label(self, text=_t("audio_library_desc"),
                                        style="Muted.TLabel", wraplength=320)
        self.lbl_audio_desc.pack(anchor="w", pady=(0, 5))

        top_btns = ttk.Frame(self)
        top_btns.pack(fill=tk.X, pady=(0, 4))
        self.btn_import_audio = ttk.Button(top_btns, text=_t("audio_upload_btn"), command=self.import_audio_tracks, style="Success.TButton")
        self.btn_import_audio.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        btn_rename = ttk.Button(top_btns, text="✏", width=3, command=self.rename_audio_track)
        btn_rename.pack(side=tk.LEFT, padx=1)
        btn_toggle = ttk.Button(top_btns, text="🔁", width=3, command=self.toggle_audio_category)
        btn_toggle.pack(side=tk.LEFT, padx=1)
        btn_remove = ttk.Button(top_btns, text="🗑", width=3, command=self.remove_audio_track)
        btn_remove.pack(side=tk.LEFT, padx=(1, 0))

        ToolTip(btn_rename, "Rinomina traccia")
        ToolTip(btn_toggle, "Cambia tipo (Musica / Effetto)")
        ToolTip(btn_remove, "Elimina traccia dalla libreria")

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.audio_tree = ttk.Treeview(tree_frame, columns=("Nome", "Tipo", "Durata"), show="headings", height=9, selectmode="browse")
        self.audio_tree.heading("Nome", text=_t("audio_col_name"))
        self.audio_tree.heading("Tipo", text=_t("audio_col_type"))
        self.audio_tree.heading("Durata", text=_t("audio_col_duration"))
        self.audio_tree.column("Nome", width=170)
        self.audio_tree.column("Tipo", width=65, anchor="center")
        self.audio_tree.column("Durata", width=55, anchor="center")
        self.audio_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.audio_tree.yview)
        self.audio_tree.configure(yscroll=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.audio_tree.bind("<Double-1>", lambda e: self.play_selected_audio())

        opts = ttk.Frame(self)
        opts.pack(fill=tk.X, pady=4)
        self.audio_loop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Ripeti musica (loop)", variable=self.audio_loop_var).pack(anchor="w")
        self.audio_dm_listen_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Ascolta anche io (DM)", variable=self.audio_dm_listen_var).pack(anchor="w")

        vol_row = ttk.Frame(self)
        vol_row.pack(fill=tk.X)
        ttk.Label(vol_row, text="Volume per i giocatori:").pack(side=tk.LEFT)
        self.audio_volume_var = tk.IntVar(value=80)
        ttk.Scale(vol_row, from_=0, to=100, variable=self.audio_volume_var, orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        play_row = ttk.Frame(self)
        play_row.pack(fill=tk.X, pady=(6, 2))
        ttk.Button(play_row, text="▶ Riproduci per tutti", command=self.play_selected_audio, style="Primary.TButton").pack(fill=tk.X, pady=1)
        stop_row = ttk.Frame(self)
        stop_row.pack(fill=tk.X)
        ttk.Button(stop_row, text="⏹ Ferma musica", command=lambda: self.stop_audio("music")).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(stop_row, text="⏹ Ferma tutto", command=lambda: self.stop_audio("all"), style="Danger.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

        self.audio_now_playing = ttk.Label(self, text="In riproduzione: -", style="Muted.TLabel", wraplength=320)
        self.audio_now_playing.pack(anchor="w", pady=(6, 4))

        ttk.Separator(self).pack(fill=tk.X, pady=4)
        ttk.Button(self, text="🔗 Apri link (YouTube) ai giocatori...", command=self.share_audio_link).pack(fill=tk.X)

        self.refresh_audio_list()

    @staticmethod
    def _format_duration(seconds):
        seconds = int(seconds or 0)
        return f"{seconds // 60}:{seconds % 60:02d}"

    def refresh_audio_list(self):
        if not hasattr(self.dm_gui, "server") or not self.dm_gui.server:
            return
        library = self.dm_gui.server.game_state.audio_library
        for item in self.audio_tree.get_children():
            self.audio_tree.delete(item)
        for t in library.tracks:
            icon = "🎵" if t["category"] == "Musica" else "💥"
            self.audio_tree.insert("", tk.END, iid=t["id"], values=(t["name"], f"{icon} {t['category']}", self._format_duration(t.get("duration"))))

    def _selected_track(self):
        sel = self.audio_tree.selection()
        if not sel:
            messagebox.showinfo("Audio", "Seleziona prima una traccia dalla libreria.")
            return None
        return self.dm_gui.server.game_state.audio_library.get(sel[0])

    def import_audio_tracks(self):
        paths = filedialog.askopenfilenames(
            title="Seleziona tracce audio",
            filetypes=[("File audio", "*.mp3 *.ogg *.wav *.flac"), ("Tutti i file", "*.*")])
        if not paths:
            return
        library = self.dm_gui.server.game_state.audio_library
        errors = []
        imported = 0
        for p in paths:
            try:
                library.import_file(p)
                imported += 1
            except Exception as e:
                errors.append(f"{os.path.basename(p)}: {e}")
        self.refresh_audio_list()
        if imported:
            self.dm_gui.log_to_chat(f"[AUDIO] {imported} traccia/e aggiunte alla libreria.")
        if errors:
            messagebox.showwarning("Alcuni file non sono stati importati", "\n".join(errors))

    def rename_audio_track(self):
        t = self._selected_track()
        if not t: return
        new_name = simpledialog.askstring("Rinomina traccia", "Nuovo nome:", initialvalue=t["name"], parent=self.dm_gui.master)
        if new_name and new_name.strip():
            self.dm_gui.server.game_state.audio_library.rename(t["id"], new_name.strip())
            self.refresh_audio_list()

    def toggle_audio_category(self):
        t = self._selected_track()
        if not t: return
        self.dm_gui.server.game_state.audio_library.toggle_category(t["id"])
        self.refresh_audio_list()
        self.audio_tree.selection_set(t["id"])

    def remove_audio_track(self):
        t = self._selected_track()
        if not t: return
        if messagebox.askyesno("Elimina traccia", f"Eliminare '{t['name']}' dalla libreria?"):
            self.dm_gui.server.game_state.audio_library.remove(t["id"])
            self.refresh_audio_list()

    def play_selected_audio(self):
        t = self._selected_track()
        if not t: return
        is_music = t["category"] == "Musica"
        channel = "music" if is_music else "sfx"
        loop = bool(self.audio_loop_var.get()) if is_music else False
        volume = self.audio_volume_var.get() / 100.0
        msg = make_audio_track_play(t["id"], t["name"], t["ext"], t["size"], channel=channel, loop=loop, volume=volume)

        game_state = self.dm_gui.server.game_state
        if is_music:
            game_state.current_music = msg if loop else None
        broadcast(game_state, msg)

        if self.audio_dm_listen_var.get():
            self.dm_gui.audio_manager.play(game_state.audio_library.get_path(t["id"]), channel=channel, loop=loop, volume=volume, name=t["name"])
        if is_music:
            self.audio_now_playing.config(text=f"In riproduzione: 🎵 {t['name']}{' (loop)' if loop else ''}")
        self.dm_gui.log_to_chat(f"[AUDIO] {'Musica' if is_music else 'Effetto'} avviato per tutti: {t['name']}")

    def stop_audio(self, channel="all"):
        if channel in ("music", "all"):
            self.dm_gui.server.game_state.current_music = None
            self.audio_now_playing.config(text="In riproduzione: -")
        broadcast(self.dm_gui.server.game_state, make_audio_stop(channel))
        self.dm_gui.audio_manager.stop(channel)
        self.dm_gui.log_to_chat(f"[AUDIO] {'Musica fermata' if channel == 'music' else 'Tutto l audio fermato'}.")

    def share_audio_link(self):
        url = simpledialog.askstring("Link audio", "Incolla il link (es. YouTube) da aprire nel browser dei giocatori:", parent=self.dm_gui.master)
        if url and url.strip():
            self.play_audio(url.strip())

    def play_audio(self, url):
        broadcast(self.dm_gui.server.game_state, make_audio_play_broadcast(url))
        self.dm_gui.log_to_chat(f"Audio avviato: {url}")

