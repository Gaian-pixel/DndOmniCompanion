# server/dm_generators.py
"""
Generatori di improvvisazione per il Dungeon Master (5e):
1. Generatore di Bottino (Loot 5e) basato su GS con divisione monete e assegnazione oggetti.
2. Generatore Rapido di PNG con tratti, segreti e generazione istantanea di token sulla mappa.
"""

import random
import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog
from typing import Dict, Any, List

from common.theme import (
    apply_modern_window_style, BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT,
    BORDER_COLOR, ACCENT_GOLD, ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE,
    TEXT_COLOR, TEXT_MUTED, TEXT_DARK,
    FONT_TITLE, FONT_HEADER, FONT_MAIN, FONT_BOLD, FONT_SMALL
)
from common.messagebox import messagebox
from common.game_state import Player
from common.protocol import make_player_joined, make_chat_broadcast, make_receive_item
from common.network_utils import broadcast, send_message


class LootGenerator:
    """Motore di generazione bottino basato sulle tabelle della DMG 5e."""
    
    GEMS_50 = ["Calcedonio (50 MO)", "Citrino (50 MO)", "Diarroite (50 MO)", "Occhio di Tigre (50 MO)", "Turchese (50 MO)", "Quarzo Rosa (50 MO)"]
    GEMS_100 = ["Ambra (100 MO)", "Ametista (100 MO)", "Crisoberillo (100 MO)", "Giada (100 MO)", "Perla (100 MO)", "Spinello (100 MO)"]
    GEMS_500 = ["Alessandrite (500 MO)", "Acquamarina (500 MO)", "Perla Nera (500 MO)", "Topazio (500 MO)"]
    
    MAGIC_COMMON = [
        {"name": "Pozione di Cura (2d4+2)", "type": "Consumabile", "weight": 0.5, "desc": "Ripristina 2d4 + 2 HP con un'azione."},
        {"name": "Pergamena: Dardo Incantato", "type": "Pergamena", "weight": 0.1, "desc": "Lancia Dardo Incantato di 1° livello."},
        {"name": "Pergamena: Armatura Magica", "type": "Pergamena", "weight": 0.1, "desc": "CA 13 + Mod Des per 8 ore."},
        {"name": "Olio di Scivolosità", "type": "Consumabile", "weight": 1.0, "desc": "Fornisce libertà di movimento per 8 ore."},
        {"name": "Corda dell'Arrampicata", "type": "Oggetto Magico", "weight": 3.0, "desc": "Corda animata di 18 metri."}
    ]
    
    MAGIC_UNCOMMON = [
        {"name": "Pozione di Guarigione Maggiore (4d4+4)", "type": "Consumabile", "weight": 0.5, "desc": "Ripristina 4d4 + 4 HP."},
        {"name": "Spada Corta +1", "type": "Arma", "weight": 2.0, "desc": "+1 al TxC e ai danni."},
        {"name": "Stocco +1", "type": "Arma", "weight": 2.0, "desc": "+1 al TxC e ai danni (Accurata)."},
        {"name": "Bacchetta dei Dardi Incantati", "type": "Bacchetta", "weight": 1.0, "desc": "7 cariche di Dardo Incantato."},
        {"name": "Stivali dell'Elfo", "type": "Meraviglioso", "weight": 1.0, "desc": "Vantaggio alle prove di Furtività per muoversi silenziosamente."},
        {"name": "Borsa Conservante (Bag of Holding)", "type": "Meraviglioso", "weight": 15.0, "desc": "Contiene fino a 250 kg in uno spazio extradimensionale."}
    ]
    
    MAGIC_RARE = [
        {"name": "Pozione di Guarigione Superiore (8d4+8)", "type": "Consumabile", "weight": 0.5, "desc": "Ripristina 8d4 + 8 HP."},
        {"name": "Spada Fiammeggiante (+2d6 Fuoco)", "type": "Arma", "weight": 3.0, "desc": "Emana luce e infligge +2d6 danni da fuoco."},
        {"name": "Anello di Protezione (+1 CA, +1 TS)", "type": "Anello", "weight": 0.1, "desc": "+1 alla CA e a tutti i Tiri Salvezza."},
        {"name": "Mantello dello Spostamento", "type": "Meraviglioso", "weight": 1.0, "desc": "Gli attacchi contro di te subiscono svantaggio finché non subisci danni."}
    ]

    @classmethod
    def generate(cls, tier: str = "GS 0-4", loot_type: str = "Tesoro della Tana") -> Dict[str, Any]:
        result = {
            "coins": {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0},
            "gems": [],
            "items": [],
            "total_value_gp": 0
        }
        
        if tier == "GS 0-4":
            if loot_type == "Bottino Individuale":
                roll = random.randint(1, 100)
                if roll <= 30:
                    result["coins"]["MR"] = random.randint(4, 24) * 10
                elif roll <= 60:
                    result["coins"]["MA"] = random.randint(3, 18) * 10
                elif roll <= 95:
                    result["coins"]["MO"] = random.randint(2, 12) * 5
                else:
                    result["coins"]["MP"] = random.randint(1, 6)
            else: # Tana / Forziere
                result["coins"]["MR"] = random.randint(6, 36) * 100
                result["coins"]["MA"] = random.randint(3, 18) * 100
                result["coins"]["MO"] = random.randint(2, 16) * 10
                # Gemme
                gem_count = random.randint(2, 6)
                result["gems"] = [random.choice(cls.GEMS_50) for _ in range(gem_count)]
                # Oggetti magici
                item_count = random.randint(1, 2)
                result["items"] = [random.choice(cls.MAGIC_COMMON).copy() for _ in range(item_count)]

        elif tier == "GS 5-10":
            if loot_type == "Bottino Individuale":
                result["coins"]["MA"] = random.randint(4, 24) * 100
                result["coins"]["MO"] = random.randint(2, 16) * 10
                result["coins"]["MP"] = random.randint(1, 8) * 2
            else:
                result["coins"]["MA"] = random.randint(4, 24) * 200
                result["coins"]["MO"] = random.randint(6, 36) * 100
                result["coins"]["MP"] = random.randint(3, 18) * 10
                gem_count = random.randint(3, 8)
                result["gems"] = [random.choice(cls.GEMS_100) for _ in range(gem_count)]
                item_count = random.randint(1, 3)
                result["items"] = [random.choice(cls.MAGIC_UNCOMMON).copy() for _ in range(item_count)]

        else: # GS 11-16
            result["coins"]["MO"] = random.randint(10, 60) * 100
            result["coins"]["MP"] = random.randint(5, 30) * 100
            gem_count = random.randint(4, 10)
            result["gems"] = [random.choice(cls.GEMS_500) for _ in range(gem_count)]
            item_count = random.randint(2, 4)
            result["items"] = [random.choice(cls.MAGIC_RARE).copy() for _ in range(item_count)]
            
        # Calcolo valore approssimativo in MO
        c = result["coins"]
        tot_gp = (c["MR"] / 100) + (c["MA"] / 10) + (c["ME"] / 2) + c["MO"] + (c["MP"] * 10)
        tot_gp += len(result["gems"]) * (50 if tier == "GS 0-4" else (100 if tier == "GS 5-10" else 500))
        result["total_value_gp"] = int(tot_gp)
        
        return result


