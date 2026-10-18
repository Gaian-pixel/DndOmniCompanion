# client/manuals_ui.py
"""
Interfaccia di Consultazione e Interpellazione dei Manuali di Gioco D&D 5e (Dark Fantasy).
Consente a DM e Giocatori di:
- Consultare tutti i manuali ufficiali 5e (PHB, DMG, MM, XGtE/TCoE) e manuali personalizzati
- Cercare argomenti e regole con filtro istantaneo
- Visualizzare spiegazioni complete, formule e tabelle
- Condividere estratti di regole direttamente nella chat della sessione
- Importare nuovi manuali (.md, .json, .txt) nella cartella manuals/
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import shutil
import os
import threading

from common.theme import (
    apply_modern_window_style, BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT,
    BORDER_COLOR, ACCENT_GOLD,
    TEXT_COLOR, TEXT_MUTED, FONT_TITLE, FONT_SMALL
)
from common.manuals_manager import ManualsManager, MANUALS_DIR
from common.i18n import _t
from common.messagebox import messagebox


class ManualsDialog(tk.Toplevel):
    def __init__(self, master, share_callback=None, initial_query=""):
        super().__init__(master)
        self.transient(master)
        self.title(f"📖 {_t('manuals_title')}")
        self.minsize(860, 640)
        apply_modern_window_style(self)
        
        self.share_callback = share_callback
        self.manager = ManualsManager()
        self.current_rule = None
        self.selected_manual = tk.StringVar(value="Tutti")
        self.selected_category = tk.StringVar(value="Tutte")
        self.search_var = tk.StringVar(value=initial_query)

        self.setup_ui()
        self.refresh_list()
        
        if initial_query:
            results = self.manager.search(initial_query)
            if results:
                self.show_rule_details(results[0])

    def setup_ui(self):
        # Header banner
        header = tk.Frame(self, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        header.pack(fill=tk.X, padx=12, pady=(10, 6))

        tk.Label(header, text="📖 CONSULTA I MANUALI DI GIOCO", font=FONT_TITLE, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=12, pady=(8, 2))
        
        total_rules = len(self.manager.rules)
        tk.Label(header, text=f"Knowledge Base 5e Integrata: {total_rules} voci (PHB 2024, DMG 2024, MM 2025, XGtE, TCoE, Custom) ricercabili offline in tempo reale.",
                 font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", padx=12, pady=(0, 8))

        # Main horizontal container
        main_split = tk.Frame(self, bg=BG_COLOR)
        main_split.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        # -------------------------------------------------------------
        # PANNELLO SINISTRO (Ricerca e Selezione Manuali)
        # -------------------------------------------------------------
        left_panel = tk.Frame(main_split, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, width=330)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 6))
        left_panel.pack_propagate(False)

        # Filtri Manuale & Categoria
        filters_f = tk.Frame(left_panel, bg=SURFACE_COLOR)
        filters_f.pack(fill=tk.X, padx=10, pady=(8, 4))

        tk.Label(filters_f, text="Manuale:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w")
        manual_names = [f"{code} - {name}" if code != "Tutti" else "Tutti i Manuali" for code, name in self.manager.get_available_manuals()]
        self.manual_cb = ttk.Combobox(filters_f, state="readonly", values=manual_names)
        self.manual_cb.current(0)
        self.manual_cb.pack(fill=tk.X, pady=(2, 6))
        self.manual_cb.bind("<<ComboboxSelected>>", self.on_manual_changed)

        tk.Label(filters_f, text="Categoria:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w")
        self.cat_cb = ttk.Combobox(filters_f, textvariable=self.selected_category, state="readonly", values=["Tutte"])
        self.cat_cb.current(0)
        self.cat_cb.pack(fill=tk.X, pady=(2, 6))
        self.cat_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_list())

        # Campo di Ricerca con icona
        tk.Label(filters_f, text="Cerca per termine o CD (es. Fireball, Scatto):", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w")
        search_entry = ttk.Entry(filters_f, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, pady=(2, 8))
        search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())

        # Treeview / Lista Argomenti
        list_container = tk.Frame(left_panel, bg=SURFACE_COLOR)
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        self.tree = ttk.Treeview(list_container, columns=("Titolo", "Manuale"), show="headings", selectmode="browse")
        self.tree.heading("Titolo", text="Regola / Argomento")
        self.tree.heading("Manuale", text="Manuale")
        self.tree.column("Titolo", width=215)
        self.tree.column("Manuale", width=70, anchor="center")
        
        sb_left = ttk.Scrollbar(list_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb_left.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_left.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_selected)

        # Pulsanti gestione manuali custom e PDF in basso a sinistra
        b_left_top = tk.Frame(left_panel, bg=SURFACE_COLOR)
        b_left_top.pack(fill=tk.X, padx=10, pady=(4, 2))
        ttk.Button(b_left_top, text="➕ Importa Regola...", command=self.import_custom_file, style="Info.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ttk.Button(b_left_top, text="📁 Cartella PDF", command=self.open_pdf_folder, style="Secondary.TButton").pack(side=tk.LEFT, padx=1)

        b_left_bot = tk.Frame(left_panel, bg=SURFACE_COLOR)
        b_left_bot.pack(fill=tk.X, padx=10, pady=(2, 8))
        ttk.Button(b_left_bot, text="🔄 Reindicizza Manuali PDF", command=self.trigger_reindex, style="Secondary.TButton").pack(fill=tk.X)

        # -------------------------------------------------------------
        # PANNELLO DESTRO (Lettura Regola e Azioni)
        # -------------------------------------------------------------
        right_panel = tk.Frame(main_split, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Intestazione Dettaglio
        self.detail_header = tk.Frame(right_panel, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.detail_header.pack(fill=tk.X, padx=12, pady=(12, 6))

        top_meta = tk.Frame(self.detail_header, bg=SURFACE_COLOR_ALT)
        top_meta.pack(fill=tk.X, padx=10, pady=(6, 2))

        self.lbl_badge = tk.Label(top_meta, text="📕 D&D 5e", font=FONT_SMALL, bg="#2C2E33", fg=ACCENT_GOLD, padx=6, pady=2)
        self.lbl_badge.pack(side=tk.LEFT)

        self.lbl_category = tk.Label(top_meta, text="Categoria: Generale", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED)
        self.lbl_category.pack(side=tk.LEFT, padx=10)

        self.lbl_title = tk.Label(self.detail_header, text="Seleziona una regola dall'elenco a sinistra", font=FONT_TITLE, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD, wraplength=480, justify="left")
        self.lbl_title.pack(anchor="w", padx=10, pady=(2, 4))

        # Box Sommario Rapido
        self.summary_frame = tk.Frame(right_panel, bg="#212529", highlightbackground="#343A40", highlightthickness=1)
        self.summary_frame.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(self.summary_frame, text="💡 SINTESI REGOLA:", font=("Segoe UI", 9, "bold"), bg="#212529", fg=ACCENT_GOLD).pack(anchor="w", padx=8, pady=(4, 1))
        self.lbl_summary = tk.Label(self.summary_frame, text="Scegli un argomento per visualizzare il sunto rapido o cerca con parole chiave.", font=FONT_SMALL, bg="#212529", fg=TEXT_COLOR, wraplength=480, justify="left")
        self.lbl_summary.pack(anchor="w", padx=8, pady=(0, 6))

        # Testo Completo con supporto Markdown
        self.txt_content = scrolledtext.ScrolledText(right_panel, wrap=tk.WORD, bg=BG_COLOR, fg=TEXT_COLOR,
                                                     font=("Segoe UI", 10), insertbackground="white", highlightthickness=0, bd=0)
        self.txt_content.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
        
        # Stili Markdown per ScrolledText
        self.txt_content.tag_configure("h1", font=("Segoe UI", 14, "bold"), foreground=ACCENT_GOLD, spacing1=8, spacing3=4)
        self.txt_content.tag_configure("h2", font=("Segoe UI", 12, "bold"), foreground=ACCENT_GOLD, spacing1=6, spacing3=3)
        self.txt_content.tag_configure("h3", font=("Segoe UI", 11, "bold"), foreground="#F1C40F", spacing1=5, spacing3=2)
        self.txt_content.tag_configure("h4", font=("Segoe UI", 10, "bold"), foreground="#5DADE2", spacing1=5, spacing3=2)
        self.txt_content.tag_configure("bold", font=("Segoe UI", 10, "bold"), foreground="#FFFFFF")
        self.txt_content.tag_configure("italic", font=("Segoe UI", 10, "italic"), foreground="#D0D0D0")
        self.txt_content.tag_configure("bullet_symbol", font=("Segoe UI", 10, "bold"), foreground=ACCENT_GOLD, lmargin1=16, lmargin2=28)
        self.txt_content.tag_configure("bullet_line", font=("Segoe UI", 10), foreground=TEXT_COLOR, lmargin1=16, lmargin2=28, spacing1=2, spacing3=2)
        self.txt_content.tag_configure("normal", font=("Segoe UI", 10), foreground=TEXT_COLOR, spacing1=2, spacing3=2)
        self.txt_content.tag_configure("quote", font=("Segoe UI", 9, "italic"), foreground=TEXT_MUTED, lmargin1=20, lmargin2=20)
        self.txt_content.config(state="disabled")

        # Barra Azioni Inferiore
        btn_bar = tk.Frame(right_panel, bg=SURFACE_COLOR)
        btn_bar.pack(fill=tk.X, padx=12, pady=10)

        self.btn_share = ttk.Button(btn_bar, text="💬 Condividi in Chat", command=self.share_to_chat, style="Primary.TButton")
        self.btn_share.pack(side=tk.LEFT, padx=3)

        ttk.Button(btn_bar, text="📋 Copia Testo", command=self.copy_rule_text).pack(side=tk.LEFT, padx=3)
        self.btn_pdf = ttk.Button(btn_bar, text="📄 Fonte PDF", command=self.open_pdf_source, style="Secondary.TButton")
        self.btn_pdf.pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar, text="🌐 Cerca Online SRD", command=self.search_online_srd, style="Info.TButton").pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar, text="Chiudi", command=self.destroy).pack(side=tk.RIGHT, padx=3)

    def on_manual_changed(self, event=None):
        raw = self.manual_cb.get()
        manual_code = raw.split(" - ")[0].strip() if " - " in raw else "Tutti"
        self.selected_manual.set(manual_code)
        
        # Aggiorna categorie per quel manuale
        cats = ["Tutte"] + self.manager.get_manual_categories(manual_code if manual_code != "Tutti" else None)
        self.cat_cb["values"] = cats
        self.selected_category.set("Tutte")
        self.refresh_list()

    def refresh_list(self):
        query = self.search_var.get().strip()
        man = self.selected_manual.get()
        cat = self.selected_category.get()
        
        results = self.manager.search(query, manual_filter=man, category_filter=cat)
        
        # Pulisci Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.tree_rules_map = {}
        for r in results:
            item_id = self.tree.insert("", tk.END, values=(r.get("title", ""), r.get("manual", "")))
            self.tree_rules_map[item_id] = r

        # Seleziona primo elemento se presente
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.show_rule_details(self.tree_rules_map[children[0]])

    def on_tree_selected(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        item_id = sel[0]
        rule = self.tree_rules_map.get(item_id)
        if rule:
            self.show_rule_details(rule)

    def show_rule_details(self, rule: dict):
        self.current_rule = rule
        man = rule.get("manual", "PHB")
        page = rule.get("page_ref", "Manuale 5e")
        cat = rule.get("category", "Regole")
        title = rule.get("title", "Senza Titolo")
        summary = rule.get("summary", "")
        content = rule.get("content", "")

        icon_map = {"PHB": "📕", "DMG": "📘", "MM": "📗", "XGtE": "📙", "TCoE": "📙", "Custom": "📝", "SRD": "🌐"}
        badge_text = f"{icon_map.get(man, '📖')} {man} • {page}"
        
        self.lbl_badge.config(text=badge_text)
        self.lbl_category.config(text=f"Categoria: {cat}")
        self.lbl_title.config(text=title)
        self.lbl_summary.config(text=summary or "Nessun sommario rapido disponibile.")

        # Popola text area con formattazione Markdown ricca
        self.render_markdown_to_text(self.txt_content, content)

    def render_markdown_to_text(self, text_widget, markdown_text: str):
        """Renderizza Markdown strutturato con tag visivi ricchi in un widget Text/ScrolledText."""
        text_widget.config(state="normal")
        text_widget.delete("1.0", tk.END)
        
        if not markdown_text:
            text_widget.config(state="disabled")
            return

        lines = markdown_text.splitlines()
        for line in lines:
            stripped = line.strip()
            if not stripped:
                text_widget.insert(tk.END, "\n", ("normal",))
                continue
                
            if stripped.startswith("#### "):
                h_text = stripped[5:]
                text_widget.insert(tk.END, h_text + "\n", ("h4",))
            elif stripped.startswith("### "):
                h_text = stripped[4:]
                text_widget.insert(tk.END, h_text + "\n", ("h3",))
            elif stripped.startswith("## "):
                h_text = stripped[3:]
                text_widget.insert(tk.END, h_text + "\n", ("h2",))
            elif stripped.startswith("# "):
                h_text = stripped[2:]
                text_widget.insert(tk.END, h_text + "\n", ("h1",))
            elif stripped.startswith("> "):
                q_text = stripped[2:]
                text_widget.insert(tk.END, q_text + "\n", ("quote",))
            elif stripped.startswith("• "):
                bullet_body = stripped[2:]
                text_widget.insert(tk.END, "  • ", ("bullet_symbol",))
                self._insert_inline_formatted(text_widget, bullet_body, base_tags=("bullet_line",))
                text_widget.insert(tk.END, "\n", ("bullet_line",))
            else:
                self._insert_inline_formatted(text_widget, line, base_tags=("normal",))
                text_widget.insert(tk.END, "\n", ("normal",))
                
        text_widget.config(state="disabled")

    def _insert_inline_formatted(self, text_widget, text: str, base_tags=("normal",)):
        """Parsa e inserisce porzioni in **grassetto** o *corsivo* mantenendo i tag base."""
        import re
        tokens = re.split(r'(\*\*.*?\*\*|\*.*?\*)', text)
        for token in tokens:
            if not token:
                continue
            if token.startswith("**") and token.endswith("**") and len(token) >= 4:
                inner = token[2:-2]
                text_widget.insert(tk.END, inner, ("bold",) + base_tags)
            elif token.startswith("*") and token.endswith("*") and len(token) >= 2:
                inner = token[1:-1]
                text_widget.insert(tk.END, inner, ("italic",) + base_tags)
            else:
                text_widget.insert(tk.END, token, base_tags)

    def share_to_chat(self):
        if not self.current_rule:
            return
        title = self.current_rule.get("title", "")
        page = self.current_rule.get("page_ref", "5e")
        summary = self.current_rule.get("summary", "")
        
        share_text = f"📖 [MANUALE - {page}] {title}:\n{summary}"
        
        if self.share_callback:
            self.share_callback(share_text)
            self._notify_action("Regola condivisa nella chat della sessione!")
        else:
            # Fallback copia negli appunti
            self.clipboard_clear()
            self.clipboard_append(share_text)
            self._notify_action("Estratto copiato negli appunti (nessuna sessione chat attiva).")

    def copy_rule_text(self):
        if not self.current_rule:
            return
        title = self.current_rule.get("title", "")
        page = self.current_rule.get("page_ref", "5e")
        content = self.current_rule.get("content", "")
        
        full_text = f"=== {title} ({page}) ===\n\n{content}"
        self.clipboard_clear()
        self.clipboard_append(full_text)
        self._notify_action("Testo completo della regola copiato negli appunti!")

    def _notify_action(self, msg: str):
        try:
            from components.ui_components import show_toast
            show_toast(self, msg, title="📖 Manuale di Gioco", duration=2500, toast_type="info")
        except Exception:
            pass

    def import_custom_file(self):
        filetypes = [("Documenti Regole / Manuali", "*.md *.json *.txt"), ("Markdown", "*.md"), ("JSON", "*.json"), ("Testo", "*.txt")]
        selected = filedialog.askopenfilename(title="Seleziona Manuale o File Regole da Importare", filetypes=filetypes)
        if not selected:
            return
            
        try:
            dest = os.path.join(MANUALS_DIR, os.path.basename(selected))
            shutil.copyfile(selected, dest)
            self.manager = ManualsManager()
            self.on_manual_changed()
            self._notify_action(f"Manuale '{os.path.basename(selected)}' importato con successo!")
        except Exception as e:
            from common.messagebox import messagebox
            messagebox.showerror("Errore Importazione", f"Impossibile importare il file: {e}")

    def open_manuals_folder(self):
        os.makedirs(MANUALS_DIR, exist_ok=True)
        import subprocess
        try:
            if os.name == 'nt':
                os.startfile(MANUALS_DIR)
            else:
                subprocess.Popen(["xdg-open", MANUALS_DIR])
        except Exception:
            messagebox.showinfo("Cartella Manuali", f"I manuali custom si trovano in:\n{MANUALS_DIR}")

    def open_pdf_folder(self):
        from common.pdf_manuals_indexer import PDF_DIR
        os.makedirs(PDF_DIR, exist_ok=True)
        import subprocess
        try:
            if os.name == 'nt':
                os.startfile(PDF_DIR)
            else:
                subprocess.Popen(["xdg-open", PDF_DIR])
        except Exception:
            messagebox.showinfo("Cartella Manuali PDF", f"I manuali PDF si trovano in:\n{PDF_DIR}")

    def trigger_reindex(self):
        self._notify_action("Rianalisi ed indicizzazione manuali PDF avviata in background...")
        def _on_done(count):
            self.manager = ManualsManager()
            self.after(0, lambda: [
                self.on_manual_changed(),
                self._notify_action(f"Indicizzazione PDF completata! {count} voci pronte.")
            ])
        if hasattr(self.manager, 'pdf_indexer'):
            self.manager.pdf_indexer.reindex_async(on_done_callback=_on_done)

    def open_pdf_source(self):
        if not self.current_rule:
            return
        from common.pdf_manuals_indexer import PDF_DIR
        fname = self.current_rule.get("pdf_filename")
        page_num = self.current_rule.get("pdf_page", 1)
        page_ref = self.current_rule.get("page_ref", "Manuale")
        
        if not fname:
            from common.messagebox import messagebox
            messagebox.showinfo("Fonte Manuale", f"Questa voce fa parte delle regole integrate:\n{page_ref}")
            return
            
        full_pdf_path = os.path.join(PDF_DIR, fname)
        if os.path.exists(full_pdf_path):
            try:
                if os.name == 'nt':
                    os.startfile(full_pdf_path)
                self._notify_action(f"Aperto '{fname}' (Riferimento: {page_ref})")
            except Exception:
                from common.messagebox import messagebox
                messagebox.showinfo("Fonte PDF", f"File: {fname}\nRiferimento: {page_ref} (Pagina PDF: {page_num})")
        else:
            from common.messagebox import messagebox
            messagebox.showinfo("Fonte PDF", f"File: {fname}\nRiferimento: {page_ref} (Pagina PDF: {page_num})")

    def search_online_srd(self):
        from tkinter import simpledialog
        query = simpledialog.askstring("Cerca su 5e SRD Online", "Inserisci il nome della regola o incantesimo (in inglese):\n(es. 'cover', 'exhaustion', 'fireball', 'grappled')", parent=self)
        if not query:
            return
            
        def do_query():
            online_res = self.manager.query_online_srd_rule(query)
            if online_res:
                self.manager.rules.append(online_res)
                self.after(0, lambda: self.show_rule_details(online_res))
                self.after(0, lambda: self._notify_action(f"Regola '{online_res['title']}' trovata online su SRD!"))
            else:
                self.after(0, lambda: self._notify_action(f"Nessuna regola trovata online per '{query}'."))

        threading.Thread(target=do_query, daemon=True).start()


