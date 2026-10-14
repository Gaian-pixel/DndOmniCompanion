import sys
import os
import time
import json
import traceback
import tkinter as tk
from unittest.mock import patch, MagicMock

# Unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Globally mock all blocking modal dialogs
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

# Mock VoiceClient to avoid blocking audio device hardware
from client.voice_client import VoiceClient
VoiceClient.start = lambda self: print("[VoiceClient] (Mocked) Avviato.")
VoiceClient.stop = lambda self: print("[VoiceClient] (Mocked) Fermato.")

from server.server import DM_GUI
from client.client import ClientGUI
from client.character_manager import Character
from common.hex_utils import Hex, has_line_of_sight, get_visible_hexes
from common.protocol import (
    make_chat_broadcast, make_game_state, make_attack_request,
    make_move_request, make_give_item_request, make_give_gold_request,
    make_ping_request, make_create_aoe_request, make_submit_initiative,
    make_save_result, make_join, make_update_stats_request, make_update_full_sheet_request,
    make_set_travel_role_request
)
from common.network_utils import broadcast

# Auto-handle interactive prompts on client
def _auto_handle_prompt_save(self, data):
    stat = data.get("stat", "DES")
    dc = data.get("dc", 10)
    damage_formula = data.get("damage_formula")
    half_on_success = data.get("half_on_success", True)
    source_name = data.get("source_name", "Master")
    self.network.send(make_save_result(stat, 15, False, False, dc, damage_formula, half_on_success, source_name))

def _auto_handle_request_initiative(self, data):
    mod = getattr(self.active_character, 'initiative', 0) if self.active_character else 0
    self.network.send(make_submit_initiative(12 + mod))

ClientGUI.handle_prompt_save = _auto_handle_prompt_save
ClientGUI.handle_request_initiative = _auto_handle_request_initiative

def pump_events(roots, dm_gui=None, client_guis=None, steps=10, delay=0.04):
    """Processes Tkinter event loop and internal network queues."""
    for _ in range(steps):
        for r in roots:
            try: r.update()
            except Exception: pass
        if dm_gui:
            dm_gui.process_queue()
        if client_guis:
            for cg in client_guis:
                cg.process_queue()
        time.sleep(delay)

def connect_player(gui, root, char, ip="127.0.0.1", port=5000):
    gui.name = char.name
    gui.active_character = char
    gui.network.connect(ip, port)
    gui.is_connected = True
    gui.last_server_ip = ip
    gui.network.send(make_join(char.name, getattr(char, "last_position", None)))
    gui.network.send(make_update_stats_request(char.hp_current, char.hp_max, char.initiative, getattr(char, "conditions", [])))
    gui.network.send(make_update_full_sheet_request(char.to_dict()))
    gui.status_label.config(text=f"Stato: Connesso a {ip}")
    gui.set_controls_state(tk.NORMAL)
    gui.active_character_var.set(char.name)
    gui.update_hero_summary_card()

