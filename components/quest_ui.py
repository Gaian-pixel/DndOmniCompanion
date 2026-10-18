import tkinter as tk
from tkinter import ttk, simpledialog
from common.messagebox import messagebox

class QuestLogDialog(tk.Toplevel):
    def __init__(self, parent, game_state, is_dm=False, network_or_server=None):
        super().__init__(parent)
        self.title("Quest Log / Note Condivise")
        self.minsize(750, 550)
        self.transient(parent)
        self.grab_set()

        from common.theme import apply_modern_window_style
        apply_modern_window_style(self)

        self.game_state = game_state
        self.is_dm = is_dm
        self.network = network_or_server
        
        self.create_widgets()
        self.refresh_list()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top_frame, text="Missioni e Appunti", font=("Helvetica", 16, "bold")).pack(side=tk.LEFT)
        
        if self.is_dm:
            ttk.Button(top_frame, text="➕ Nuova Missione", command=self.add_quest, style="Success.TButton").pack(side=tk.RIGHT)
            
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.quest_listbox = tk.Listbox(list_frame, font=("Helvetica", 12), selectmode=tk.SINGLE)
        self.quest_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.quest_listbox.bind('<<ListboxSelect>>', self.on_select)
        
        if self.is_dm:
            self.quest_listbox.bind('<Double-1>', lambda e: self.edit_quest())
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.quest_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.quest_listbox.config(yscrollcommand=scrollbar.set)
        
        detail_frame = ttk.Frame(main_frame)
        detail_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 0))
        
        self.detail_text = tk.Text(detail_frame, height=12, wrap=tk.WORD, font=("Helvetica", 12))
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        self.detail_text.config(state=tk.DISABLED)
        
        if self.is_dm:
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(fill=tk.X, pady=(15, 0))
            ttk.Button(btn_frame, text="✅ Segna Completata", command=self.complete_quest).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="✏️ Modifica", command=self.edit_quest, style="Info.TButton").pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="❌ Elimina", command=self.delete_quest, style="Danger.TButton").pack(side=tk.LEFT, padx=5)

    def _get_quests(self):
        if isinstance(self.game_state, dict):
            return self.game_state.get("quests", [])
        return getattr(self.game_state, "quests", [])

    def refresh_list(self):
        self.quest_listbox.delete(0, tk.END)
        quests = self._get_quests()
        for i, q in enumerate(quests):
            status = "✅" if q.get("status") == "completed" else "📜"
            self.quest_listbox.insert(tk.END, f"{status} {q.get('title', 'Senza Titolo')}")

    def on_select(self, event):
        sel = self.quest_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        quests = self._get_quests()
        if idx < len(quests):
            q = quests[idx]
            self.detail_text.config(state=tk.NORMAL)
            self.detail_text.delete("1.0", tk.END)
            self.detail_text.insert(tk.END, f"Titolo: {q.get('title')}\nStato: {q.get('status')}\n\nDescrizione:\n{q.get('description', '')}")
            self.detail_text.config(state=tk.DISABLED)

    def add_quest(self):
        QuestEditorDialog(self, "Nuova Missione")

    def edit_quest(self):
        sel = self.quest_listbox.curselection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona una missione da modificare.")
            return
        idx = sel[0]
        quests = self._get_quests()
        if idx < len(quests):
            QuestEditorDialog(self, "Modifica Missione", quests[idx], idx)

    def complete_quest(self):
        sel = self.quest_listbox.curselection()
        if not sel: return
        idx = sel[0]
        quests = self._get_quests()
        quests[idx]["status"] = "completed"
        self._sync()
        self.refresh_list()

    def delete_quest(self):
        sel = self.quest_listbox.curselection()
        if not sel: return
        if not messagebox.askyesno("Conferma", "Sei sicuro di voler eliminare questa missione?"):
            return
        idx = sel[0]
        quests = self._get_quests()
        quests.pop(idx)
        self._sync()
        self.refresh_list()
        
    def save_quest(self, title, desc, idx=None):
        quests = self._get_quests()
        if idx is None:
            quests.append({"title": title, "description": desc, "status": "active"})
        else:
            quests[idx]["title"] = title
            quests[idx]["description"] = desc
        self._sync()
        self.refresh_list()

    def _sync(self):
        if self.is_dm and self.network:
            if hasattr(self.game_state, "_trigger_gui_update"):
                self.game_state._trigger_gui_update()
            from common.protocol import make_quest_list_update, make_game_state
            from server.network import broadcast
            g_state = getattr(self.network, "game_state", self.game_state)
            try:
                broadcast(g_state, make_quest_list_update(self._get_quests()))
                broadcast(g_state, make_game_state(g_state.get_state_dict()))
            except Exception as e:
                print("Errore sync quest:", e)

class QuestEditorDialog(tk.Toplevel):

    def __init__(self, parent, title_str, quest_data=None, idx=None):
        super().__init__(parent)
        self.title(title_str)
        self.minsize(600, 450)
        self.transient(parent)
        self.grab_set()
        
        from common.theme import apply_modern_window_style
        apply_modern_window_style(self)
        
        self.parent = parent
        self.quest_idx = idx
        
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Titolo Missione:", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.title_entry = ttk.Entry(main_frame, font=("Helvetica", 12))
        self.title_entry.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(main_frame, text="Descrizione / Note:", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))
        from tkinter import scrolledtext
        self.desc_text = scrolledtext.ScrolledText(main_frame, font=("Helvetica", 11), wrap=tk.WORD, height=10)
        self.desc_text.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        if quest_data:
            self.title_entry.insert(0, quest_data.get("title", ""))
            self.desc_text.insert(tk.END, quest_data.get("description", ""))
            
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Salva", style="Success.TButton", command=self.on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Annulla", command=self.destroy).pack(side=tk.RIGHT)
        
        self.title_entry.focus_set()
        
    def on_save(self):
        t = self.title_entry.get().strip()
        if not t:
            messagebox.showerror("Errore", "Il titolo è obbligatorio.", parent=self)
            return
        d = self.desc_text.get("1.0", tk.END).strip()
        self.parent.save_quest(t, d, self.quest_idx)
        self.destroy()


