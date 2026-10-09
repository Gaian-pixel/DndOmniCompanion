import re

def modify_server():
    with open('server/dm_gui.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 4. Chat formatting (discord style) - using Regex to match the multiline create_chat_tab
    pattern_create = re.compile(
        r"    def create_chat_tab\(self, name\):\s*if name in self\.chat_tabs: return\s*tab_frame = ttk\.Frame\(self\.notebook\)\s*text_widget = scrolledtext\.ScrolledText\(tab_frame, state='disabled', wrap=tk\.WORD, bg=SURFACE_COLOR, \s*fg=TEXT_COLOR, borderwidth=0, highlightthickness=0\)\s*text_widget\.pack\(fill=tk\.BOTH, expand=True\)\s*self\.notebook\.add\(tab_frame, text=name\)\s*self\.chat_tabs\[name\] = text_widget"
    )
    
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
        
    content = pattern_create.sub(new_create, content)
    
    with open('server/dm_gui.py', 'w', encoding='utf-8') as f:
        f.write(content)

modify_server()
