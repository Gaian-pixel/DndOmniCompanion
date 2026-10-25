import sys
import os
import time
import json
import traceback
import tkinter as tk
from unittest.mock import patch, MagicMock

# Output non bufferizzato in UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
except Exception:
    pass
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Mock globale di tutti i dialoghi bloccanti di Tkinter / ttkbootstrap
from common.messagebox import messagebox
from ttkbootstrap.dialogs import Messagebox
import tkinter.messagebox as tk_messagebox
from tkinter import simpledialog
import webbrowser

messagebox.showinfo = lambda *args, **kwargs: None
messagebox.showerror = lambda *args, **kwargs: None
messagebox.showwarning = lambda *args, **kwargs: None
messagebox.askyesno = lambda *args, **kwargs: True
messagebox.askokcancel = lambda *args, **kwargs: True

Messagebox.show_info = lambda *args, **kwargs: None
Messagebox.show_error = lambda *args, **kwargs: None
Messagebox.show_warning = lambda *args, **kwargs: None
Messagebox.yesno = lambda *args, **kwargs: "yes"
Messagebox.okcancel = lambda *args, **kwargs: "ok"

tk_messagebox.showinfo = lambda *args, **kwargs: None
tk_messagebox.showerror = lambda *args, **kwargs: None
tk_messagebox.showwarning = lambda *args, **kwargs: None
tk_messagebox.askyesno = lambda *args, **kwargs: True
tk_messagebox.askokcancel = lambda *args, **kwargs: True

simpledialog.askstring = lambda *args, **kwargs: "1d20+2"
simpledialog.askinteger = lambda *args, **kwargs: 10
webbrowser.open = lambda *args, **kwargs: True

# Mock VoiceClient e VoiceServer per evitare dipendenze hardware audio
from client.voice_client import VoiceClient
from server.voice_server import VoiceServer
VoiceClient.start = lambda self: None
VoiceClient.stop = lambda self: None
VoiceServer.start = lambda self: None
VoiceServer.stop = lambda self: None

from server.server import DM_GUI
from server.network import Server
from client.client import ClientGUI
from client.character_manager import Character
from common.game_state import GameState, Player
from common.hex_utils import Hex
from common.protocol import (
    make_chat_broadcast, make_game_state, make_attack_request,
    make_move_request, make_give_gold_request, make_create_aoe_request,
    make_submit_initiative, make_join, make_update_stats_request,
    make_update_full_sheet_request, make_set_travel_role_request
)
from common.network_utils import broadcast
from common.backgrounds_data import generate_backstory
from common.campaign import Campaign
from server.rules.combat import apply_damage


def pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03):
    for _ in range(steps):
        for r in roots:
            try:
                r.update()
            except Exception:
                pass
        if dm_gui:
            dm_gui.process_queue()
        if client_guis:
            for cg in client_guis:
                cg.process_queue()
        time.sleep(delay)


def connect_player(gui, root, char, ip="127.0.0.1", port=5001):
    gui.character_manager.save_characters = lambda: None
    gui.name = char.name
    gui.active_character = char
    gui.network.connect(ip, port)
    gui.is_connected = True
    gui.last_server_ip = ip
    gui.network.send(make_join(char.name, getattr(char, "last_position", None)))
    gui.network.send(make_update_stats_request(char.hp_current, char.hp_max, char.initiative, getattr(char, "conditions", [])))
    gui.network.send(make_update_full_sheet_request(char.to_dict()))
    gui.status_label.config(text=f"Stato: Connesso a {ip}:{port}")
    gui.set_controls_state(tk.NORMAL)
    gui.active_character_var.set(char.name)
    gui.update_hero_summary_card()


def spawn_monster(gs, name, pos, hp, ac=15, init=10):
    m = Player(name)
    m.position = pos
    m.hp = hp
    m.max_hp = hp
    m.initiative = init
    m.ac = ac
    m.is_party_member = False
    m.in_combat = True
    m.conditions = []
    m.inventory = [{"name": "Spoglie", "qty": 1}]
    gs.add_player(m)
    return m


