import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog
from common.protocol import make_game_state

class CalendarDialog(tk.Toplevel):
    def __init__(self, master, game_state, is_dm=False, network_or_server=None):
        super().__init__(master)
        self.title("Calendario della Campagna")
        self.minsize(700, 500)
        self.transient(master)
        
        self.game_state = game_state
        self.is_dm = is_dm
        self.network_or_server = network_or_server
        
        if isinstance(self.game_state, dict):
            self.view_year = self.game_state.get('time_year', 1492)
            self.view_month = self.game_state.get('time_month', 1)
        else:
            self.view_year = getattr(self.game_state, 'time_year', 1492)
            self.view_month = getattr(self.game_state, 'time_month', 1)
        
        self.months = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]
        
        self.setup_ui()
        self.refresh_calendar()
        
    def setup_ui(self):
        # Top Bar (Navigation)
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Button(top_frame, text="< Mese Prec", command=self.prev_month).pack(side=tk.LEFT)
        self.lbl_month_year = ttk.Label(top_frame, text="", font=("Arial", 16, "bold"))
        self.lbl_month_year.pack(side=tk.LEFT, expand=True)
        ttk.Button(top_frame, text="Mese Succ >", command=self.next_month).pack(side=tk.RIGHT)
        
        # Calendar Grid (3 weeks of 10 days for Harptos)
        grid_frame = ttk.Frame(self)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.day_frames = {}
        for row in range(3):
            for col in range(10):
                day_num = row * 10 + col + 1
                df = tk.Frame(grid_frame, borderwidth=1, relief="solid", bg="#2B2B2B", width=60, height=60)
                df.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
                grid_frame.columnconfigure(col, weight=1)
                grid_frame.rowconfigure(row, weight=1)
                df.grid_propagate(False)
                
                lbl = tk.Label(df, text=str(day_num), bg="#2B2B2B", fg="white", font=("Arial", 10, "bold"))
                lbl.place(x=2, y=2)
                
                ind = tk.Label(df, text="", bg="#2B2B2B", fg="#FFD700", font=("Arial", 14))
                ind.place(relx=0.5, rely=0.5, anchor="center")
                
                df.bind("<Button-1>", lambda e, d=day_num: self.select_day(d))
                lbl.bind("<Button-1>", lambda e, d=day_num: self.select_day(d))
                ind.bind("<Button-1>", lambda e, d=day_num: self.select_day(d))
                
                self.day_frames[day_num] = {"frame": df, "lbl": lbl, "ind": ind}
                
        # Bottom details
        bot_frame = ttk.Frame(self)
        bot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.lbl_selected_day = ttk.Label(bot_frame, text="Seleziona un giorno", font=("Arial", 12, "bold"))
        self.lbl_selected_day.pack(anchor="w")
        
        self.events_listbox = tk.Listbox(bot_frame, bg="#36393F", fg="white", font=("Arial", 10), height=8)
        self.events_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        if self.is_dm:
            btn_add = ttk.Button(bot_frame, text="Aggiungi Evento (DM)", command=self.add_manual_event)
            btn_add.pack(anchor="e")
            
        self.selected_day = None
        
    def prev_month(self):
        self.view_month -= 1
        if self.view_month < 1:
            self.view_month = 12
            self.view_year -= 1
        self.refresh_calendar()
        
    def next_month(self):
        self.view_month += 1
        if self.view_month > 12:
            self.view_month = 1
            self.view_year += 1
        self.refresh_calendar()
        
    def refresh_calendar(self):
        m_name = self.months[self.view_month]
        self.lbl_month_year.config(text=f"{m_name} {self.view_year}")
        
        if isinstance(self.game_state, dict):
            events_dict = self.game_state.get('calendar_events', {})
            current_y = self.game_state.get('time_year', 1492)
            current_m = self.game_state.get('time_month', 1)
            current_d = self.game_state.get('time_day', 1)
        else:
            events_dict = getattr(self.game_state, 'calendar_events', {})
            current_y = getattr(self.game_state, 'time_year', 1492)
            current_m = getattr(self.game_state, 'time_month', 1)
            current_d = getattr(self.game_state, 'time_day', 1)
        
        for d in range(1, 31):
            date_key = f"{self.view_year}-{self.view_month}-{d}"
            evs = events_dict.get(date_key, [])
            
            bg_col = "#2B2B2B"
            if self.view_year == current_y and self.view_month == current_m and d == current_d:
                bg_col = "#005f5f" # Highlight current day
                
            self.day_frames[d]["frame"].config(bg=bg_col)
            self.day_frames[d]["lbl"].config(bg=bg_col)
            self.day_frames[d]["ind"].config(bg=bg_col)
            
            if evs:
                self.day_frames[d]["ind"].config(text="📅")
            else:
                self.day_frames[d]["ind"].config(text="")
                
        if self.selected_day:
            self.select_day(self.selected_day)
            
    def select_day(self, day):
        self.selected_day = day
        m_name = self.months[self.view_month]
        self.lbl_selected_day.config(text=f"Eventi del {day} {m_name} {self.view_year}:")
        
        self.events_listbox.delete(0, tk.END)
        if isinstance(self.game_state, dict):
            events_dict = self.game_state.get('calendar_events', {})
        else:
            events_dict = getattr(self.game_state, 'calendar_events', {})
        
        date_key = f"{self.view_year}-{self.view_month}-{day}"
        evs = events_dict.get(date_key, [])
        
        if not evs:
            self.events_listbox.insert(tk.END, "Nessun evento registrato.")
        else:
            for ev in evs:
                self.events_listbox.insert(tk.END, f"• {ev}")
                
        # Highlight selected day in grid
        for d in range(1, 31):
            if d == day:
                self.day_frames[d]["frame"].config(relief="raised", borderwidth=2)
            else:
                self.day_frames[d]["frame"].config(relief="solid", borderwidth=1)
                
    def add_manual_event(self):
        if not self.selected_day: return
        text = simpledialog.askstring("Nuovo Evento", "Descrizione dell'evento:")
        if text:
            date_key = f"{self.view_year}-{self.view_month}-{self.selected_day}"
            if not hasattr(self.game_state, 'calendar_events'):
                self.game_state.calendar_events = {}
            if date_key not in self.game_state.calendar_events:
                self.game_state.calendar_events[date_key] = []
            
            # Format time if it's the current day, otherwise just add it
            if self.view_year == self.game_state.time_year and self.view_month == self.game_state.time_month and self.selected_day == self.game_state.time_day:
                time_str = f"[{self.game_state.time_hour:02d}:00] {text}"
            else:
                time_str = text
                
            self.game_state.calendar_events[date_key].append(time_str)
            self.refresh_calendar()
            self.select_day(self.selected_day)
            
            # Sync
            if self.network_or_server:
                self.game_state._trigger_gui_update()
                from server.server import broadcast
                broadcast(self.game_state, make_game_state(self.game_state.get_state_dict()))
