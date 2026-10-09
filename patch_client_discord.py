import re

def modify_client():
    with open('client/client.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update imports
    content = content.replace(
        "from components.ui_components import HexMapCanvas",
        "from components.ui_components import HexMapCanvas, ToolTip"
    )

    # 2. Add ToolTips
    content = content.replace(
        "self.center_map_btn.pack(pady=2)",
        "self.center_map_btn.pack(pady=2)\n        ToolTip(self.center_map_btn, \"Centra Mappa\")"
    )
    content = content.replace(
        "self.aoe_button.pack(pady=2)",
        "self.aoe_button.pack(pady=2)\n        ToolTip(self.aoe_button, \"Area di Effetto\")"
    )
    content = content.replace(
        "self.measure_btn.pack(pady=2)",
        "self.measure_btn.pack(pady=2)\n        ToolTip(self.measure_btn, \"Misura Distanza\")"
    )

    # 3. Add Voice Controls
    old_cmd_frame = """        chat_cmd_frame = ttk.Frame(chat_tab)
        chat_cmd_frame.pack(fill=tk.X, padx=5, pady=(2, 5))
        self.entry = ttk.Entry(chat_cmd_frame, font=self.default_font)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entry.bind("<Return>", self.send_chat_message)
        ttk.Button(chat_cmd_frame, text="Invia", command=self.send_chat_message).pack(side=tk.LEFT)"""
        
    new_cmd_frame = """        chat_cmd_frame = ttk.Frame(chat_tab)
        chat_cmd_frame.pack(fill=tk.X, padx=5, pady=(2, 5))
        self.entry = ttk.Entry(chat_cmd_frame, font=self.default_font)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entry.bind("<Return>", self.send_chat_message)
        ttk.Button(chat_cmd_frame, text="Invia", command=self.send_chat_message).pack(side=tk.LEFT)

        self.voice_controls_frame = tk.Frame(chat_tab, bg="#292B2F", pady=5, padx=5)
        self.voice_controls_frame.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(self.voice_controls_frame, text="Voice Channel: Disconnesso", bg="#292B2F", fg="#8E9297", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        self.btn_deafen = tk.Button(self.voice_controls_frame, text=" 🎧 ", bg="#36393F", fg="white", relief=tk.FLAT, command=self.toggle_deafen)
        self.btn_deafen.pack(side=tk.RIGHT, padx=2)
        self.btn_mute = tk.Button(self.voice_controls_frame, text=" 🎤 ", bg="#36393F", fg="white", relief=tk.FLAT, command=self.toggle_mute)
        self.btn_mute.pack(side=tk.RIGHT, padx=2)"""
    
    content = content.replace(old_cmd_frame, new_cmd_frame)

    # 4. Modify chat visual setup
    old_chat_tab = """    def create_chat_tab(self, name):
        if name in self.chat_tabs: return
        tab_frame=ttk.Frame(self.notebook)
        text_widget=scrolledtext.ScrolledText(tab_frame, state='disabled', wrap=tk.WORD, height=8, bg="#1E1E1E", fg="#E0E0E0", borderwidth=0, highlightthickness=0)
        text_widget.pack(fill=tk.BOTH, expand=True); self.notebook.add(tab_frame, text=name); self.chat_tabs[name]=text_widget"""
        
    new_chat_tab = """    def create_chat_tab(self, name):
        if name in self.chat_tabs: return
        tab_frame=ttk.Frame(self.notebook)
        text_widget=scrolledtext.ScrolledText(tab_frame, state='disabled', wrap=tk.WORD, height=8, bg="#36393F", fg="#DCDDDE", borderwidth=0, highlightthickness=0, font=("Arial", 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(tab_frame, text=name)
        self.chat_tabs[name]=text_widget
        
        # Configure tags for Discord-like format
        text_widget.tag_config("timestamp", foreground="#72767D", font=("Arial", 8))
        text_widget.tag_config("sender", font=("Arial", 10, "bold"))
        text_widget.tag_config("text", foreground="#DCDDDE")"""
        
    content = content.replace(old_chat_tab, new_chat_tab)
    
    old_log = """    def log_to_chat(self, message, tab_name, color="white"):
        text_widget=self.chat_tabs.get(tab_name)
        if not text_widget: return
        text_widget.config(state='normal')
        if color not in text_widget.tag_names(): text_widget.tag_config(color, foreground=color)
        text_widget.insert(tk.END, message + "\\n", color)
        text_widget.config(state='disabled'); text_widget.see(tk.END)"""
        
    new_log = """    def log_to_chat(self, message, tab_name, sender="Sistema", color="white"):
        text_widget=self.chat_tabs.get(tab_name)
        if not text_widget: return
        text_widget.config(state='normal')
        
        import datetime
        timestamp = datetime.datetime.now().strftime("[%H:%M]")
        
        text_widget.insert(tk.END, f"{timestamp} ", "timestamp")
        
        sender_color = color if sender != "Sistema" else "#72767D"
        if sender_color not in text_widget.tag_names(): text_widget.tag_config(sender_color, foreground=sender_color, font=("Arial", 10, "bold"))
        
        text_widget.insert(tk.END, f"{sender}: ", sender_color)
        
        if "\n" in message:
            text_widget.insert(tk.END, message + "\\n", "text")
        else:
            text_widget.insert(tk.END, message + "\\n", color)
            
        text_widget.config(state='disabled')
        text_widget.see(tk.END)"""
    content = content.replace(old_log, new_log)
    
    old_broadcast = """    def handle_chat_broadcast(self, data):
        sender, text, is_whisper=data.get('sender'), data.get('text'), data.get('is_whisper')
        if not is_whisper: self.log_to_chat(f"[{sender}]: {text}", "Globale", "white")
        else:
            tab_name=sender.replace("Tu -> ", "") if sender.startswith("Tu -> ") else sender
            prefix="Tu" if sender.startswith("Tu -> ") else sender
            self.create_chat_tab(tab_name); self.log_to_chat(f"[{prefix}]: {text}", tab_name, "#87CEFA")"""
            
    new_broadcast = """    def handle_chat_broadcast(self, data):
        sender, text, is_whisper=data.get('sender'), data.get('text'), data.get('is_whisper')
        if not is_whisper: self.log_to_chat(text, "Globale", sender=sender, color="#5865F2")
        else:
            tab_name=sender.replace("Tu -> ", "") if sender.startswith("Tu -> ") else sender
            prefix="Tu" if sender.startswith("Tu -> ") else sender
            self.create_chat_tab(tab_name)
            self.log_to_chat(text, tab_name, sender=prefix, color="#EB459E")"""
    content = content.replace(old_broadcast, new_broadcast)
    
    old_dice = """    def handle_dice_roll(self, data):
        res, reason_text=data.get('result', {}), f" ({data.get('reason')})" if data.get('reason') else ""
        log_text=(f"[{data.get('player_name')}] tira {data.get('formula')}{reason_text}: " f"{res.get('rolls')} + {res.get('modifier')} = {res.get('total')}")
        self.log_to_chat(log_text, "Globale", "orange")"""
        
    new_dice = """    def handle_dice_roll(self, data):
        res, reason_text=data.get('result', {}), f" ({data.get('reason')})" if data.get('reason') else ""
        log_text=(f"tira {data.get('formula')}{reason_text}: " f"{res.get('rolls')} + {res.get('modifier')} = {res.get('total')}")
        self.log_to_chat(log_text, "Globale", sender=data.get('player_name'), color="#FEE75C")"""
    content = content.replace(old_dice, new_dice)

    old_trade = """    def do_trade(self, item, target_name):
        if self.is_connected:
            self.network.send(make_give_item_request(target_name, item))
            self.log_to_chat(f"Hai inviato l'oggetto '{item.get('name')}' a {target_name}.", "Globale", "lightblue")"""
    new_trade = """    def do_trade(self, item, target_name):
        if self.is_connected:
            self.network.send(make_give_item_request(target_name, item))
            self.log_to_chat(f"Hai inviato l'oggetto '{item.get('name')}' a {target_name}.", "Globale", sender="Sistema", color="#00B0F4")"""
    content = content.replace(old_trade, new_trade)

    old_open_priv = """    def open_private_chat_from_list(self, event):
        selected_indices=self.player_listbox.curselection()
        if not selected_indices: return
        display_text=self.player_listbox.get(selected_indices[0])
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip() if " (HP" in display_text else display_text.strip()
        if player_name == "DM": pass
        elif player_name == self.name: return # Non aprire chat con se stessi
        self.create_chat_tab(player_name)
        for i, tab_text in enumerate(self.notebook.tabs()):
            if self.notebook.tab(i, "text") == player_name: self.notebook.select(i); break
        self.entry.focus_set(); self.log_to_chat(f"Hai aperto una chat con {player_name}.", player_name, "grey")"""
    new_open_priv = """    def open_private_chat_from_list(self, event):
        selected_indices=self.player_listbox.curselection()
        if not selected_indices: return
        display_text=self.player_listbox.get(selected_indices[0])
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip() if " (HP" in display_text else display_text.strip()
        if player_name == "DM": pass
        elif player_name == self.name: return # Non aprire chat con se stessi
        self.create_chat_tab(player_name)
        for i, tab_text in enumerate(self.notebook.tabs()):
            if self.notebook.tab(i, "text") == player_name: self.notebook.select(i); break
        self.entry.focus_set(); self.log_to_chat(f"Hai aperto una chat con {player_name}.", player_name, sender="Sistema", color="#99AAB5")"""
    content = content.replace(old_open_priv, new_open_priv)
    
    # 5. Add Voice placeholder methods
    if "def toggle_mute" not in content:
        content += """
    def toggle_mute(self):
        print("Mute toggled")

    def toggle_deafen(self):
        print("Deafen toggled")
"""
        
    with open('client/client.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
modify_client()