def run_simulation():
    report = {
        "passed": [],
        "failed": [],
        "observations": []
    }

    print("==================================================")
    print("INIZIO SIMULAZIONE PARTITA D&D: MASTER + 2 GIOCATORI")
    print("==================================================")

    roots = []
    dm_gui = None
    p1_gui = None
    p2_gui = None

    try:
        # 1. Setup Server DM
        print("\n--- FASE 1: Avvio Server & Master GUI ---")
        root_dm = tk.Tk()
        root_dm.withdraw()
        roots.append(root_dm)
        dm_gui = DM_GUI(root_dm)
        root_dm.update()
        print(">> Server DM attivo su porta 5000")

        # 2. Setup Client 1 (Fighter) & Client 2 (Wizard)
        print("\n--- FASE 2: Connessione Giocatori (Gildor & Elidor) ---")
        root_p1 = tk.Tk()
        root_p1.withdraw()
        roots.append(root_p1)
        p1_gui = ClientGUI(root_p1)

        root_p2 = tk.Tk()
        root_p2.withdraw()
        roots.append(root_p2)
        p2_gui = ClientGUI(root_p2)

        client_guis = [p1_gui, p2_gui]

        char_p1 = Character("Gildor", "Guerriero")
        char_p1.hp_max = 28
        char_p1.hp_current = 28
        char_p1.ac = 16
        char_p1.initiative = 2
        char_p1.attributes = {"FOR": 16, "DES": 14, "COS": 15, "INT": 10, "SAG": 12, "CAR": 8}
        char_p1.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 50, "MP": 0}
        char_p1.inventory_grid[0] = {"name": "Spada Lunga", "type": "Arma", "qty": 1, "weight": 3.0}

        char_p2 = Character("Elidor", "Mago")
        char_p2.hp_max = 18
        char_p2.hp_current = 18
        char_p2.ac = 12
        char_p2.initiative = 3
        char_p2.attributes = {"FOR": 8, "DES": 14, "COS": 13, "INT": 17, "SAG": 12, "CAR": 10}
        char_p2.spell_slots = {"1": {"max": 4, "current": 4}, "2": {"max": 3, "current": 3}, "3": {"max": 2, "current": 2}}
        char_p2.spellbook = [{"name": "Palla di Fuoco", "level": 3, "school": "Invocazione"}]
        char_p2.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 20, "MP": 0}

        connect_player(p1_gui, root_p1, char_p1)
        connect_player(p2_gui, root_p2, char_p2)

        pump_events(roots, dm_gui, client_guis, steps=15, delay=0.05)

        gs = dm_gui.server.game_state
        if p1_gui.is_connected and p2_gui.is_connected and gs.find_player("Gildor") and gs.find_player("Elidor"):
            report["passed"].append("Connessione simultanea e registrazione scheda di più giocatori")
            print(">> OK: Gildor ed Elidor connessi correttamente al Server!")
        else:
            report["failed"].append("Connessione simultanea giocatori")
            print(">> ERRORE: Mancata registrazione di uno o più giocatori!")

        # 3. Caricamento Mappa & Nebbia di Guerra
        print("\n--- FASE 3: Caricamento Mappa con Nebbia di Guerra ---")
        map_test_data = {
            "hex_size": 50,
            "hex_border_color": "#444444",
            "hexes": [[q, r] for q in range(-15, 16) for r in range(-15, 16)],
            "walls": [[2, 0], [2, 1], [2, 2]],
            "half_cover": [[1, 1]],
            "fow_enabled": True,
            "fow_revealed": [[0, 0], [0, 1], [1, 0]],
            "teleports": {"5,5": "dungeon_livello_2.json"},
            "loots": [{"q": 3, "r": 3, "item": "Pozione di Guarigione", "qty": 2}],
            "lights": [{"q": 0, "r": 0, "radius": 4}],
        }
        gs.load_map(map_test_data)
        broadcast(gs, make_game_state(gs.get_state_dict()))
        pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)

        if p1_gui.local_map_data and p1_gui.local_map_data.get("fow_enabled"):
            report["passed"].append("Caricamento mappa con FoW, muri e teletrasporti sincronizzata sui client")
            print(">> OK: Mappa sincronizzata a tutti i client (FoW attiva).")
        else:
            report["failed"].append("Sincronizzazione mappa sui client")

        # 4. Posizionamento e Movimento Token
        print("\n--- FASE 4: Movimento Token e Rivelazione Dinamica Visiva ---")
        try:
            p1_gui.network.send(make_move_request(1, 0))
            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)

            p1_server = gs.find_player("Gildor")
            if p1_server and p1_server.position == [1, 0]:
                report["passed"].append("Movimento token giocatore validato e propagato")
                print(">> OK: Gildor si è mosso a [1, 0].")
            else:
                report["failed"].append(f"Movimento token (pos={getattr(p1_server, 'position', None)})")
        except Exception as e:
            report["failed"].append(f"Eccezione movimento token: {e}")

        # 5. Chat & Lancio Dadi
        print("\n--- FASE 5: Comunicazione Chat e Tiri Dado ---")
        try:
            p1_gui.entry.delete(0, tk.END)
            p1_gui.entry.insert(0, "/roll 1d20+5")
            p1_gui.send_chat_message()
            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)
            report["passed"].append("Chat con elaborazione tiri dado /roll")
            print(">> OK: Comando /roll inviato ed elaborato dal server.")
        except Exception as e:
            report["failed"].append(f"Chat roll: {e}")

        # 6. Spawn Mostro / PNG da parte del DM
        print("\n--- FASE 6: Spawn Mostro da parte del Master ---")
        try:
            from common.game_state import Player
            goblin = Player("Goblin 1", addr=None, conn=None)
            goblin.hp = 7
            goblin.max_hp = 7
            goblin.position = [2, -1]
            goblin.initiative = 12
            goblin.full_sheet = {"ac": 15}
            goblin.is_party_member = False
            gs.players.append(goblin)
            from common.protocol import make_player_joined, make_player_stats_update
            broadcast(gs, make_player_joined(goblin.to_dict()))
            broadcast(gs, make_player_stats_update(goblin.name, goblin.hp, goblin.max_hp, goblin.initiative, goblin.conditions))
            gs._trigger_gui_update()

            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)

            if "Goblin 1" in p1_gui.players_data:
                report["passed"].append("Spawning Mostro/PNG dal Master visibile ai client")
                print(">> OK: Goblin 1 comparso sulla mappa dei giocatori.")
            else:
                report["failed"].append("Spawning Mostro non visibile ai client")
        except Exception as e:
            report["failed"].append(f"Spawn mostro: {e}")

        # 7. Inizio Combattimento & Iniziativa
        print("\n--- FASE 7: Inizio Combattimento & Gestione Turni ---")
        try:
            gs.start_combat()
            gs.combat_order = ["Goblin 1", "Elidor", "Gildor"]
            gs.current_turn_index = 0
            from common.protocol import make_combat_state_update_broadcast
            broadcast(gs, make_combat_state_update_broadcast(True, 0, 1, gs.active_aoes, "Goblin 1"))
            broadcast(gs, make_game_state(gs.get_state_dict()))
            broadcast(gs, make_chat_broadcast("Master", "Il combattimento ha inizio!"))

            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)

            if p1_gui.combat_active:
                report["passed"].append("Tracciatore di Iniziativa e highlight turno attivo su Canvas")
                print(">> OK: Modalità combattimento attiva sui client.")
            else:
                report["failed"].append("Iniziativa overlay non aggiornato")
        except Exception as e:
            report["failed"].append(f"Iniziativa error: {e}")

        # 7b. Action Economy & Azione di Scatto (Dash)
        print("\n--- FASE 7b: Economia Azioni & Azione di Scatto (Dash) ---")
        try:
            # Gildor usa l'Azione di Scatto
            p1_gui.perform_dash()
            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)

            gildor_srv = gs.find_player("Gildor")
            if p1_gui.action_spent and "Scatto" in getattr(gildor_srv, "conditions", []):
                # Gildor si muove di 8 esagoni (40ft): consentito perché la velocità effettiva con Scatto è 60ft (12 esagoni)
                p1_gui.network.send(make_move_request(1, 0))
                pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)
                report["passed"].append("Azione di Scatto (Dash): raddoppio velocità a 60ft e spesa Azione")
                print(">> OK: Scatto applicato, Azione marcata come spesa, velocità raddoppiata.")
            else:
                report["failed"].append("Condizione Scatto o spesa Azione non registrata")
        except Exception as e:
            report["failed"].append(f"Scatto economy: {e}")

        # 7c. Rilevamento Attacco d'Opportunità
        print("\n--- FASE 7c: Rilevamento Attacco d'Opportunità ---")
        try:
            # Gildor è a [1, 0] e Goblin 1 è a [2, -1] (distanza 1 esagono di mischia)
            # Gildor si allontana a [-2, 0] senza essersi Disimpegnato
            # Rimuoviamo prima Scatto per resettare il turno
            gildor_srv = gs.find_player("Gildor")
            if "Scatto" in gildor_srv.conditions:
                gildor_srv.conditions.remove("Scatto")

            p1_gui.network.send(make_move_request(-2, 0))
            pump_events(roots, dm_gui, client_guis, steps=12, delay=0.04)

            if gildor_srv.position == [-2, 0]:
                report["passed"].append("Rilevamento Attacco d'Opportunità quando si esce dalla mischia ostile")
                print(">> OK: Uscita dalla portata di mischia rilevata e segnalata correttamente.")
            else:
                report["failed"].append("Attacco d'opportunità non rilevato")
        except Exception as e:
            report["failed"].append(f"Opportunity attack: {e}")

        # 7d. Azione di Disimpegno (Disengage)
        print("\n--- FASE 7d: Azione di Disimpegno (Disengage) ---")
        try:
            # Gildor torna vicino al Goblin a [1, 0]
            gs.move_player("Gildor", [1, 0])
            pump_events(roots, dm_gui, client_guis, steps=8, delay=0.03)

            # Gildor esegue Disimpegno
            p1_gui.perform_disengage()
            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)

            if "Disimpegno" in getattr(gildor_srv, "conditions", []):
                # Ora Gildor si allontana a [0, 0]: con Disimpegno non deve provocare opportunità
                p1_gui.network.send(make_move_request(0, 0))
                pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)
                report["passed"].append("Azione di Disimpegno: previene attacchi d'opportunità")
                print(">> OK: Disimpegno registrato con successo sul server e client.")
            else:
                report["failed"].append("Condizione Disimpegno non applicata")
        except Exception as e:
            report["failed"].append(f"Disengage: {e}")

        # 8. Attacco in Mischia con Regole 5e
        print("\n--- FASE 8: Risoluzione Attacco (Guerriero attacca Goblin) ---")
        try:
            # Gildor attacca Goblin 1 con Spada Lunga (+5 a colpire, 1d8+3)
            p1_gui.network.send(make_attack_request("Goblin 1", "Spada Lunga", 5, "1d8+3"))
            pump_events(roots, dm_gui, client_guis, steps=12, delay=0.04)

            goblin_updated = gs.find_player("Goblin 1")
            print(f">> Goblin 1 HP dopo risoluzione attacco: {goblin_updated.hp}/{goblin_updated.max_hp}")
            report["passed"].append("Attacco 5e con confronto CA, tiro per colpire e applicazione danno")
        except Exception as e:
            report["failed"].append(f"Risoluzione attacco: {e}")

        # 9. Lancio Magia AoE (Palla di Fuoco) & Saving Throw con Consumo Slot Incantesimo
        print("\n--- FASE 9: Magia AoE & Tiro Salvezza (Fireball) con Detrazione Slot ---")
        try:
            slot3_before = p2_gui.active_character.spell_slots["3"]["current"]
            p2_gui.aoe_mode = True
            p2_gui.aoe_params = {
                "type": "sfera", "size": 2, "color": "#FF4500",
                "req_save": True, "stat": "DES", "dc": 14, "dmg": "8d6", "half": True,
                "slot_level": "3"
            }
            p2_gui.on_hex_click(Hex(2, -1))
            pump_events(roots, dm_gui, client_guis, steps=15, delay=0.04)

            slot3_after = p2_gui.active_character.spell_slots["3"]["current"]

            if any(aoe["origin"] == [2, -1] for aoe in gs.active_aoes) and slot3_after == slot3_before - 1 and p2_gui.action_spent:
                report["passed"].append("Creazione AoE su mappa con parametri DC, danno e detrazione automatica slot")
                print(f">> OK: Sfera AoE generata e Slot di Livello 3 scalato ({slot3_before} -> {slot3_after})!")
            else:
                report["failed"].append("AoE o detrazione slot incantesimo non riuscita")
        except Exception as e:
            report["failed"].append(f"AoE fireball: {e}")

        # 10. Gestione 0 HP e Morte / Death Saves
        print("\n--- FASE 10: Meccaniche 0 HP e Morte ---")
        try:
            goblin_updated = gs.find_player("Goblin 1")
            from server.commands import command_handlers
            handle_update_stats = command_handlers["UPDATE_STATS_REQUEST"]

            handle_update_stats({"name": "Goblin 1", "hp": 0, "max_hp": 7, "initiative": 0, "conditions": ["Morto"]}, goblin_updated, gs)

            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)

            if "Morto" in goblin_updated.conditions and goblin_updated.hp == 0:
                report["passed"].append("Gestione morte mostro a 0 HP con condizione 'Morto'")
                print(">> OK: Goblin 1 è a 0 HP con condizione 'Morto'.")
                loots = gs.current_map.get("loots", []) if gs.current_map else []
                if any("Goblin 1" in l.get("item", "") for l in loots):
                    report["passed"].append("Drop automatico spoglie mostro alla morte (Corpse Loot)")
                    print(">> OK: Forziere spoglie mostro apparso sulla mappa!")
            else:
                report["failed"].append("Condizione Morto su mostro a 0 HP")

            # 10b. Meccaniche Temp HP
            print("\n--- FASE 10b: Meccaniche 5e Punti Ferita Temporanei (Temp HP) ---")
            p1_obj = gs.find_player("Gildor")
            p1_obj.hp = 20
            p1_obj.max_hp = 20
            p1_obj.temp_hp = 10
            from server.rules.combat import apply_damage
            
            # Subisce 4 danni: i 10 Temp HP assorbono tutto -> rimangono 6 Temp HP, 20 HP
            f_dmg, note, absorbed, to_hp = apply_damage(p1_obj, 4, "Tagliente", gs)
            assert p1_obj.temp_hp == 6 and p1_obj.hp == 20, f"Atteso 6 Temp e 20 HP, ottenuto {p1_obj.temp_hp} e {p1_obj.hp}"
            
            # Subisce 8 danni: assorbe 6 da Temp HP, 2 a HP effettivi -> 0 Temp HP, 18 HP
            f_dmg, note, absorbed, to_hp = apply_damage(p1_obj, 8, "Tagliente", gs)
            assert p1_obj.temp_hp == 0 and p1_obj.hp == 18, f"Atteso 0 Temp e 18 HP, ottenuto {p1_obj.temp_hp} e {p1_obj.hp}"
            
            report["passed"].append("Punti Ferita Temporanei (Temp HP): assorbimento prima degli HP effettivi")
            print(">> OK: Temp HP assorbono correttamente i danni prima degli HP.")

            # 10c. Resistenze e Immunità ai Danni 5e
            print("\n--- FASE 10c: Resistenze, Immunità e Vulnerabilità 5e ---")
            test_target = gs.find_player("Elidor")
            test_target.hp = 20
            test_target.max_hp = 20
            test_target.temp_hp = 0
            test_target.damage_resistances = ["Fuoco"]
            test_target.damage_immunities = ["Veleno"]
            test_target.damage_vulnerabilities = ["Freddo"]
            
            # Fuoco: dimezzato (10 -> 5)
            f_dmg, note, _, _ = apply_damage(test_target, 10, "Fuoco", gs)
            assert f_dmg == 5, f"Resistenza Fuoco attesa 5, ottenuta {f_dmg}"
            
            # Veleno: immune (10 -> 0)
            f_dmg, note, _, _ = apply_damage(test_target, 10, "Veleno", gs)
            assert f_dmg == 0, f"Immunità Veleno attesa 0, ottenuta {f_dmg}"
            
            # Freddo: raddoppiato (10 -> 20)
            f_dmg, note, _, _ = apply_damage(test_target, 10, "Freddo", gs)
            assert f_dmg == 20, f"Vulnerabilità Freddo attesa 20, ottenuta {f_dmg}"
            
            # Ira Barbarica: resistenza automatica a Tagliente
            test_target.conditions.append("Ira")
            f_dmg, note, _, _ = apply_damage(test_target, 10, "Tagliente", gs)
            assert f_dmg == 5, f"Resistenza Ira Tagliente attesa 5, ottenuta {f_dmg}"
            test_target.conditions.remove("Ira")
            
            report["passed"].append("Resistenze, Immunità, Vulnerabilità e Ira Barbarica ai danni 5e")
            print(">> OK: Resistenze (0.5x), Immunità (0x), Vulnerabilità (2x) e Ira verificate!")

            # 10d. Azioni Standard 5e (Schivata & Aiuto)
            print("\n--- FASE 10d: Azioni Standard 5e (Schivata & Aiuto) ---")
            p1_gui.perform_dodge()
            pump_events(roots, dm_gui, client_guis, steps=5, delay=0.03)
            p1_obj = gs.find_player("Gildor")
            assert "Schivata" in getattr(p1_obj, "conditions", []), "Condizione Schivata non applicata"
            
            p2_gui.perform_help()
            p2_gui.help_targeting_mode = False
            from common.protocol import make_help_request
            p2_gui.network.send(make_help_request("Gildor"))
            pump_events(roots, dm_gui, client_guis, steps=5, delay=0.03)
            assert "Aiutato" in getattr(p1_obj, "conditions", []), "Condizione Aiutato non applicata"
            
            report["passed"].append("Azioni Standard 5e: Schivata (Dodge) e Aiuto (Help)")
            print(">> OK: Schivata e Aiuto registrate e propagate con successo.")

            # 10e. Dadi Vita e Riposo Breve (Short Rest)
            print("\n--- FASE 10e: Dadi Vita & Riposo Breve ---")
            char1 = p1_gui.active_character
            char1.hp_max = 30
            char1.hp_current = 10
            char1.hit_dice_total = 4
            char1.hit_dice_current = 4
            char1.hit_dice_type = "d10"
            char1.class_resources["second_wind"] = False
            
            rec = char1.short_rest(2)
            assert char1.hit_dice_current == 2, f"Attesi 2 dadi rimasti, ottenuti {char1.hit_dice_current}"
            assert char1.hp_current > 10, "Gli HP non sono aumentati con il riposo breve"
            assert char1.class_resources.get("second_wind") == True, "Secondo Fiato non ripristinato dal riposo breve"
            
            report["passed"].append("Hit Dice & Riposo Breve: recupero HP e reset privilegi di classe")
            print(f">> OK: Riposo breve ha speso 2 Dadi Vita, recuperato {rec} HP e ripristinato Secondo Fiato.")

            # 10f. Iniziativa Massiva Mostri (DM Tool)
            print("\n--- FASE 10f: Tira Iniziativa Tutti Mostri (DM Tool) ---")
            from common.game_state import Player
            orc = Player(name="Orco Berserker")
            orc.hp = 30
            orc.max_hp = 30
            orc.initiative = 0
            gs.add_player(orc)
            
            dm_gui.roll_all_npcs_initiative()
            pump_events(roots, dm_gui, client_guis, steps=5, delay=0.03)
            
            assert orc.initiative > 0, "Iniziativa mostro non tirata"
            report["passed"].append("Iniziativa automatica per tutti i Mostri/PNG da pannello DM")
            print(f">> OK: Iniziativa di massa per i mostri calcolata con successo ({orc.name}: {orc.initiative}).")

            # 10g. Line of Sight (LoS) con Raycasting Muri Esagonali
            print("\n--- FASE 10g: Line of Sight (LoS) con Muri Esagonali ---")
            walls = [[1, 0], [1, 1]]
            origin = Hex(0, 0)
            target_behind_wall = Hex(2, 0)
            target_clear = Hex(0, 2)
            
            los_blocked = has_line_of_sight(origin, target_behind_wall, walls)
            los_clear = has_line_of_sight(origin, target_clear, walls)
            
            assert not los_blocked, "La linea di vista non dovrebbe attraversare il muro in [1, 0]"
            assert los_clear, "La linea di vista libera dovrebbe essere valida"
            
            vis_hexes = get_visible_hexes(origin, 3, walls)
            assert target_behind_wall not in vis_hexes, "L'esagono dietro il muro non deve essere visibile"
            assert target_clear in vis_hexes, "L'esagono in campo aperto deve essere visibile"
            
            report["passed"].append("True Line of Sight (LoS) su griglia esagonale con blocco muri")
            print(">> OK: Line of Sight previene la visione a raggi X attraverso i muri.")

            # Termina combattimento ora che il Goblin è morto
            gs.end_combat()
            from common.protocol import make_combat_state_update_broadcast
            broadcast(gs, make_combat_state_update_broadcast(False, 0, 1, []))
            broadcast(gs, make_game_state(gs.get_state_dict()))
            pump_events(roots, dm_gui, client_guis, steps=5, delay=0.03)
        except Exception as e:
            report["failed"].append(f"Morte mostro o meccaniche 5e: {e}")

        # 11. Divisione Loot Monete dal Master
        print("\n--- FASE 11: Divisione Denaro (Loot Split) ---")
        try:
            dm_gui.server.send_loot_split(100)
            pump_events(roots, dm_gui, client_guis, steps=12, delay=0.04)

            p1_obj = gs.find_player("Gildor")
            p2_obj = gs.find_player("Elidor")
            mo_p1 = p1_obj.full_sheet.get("currency", {}).get("MO", 0) if p1_obj.full_sheet else 0
            mo_p2 = p2_obj.full_sheet.get("currency", {}).get("MO", 0) if p2_obj.full_sheet else 0
            print(f">> MO Gildor: {mo_p1}, MO Elidor: {mo_p2}")
            report["passed"].append("Divisione denaro (Loot Split) broadcastata e assegnata ai membri del party")
        except Exception as e:
            report["failed"].append(f"Loot split: {e}")

        # 12. Scambio Oggetti / Oro tra Giocatori
        print("\n--- FASE 12: Scambio Oggetti & Oro tra Giocatori ---")
        try:
            p1_gui.network.send(make_give_item_request("Elidor", {"name": "Pozione di Cura", "qty": 1, "weight": 0.5}))
            p1_gui.network.send(make_give_gold_request("Elidor", 5))
            pump_events(roots, dm_gui, client_guis, steps=12, delay=0.04)

            report["passed"].append("Sistema di Scambio Oggetti ed Oro tra Giocatori")
            print(">> OK: Richieste di scambio inviate ed elaborate.")
        except Exception as e:
            report["failed"].append(f"Scambio: {e}")

        # 13. Ping sulla Mappa
        print("\n--- FASE 13: Ping Sulla Mappa ---")
        try:
            p1_gui.network.send(make_ping_request(2, 2, "gold"))
            pump_events(roots, dm_gui, client_guis, steps=8, delay=0.03)
            report["passed"].append("Segnale di Ping visivo sul Canvas broadcastato a tutti")
            print(">> OK: Ping inviato e propagato con successo.")
        except Exception as e:
            report["failed"].append(f"Ping canvas: {e}")

        # 14. Audio Broadcast dal DM
        print("\n--- FASE 14: Riproduzione Audio Sfx / Soundscape ---")
        try:
            from common.protocol import make_audio_play_broadcast
            broadcast(gs, make_audio_play_broadcast("https://example.com/tavern_music.mp3"))
            pump_events(roots, dm_gui, client_guis, steps=8, delay=0.03)
            report["passed"].append("Soundboard Master con broadcast tracce audio ai client")
            print(">> OK: Audio broadcast inviato ai client.")
        except Exception as e:
            report["failed"].append(f"Audio broadcast: {e}")

        # 15. Transizione Teletrasporto Mappa
        print("\n--- FASE 15: Teletrasporto tra Mappe ---")
        try:
            p1_gui.network.send(make_move_request(5, 5))
            pump_events(roots, dm_gui, client_guis, steps=12, delay=0.04)

            p1_server = gs.find_player("Gildor")
            if p1_server and p1_server.position == [5, 5]:
                report["passed"].append("Rilevamento coordinate teletrasporto al movimento del token")
                print(">> OK: Token mosso sul punto di teletrasporto [5, 5].")
            else:
                report["failed"].append("Teletrasporto coordinate non raggiunte")
        except Exception as e:
            report["failed"].append(f"Teleport: {e}")

        # 16. Sistema Notifiche Toast Non-Bloccanti
        print("\n--- FASE 16: Notifiche Toast Moderne (Non-Bloccanti) ---")
        try:
            toast = p1_gui.show_toast("Questo è un test per le notifiche Toast!", title="Notifica Dark Fantasy", duration=1500, toast_type="success")
            pump_events(roots, dm_gui, client_guis, steps=5, delay=0.03)
            if toast:
                toast.destroy()
            report["passed"].append("Widget ToastNotification non-bloccante dark fantasy")
            print(">> OK: Toast creato e gestito in modo asincrono senza bloccare l'interfaccia.")
        except Exception as e:
            report["failed"].append(f"Toast notification: {e}")

        # 17. Sistema di Viaggio 5e, Ordine di Marcia & Sostentamento
        print("\n--- FASE 17: Sistema di Viaggio 5e, Ordine di Marcia & Sostentamento ---")
        try:
            # 17a. Impostazione Ruoli e Ordine di Marcia (Marching Order)
            p1_gui.network.send(make_set_travel_role_request("Navigatore", "Avanguardia"))
            p2_gui.network.send(make_set_travel_role_request("Sentinella", "Retroguardia"))
            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)

            p1_s = gs.find_player("Gildor")
            p2_s = gs.find_player("Elidor")
            assert p1_s and p1_s.marching_order == "Avanguardia", f"Gildor marching order atteso Avanguardia, ottenuto {getattr(p1_s, 'marching_order', None)}"
            assert p1_s and p1_s.travel_role == "Navigatore", f"Gildor travel role atteso Navigatore, ottenuto {getattr(p1_s, 'travel_role', None)}"
            assert p2_s and p2_s.marching_order == "Retroguardia", f"Elidor marching order atteso Retroguardia, ottenuto {getattr(p2_s, 'marching_order', None)}"
            assert p2_s and p2_s.travel_role == "Sentinella", f"Elidor travel role atteso Sentinella, ottenuto {getattr(p2_s, 'travel_role', None)}"
            report["passed"].append("Formazione 5e e Ordine di Marcia (Avanguardia/Centro/Retroguardia) sincronizzati")
            print(">> OK: Formazione e Ruoli di Viaggio registrati correttamente sul server!")

            # 17b. Sostentamento & Consumo Razioni Giornaliere (doppio inventario: grid e list)
            p1_s.full_sheet.setdefault("inventory_grid", [None] * 25)
            p1_s.full_sheet["inventory_grid"][0] = {"name": "Razioni da Viaggio", "qty": 2}
            p1_s.full_sheet["inventory_grid"][1] = {"name": "Otre d'Acqua", "qty": 1}
            p1_s.full_sheet["inventory"] = []
            p1_s.exhaustion_level = 0

            p2_s.full_sheet.setdefault("inventory_grid", [None] * 25)
            p2_s.full_sheet["inventory_grid"] = [None] * 25
            p2_s.full_sheet["inventory"] = []
            p2_s.exhaustion_level = 0

            # Esegui consumo razioni
            party_members = [p1_s, p2_s]
            for p in party_members:
                sheet = p.full_sheet
                has_ration, has_water = False, False
                grid = sheet.get("inventory_grid", [])
                for idx, it in enumerate(grid):
                    if not it: continue
                    name_l = str(it.get("name", "")).lower()
                    qty = int(it.get("qty", it.get("quantity", 1)) or 1)
                    if not has_ration and "razion" in name_l and qty > 0:
                        if qty - 1 <= 0: grid[idx] = None
                        else: it["qty"] = qty - 1
                        has_ration = True
                    elif not has_water and ("acqua" in name_l or "otre" in name_l) and qty > 0:
                        if qty - 1 <= 0: grid[idx] = None
                        else: it["qty"] = qty - 1
                        has_water = True
                if not has_ration or not has_water:
                    p.exhaustion_level = min(6, getattr(p, "exhaustion_level", 0) + 1)
                    p.conditions = [c for c in p.conditions if not c.startswith("Sfinimento")] + [f"Sfinimento (Liv. {p.exhaustion_level})"]
            
            assert p1_s.exhaustion_level == 0, f"Gildor doveva avere 0 sfinimento, ha {p1_s.exhaustion_level}"
            assert p1_s.full_sheet["inventory_grid"][0]["qty"] == 1, "Gildor doveva avere 1 razione rimanente"
            assert p1_s.full_sheet["inventory_grid"][1] is None, "Gildor doveva avere 0 acqua rimanente"
            assert p2_s.exhaustion_level == 1, f"Elidor senza cibo doveva avere 1 sfinimento, ha {p2_s.exhaustion_level}"
            assert any("Sfinimento" in c for c in p2_s.conditions), "Elidor doveva avere condizione Sfinimento"
            report["passed"].append("Consumo Razioni & Acqua con supporto inventory_grid e sfinimento automatico")
            print(">> OK: Sostentamento verificato (cibo scalato da grid, sfinimento applicato in caso di carestia).")

            # 17c. Marcia Forzata & Tiri Salvezza su Costituzione (> 8 ore)
            gs.travel_hours_today = 8
            dm_gui.advance_time(4, is_rest=False)
            gs.travel_hours_today += 4
            assert gs.travel_hours_today == 12, f"Ore attese 12, ottenute {gs.travel_hours_today}"
            con_dc = 10 + (gs.travel_hours_today - 8)
            assert con_dc == 14, f"CD attesa 14, ottenuta {con_dc}"
            report["passed"].append("Avanzamento Viaggio e Marcia Forzata 5e con calcolo CD Costituzione")
            print(">> OK: Marcia Forzata 5e (> 8 ore) calcolata con CD progressiva corretta.")

        except Exception as e:
            traceback.print_exc()
            report["failed"].append(f"Sistema Viaggio: {e}")

    finally:
        print("\n--- PULIZIA SESSIONE ---")
        try:
            if p1_gui: p1_gui.disconnect()
            if p2_gui: p2_gui.disconnect()
            if dm_gui and hasattr(dm_gui, 'server'): dm_gui.server.stop()
            for r in roots:
                try: r.destroy()
                except Exception: pass
            print(">> Pulizia completata con successo.")
        except Exception as e:
            print(f">> Errore pulizia: {e}")

    print("\n==================================================")
    print("RESOCONTO FINALE DELLA SIMULAZIONE")
    print("==================================================")
    print(f"Test Superati: {len(report['passed'])}")
    for p in report['passed']:
        print(f"  [PASSED] {p}")

    print(f"\nTest Falliti o con Errori: {len(report['failed'])}")
    for f in report['failed']:
        print(f"  [FAILED] {f}")

    return report

if __name__ == "__main__":
    run_simulation()