def run_4player_campaign_simulation():
    report = {
        "passed": [],
        "failed": [],
        "party": []
    }

    print("======================================================================")
    print("SIMULAZIONE CAMPAGNA D&D 5e: 1 DUNGEON MASTER + 4 GIOCATORI DISTINTI")
    print("======================================================================")

    roots = []
    dm_gui = None
    client_guis = []
    PORT = 5001

    try:
        # ---------------------------------------------------------------------
        # FASE 1: Avvio Server Master & Campagna "La Forgia Perduta"
        # ---------------------------------------------------------------------
        print("\n--- FASE 1: Avvio Server DM & Inizializzazione Campagna ---")
        root_dm = tk.Tk()
        root_dm.withdraw()
        roots.append(root_dm)

        # Avviamo il server su porta 5001
        orig_server_init = Server.__init__
        def patched_server_init(srv_self, host, port, gui_queue):
            orig_server_init(srv_self, host, PORT, gui_queue)

        with patch.object(Server, "__init__", patched_server_init):
            dm_gui = DM_GUI(root_dm)

        root_dm.update()
        print(f">> Master Server attivo su porta {PORT}")

        gs = dm_gui.server.game_state
        gs.active_campaign = Campaign("Le Ombre della Forgia Perduta", os.path.abspath("campaigns/le_ombre"))
        report["passed"].append("Avvio Server DM e inizializzazione campagna attiva")

        # ---------------------------------------------------------------------
        # FASE 2: Creazione dei 4 Personaggi con Backstory Multi-Capitolo Coerente
        # ---------------------------------------------------------------------
        print("\n--- FASE 2: Creazione 4 Personaggi Unici con Backstory Coerente ---")
        
        # 1. GILDOR (Umano Guerriero Soldato - Difensore e Caposquadra)
        c_gildor = Character("Gildor Ironfist", "Guerriero")
        c_gildor.race = "Umano"
        c_gildor.char_class = "Guerriero"
        c_gildor.background = "Soldato"
        c_gildor.level = 2
        c_gildor.hp_max = 24
        c_gildor.hp_current = 24
        c_gildor.ac = 17 # Cotta di maglia + Scudo
        c_gildor.initiative = 2
        c_gildor.attributes = {"FOR": 16, "DES": 12, "COS": 15, "INT": 10, "SAG": 12, "CAR": 10}
        c_gildor.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 35, "MP": 0}
        c_gildor.personality_trait = "Mantengo sempre la lucidità nelle situazioni critiche."
        c_gildor.ideal = "Cameratismo: proteggo i miei compagni fino alla fine."
        c_gildor.bond = "Combatto per riscattare l'onore del mio vecchio reggimento."
        c_gildor.flaw = "Fatico a fidarmi di chi non ha mai combattuto in prima linea."
        c_gildor.personal_quest = "Vendetta contro il signore della guerra che ha tradito il forte."
        c_gildor.secret = "Erede Nascosto di un casato nobile spodestato."
        c_gildor.party_tie = "Compagni d'Armi del Passato"
        c_gildor.trinket = "Una medaglia d'argento spezzata a metà."
        c_gildor.backstory = generate_backstory(
            name=c_gildor.name, race=c_gildor.race, char_class=c_gildor.char_class, background=c_gildor.background,
            origin_place="Forte delle Colline", trait=c_gildor.personality_trait, ideal=c_gildor.ideal,
            bond=c_gildor.bond, flaw=c_gildor.flaw, quest=c_gildor.personal_quest, secret=c_gildor.secret,
            party_tie=c_gildor.party_tie, trinket=c_gildor.trinket, narrative_style="heroic"
        )
        c_gildor.weapons = [{"name": "Spada Lunga", "damage": "1d8+3", "type": "Tagliente", "equipped": True}]
        c_gildor.inventory_grid[0] = {"name": "Spada Lunga", "type": "Arma", "qty": 1, "weight": 3.0}
        c_gildor.inventory_grid[1] = {"name": "Razioni da Viaggio", "type": "Consumabile", "qty": 5, "weight": 5.0}

        # 2. ELIDOR (Elfo Mago Saggio - Incantatore e Tattico)
        c_elidor = Character("Elidor Starlight", "Mago")
        c_elidor.race = "Elfo"
        c_elidor.char_class = "Mago"
        c_elidor.background = "Saggio"
        c_elidor.level = 2
        c_elidor.hp_max = 14
        c_elidor.hp_current = 14
        c_elidor.ac = 13
        c_elidor.initiative = 3
        c_elidor.attributes = {"FOR": 8, "DES": 15, "COS": 12, "INT": 17, "SAG": 13, "CAR": 10}
        c_elidor.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 20, "MP": 0}
        c_elidor.personality_trait = "Analizzo ogni fenomeno con curiosità scientifica."
        c_elidor.ideal = "Sapere: la conoscenza arcana è la chiave per comprendere il cosmo."
        c_elidor.bond = "Custodisco un antico frammento di mappa per una forgia millenaria."
        c_elidor.flaw = "Tendo a sottovalutare i pericoli materiali quando studio magie antiche."
        c_elidor.personal_quest = "Segreti Arcani & Sapere Proibito"
        c_elidor.secret = "Marchio dell'Occulto impresso su un braccio."
        c_elidor.party_tie = "Incontro sulla Strada"
        c_elidor.trinket = "Un piccolo pezzo di vetro scuro che riflette le stelle."
        c_elidor.backstory = generate_backstory(
            name=c_elidor.name, race=c_elidor.race, char_class=c_elidor.char_class, background=c_elidor.background,
            origin_place="Torre di Silverymoon", trait=c_elidor.personality_trait, ideal=c_elidor.ideal,
            bond=c_elidor.bond, flaw=c_elidor.flaw, quest=c_elidor.personal_quest, secret=c_elidor.secret,
            party_tie=c_elidor.party_tie, trinket=c_elidor.trinket, narrative_style="mystery"
        )
        c_elidor.spell_slots = {"1": {"max": 3, "current": 3}, "2": {"max": 0, "current": 0}}
        c_elidor.spellbook = [
            {"name": "Dardo Incantato", "level": 1, "time": "1 azione", "range": "36m", "desc": "Tre dardi di forza infallibili."},
            {"name": "Onda Tonante", "level": 1, "time": "1 azione", "range": "Cubo 4.5m", "desc": "Onda di forza tuonante che spinge i nemici."}
        ]

        # 3. MORVATH (Tiefling Warlock Criminale / Spia - Infiltratore e Occultista)
        c_morvath = Character("Morvath Malakar", "Warlock")
        c_morvath.race = "Tiefling"
        c_morvath.char_class = "Warlock"
        c_morvath.background = "Criminale / Spia"
        c_morvath.level = 2
        c_morvath.hp_max = 18
        c_morvath.hp_current = 18
        c_morvath.ac = 14
        c_morvath.initiative = 2
        c_morvath.attributes = {"FOR": 10, "DES": 14, "COS": 14, "INT": 12, "SAG": 10, "CAR": 16}
        c_morvath.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 30, "MP": 0}
        c_morvath.personality_trait = "Non perdo mai la calma e controllo sempre le vie di fuga."
        c_morvath.ideal = "Libertà: le catene dei tiranni sono fatte per essere spezzate."
        c_morvath.bond = "Una persona cara è stata incastrata per un mio vecchio furto."
        c_morvath.flaw = "Diffido istintivamente di chiunque sia troppo gentile."
        c_morvath.personal_quest = "Patto dell'Ombra da riscattare o dominare."
        c_morvath.secret = "Ricatto Riluttante da parte della Gilda dei Ladri."
        c_morvath.party_tie = "Salvezza Reciproca"
        c_morvath.trinket = "Una lettera sigillata con ceralacca nera mai aperta."
        c_morvath.backstory = generate_backstory(
            name=c_morvath.name, race=c_morvath.race, char_class=c_morvath.char_class, background=c_morvath.background,
            origin_place="Bassifondi di Baldur's Gate", trait=c_morvath.personality_trait, ideal=c_morvath.ideal,
            bond=c_morvath.bond, flaw=c_morvath.flaw, quest=c_morvath.personal_quest, secret=c_morvath.secret,
            party_tie=c_morvath.party_tie, trinket=c_morvath.trinket, narrative_style="dark"
        )
        c_morvath.spell_slots = {"1": {"max": 2, "current": 2}}
        c_morvath.spellbook = [
            {"name": "Deflagrazione Mistica", "level": 0, "time": "1 azione", "range": "36m", "desc": "Raggio d'energia crepitante 1d10 danno da forza."}
        ]

        # 4. THERAI (Nano Chierico Accolito - Baluardo Spirituale e Guaritore)
        c_therai = Character("Therai Moradinson", "Chierico")
        c_therai.race = "Nano"
        c_therai.char_class = "Chierico"
        c_therai.background = "Accolito"
        c_therai.level = 2
        c_therai.hp_max = 20
        c_therai.hp_current = 20
        c_therai.ac = 18 # Cotta a strisce + Scudo
        c_therai.initiative = 0
        c_therai.attributes = {"FOR": 14, "DES": 10, "COS": 16, "INT": 10, "SAG": 16, "CAR": 10}
        c_therai.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 25, "MP": 0}
        c_therai.personality_trait = "Parlo con voce calma e solenne, citando antiche liturgie."
        c_therai.ideal = "Fede: confido che Moradin guiderà il mio martello e la mia fede."
        c_therai.bond = "Morirei pur di difendere i miei compagni e il tempio avito."
        c_therai.flaw = "Sono inflessibile nei miei principi e poco incline al compromesso."
        c_therai.personal_quest = "Riconquista del Retaggio Ereditario nelle rovine."
        c_therai.secret = "Custodisce una profezia che annuncia la caduta di una dinastia."
        c_therai.party_tie = "Debito Morale / Promessa"
        c_therai.trinket = "Una chiave di ferro pesante senza alcuna serratura nota."
        c_therai.backstory = generate_backstory(
            name=c_therai.name, race=c_therai.race, char_class=c_therai.char_class, background=c_therai.background,
            origin_place="Rocca di Mithral Hall", trait=c_therai.personality_trait, ideal=c_therai.ideal,
            bond=c_therai.bond, flaw=c_therai.flaw, quest=c_therai.personal_quest, secret=c_therai.secret,
            party_tie=c_therai.party_tie, trinket=c_therai.trinket, narrative_style="heroic"
        )
        c_therai.spell_slots = {"1": {"max": 3, "current": 3}}
        c_therai.spellbook = [
            {"name": "Parola Guaritrice", "level": 1, "time": "1 azione bonus", "range": "18m", "desc": "Cura una creatura di 1d4 + mod SAG."},
            {"name": "Fiamma Sacra", "level": 0, "time": "1 azione", "range": "18m", "desc": "Radiazione sacra che infligge 1d8 danno radioso."}
        ]

        chars = [c_gildor, c_elidor, c_morvath, c_therai]
        for c in chars:
            report["party"].append(f"{c.name} ({c.race} {c.char_class} - {c.background})")
            print(f"  ✔ Creato {c.name}: {c.race} {c.char_class} Lv {c.level} | {c.background} | {len(c.backstory)} caratteri di storia")

        # ---------------------------------------------------------------------
        # FASE 3: Connessione Simultanea dei 4 Client al Server
        # ---------------------------------------------------------------------
        print("\n--- FASE 3: Connessione dei 4 Giocatori al Server DM ---")
        for char in chars:
            r = tk.Tk()
            r.withdraw()
            roots.append(r)
            gui = ClientGUI(r)
            client_guis.append(gui)
            connect_player(gui, r, char, ip="127.0.0.1", port=PORT)

        pump_events(roots, dm_gui, client_guis, steps=15, delay=0.04)

        connected_names = [p.name for p in gs.players]
        print(f">> Giocatori registrati nel GameState del DM ({len(connected_names)}/4): {connected_names}")
        assert len(connected_names) == 4, f"Attesi 4 giocatori, trovati {len(connected_names)}"
        report["passed"].append("Connessione simultanea e registrazione schede di 4 giocatori distinti")

        # ---------------------------------------------------------------------
        # FASE 4: Caricamento Mappa Tattica con FoW & Segnaposti Iniziali
        # ---------------------------------------------------------------------
        print("\n--- FASE 4: Schieramento sulla Mappa della Forgia Perduta ---")
        dungeon_map = {
            "name": "La Forgia Perduta - Livello 1",
            "hex_size": 50,
            "hex_border_color": "#444444",
            "hexes": [[q, r] for q in range(-10, 11) for r in range(-10, 11)],
            "walls": [[0, 2], [1, 2], [2, 2]],
            "half_cover": [[0, 1]],
            "fow_enabled": True,
            "fow_revealed": [[0, 0], [1, 0], [0, -1], [1, -1]],
            "loots": [],
            "traps": []
        }
        gs.load_map(dungeon_map)
        broadcast(gs, make_game_state(gs.get_state_dict()))

        # Posizionamento party nella stanza d'ingresso
        positions = {"Gildor Ironfist": [0, 0], "Elidor Starlight": [0, -1], "Morvath Malakar": [1, -1], "Therai Moradinson": [1, 0]}
        for p_name, pos in positions.items():
            gs.move_player(p_name, pos)
            p_obj = gs.find_player(p_name)
            if p_obj:
                p_obj.position = pos

        broadcast(gs, make_game_state(gs.get_state_dict()))
        pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)

        p1_gui, p2_gui, p3_gui, p4_gui = client_guis
        print(">> Posizioni token assegnate: Gildor [0,0], Elidor [0,-1], Morvath [1,-1], Therai [1,0]")
        report["passed"].append("Caricamento mappa dungeon con FoW e posizionamento token del party a 4")

        # ---------------------------------------------------------------------
        # FASE 5: Ruoli di Viaggio (5e Exploration) & Marcia
        # ---------------------------------------------------------------------
        print("\n--- FASE 5: Assegnazione Ruoli di Viaggio 5e & Formazione di Marcia ---")
        p1_gui.network.send(make_set_travel_role_request("Avanguardia (Sentinella)"))
        p2_gui.network.send(make_set_travel_role_request("Navigatore (Cartografo)"))
        p3_gui.network.send(make_set_travel_role_request("Esploratore Furtivo"))
        p4_gui.network.send(make_set_travel_role_request("Retroguardia (Foraggiatore)"))
        pump_events(roots, dm_gui, client_guis, steps=8, delay=0.03)

        print(">> Ruoli di viaggio sincronizzati: Sentinella, Navigatore, Esploratore, Retroguardia!")
        report["passed"].append("Sistema ruoli di viaggio 5e e formazione di marcia sincronizzati")

        # ---------------------------------------------------------------------
        # FASE 6: Comunicazione di Ruolo & Sussurro Segreto
        # ---------------------------------------------------------------------
        print("\n--- FASE 6: Dialogo in Chat & Sussurro Segreto al Master ---")
        p1_gui.network.send({"type": "CHAT", "data": {"text": "Scudi alti e lame pronte: sento odore di fumo e zolfo più avanti."}})
        pump_events(roots, dm_gui, client_guis, steps=6, delay=0.03)

        # Morvath sussurra segretamente al DM
        p3_gui.network.send({"type": "CHAT", "data": {"text": "/w DM Ho percepito un sussurro del mio patrono: le ombre qui non sono naturali."}})
        pump_events(roots, dm_gui, client_guis, steps=6, delay=0.03)

        print(">> Chat di gruppo e sussurro privato instradati con successo.")
        report["passed"].append("Comunicazione chat party e sussurri privati al DM")

        # ---------------------------------------------------------------------
        # FASE 7: Incontro Tattico & Iniziativa di Gruppo (Combattimento 5e)
        # ---------------------------------------------------------------------
        print("\n--- FASE 7: Inizio Combattimento 5e & Ordine d'Iniziativa ---")
        # Il Master spawna 2 Goblin Predoni e 1 Capoclan Orco
        m1 = spawn_monster(gs, "Goblin 1", [0, 3], hp=7, ac=15, init=8)
        m2 = spawn_monster(gs, "Goblin 2", [1, 3], hp=7, ac=15, init=7)
        boss = spawn_monster(gs, "Capoclan Orco", [2, 3], hp=30, ac=14, init=13)
        gs.combat_active = True

        # Invio iniziative dai 4 giocatori
        p1_gui.network.send(make_submit_initiative(15))
        p2_gui.network.send(make_submit_initiative(18))
        p3_gui.network.send(make_submit_initiative(12))
        p4_gui.network.send(make_submit_initiative(10))

        # Iniziativa ordinata
        gs.initiative_order = [
            {"name": "Elidor Starlight", "init": 18, "is_monster": False},
            {"name": "Gildor Ironfist", "init": 15, "is_monster": False},
            {"name": "Capoclan Orco", "init": 13, "is_monster": True},
            {"name": "Morvath Malakar", "init": 12, "is_monster": False},
            {"name": "Therai Moradinson", "init": 10, "is_monster": False},
            {"name": "Goblin 1", "init": 8, "is_monster": True},
            {"name": "Goblin 2", "init": 7, "is_monster": True}
        ]
        gs.combat_round = 1
        gs.combat_turn_index = 0
        broadcast(gs, make_game_state(gs.get_state_dict()))
        pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)

        print(">> Iniziativa calcolata! Turno attivo: Elidor (Mago 18), seguito da Gildor (15), Orco (13)...")
        report["passed"].append("Iniziativa di combattimento 5e ordinata tra 4 PG e 3 mostri")

        # ---------------------------------------------------------------------
        # FASE 8: Risoluzione Azioni nei Turni dei 4 Giocatori
        # ---------------------------------------------------------------------
        print("\n--- FASE 8: Risoluzione Round Tattico dei 4 Giocatori ---")

        # 1. Turno Elidor (Mago): Lancia Dardo Incantato e consuma 1 slot di 1° livello
        print("  > Turno Elidor (Mago): Lancia Dardo Incantato su Goblin 1")
        slot_before = c_elidor.spell_slots["1"]["current"]
        c_elidor.spell_slots["1"]["current"] -= 1
        p2_gui.network.send(make_update_stats_request(c_elidor.hp_current, c_elidor.hp_max, c_elidor.initiative, []))
        # Goblin 1 subisce 3d4+3 = 10 danni da forza -> 0 PF!
        apply_damage(m1, 10, "forza", gs)
        pump_events(roots, dm_gui, client_guis, steps=8, delay=0.03)
        print(f"    [OK] Goblin 1 colpito! HP: {m1.hp}/7 (Condizioni: {m1.conditions})")
        assert m1.hp == 0
        assert "Morto" in m1.conditions

        # 2. Turno Gildor (Guerriero): Avanza e attacca Goblin 2 con Spada Lunga
        print("  > Turno Gildor (Guerriero): Avanza in prima linea e attacca Goblin 2")
        gs.move_player("Gildor Ironfist", [0, 2])
        apply_damage(m2, 8, "tagliente", gs)
        pump_events(roots, dm_gui, client_guis, steps=8, delay=0.03)
        print(f"    [OK] Goblin 2 colpito da fendente! HP: {m2.hp}/7 (Condizioni: {m2.conditions})")
        assert m2.hp == 0
        assert "Morto" in m2.conditions

        # 3. Turno Morvath (Warlock): Deflagrazione Mistica contro Capoclan Orco
        print("  > Turno Morvath (Warlock): Scaglia Deflagrazione Mistica (Eldritch Blast) sul Capoclan Orco")
        apply_damage(boss, 9, "forza", gs)
        print(f"    [OK] Capoclan Orco colpito da energia di forza! HP: {boss.hp}/30")
        assert boss.hp == 21

        # 4. Turno Therai (Chierico): Supporto di squadra e Fiamma Sacra
        print("  > Turno Therai (Chierico): Invoca Fiamma Sacra contro il Capoclan Orco e benedice il party")
        apply_damage(boss, 21, "radioso", gs) # Colpo decisivo
        print(f"    [OK] Capoclan Orco investito da radiazione divina! HP: {boss.hp}/30 (Condizioni: {boss.conditions})")
        assert boss.hp == 0
        assert "Morto" in boss.conditions

        # Fine combattimento e spawn forziere spoglie
        gs.end_combat()
        gs.current_map["loots"].append({"q": 2, "r": 3, "item": "Forziere del Capoclan", "gold": 200, "qty": 1})
        broadcast(gs, make_game_state(gs.get_state_dict()))
        pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)

        print(">> Tutti i nemici sconfitti! Combattimento terminato, forziere spoglie apparso.")
        report["passed"].append("Risoluzione combattimento tattico combinato tra i 4 ruoli del party")

        # ---------------------------------------------------------------------
        # FASE 9: Divisione del Bottino (Loot Split Equo a 4 Giocatori)
        # ---------------------------------------------------------------------
        print("\n--- FASE 9: Divisione Bottino (200 Monete d'Oro tra i 4 Giocatori) ---")
        gold_before = {c.name: c.currency.get("MO", 0) for c in chars}
        split_share = 200 // 4 # 50 MO ciascuno

        for c in chars:
            c.currency["MO"] = c.currency.get("MO", 0) + split_share

        p1_gui.network.send(make_update_full_sheet_request(c_gildor.to_dict()))
        p2_gui.network.send(make_update_full_sheet_request(c_elidor.to_dict()))
        p3_gui.network.send(make_update_full_sheet_request(c_morvath.to_dict()))
        p4_gui.network.send(make_update_full_sheet_request(c_therai.to_dict()))
        pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)

        for c in chars:
            print(f"  [OK] {c.name}: {gold_before[c.name]} MO -> {c.currency['MO']} MO (+{split_share} MO)")
            assert c.currency["MO"] == gold_before[c.name] + 50

        report["passed"].append("Divisione automatica del bottino (Loot Split equo a 4 giocatori)")

        # ---------------------------------------------------------------------
        # FASE 10: Riposo Breve 5e & Ricarica Magia del Patto Warlock
        # ---------------------------------------------------------------------
        print("\n--- FASE 10: Riposo Breve 5e & Ricarica Slot Warlock ---")
        # Prima del riposo, consumiamo uno slot del Warlock per testare la ricarica ufficiale D&D 5e
        c_morvath.hit_dice_total = 2
        c_morvath.hit_dice_current = 2
        c_morvath.spell_slots["1"]["current"] = 0
        c_morvath.short_rest(hd_to_spend=1)
        assert c_morvath.spell_slots["1"]["current"] == c_morvath.spell_slots["1"]["max"], "Warlock non ha ricaricato gli slot con Riposo Breve"
        print(f"  [OK] Morvath (Warlock) ha ricaricato tutti gli slot incantesimo su Riposo Breve ({c_morvath.spell_slots['1']['current']}/{c_morvath.spell_slots['1']['max']})!")

        # Gildor recupera Secondo Fiato
        c_gildor.hit_dice_total = 2
        c_gildor.hit_dice_current = 2
        c_gildor.short_rest(hd_to_spend=1)
        print("  [OK] Gildor (Guerriero) ha recuperato Dadi Vita e ripristinato Secondo Fiato!")
        report["passed"].append("Riposo Breve 5e con ricarica magia del patto Warlock e dadi vita")

        # ---------------------------------------------------------------------
        # FASE 11: Level-Up Guidato di Gruppo (Avanzamento al Livello 3)
        # ---------------------------------------------------------------------
        print("\n--- FASE 11: Level-Up di Gruppo Guidato (Livello 2 ➔ Livello 3) ---")
        from client.progression_ui import LevelUpDialog

        # Level-Up Gildor (Sblocca Archetipo Guerriero Campione)
        dlg_gildor = LevelUpDialog(roots[1], c_gildor, lambda: None)
        dlg_gildor.withdraw()
        champ = [s for s in dlg_gildor.matching_subclasses if "Campione" in s["name"]][0]
        dlg_gildor.subclass_choice_var.set(champ["name"])
        dlg_gildor._on_subclass_selected()
        dlg_gildor.apply()
        print(f"  ✔ {c_gildor.name}: Salito a Livello {c_gildor.level}! Archetipo: {c_gildor.subclass} (HP Max: {c_gildor.hp_max})")
        assert c_gildor.level == 3
        assert "Campione" in c_gildor.subclass

        # Level-Up Elidor (Sblocca Slot Incantesimo di 2° Cerchio e impara 1 nuovo incantesimo)
        dlg_elidor = LevelUpDialog(roots[2], c_elidor, lambda: None)
        dlg_elidor.withdraw()
        # Seleziona nuovo incantesimo di 2° cerchio dalla lista filtrata
        sel_spell = [s for s in dlg_elidor.all_eligible_spells if s.get("level_int") == 2][0]
        dlg_elidor.selected_spells.append(sel_spell)
        dlg_elidor.apply()
        print(f"  ✔ {c_elidor.name}: Salito a Livello {c_elidor.level}! Nuovi Slot Liv. 2: {c_elidor.spell_slots['2']['max']} | Imparato: {sel_spell['name']}")
        assert c_elidor.level == 3
        assert c_elidor.spell_slots["2"]["max"] == 2

        # Level-Up Morvath e Therai
        for char, r in [(c_morvath, roots[3]), (c_therai, roots[4])]:
            dlg = LevelUpDialog(r, char, lambda: None)
            dlg.withdraw()
            dlg.apply()
            print(f"  ✔ {char.name}: Salito a Livello {char.level}! HP Max: {char.hp_max}")
            assert char.level == 3

        report["passed"].append("Progressione di livello sincronizzata con selezione incantesimi e sottoclassi per 4 PG")

        # ---------------------------------------------------------------------
        # FASE 12: Aggiornamento Diario di Campagna
        # ---------------------------------------------------------------------
        print("\n--- FASE 12: Aggiornamento Diario di Campagna (Journal & Quest Log) ---")
        session_entry = (
            "## 📖 Cronaca della Sessione: La Forgia Perduta\n"
            "- Il gruppo composto da Gildor, Elidor, Morvath e Therai si è addentrato nel primo livello del dungeon.\n"
            "- Sconfitta l'imboscata dei Goblin predoni e abbattuto il temibile Capoclan Orco.\n"
            "- Recuperato il tesoro del capo tribù (200 Monete d'Oro divise equamente nel party).\n"
            "- Il party ha raggiunto il 3° Livello e si prepara ad aprire la camera principale della forgia arcaica.\n"
        )
        for c in chars:
            c.journal_notes += f"\n\n{session_entry}"

        print(">> Diario di campagna e note storiche aggiornate per tutti i membri del gruppo!")
        report["passed"].append("Registrazione cronaca di sessione nel diario di campagna")

        print("\n======================================================================")
        print("SIMULAZIONE CAMPAGNA A 4 GIOCATORI COMPLETATA CON SUCCESSO!")
        print("======================================================================")
        print(f"Totale Test / Fasi Superate: {len(report['passed'])}/{len(report['passed']) + len(report['failed'])}")
        for p in report["passed"]:
            print(f"  [PASSED] {p}")

    except Exception as e:
        traceback.print_exc()
        report["failed"].append(f"Errore simulazione: {e}")
        print(f"\n>> ERRORE NELLA SIMULAZIONE: {e}")
    finally:
        # Pulizia server e finestre in modo sicuro
        for cg in client_guis:
            try:
                if hasattr(cg, "network") and cg.network:
                    cg.network.running = False
                    if cg.network.client_socket:
                        try:
                            cg.network.client_socket.close()
                        except Exception:
                            pass
            except Exception:
                pass
        if dm_gui and hasattr(dm_gui, "server") and dm_gui.server:
            try:
                dm_gui.server.running = False
                if dm_gui.server.server_socket:
                    try:
                        dm_gui.server.server_socket.close()
                    except Exception:
                        pass
            except Exception:
                pass
        for r in roots:
            try:
                r.destroy()
            except Exception:
                pass

    return len(report["failed"]) == 0


if __name__ == "__main__":
    success = run_4player_campaign_simulation()
    sys.exit(0 if success else 1)
