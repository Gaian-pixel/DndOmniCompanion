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
from common.i18n import _t, get_language


class LootGenerator:
    """Motore di generazione bottino basato sulle tabelle della DMG 5e (Italiano & English)."""
    
    GEMS_50_IT = ["Calcedonio (50 MO)", "Citrino (50 MO)", "Diarroite (50 MO)", "Occhio di Tigre (50 MO)", "Turchese (50 MO)", "Quarzo Rosa (50 MO)"]
    GEMS_50_EN = ["Chalcedony (50 GP)", "Citrine (50 GP)", "Jasper (50 GP)", "Tiger Eye (50 GP)", "Turquoise (50 GP)", "Rose Quartz (50 GP)"]
    GEMS_50 = GEMS_50_IT

    GEMS_100_IT = ["Ambra (100 MO)", "Ametista (100 MO)", "Crisoberillo (100 MO)", "Giada (100 MO)", "Perla (100 MO)", "Spinello (100 MO)"]
    GEMS_100_EN = ["Amber (100 GP)", "Amethyst (100 GP)", "Chrysoberyl (100 GP)", "Jade (100 GP)", "Pearl (100 GP)", "Spinel (100 GP)"]
    GEMS_100 = GEMS_100_IT

    GEMS_500_IT = ["Alessandrite (500 MO)", "Acquamarina (500 MO)", "Perla Nera (500 MO)", "Topazio (500 MO)"]
    GEMS_500_EN = ["Alexandrite (500 GP)", "Aquamarine (500 GP)", "Black Pearl (500 GP)", "Topaz (500 GP)"]
    GEMS_500 = GEMS_500_IT
    
    MAGIC_COMMON_IT = [
        {"name": "Pozione di Cura (2d4+2)", "type": "Consumabile", "weight": 0.5, "desc": "Ripristina 2d4 + 2 HP con un'azione."},
        {"name": "Pergamena: Dardo Incantato", "type": "Pergamena", "weight": 0.1, "desc": "Lancia Dardo Incantato di 1° livello."},
        {"name": "Pergamena: Armatura Magica", "type": "Pergamena", "weight": 0.1, "desc": "CA 13 + Mod Des per 8 ore."},
        {"name": "Olio di Scivolosità", "type": "Consumabile", "weight": 1.0, "desc": "Fornisce libertà di movimento per 8 ore."},
        {"name": "Corda dell'Arrampicata", "type": "Oggetto Magico", "weight": 3.0, "desc": "Corda animata di 18 metri."}
    ]
    MAGIC_COMMON_EN = [
        {"name": "Potion of Healing (2d4+2)", "type": "Consumable", "weight": 0.5, "desc": "Regain 2d4 + 2 HP as an action."},
        {"name": "Scroll: Magic Missile", "type": "Scroll", "weight": 0.1, "desc": "Cast 1st-level Magic Missile."},
        {"name": "Scroll: Mage Armor", "type": "Scroll", "weight": 0.1, "desc": "AC 13 + DEX Mod for 8 hours."},
        {"name": "Oil of Slipperiness", "type": "Consumable", "weight": 1.0, "desc": "Provides freedom of movement for 8 hours."},
        {"name": "Rope of Climbing", "type": "Wondrous Item", "weight": 3.0, "desc": "60-foot enchanted climbing rope."}
    ]
    MAGIC_COMMON = MAGIC_COMMON_IT
    
    MAGIC_UNCOMMON_IT = [
        {"name": "Pozione di Guarigione Maggiore (4d4+4)", "type": "Consumabile", "weight": 0.5, "desc": "Ripristina 4d4 + 4 HP."},
        {"name": "Spada Corta +1", "type": "Arma", "weight": 2.0, "desc": "+1 al TxC e ai danni."},
        {"name": "Stocco +1", "type": "Arma", "weight": 2.0, "desc": "+1 al TxC e ai danni (Accurata)."},
        {"name": "Bacchetta dei Dardi Incantati", "type": "Bacchetta", "weight": 1.0, "desc": "7 cariche di Dardo Incantato."},
        {"name": "Stivali dell'Elfo", "type": "Meraviglioso", "weight": 1.0, "desc": "Vantaggio alle prove di Furtività per muoversi silenziosamente."},
        {"name": "Borsa Conservante (Bag of Holding)", "type": "Meraviglioso", "weight": 15.0, "desc": "Contiene fino a 250 kg in uno spazio extradimensionale."}
    ]
    MAGIC_UNCOMMON_EN = [
        {"name": "Potion of Greater Healing (4d4+4)", "type": "Consumable", "weight": 0.5, "desc": "Regain 4d4 + 4 HP as an action."},
        {"name": "Shortsword +1", "type": "Weapon", "weight": 2.0, "desc": "+1 bonus to attack and damage rolls."},
        {"name": "Rapier +1", "type": "Weapon", "weight": 2.0, "desc": "+1 bonus to attack and damage rolls (Finesse)."},
        {"name": "Wand of Magic Missiles", "type": "Wand", "weight": 1.0, "desc": "7 charges of Magic Missile."},
        {"name": "Boots of Elvenkind", "type": "Wondrous Item", "weight": 1.0, "desc": "Advantage on Stealth checks to move silently."},
        {"name": "Bag of Holding", "type": "Wondrous Item", "weight": 15.0, "desc": "Holds up to 500 lbs in an extradimensional pocket."}
    ]
    MAGIC_UNCOMMON = MAGIC_UNCOMMON_IT
    
    MAGIC_RARE_IT = [
        {"name": "Pozione di Guarigione Superiore (8d4+8)", "type": "Consumabile", "weight": 0.5, "desc": "Ripristina 8d4 + 8 HP."},
        {"name": "Spada Fiammeggiante (+2d6 Fuoco)", "type": "Arma", "weight": 3.0, "desc": "Emana luce e infligge +2d6 danni da fuoco."},
        {"name": "Anello di Protezione (+1 CA, +1 TS)", "type": "Anello", "weight": 0.1, "desc": "+1 alla CA e a tutti i Tiri Salvezza."},
        {"name": "Mantello dello Spostamento", "type": "Meraviglioso", "weight": 1.0, "desc": "Gli attacchi contro di te subiscono svantaggio finché non subisci danni."}
    ]
    MAGIC_RARE_EN = [
        {"name": "Potion of Superior Healing (8d4+8)", "type": "Consumable", "weight": 0.5, "desc": "Regain 8d4 + 8 HP as an action."},
        {"name": "Flame Tongue Sword (+2d6 Fire)", "type": "Weapon", "weight": 3.0, "desc": "Sheds light and deals +2d6 fire damage on hit."},
        {"name": "Ring of Protection (+1 AC, +1 Saves)", "type": "Ring", "weight": 0.1, "desc": "+1 bonus to AC and all Saving Throws."},
        {"name": "Cloak of Displacement", "type": "Wondrous Item", "weight": 1.0, "desc": "Attackers have disadvantage on attack rolls against you."}
    ]
    MAGIC_RARE = MAGIC_RARE_IT

    @classmethod
    def generate(cls, tier: str = "GS 0-4", loot_type: str = "Tesoro della Tana") -> Dict[str, Any]:
        result = {
            "coins": {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0},
            "gems": [],
            "items": [],
            "total_value_gp": 0
        }
        
        lang = get_language()
        is_en = (lang == "en")
        pool_gems_50 = cls.GEMS_50_EN if is_en else cls.GEMS_50_IT
        pool_gems_100 = cls.GEMS_100_EN if is_en else cls.GEMS_100_IT
        pool_gems_500 = cls.GEMS_500_EN if is_en else cls.GEMS_500_IT
        pool_common = cls.MAGIC_COMMON_EN if is_en else cls.MAGIC_COMMON_IT
        pool_uncommon = cls.MAGIC_UNCOMMON_EN if is_en else cls.MAGIC_UNCOMMON_IT
        pool_rare = cls.MAGIC_RARE_EN if is_en else cls.MAGIC_RARE_IT

        is_individual = ("indiv" in str(loot_type).lower())
        
        if "0-4" in str(tier):
            if is_individual:
                roll = random.randint(1, 100)
                if roll <= 30:
                    result["coins"]["MR"] = random.randint(4, 24) * 10
                elif roll <= 60:
                    result["coins"]["MA"] = random.randint(3, 18) * 10
                elif roll <= 95:
                    result["coins"]["MO"] = random.randint(2, 12) * 5
                else:
                    result["coins"]["MP"] = random.randint(1, 6)
            else: # Tana / Hoard
                result["coins"]["MR"] = random.randint(6, 36) * 100
                result["coins"]["MA"] = random.randint(3, 18) * 100
                result["coins"]["MO"] = random.randint(2, 16) * 10
                gem_count = random.randint(2, 6)
                result["gems"] = [random.choice(pool_gems_50) for _ in range(gem_count)]
                item_count = random.randint(1, 2)
                result["items"] = [random.choice(pool_common).copy() for _ in range(item_count)]

        elif "5-10" in str(tier):
            if is_individual:
                result["coins"]["MA"] = random.randint(4, 24) * 100
                result["coins"]["MO"] = random.randint(2, 16) * 10
                result["coins"]["MP"] = random.randint(1, 8) * 2
            else:
                result["coins"]["MA"] = random.randint(4, 24) * 200
                result["coins"]["MO"] = random.randint(6, 36) * 100
                result["coins"]["MP"] = random.randint(3, 18) * 10
                gem_count = random.randint(3, 8)
                result["gems"] = [random.choice(pool_gems_100) for _ in range(gem_count)]
                item_count = random.randint(1, 3)
                result["items"] = [random.choice(pool_uncommon).copy() for _ in range(item_count)]

        else: # 11-16
            result["coins"]["MO"] = random.randint(10, 60) * 100
            result["coins"]["MP"] = random.randint(5, 30) * 100
            gem_count = random.randint(4, 10)
            result["gems"] = [random.choice(pool_gems_500) for _ in range(gem_count)]
            item_count = random.randint(2, 4)
            result["items"] = [random.choice(pool_rare).copy() for _ in range(item_count)]
            
        # Calcolo valore approssimativo in MO/GP
        c = result["coins"]
        tot_gp = (c["MR"] / 100) + (c["MA"] / 10) + (c["ME"] / 2) + c["MO"] + (c["MP"] * 10)
        tot_gp += len(result["gems"]) * (50 if "0-4" in str(tier) else (100 if "5-10" in str(tier) else 500))
        result["total_value_gp"] = int(tot_gp)
        
        return result