class LootGeneratorDialog(tk.Toplevel):
    """Interfaccia grafica moderna per generare e assegnare bottino D&D 5e."""
    def __init__(self, master, game_state):
        super().__init__(master)
        self.game_state = game_state
        self.title("D&D OmniCompanion • Generatore di Bottino 5e")
        self.minsize(680, 560)
        self.transient(master)
        self.grab_set()
        apply_modern_window_style(self)
        self.configure(bg=BG_COLOR)
        
        self.current_loot: Optional[Dict[str, Any]] = None
        self.setup_ui()
        self.generate_loot()

    def setup_ui(self):
        container = tk.Frame(self, bg=BG_COLOR, padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Header
        hdr = tk.Frame(container, bg=BG_COLOR)
        hdr.pack(fill=tk.X, pady=(0, 10))
        tk.Label(hdr, text="💰 Generatore di Tesoro & Bottino", font=("Georgia", 16, "bold"), bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
        tk.Label(hdr, text="Genera ricompense secondo le tabelle della Guida del Dungeon Master (DMG 5e)", font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w")
        
        # Controls Card
        ctrl_card = tk.Frame(container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        ctrl_card.pack(fill=tk.X, pady=(0, 10))
        
        row1 = tk.Frame(ctrl_card, bg=SURFACE_COLOR)
        row1.pack(fill=tk.X)
        
        tk.Label(row1, text="Grado Sfida (CR):", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT, padx=(0, 6))
        self.tier_var = tk.StringVar(value="GS 0-4")
        tier_combo = ttk.Combobox(row1, textvariable=self.tier_var, values=["GS 0-4", "GS 5-10", "GS 11-16"], state="readonly", width=10)
        tier_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(row1, text="Tipo Bottino:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT, padx=(0, 6))
        self.type_var = tk.StringVar(value="Tesoro della Tana")
        type_combo = ttk.Combobox(row1, textvariable=self.type_var, values=["Tesoro della Tana", "Bottino Individuale"], state="readonly", width=18)
        type_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Button(row1, text="🎲 Genera Nuovo Bottino", command=self.generate_loot, style="Gold.TButton").pack(side=tk.RIGHT)
        
        # Results Section
        res_frame = tk.Frame(container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=14, pady=12)
        res_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Coins summary banner
        self.lbl_coins = tk.Label(res_frame, text="Monete: --", font=("Georgia", 13, "bold"), bg=SURFACE_COLOR, fg=ACCENT_GOLD)
        self.lbl_coins.pack(anchor="w", pady=(0, 6))
        
        self.lbl_value = tk.Label(res_frame, text="Valore Totale Stimato: --", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
        self.lbl_value.pack(anchor="w", pady=(0, 10))
        
        # Items & Gems Treeview
        tree_box = tk.Frame(res_frame, bg=SURFACE_COLOR)
        tree_box.pack(fill=tk.BOTH, expand=True)
        
        cols = ("Tipo", "Nome", "Dettagli / Proprietà")
        self.tree_loot = ttk.Treeview(tree_box, columns=cols, show="headings", height=8)
        self.tree_loot.heading("Tipo", text="Tipo")
        self.tree_loot.heading("Nome", text="Nome / Descrizione")
        self.tree_loot.heading("Dettagli / Proprietà", text="Proprietà")
        
        self.tree_loot.column("Tipo", width=100, anchor="center")
        self.tree_loot.column("Nome", width=220)
        self.tree_loot.column("Dettagli / Proprietà", width=300)
        
        sb = ttk.Scrollbar(tree_box, orient=tk.VERTICAL, command=self.tree_loot.yview)
        self.tree_loot.configure(yscrollcommand=sb.set)
        self.tree_loot.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action Buttons Row
        actions_row = tk.Frame(container, bg=BG_COLOR)
        actions_row.pack(fill=tk.X)
        
        ttk.Button(actions_row, text="💰 Distribuisci Monete d'Oro al Party", command=self.split_loot_gold, style="Gold.TButton").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(actions_row, text="🎒 Assegna Oggetto Selezionato a Giocatore", command=self.grant_selected_item, style="Primary.TButton").pack(side=tk.LEFT)
        ttk.Button(actions_row, text="Chiudi", command=self.destroy).pack(side=tk.RIGHT)

    def generate_loot(self):
        self.current_loot = LootGenerator.generate(self.tier_var.get(), self.type_var.get())
        c = self.current_loot["coins"]
        parts = []
        if c["MP"] > 0: parts.append(f"{c['MP']} MP")
        if c["MO"] > 0: parts.append(f"{c['MO']} MO")
        if c["ME"] > 0: parts.append(f"{c['ME']} ME")
        if c["MA"] > 0: parts.append(f"{c['MA']} MA")
        if c["MR"] > 0: parts.append(f"{c['MR']} MR")
        coins_str = ", ".join(parts) if parts else "Nessuna moneta"
        
        self.lbl_coins.config(text=f"🪙 Monete: {coins_str}")
        self.lbl_value.config(text=f"Valore Totale Stimato: ~{self.current_loot['total_value_gp']} Monete d'Oro")
        
        for it in self.tree_loot.get_children():
            self.tree_loot.delete(it)
            
        for g in self.current_loot["gems"]:
            self.tree_loot.insert("", tk.END, values=("Gemma", g, "Prezioso da rivendita"))
            
        for item in self.current_loot["items"]:
            self.tree_loot.insert("", tk.END, values=(item.get("type", "Magico"), item.get("name", "Oggetto"), item.get("desc", "")))

    def split_loot_gold(self):
        if not self.current_loot: return
        mo = self.current_loot["coins"]["MO"]
        if mo <= 0:
            # Calcola conversione
            mo = self.current_loot["total_value_gp"]
            
        if mo <= 0:
            messagebox.showinfo("Nessun Oro", "Non ci sono monete d'oro in questo bottino.", parent=self)
            return
            
        party_players = [p for p in self.game_state.players if getattr(p, "is_party_member", False) or getattr(p, "conn", None)]
        if not party_players:
            messagebox.showwarning("Nessun Giocatore", "Non ci sono giocatori nel party a cui distribuire l'oro.", parent=self)
            return
            
        share = mo // len(party_players)
        for p in party_players:
            if not p.full_sheet: p.full_sheet = {}
            if "currency" not in p.full_sheet or not isinstance(p.full_sheet["currency"], dict):
                p.full_sheet["currency"] = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
            p.full_sheet["currency"]["MO"] = p.full_sheet["currency"].get("MO", 0) + share
            if getattr(p, "conn", None):
                send_message(p.conn, {"type": "RECEIVE_GOLD", "data": {"amount": share}})
                
        broadcast(self.game_state, make_chat_broadcast("Sistema", f"💰 Il DM ha distribuito il bottino: {mo} MO ({share} a testa per {len(party_players)} avventurieri)!"))
        messagebox.showinfo("Oro Distribuito", f"{mo} MO distribuiti con successo ({share} MO a testa).", parent=self)

    def grant_selected_item(self):
        sel = self.tree_loot.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un oggetto o gemma dalla lista.", parent=self)
            return
            
        vals = self.tree_loot.item(sel[0])["values"]
        item_type = vals[0]
        item_name = vals[1]
        item_desc = vals[2]
        
        online_players = [p.name for p in self.game_state.players if getattr(p, "conn", None)]
        if not online_players:
            messagebox.showwarning("Nessun Connesso", "Nessun giocatore online a cui assegnare l'oggetto.", parent=self)
            return
            
        target = simpledialog.askstring("Assegna Oggetto", f"A chi vuoi assegnare '{item_name}'?\nGiocatori disponibili: " + ", ".join(online_players), parent=self)
        if not target or target not in online_players: return
        
        target_p = self.game_state.find_player(target)
        if not target_p or not target_p.conn: return
        
        item_payload = {
            "name": item_name,
            "type": item_type,
            "desc": item_desc,
            "qty": 1,
            "weight": 0.5 if item_type in ["Gemma", "Consumabile"] else 2.0
        }
        send_message(target_p.conn, make_receive_item(item_payload))
        broadcast(self.game_state, make_chat_broadcast("Sistema", f"🎁 Il DM ha assegnato '{item_name}' a {target}!"))
        messagebox.showinfo("Assegnato", f"'{item_name}' inviato all'inventario di {target}.", parent=self)


class RandomNPCGenerator:
    """Generatore di PNG con personalità, segreti, allineamento e statistiche base 5e."""
    
    FIRST_NAMES_M = ["Gareth", "Boran", "Theron", "Kaelen", "Brom", "Lucian", "Doran", "Varis", "Fritz", "Orin", "Alvar"]
    FIRST_NAMES_F = ["Lyra", "Elora", "Seraphina", "Morwen", "Brenna", "Isolde", "Vespera", "Kaelia", "Dara", "Rowan"]
    SURNAMES = ["Roccarupe", "Lumacorno", "Ombralesta", "Cuordileone", "Nottetempo", "Fiumargenteo", "Barbaferro", "Ventofreddo", "Lamafina"]
    
    RACES = ["Umano", "Elfo dei Boschi", "Alto Elfo", "Nano delle Colline", "Nano delle Montagne", "Halfling Piedelesto", "Tiefling", "Mezzorco", "Gnomo"]
    ROLES = [
        "Locandiere gioviale", "Fabbro muscoloso", "Cacciatore di taglie", "Guardia cittadina corrotta", 
        "Erborista eccentrica", "Sacerdote devoto", "Marinaio scampato a un naufragio", "Studioso arcano",
        "Mendicante astuto (informatore)", "Mercante di spezie esotiche", "Nobile decaduto"
    ]
    ALIGNMENTS = ["Legale Buono", "Neutrale Buono", "Caotico Buono", "Legale Neutrale", "Neutrale Puro", "Caotico Neutrale", "Neutrale Malvagio"]
    
    TRAITS = [
        "Parla sempre a bassa voce come se svelasse un mistero.",
        "Gesticola vistosamente e ride alle proprie battute.",
        "Sospetta costantemente di essere seguito o spiato.",
        "Tiene maniacalmente puliti i propri stivali e abiti.",
        "Ha una cicatrice evidente sul volto che tocca quando mente.",
        "Cita proverbi popolari assurdi o incomprensibili.",
        "Molto protettivo verso i membri della propria famiglia.",
        "Non guarda mai negli occhi le persone con cui parla."
    ]
    
    SECRETS = [
        "Ha contratto un pesante debito con la gilda dei ladri locale.",
        "Nasconde una mappa antica che indica una catacomba sigillata.",
        "È fuggito da una città vicina sotto falsa identità.",
        "Conosce la debolezza del tiranno/mostro che minaccia la regione.",
        "È segretamente devoto a un'entità ultraterrena dimenticata.",
        "Custodisce una chiave ornata di cui ignora la serratura."
    ]

    @classmethod
    def generate(cls) -> Dict[str, Any]:
        gender = random.choice(["M", "F"])
        name = f"{random.choice(cls.FIRST_NAMES_M if gender == 'M' else cls.FIRST_NAMES_F)} {random.choice(cls.SURNAMES)}"
        race = random.choice(cls.RACES)
        role = random.choice(cls.ROLES)
        align = random.choice(cls.ALIGNMENTS)
        trait = random.choice(cls.TRAITS)
        secret = random.choice(cls.SECRETS)
        
        hp = random.randint(12, 35)
        ac = random.choice([10, 11, 12, 13, 14, 15])
        
        return {
            "name": name,
            "race": race,
            "role": role,
            "alignment": align,
            "hp": hp,
            "ac": ac,
            "faction": "Neutrale",
            "trait": trait,
            "secret": secret,
            "notes": f"Tratto: {trait}\nSegreto: {secret}\nAllineamento: {align}"
        }


class RandomNPCDialog(tk.Toplevel):
    """Finestra di generazione immediata di PNG per il DM."""
    def __init__(self, master, game_state):
        super().__init__(master)
        self.game_state = game_state
        self.title("D&D OmniCompanion • Generatore Rapido PNG")
        self.minsize(580, 520)
        self.transient(master)
        self.grab_set()
        apply_modern_window_style(self)
        self.configure(bg=BG_COLOR)
        
        self.npc_data: Optional[Dict[str, Any]] = None
        self.setup_ui()
        self.generate_npc()

    def setup_ui(self):
        container = tk.Frame(self, bg=BG_COLOR, padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Header
        hdr = tk.Frame(container, bg=BG_COLOR)
        hdr.pack(fill=tk.X, pady=(0, 10))
        tk.Label(hdr, text="🎭 Generatore Rapido di PNG", font=("Georgia", 16, "bold"), bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
        tk.Label(hdr, text="Crea al volo personaggi non giocanti con personalità, segreti e statistiche", font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w")
        
        # Details Card
        card = tk.Frame(container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=14, pady=12)
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Nome e Ruolo
        r1 = tk.Frame(card, bg=SURFACE_COLOR)
        r1.pack(fill=tk.X, pady=(0, 6))
        tk.Label(r1, text="Nome:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        self.ent_name = ttk.Entry(r1, font=FONT_HEADER)
        self.ent_name.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 12))
        
        tk.Label(r1, text="HP:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.sp_hp = ttk.Spinbox(r1, from_=1, to=200, width=5)
        self.sp_hp.pack(side=tk.LEFT, padx=(4, 10))
        
        tk.Label(r1, text="CA:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.sp_ac = ttk.Spinbox(r1, from_=8, to=25, width=4)
        self.sp_ac.pack(side=tk.LEFT, padx=(4, 0))
        
        # Razza, Ruolo, Fazione
        r2 = tk.Frame(card, bg=SURFACE_COLOR)
        r2.pack(fill=tk.X, pady=(0, 8))
        tk.Label(r2, text="Razza & Ruolo:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT)
        self.lbl_race_role = tk.Label(r2, text="--", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR)
        self.lbl_race_role.pack(side=tk.LEFT, padx=6)
        
        tk.Label(r2, text="Allineamento:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(10, 0))
        self.lbl_align = tk.Label(r2, text="--", font=FONT_BOLD, bg=SURFACE_COLOR, fg="#5C7CFA")
        self.lbl_align.pack(side=tk.LEFT, padx=6)
        
        # Note, Tratto e Segreto
        tk.Label(card, text="Personalità, Tratti e Segreti del PNG:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(4, 2))
        self.txt_notes = scrolledtext.ScrolledText(card, height=8, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_MAIN,
                                                  relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, wrap=tk.WORD)
        self.txt_notes.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        
        # Action Buttons
        b_row = tk.Frame(container, bg=BG_COLOR)
        b_row.pack(fill=tk.X)
        
        ttk.Button(b_row, text="🔄 Genera Altro PNG", command=self.generate_npc).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(b_row, text="⚡ Spawna Token sulla Mappa", command=self.spawn_token, style="Gold.TButton").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(b_row, text="💾 Salva nella Campagna", command=self.save_to_campaign, style="Primary.TButton").pack(side=tk.LEFT)
        ttk.Button(b_row, text="Chiudi", command=self.destroy).pack(side=tk.RIGHT)

    def generate_npc(self):
        self.npc_data = RandomNPCGenerator.generate()
        self.ent_name.delete(0, tk.END)
        self.ent_name.insert(0, self.npc_data["name"])
        self.sp_hp.set(self.npc_data["hp"])
        self.sp_ac.set(self.npc_data["ac"])
        self.lbl_race_role.config(text=f"{self.npc_data['race']} • {self.npc_data['role']}")
        self.lbl_align.config(text=self.npc_data["alignment"])
        
        self.txt_notes.delete("1.0", tk.END)
        desc = (
            f"• Ruolo: {self.npc_data['role']}\n"
            f"• Allineamento: {self.npc_data['alignment']}\n\n"
            f"• Tratto Distintivo:\n  {self.npc_data['trait']}\n\n"
            f"• Segreto / Motivazione:\n  {self.npc_data['secret']}"
        )
        self.txt_notes.insert("1.0", desc)

    def spawn_token(self):
        if not self.npc_data: return
        name = self.ent_name.get().strip() or self.npc_data["name"]
        
        # Evita duplicati
        base_name = name
        c = 1
        while self.game_state.find_player(name):
            c += 1
            name = f"{base_name} ({c})"
            
        p = Player(name=name)
        try:
            p.hp = int(self.sp_hp.get())
            p.max_hp = p.hp
        except ValueError:
            p.hp = 20
            p.max_hp = 20
            
        p.is_party_member = False
        p.full_sheet = {
            "name": p.name,
            "char_class": self.npc_data.get("role", "PNG"),
            "level": 1,
            "hp_current": p.hp,
            "hp_max": p.max_hp
        }
        self.game_state.add_player(p)
        broadcast(self.game_state, make_player_joined(p.to_dict()))
        self.game_state._trigger_gui_update()
        broadcast(self.game_state, make_chat_broadcast("DM", f"🎭 PNG '{name}' ({self.npc_data.get('role')}) schierato sulla mappa."))
        messagebox.showinfo("PNG Schierato", f"Token per '{name}' creato con successo sulla mappa!", parent=self)

    def save_to_campaign(self):
        active_c = getattr(self.game_state, "active_campaign", None)
        if not active_c:
            messagebox.showinfo("Nessuna Campagna", "Nessuna campagna attiva caricata. Carica o crea una campagna dal menu File.", parent=self)
            return
            
        name = self.ent_name.get().strip() or self.npc_data["name"]
        active_c.add_npc(
            name=name,
            role=self.npc_data.get("role", "PNG"),
            hp=int(self.sp_hp.get()),
            ac=int(self.sp_ac.get()),
            notes=self.txt_notes.get("1.0", tk.END).strip(),
            faction="Neutrale"
        )
        active_c.save()
        messagebox.showinfo("Salvato", f"PNG '{name}' salvato nella campagna '{active_c.name}'!", parent=self)

