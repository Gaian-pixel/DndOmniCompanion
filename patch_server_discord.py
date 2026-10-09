import re

def modify_server():
    with open('server/dm_gui.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update imports
    content = content.replace(
        "from components.ui_components import HexMapCanvas",
        "from components.ui_components import HexMapCanvas, ToolTip"
    )

    # 2. Add ToolTips for left toolbar buttons
    # In dm_gui.py, the buttons are created without being assigned to self, but wait, looking at dm_gui.py lines 77-79:
    # ttk.Button(left_toolbar, text="👆", width=3, command=lambda: self.map_canvas.center_view() if self.map_canvas else None).pack(pady=5)
    # ttk.Button(left_toolbar, text="☁️", width=3, command=lambda: print("Nebbia: Placeholder")).pack(pady=5)
    # ttk.Button(left_toolbar, text="📏", width=3, command=lambda: print("Misura: Placeholder")).pack(pady=5)

    old_btn1 = 'ttk.Button(left_toolbar, text="👆", width=3, command=lambda: self.map_canvas.center_view() if self.map_canvas else None).pack(pady=5)'
    new_btn1 = '''btn1 = ttk.Button(left_toolbar, text="👆", width=3, command=lambda: self.map_canvas.center_view() if self.map_canvas else None)
        btn1.pack(pady=5)
        ToolTip(btn1, "Centra Mappa")'''
    content = content.replace(old_btn1, new_btn1)

    old_btn2 = 'ttk.Button(left_toolbar, text="☁️", width=3, command=lambda: print("Nebbia: Placeholder")).pack(pady=5)'
    new_btn2 = '''btn2 = ttk.Button(left_toolbar, text="☁️", width=3, command=lambda: print("Nebbia: Placeholder"))
        btn2.pack(pady=5)
        ToolTip(btn2, "Nebbia")'''
    content = content.replace(old_btn2, new_btn2)

    old_btn3 = 'ttk.Button(left_toolbar, text="📏", width=3, command=lambda: print("Misura: Placeholder")).pack(pady=5)'
    new_btn3 = '''btn3 = ttk.Button(left_toolbar, text="📏", width=3, command=lambda: print("Misura: Placeholder"))
        btn3.pack(pady=5)
        ToolTip(btn3, "Misura Distanza")'''
    content = content.replace(old_btn3, new_btn3)
    
    # And there are some other buttons like btn_clear_aoe and center_map_btn
    # self.btn_clear_aoe.pack(side=tk.RIGHT, padx=5) -> ToolTip(self.btn_clear_aoe, "Pulisci AoE")
    content = content.replace(
        "self.btn_clear_aoe.pack(side=tk.RIGHT, padx=5)",
        "self.btn_clear_aoe.pack(side=tk.RIGHT, padx=5)\n        ToolTip(self.btn_clear_aoe, \"Pulisci Aree di Effetto\")"
    )
    content = content.replace(
        "self.center_map_btn.pack(side=tk.LEFT, padx=5)",
        "self.center_map_btn.pack(side=tk.LEFT, padx=5)\n        ToolTip(self.center_map_btn, \"Centra Mappa sulla Vista\")"
    )
    
    # 3. Add Voice Controls
    old_chat_input = '''        chat_input_frame = ttk.Frame(tab_chat)
        chat_input_frame.pack(fill=tk.X, pady=(5, 0))
        self.chat_entry = ttk.Entry(chat_input_frame)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_entry.bind("<Return>", lambda e: self.send_dm_chat())
        ttk.Button(chat_input_frame, text="Invia", command=self.send_dm_chat).pack(side=tk.LEFT)'''
        
    new_chat_input = '''        chat_input_frame = ttk.Frame(tab_chat)
        chat_input_frame.pack(fill=tk.X, pady=(5, 0))
        self.chat_entry = ttk.Entry(chat_input_frame)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_entry.bind("<Return>", lambda e: self.send_dm_chat())
        ttk.Button(chat_input_frame, text="Invia", command=self.send_dm_chat).pack(side=tk.LEFT)

        self.voice_controls_frame = tk.Frame(tab_chat, bg="#292B2F", pady=5, padx=5)
        self.voice_controls_frame.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(self.voice_controls_frame, text="Voice Channel: Disconnesso", bg="#292B2F", fg="#8E9297", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        self.btn_deafen = tk.Button(self.voice_controls_frame, text=" 🎧 ", bg="#36393F", fg="white", relief=tk.FLAT, command=self.toggle_deafen)
        self.btn_deafen.pack(side=tk.RIGHT, padx=2)
        self.btn_mute = tk.Button(self.voice_controls_frame, text=" 🎤 ", bg="#36393F", fg="white", relief=tk.FLAT, command=self.toggle_mute)
        self.btn_mute.pack(side=tk.RIGHT, padx=2)'''
    content = content.replace(old_chat_input, new_chat_input)

    # 4. Chat formatting (discord style)
    old_create = '''    def create_chat_tab(self, name):
        if name in self.chat_tabs: return
        tab_frame = ttk.Frame(self.notebook)
        text_widget = scrolledtext.ScrolledText(tab_frame, state='disabled', wrap=tk.WORD, bg=SURFACE_COLOR, 
fg=TEXT_COLOR, borderwidth=0, highlightthickness=0)
        text_widget.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(tab_frame, text=name)
        self.chat_tabs[name] = text_widget'''
        
    new_create = '''    def create_chat_tab(self, name):
        if name in self.chat_tabs: return
        tab_frame = ttk.Frame(self.notebook)
        text_widget = scrolledtext.ScrolledText(tab_frame, state='disabled', wrap=tk.WORD, bg="#36393F", 
fg="#DCDDDE", borderwidth=0, highlightthickness=0, font=("Arial", 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(tab_frame, text=name)
        self.chat_tabs[name] = text_widget
        
        # Configure tags for Discord-like format
        text_widget.tag_config("timestamp", foreground="#72767D", font=("Arial", 8))
        text_widget.tag_config("sender", font=("Arial", 10, "bold"))
        text_widget.tag_config("text", foreground="#DCDDDE")'''
    content = content.replace(old_create, new_create)
    
    old_log = '''    def log_to_chat(self, message, tab_name="Sistema"):
        text_widget = self.chat_tabs.get(tab_name)
        if not text_widget: return
        text_widget.config(state="normal"); text_widget.insert(tk.END, message + "\\n")
        text_widget.config(state="disabled"); text_widget.see(tk.END)'''
        
    new_log = '''    def log_to_chat(self, message, tab_name="Sistema", sender="DM", color="white"):
        text_widget = self.chat_tabs.get(tab_name)
        if not text_widget: return
        text_widget.config(state="normal")
        
        import datetime
        timestamp = datetime.datetime.now().strftime("[%H:%M]")
        
        text_widget.insert(tk.END, f"{timestamp} ", "timestamp")
        
        sender_color = color if sender != "Sistema" else "#72767D"
        if sender_color not in text_widget.tag_names(): text_widget.tag_config(sender_color, foreground=sender_color, font=("Arial", 10, "bold"))
        
        text_widget.insert(tk.END, f"{sender}: ", sender_color)
        
        if "\\n" in message:
            text_widget.insert(tk.END, message + "\\n", "text")
        else:
            text_widget.insert(tk.END, message + "\\n", color)
            
        text_widget.config(state="disabled")
        text_widget.see(tk.END)'''
    content = content.replace(old_log, new_log)
    
    # also add voice placeholders if not present
    if "def toggle_mute" not in content:
        content += """
    def toggle_mute(self):
        print("Mute toggled in server")

    def toggle_deafen(self):
        print("Deafen toggled in server")
"""

    with open('server/dm_gui.py', 'w', encoding='utf-8') as f:
        f.write(content)

modify_server()