class LootGeneratorDialog(tk.Toplevel):
    """Interfaccia grafica moderna per generare e assegnare bottino D&D 5e (Bilingue IT/EN)."""
    def __init__(self, master, game_state):
        super().__init__(master)
        self.game_state = game_state
        self.title(_t("loot_gen_title", default="D&D OmniCompanion • Generatore di Bottino 5e"))
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
        tk.Label(hdr, text=_t("loot_gen_header", default="💰 Generatore di Tesoro & Bottino"), font=("Georgia", 16, "bold"), bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
        tk.Label(hdr, text=_t("loot_gen_subtitle", default="Genera ricompense secondo le tabelle della Guida del Dungeon Master (DMG 5e)"), font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w")
        
        # Controls Card
        ctrl_card = tk.Frame(container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        ctrl_card.pack(fill=tk.X, pady=(0, 10))
        
        row1 = tk.Frame(ctrl_card, bg=SURFACE_COLOR)
        row1.pack(fill=tk.X)
        
        tk.Label(row1, text=_t("loot_gen_cr", default="Grado Sfida (CR):"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT, padx=(0, 6))
        is_en = (get_language() == "en")
        tier_vals = ["CR 0-4", "CR 5-10", "CR 11-16"] if is_en else ["GS 0-4", "GS 5-10", "GS 11-16"]
        self.tier_var = tk.StringVar(value=tier_vals[0])
        tier_combo = ttk.Combobox(row1, textvariable=self.tier_var, values=tier_vals, state="readonly", width=10)
        tier_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(row1, text=_t("loot_gen_type", default="Tipo Bottino:"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT, padx=(0, 6))
        type_vals = [_t("loot_gen_hoard", default="Tesoro della Tana"), _t("loot_gen_individual", default="Bottino Individuale")]
        self.type_var = tk.StringVar(value=type_vals[0])
        type_combo = ttk.Combobox(row1, textvariable=self.type_var, values=type_vals, state="readonly", width=18)
        type_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Button(row1, text=_t("btn_generate_loot", default="🎲 Genera Nuovo Bottino"), command=self.generate_loot, style="Gold.TButton").pack(side=tk.RIGHT)
        
        # Results Section
        res_frame = tk.Frame(container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=14, pady=12)
        res_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Coins summary banner
        self.lbl_coins = tk.Label(res_frame, text=_t("loot_coins_summary", coins="--"), font=("Georgia", 13, "bold"), bg=SURFACE_COLOR, fg=ACCENT_GOLD)
        self.lbl_coins.pack(anchor="w", pady=(0, 6))
        
        self.lbl_value = tk.Label(res_frame, text=_t("loot_value_est", val="--"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
        self.lbl_value.pack(anchor="w", pady=(0, 10))
        
        # Items & Gems Treeview
        tree_box = tk.Frame(res_frame, bg=SURFACE_COLOR)
        tree_box.pack(fill=tk.BOTH, expand=True)
        
        cols = ("Tipo", "Nome", "Dettagli / Proprietà")
        self.tree_loot = ttk.Treeview(tree_box, columns=cols, show="headings", height=8)
        self.tree_loot.heading("Tipo", text=_t("col_type", default="Tipo"))
        self.tree_loot.heading("Nome", text=_t("col_name_desc", default="Nome / Descrizione"))
        self.tree_loot.heading("Dettagli / Proprietà", text=_t("col_properties", default="Proprietà"))
        
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
        
        ttk.Button(actions_row, text=_t("btn_distribute_gold_party", default="💰 Distribuisci Monete d'Oro al Party"), command=self.split_loot_gold, style="Gold.TButton").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(actions_row, text=_t("btn_grant_selected_item", default="🎒 Assegna Oggetto Selezionato a Giocatore"), command=self.grant_selected_item, style="Primary.TButton").pack(side=tk.LEFT)
        ttk.Button(actions_row, text=_t("btn_close", default="Chiudi"), command=self.destroy).pack(side=tk.RIGHT)

    def generate_loot(self):
        self.current_loot = LootGenerator.generate(self.tier_var.get(), self.type_var.get())
        c = self.current_loot["coins"]
        parts = []
        is_en = (get_language() == "en")
        cp_code = "PP" if is_en else "MP"
        gp_code = "GP" if is_en else "MO"
        ep_code = "EP" if is_en else "ME"
        sp_code = "SP" if is_en else "MA"
        copper_code = "CP" if is_en else "MR"

        if c["MP"] > 0: parts.append(f"{c['MP']} {cp_code}")
        if c["MO"] > 0: parts.append(f"{c['MO']} {gp_code}")
        if c["ME"] > 0: parts.append(f"{c['ME']} {ep_code}")
        if c["MA"] > 0: parts.append(f"{c['MA']} {sp_code}")
        if c["MR"] > 0: parts.append(f"{c['MR']} {copper_code}")
        coins_str = ", ".join(parts) if parts else _t("loot_no_coins", default="Nessuna moneta")
        
        self.lbl_coins.config(text=_t("loot_coins_summary", coins=coins_str))
        self.lbl_value.config(text=_t("loot_value_est", val=self.current_loot['total_value_gp']))
        
        for it in self.tree_loot.get_children():
            self.tree_loot.delete(it)
            
        gem_type_lbl = "Gem" if is_en else "Gemma"
        gem_desc_lbl = "Valuable gemstone" if is_en else "Prezioso da rivendita"
        for g in self.current_loot["gems"]:
            self.tree_loot.insert("", tk.END, values=(gem_type_lbl, g, gem_desc_lbl))
            
        for item in self.current_loot["items"]:
            self.tree_loot.insert("", tk.END, values=(item.get("type", "Magico"), item.get("name", "Oggetto"), item.get("desc", "")))

    def split_loot_gold(self):
        if not self.current_loot: return
        mo = self.current_loot["coins"]["MO"]
        if mo <= 0:
            mo = self.current_loot["total_value_gp"]
            
        if mo <= 0:
            messagebox.showinfo(_t("msg_no_gold_title", default="Nessun Oro"), _t("msg_no_gold_desc", default="Non ci sono monete d'oro in questo bottino."), parent=self)
            return
            
        party_players = [p for p in self.game_state.players if getattr(p, "is_party_member", False) or getattr(p, "conn", None)]
        if not party_players:
            messagebox.showwarning(_t("msg_no_party_players_title", default="Nessun Giocatore"), _t("msg_no_party_players_desc", default="Non ci sono giocatori nel party a cui distribuire l'oro."), parent=self)
            return
            
        share = mo // len(party_players)
        for p in party_players:
            if not p.full_sheet: p.full_sheet = {}
            if "currency" not in p.full_sheet or not isinstance(p.full_sheet["currency"], dict):
                p.full_sheet["currency"] = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
            p.full_sheet["currency"]["MO"] = p.full_sheet["currency"].get("MO", 0) + share
            if getattr(p, "conn", None):
                send_message(p.conn, {"type": "RECEIVE_GOLD", "data": {"amount": share}})
                
        broadcast(self.game_state, make_chat_broadcast("Sistema", f"💰 {self.game_state._t_local('msg_gold_distributed_desc', total=mo, share=share) if hasattr(self.game_state, '_t_local') else f'Il DM ha distribuito {mo} MO ({share} a testa)!' }"))
        messagebox.showinfo(_t("msg_gold_distributed_title", default="Oro Distribuito"), _t("msg_gold_distributed_desc", total=mo, share=share), parent=self)

    def grant_selected_item(self):
        sel = self.tree_loot.selection()
        if not sel:
            messagebox.showwarning(_t("warning", default="Attenzione"), _t("msg_select_item_warning", default="Seleziona un oggetto o gemma dalla lista."), parent=self)
            return
            
        vals = self.tree_loot.item(sel[0])["values"]
        item_type = vals[0]
        item_name = vals[1]
        item_desc = vals[2]
        
        online_players = [p.name for p in self.game_state.players if getattr(p, "conn", None)]
        if not online_players:
            messagebox.showwarning(_t("warning", default="Attenzione"), _t("msg_no_online_players", default="Nessun giocatore online a cui assegnare l'oggetto."), parent=self)
            return
            
        target = simpledialog.askstring(_t("btn_grant_selected_item", default="Assegna Oggetto"), _t("prompt_assign_item", item=item_name, players=", ".join(online_players)), parent=self)
        if not target or target not in online_players: return
        
        target_p = self.game_state.find_player(target)
        if not target_p or not target_p.conn: return
        
        item_payload = {
            "name": item_name,
            "type": item_type,
            "desc": item_desc,
            "qty": 1,
            "weight": 0.5 if item_type in ["Gemma", "Consumabile", "Gem", "Consumable"] else 2.0
        }
        send_message(target_p.conn, make_receive_item(item_payload))
        broadcast(self.game_state, make_chat_broadcast("Sistema", f"🎁 {item_name} -> {target}!"))
        messagebox.showinfo(_t("msg_item_assigned_title", default="Assegnato"), _t("msg_item_assigned_desc", item=item_name, player=target), parent=self)


class RandomNPCGenerator:
    """Generatore di PNG con personalità, segreti, allineamento e statistiche base 5e (Italiano & English)."""
    
    FIRST_NAMES_M = ["Gareth", "Boran", "Theron", "Kaelen", "Brom", "Lucian", "Doran", "Varis", "Fritz", "Orin", "Alvar"]
    FIRST_NAMES_F = ["Lyra", "Elora", "Seraphina", "Morwen", "Brenna", "Isolde", "Vespera", "Kaelia", "Dara", "Rowan"]
    
    SURNAMES_IT = ["Roccarupe", "Lumacorno", "Ombralesta", "Cuordileone", "Nottetempo", "Fiumargenteo", "Barbaferro", "Ventofreddo", "Lamafina"]
    SURNAMES_EN = ["Stonecliff", "Shadowswift", "Lionheart", "Nightfall", "Silverstream", "Ironbeard", "Coldwind", "Keenblade", "Stormpeak"]
    SURNAMES = SURNAMES_IT
    
    RACES_IT = ["Umano", "Elfo dei Boschi", "Alto Elfo", "Nano delle Colline", "Nano delle Montagne", "Halfling Piedelesto", "Tiefling", "Mezzorco", "Gnomo"]
    RACES_EN = ["Human", "Wood Elf", "High Elf", "Hill Dwarf", "Mountain Dwarf", "Lightfoot Halfling", "Tiefling", "Half-Orc", "Gnome"]
    RACES = RACES_IT

    ROLES_IT = [
        "Locandiere gioviale", "Fabbro muscoloso", "Cacciatore di taglie", "Guardia cittadina corrotta", 
        "Erborista eccentrica", "Sacerdote devoto", "Marinaio scampato a un naufragio", "Studioso arcano",
        "Mendicante astuto (informatore)", "Mercante di spezie esotiche", "Nobile decaduto"
    ]
    ROLES_EN = [
        "Jovial Innkeeper", "Muscular Blacksmith", "Bounty Hunter", "Corrupt Town Guard", 
        "Eccentric Herbalist", "Devout Priest", "Shipwrecked Sailor", "Arcane Scholar",
        "Cunning Beggar (Informant)", "Exotic Spice Merchant", "Fallen Noble"
    ]
    ROLES = ROLES_IT

    ALIGNMENTS_IT = ["Legale Buono", "Neutrale Buono", "Caotico Buono", "Legale Neutrale", "Neutrale Puro", "Caotico Neutrale", "Neutrale Malvagio"]
    ALIGNMENTS_EN = ["Lawful Good", "Neutral Good", "Chaotic Good", "Lawful Neutral", "True Neutral", "Chaotic Neutral", "Neutral Evil"]
    ALIGNMENTS = ALIGNMENTS_IT
    
    TRAITS_IT = [
        "Parla sempre a bassa voce come se svelasse un mistero.",
        "Gesticola vistosamente e ride alle proprie battute.",
        "Sospetta costantemente di essere seguito o spiato.",
        "Tiene maniacalmente puliti i propri stivali e abiti.",
        "Ha una cicatrice evidente sul volto che tocca quando mente.",
        "Cita proverbi popolari assurdi o incomprensibili.",
        "Molto protettivo verso i membri della propria famiglia.",
        "Non guarda mai negli occhi le persone con cui parla."
    ]
    TRAITS_EN = [
        "Always speaks in a hushed whisper as if revealing a deep secret.",
        "Gestures wildly and chuckles at their own jokes.",
        "Constantly suspects they are being watched or followed.",
        "Keeps their boots and garments meticulously clean.",
        "Has a prominent scar across their face and touches it when lying.",
        "Quotes bizarre or incomprehensible ancient proverbs.",
        "Fiercely protective of their family and companions.",
        "Never maintains direct eye contact when speaking."
    ]
    TRAITS = TRAITS_IT
    
    SECRETS_IT = [
        "Ha contratto un pesante debito con la gilda dei ladri locale.",
        "Nasconde una mappa antica che indica una catacomba sigillata.",
        "È fuggito da una città vicina sotto falsa identità.",
        "Conosce la debolezza del tiranno/mostro che minaccia la regione.",
        "È segretamente devoto a un'entità ultraterrena dimenticata.",
        "Custodisce una chiave ornata di cui ignora la serratura."
    ]
    SECRETS_EN = [
        "Owes a crippling debt to the local thieves' guild.",
        "Conceals an ancient map pointing to a sealed catacomb.",
        "Fled a nearby city under an assumed identity.",
        "Knows the hidden vulnerability of the tyrant or monster threatening the region.",
        "Secretly serves a forgotten otherworldly patron.",
        "Carries an ornate key and desperately seeks what it opens."
    ]
    SECRETS = SECRETS_IT

    @classmethod
    def generate(cls) -> Dict[str, Any]:
        lang = get_language()
        is_en = (lang == "en")
        
        surnames_pool = cls.SURNAMES_EN if is_en else cls.SURNAMES_IT
        races_pool = cls.RACES_EN if is_en else cls.RACES_IT
        roles_pool = cls.ROLES_EN if is_en else cls.ROLES_IT
        align_pool = cls.ALIGNMENTS_EN if is_en else cls.ALIGNMENTS_IT
        traits_pool = cls.TRAITS_EN if is_en else cls.TRAITS_IT
        secrets_pool = cls.SECRETS_EN if is_en else cls.SECRETS_IT

        gender = random.choice(["M", "F"])
        name = f"{random.choice(cls.FIRST_NAMES_M if gender == 'M' else cls.FIRST_NAMES_F)} {random.choice(surnames_pool)}"
        race = random.choice(races_pool)
        role = random.choice(roles_pool)
        align = random.choice(align_pool)
        trait = random.choice(traits_pool)
        secret = random.choice(secrets_pool)
        
        hp = random.randint(12, 35)
        ac = random.choice([10, 11, 12, 13, 14, 15])
        
        neutral_lbl = "Neutral" if is_en else "Neutrale"
        notes_hdr = (
            f"Role: {role}\nTrait: {trait}\nSecret: {secret}\nAlignment: {align}"
            if is_en else
            f"Tratto: {trait}\nSegreto: {secret}\nAllineamento: {align}"
        )
        
        return {
            "name": name,
            "race": race,
            "role": role,
            "alignment": align,
            "hp": hp,
            "ac": ac,
            "faction": neutral_lbl,
            "trait": trait,
            "secret": secret,
            "notes": notes_hdr
        }


class RandomNPCDialog(tk.Toplevel):
    """Finestra di generazione immediata di PNG per il DM (Bilingue IT/EN)."""
    def __init__(self, master, game_state):
        super().__init__(master)
        self.game_state = game_state
        self.title(_t("npc_gen_title", default="D&D OmniCompanion • Generatore Rapido PNG"))
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
        tk.Label(hdr, text=_t("npc_gen_header", default="🎭 Generatore Rapido di PNG"), font=("Georgia", 16, "bold"), bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
        tk.Label(hdr, text=_t("npc_gen_subtitle", default="Crea al volo personaggi non giocanti con personalità, segreti e statistiche"), font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w")
        
        # Details Card
        card = tk.Frame(container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=14, pady=12)
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Nome e Ruolo
        r1 = tk.Frame(card, bg=SURFACE_COLOR)
        r1.pack(fill=tk.X, pady=(0, 6))
        tk.Label(r1, text=_t("npc_gen_name", default="Nome:"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        self.ent_name = ttk.Entry(r1, font=FONT_HEADER)
        self.ent_name.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 12))
        
        tk.Label(r1, text=_t("npc_gen_hp", default="HP:"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.sp_hp = ttk.Spinbox(r1, from_=1, to=200, width=5)
        self.sp_hp.pack(side=tk.LEFT, padx=(4, 10))
        
        tk.Label(r1, text=_t("npc_gen_ac", default="CA:"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.sp_ac = ttk.Spinbox(r1, from_=8, to=25, width=4)
        self.sp_ac.pack(side=tk.LEFT, padx=(4, 0))
        
        # Razza, Ruolo, Fazione
        r2 = tk.Frame(card, bg=SURFACE_COLOR)
        r2.pack(fill=tk.X, pady=(0, 8))
        tk.Label(r2, text=_t("npc_gen_race_role", default="Razza & Ruolo:"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT)
        self.lbl_race_role = tk.Label(r2, text="--", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR)
        self.lbl_race_role.pack(side=tk.LEFT, padx=6)
        
        tk.Label(r2, text=_t("npc_gen_alignment", default="Allineamento:"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(10, 0))
        self.lbl_align = tk.Label(r2, text="--", font=FONT_BOLD, bg=SURFACE_COLOR, fg="#5C7CFA")
        self.lbl_align.pack(side=tk.LEFT, padx=6)
        
        # Note, Tratto e Segreto
        tk.Label(card, text=_t("npc_gen_personality_traits", default="Personalità, Tratti e Segreti del PNG:"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(4, 2))
        self.txt_notes = scrolledtext.ScrolledText(card, height=8, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_MAIN,
                                                  relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, wrap=tk.WORD)
        self.txt_notes.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        
        # Action Buttons
        b_row = tk.Frame(container, bg=BG_COLOR)
        b_row.pack(fill=tk.X)
        
        ttk.Button(b_row, text=_t("btn_generate_another_npc", default="🔄 Genera Altro PNG"), command=self.generate_npc).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(b_row, text=_t("btn_spawn_token_map", default="⚡ Spawna Token sulla Mappa"), command=self.spawn_token, style="Gold.TButton").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(b_row, text=_t("btn_save_to_campaign", default="💾 Salva nella Campagna"), command=self.save_to_campaign, style="Primary.TButton").pack(side=tk.LEFT)
        ttk.Button(b_row, text=_t("btn_close", default="Chiudi"), command=self.destroy).pack(side=tk.RIGHT)

    def generate_npc(self):
        self.npc_data = RandomNPCGenerator.generate()
        self.ent_name.delete(0, tk.END)
        self.ent_name.insert(0, self.npc_data["name"])
        self.sp_hp.set(self.npc_data["hp"])
        self.sp_ac.set(self.npc_data["ac"])
        self.lbl_race_role.config(text=f"{self.npc_data['race']} • {self.npc_data['role']}")
        self.lbl_align.config(text=self.npc_data["alignment"])
        
        self.txt_notes.delete("1.0", tk.END)
        role_hdr = _t("npc_gen_role_prefix", default="Ruolo:")
        align_hdr = _t("npc_gen_alignment", default="Allineamento:")
        trait_hdr = _t("npc_gen_trait_prefix", default="Tratto Distintivo:")
        secret_hdr = _t("npc_gen_secret_prefix", default="Segreto / Motivazione:")
        
        desc = (
            f"• {role_hdr} {self.npc_data['role']}\n"
            f"• {align_hdr} {self.npc_data['alignment']}\n\n"
            f"• {trait_hdr}\n  {self.npc_data['trait']}\n\n"
            f"• {secret_hdr}\n  {self.npc_data['secret']}"
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
        broadcast(self.game_state, make_chat_broadcast("DM", f"🎭 NPC '{name}' ({self.npc_data.get('role')}) deployed."))
        messagebox.showinfo(_t("msg_npc_spawned_title", default="PNG Schierato"), _t("msg_npc_spawned_desc", name=name), parent=self)

    def save_to_campaign(self):
        active_c = getattr(self.game_state, "active_campaign", None)
        if not active_c:
            messagebox.showinfo(_t("msg_no_campaign_title", default="Nessuna Campagna"), _t("msg_no_campaign_desc", default="Nessuna campagna attiva caricata. Carica o crea una campagna dal menu File."), parent=self)
            return
            
        name = self.ent_name.get().strip() or self.npc_data["name"]
        active_c.add_npc(
            name=name,
            role=self.npc_data.get("role", "PNG"),
            hp=int(self.sp_hp.get()),
            ac=int(self.sp_ac.get()),
            notes=self.txt_notes.get("1.0", tk.END).strip(),
            faction=self.npc_data.get("faction", "Neutrale")
        )
        active_c.save()
        messagebox.showinfo(_t("msg_npc_saved_title", default="Salvato"), _t("msg_npc_saved_desc", name=name, campaign=active_c.name), parent=self)

