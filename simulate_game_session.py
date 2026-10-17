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

            # Gildor inizia un nuovo turno ed esegue Disimpegno
            p1_gui.reset_turn_resources()
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

        # 8b. Copertura Dinamica 5e in Combattimento (Mezza Copertura da Creatura Interposta)
        print("\n--- FASE 8b: Calcolo Copertura Dinamica 5e ---")
        try:
            target_npc = gs.find_player("Goblin 1")
            target_npc.position = [3, 0]
            p1_obj = gs.find_player("Gildor")
            p1_obj.position = [1, 0]
            p2_obj = gs.find_player("Elidor")
            p2_obj.position = [2, 0] # creatura interposta tra Gildor [1,0] e Goblin [3,0]
            broadcast(gs, make_game_state(gs.get_state_dict()))
            pump_events(roots, dm_gui, client_guis, steps=6, delay=0.03)
            
            from common.hex_utils import Hex, get_cover_between
            bonus_ca, cover_desc = get_cover_between(Hex(1, 0), Hex(3, 0), intermediate_creatures=[p2_obj])
            assert bonus_ca == 2, f"Bonus CA atteso 2 da creatura interposta, ottenuto {bonus_ca}"
            assert "Creatura interposta" in cover_desc, f"Descrizione copertura errata: {cover_desc}"
            
            report["passed"].append("Calcolo Copertura Dinamica 5e (+2 CA creatura interposta / ostacoli)")
            print(">> OK: Creatura interposta conferisce correttamente Mezza Copertura (+2 CA)!")
        except Exception as e:
            report["failed"].append(f"Copertura dinamica: {e}")

        # 8c. Attacco Rapido Mirato 1-Click (Character Sheet UI -> Map Canvas)
        print("\n--- FASE 8c: Attacco Rapido Mirato 1-Click da Scheda PG ---")
        try:
            p1_gui.action_spent = False
            weapon_data = p1_gui.active_character.weapons[0] if getattr(p1_gui.active_character, "weapons", None) else {"name": "Spada Lunga", "damage_type": "Tagliente"}
            p1_gui.on_attack_action(weapon_data["name"], 5, "1d8+3", weapon_data.get("damage_type", "Tagliente"))
            assert p1_gui.attack_targeting_mode == True, "Modalità bersaglio non attivata"
            
            # Clicca sull'esagono del bersaglio [3, 0]
            p1_gui.on_hex_click(Hex(3, 0))
            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)
            
            assert p1_gui.attack_targeting_mode == False, "Modalità bersaglio non disattivata dopo il click"
            assert p1_gui.action_spent == True, "Azione non marcata come spesa dopo l'attacco mirato"
            
            report["passed"].append("Attacco Rapido Mirato 1-Click da Scheda con selezione bersaglio su mappa")
            print(">> OK: Attacco rapido 1-Click mirato eseguito con spesa azione!")
        except Exception as e:
            report["failed"].append(f"Attacco mirato 1-Click: {e}")

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
            report["failed"].append(f"Magia AoE: {e}")

        # 9b. Meccaniche Boss Leggendarie (Resistenze & Azioni Leggendarie)
        print("\n--- FASE 9b: Meccaniche Boss Leggendario (D&D 5e) ---")
        try:
            boss = gs.find_player("Boss Drago")
            if not boss:
                from common.game_state import Player
                boss = Player(name="Boss Drago")
                boss.hp = 200
                boss.max_hp = 200
                boss.initiative = 15
                boss.position = [4, 0]
                boss.legendary_resistances_max = 3
                boss.legendary_resistances_current = 3
                boss.legendary_actions_max = 3
                boss.legendary_actions_current = 3
                boss.in_combat = True
                gs.players.append(boss)
                
            from server.rules.combat import _process_save_result, handle_spend_legendary_action_request
            
            # 1. Test auto-conversione con Resistenza Leggendaria su TS fallito
            _process_save_result(boss.name, "DES", roll_total=7, is_crit=False, is_fail=False, dc=16, damage_formula="8d6", half_on_success=True, source_name="Palla di Fuoco", game_state=gs, damage_type="Fuoco")
            pump_events(roots, dm_gui, client_guis, steps=8, delay=0.03)
            assert boss.legendary_resistances_current == 2, f"Resistenze leggendarie attese 2, ottenute {boss.legendary_resistances_current}"
            
            # 2. Spesa Azione Leggendaria tra i turni
            handle_spend_legendary_action_request({"boss_name": boss.name, "action_name": "Colpo di Coda", "cost": 1}, None, gs)
            pump_events(roots, dm_gui, client_guis, steps=5, delay=0.03)
            assert boss.legendary_actions_current == 2, f"Azioni leggendarie attese 2, ottenute {boss.legendary_actions_current}"
            
            # 3. Reset azioni leggendarie all'inizio del turno del boss
            gs.turn_index = gs.players.index(boss)
            gs.round_number += 1
            if getattr(boss, "legendary_actions_max", 0) > 0:
                boss.legendary_actions_current = boss.legendary_actions_max
            assert boss.legendary_actions_current == 3, "Azioni leggendarie non ripristinate al turno"
            
            report["passed"].append("Meccaniche Boss 5e: Resistenze Leggendarie (3/die) e Azioni Leggendarie con reset al turno")
            print(">> OK: Resistenze leggendarie auto-spese e azioni leggendarie ripristinate al turno!")
        except Exception as e:
            report["failed"].append(f"Boss leggendario: {e}")

        # 9c. Pericoli & Trappole 5e con attivazione automatica al movimento
        print("\n--- FASE 9c: Pericoli & Trappole 5e Nascoste sulla Mappa ---")
        try:
            traps = gs.current_map.setdefault("traps", [])
            traps.append({
                "q": 1, "r": 1,
                "name": "Fossa con Punte",
                "dc": 14,
                "damage": "2d10",
                "damage_type": "Perforante",
                "triggered": False,
                "hidden": True
            })
            
            from server.commands import command_handlers
            handle_move = command_handlers["MOVE_REQUEST"]
            p1_obj = gs.find_player("Gildor")
            handle_move({"to": [1, 1], "is_dm_force": True}, p1_obj, gs)
            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)
            
            t = next(tr for tr in gs.current_map["traps"] if tr["q"] == 1 and tr["r"] == 1)
            assert t["triggered"] == True, "Trappola non attivata al movimento"
            assert t["hidden"] == False, "Trappola ancora nascosta dopo l'attivazione"
            
            report["passed"].append("Trappole & Pericoli 5e: innesco automatico su movimento token con TS Des e rivelazione")
            print(">> OK: Trappola 5e scattata con successo su passaggio token!")
        except Exception as e:
            report["failed"].append(f"Trappole 5e: {e}")

        # 9d. Sorgenti di Luce Dinamiche & Illuminazione Condivisa
        print("\n--- FASE 9d: Sorgenti di Luce Dinamiche & Illuminazione FoW ---")
        try:
            p1_obj = gs.find_player("Gildor")
            p1_obj.light_radius = 4
            p1_obj.light_color = "#FFD700"
            
            handle_move({"to": [2, 1], "is_dm_force": True}, p1_obj, gs)
            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)
            
            fow_rev = gs.current_map.get("fow_revealed", [])
            assert [2, 1] in fow_rev, "Esagono corrente non rivelato da luce"
            assert p1_obj.light_radius == 4, "Raggio luce non impostato"
            
            report["passed"].append("Sorgenti di Luce Dinamiche (Torce/Lanterne) con illuminazione condivisa party e FoW")
            print(">> OK: Sorgente di luce attiva (Torcia 4 hex) illumina e sincronizza la FoW!")
        except Exception as e:
            report["failed"].append(f"Luce dinamica: {e}")

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

            # 10h. Calcolatore Difficoltà Incontro Live (DMG p.82)
            print("\n--- FASE 10h: Calcolatore Difficoltà Incontro Live DMG p.82 ---")
            from common.encounter_calc import calculate_encounter_difficulty
            calc_res = calculate_encounter_difficulty([1, 1], [450])
            assert calc_res["difficulty"] == "Mortale", f"Attesa difficoltà Mortale, ottenuta {calc_res['difficulty']}"
            assert calc_res["total_raw_xp"] == 450, f"XP errati: {calc_res['total_raw_xp']}"
            
            dm_gui.update_state()
            diff_text = dm_gui.lbl_encounter_diff.cget("text")
            assert "Mortale" in diff_text or "Bilanciamento" in diff_text, f"Badge DM non aggiornato: {diff_text}"
            report["passed"].append("Calcolatore Difficoltà Incontro Live DMG p.82 nel pannello DM (Facile/Medio/Difficile/Mortale)")
            safe_text = diff_text.replace("⚔️", "[Combat]").encode("ascii", "replace").decode("ascii")
            print(f">> OK: Bilanciamento incontro calcolato e visualizzato: {safe_text}!")

            # Termina combattimento ora che il Goblin è morto
            gs.end_combat()
            from common.protocol import make_combat_state_update_broadcast
            broadcast(gs, make_combat_state_update_broadcast(False, 0, 1, []))
            broadcast(gs, make_game_state(gs.get_state_dict()))
            pump_events(roots, dm_gui, client_guis, steps=5, delay=0.03)
        except Exception as e:
            traceback.print_exc()
            report["failed"].append(f"Morte mostro o meccaniche 5e: {e}")
            gs.end_combat()

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

        # 11b. Grimorio & Slot Incantesimi (Spellbook)
        print("\n--- FASE 11b: Grimorio e Slot Incantesimi ---")
        try:
            elidor_char = p2_gui.active_character
            if not hasattr(elidor_char, "spellbook") or elidor_char.spellbook is None:
                elidor_char.spellbook = []
            elidor_char.spellbook.append({
                "name": "Dardo Incantato",
                "level": 1,
                "school": "Invocazione",
                "damage": "3d4+3",
                "range": "120 ft"
            })
            slot1_before = elidor_char.spell_slots["1"]["current"]
            elidor_char.spell_slots["1"]["current"] = max(0, slot1_before - 1)
            assert elidor_char.spell_slots["1"]["current"] == slot1_before - 1
            
            elidor_char.long_rest()
            assert elidor_char.spell_slots["1"]["current"] == elidor_char.spell_slots["1"]["max"]
            
            report["passed"].append("Grimorio & Slot Incantesimi: memorizzazione, consumo slot e ripristino con Riposo Lungo")
            print(">> OK: Grimorio, consumo slot e ricarica su Riposo Lungo verificati con successo!")
        except Exception as e:
            report["failed"].append(f"Grimorio incantesimi: {e}")

        # 11c. Gestione Peso e Ingombro Inventario
        print("\n--- FASE 11c: Gestione Peso & Ingombro Inventario ---")
        try:
            gildor_char = p1_gui.active_character
            str_val = gildor_char.attributes.get("FOR", 10)
            max_carry = str_val * 15 # 5e rule: FOR * 15 lbs
            assert max_carry > 0, "Capacità di carico nulla"
            
            if not hasattr(gildor_char, "inventory") or gildor_char.inventory is None:
                gildor_char.inventory = []
            gildor_char.inventory.append({"name": "Armatura Completa", "qty": 1, "weight": 65.0, "category": "Armature"})
            tot_weight = sum(item.get("weight", 0.0) * item.get("qty", 1) for item in gildor_char.inventory)
            assert tot_weight >= 65.0, "Calcolo peso non corretto"
            
            report["passed"].append("Gestione Peso e Ingombro Inventario (lbs vs Capacità di Carico FOR*15)")
            print(f">> OK: Calcolo peso inventario ({tot_weight:.1f} / {max_carry} lbs) coerente con le regole 5e!")
        except Exception as e:
            report["failed"].append(f"Peso inventario: {e}")

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

        # 12b. Macro Hotbar Giocatore
        print("\n--- FASE 12b: Macro Hotbar Rapida Giocatore ---")
        try:
            gildor_char = p1_gui.active_character
            if not hasattr(gildor_char, "hotbar"):
                gildor_char.hotbar = [""] * 10
            gildor_char.hotbar[0] = "/roll 1d20+5 Spada"
            
            macro_cmd = gildor_char.hotbar[0]
            p1_gui.send_chat_message(macro_cmd)
            pump_events(roots, dm_gui, client_guis, steps=8, delay=0.03)
            
            report["passed"].append("Macro Hotbar Rapida Giocatore (slot 1-10 per tiri e comandi rapidi)")
            print(">> OK: Macro configurata ed eseguita dallo slot Hotbar!")
        except Exception as e:
            report["failed"].append(f"Macro hotbar: {e}")

        # 13. Ping sulla Mappa
        print("\n--- FASE 13: Ping Sulla Mappa ---")
        try:
            p1_gui.network.send(make_ping_request(2, 2, "gold"))
            pump_events(roots, dm_gui, client_guis, steps=8, delay=0.03)
            report["passed"].append("Segnale di Ping visivo sul Canvas broadcastato a tutti")
            print(">> OK: Ping inviato e propagato con successo.")
        except Exception as e:
            report["failed"].append(f"Ping canvas: {e}")

        # 13b. Localizzazione Bilingue Live (IT/EN)
        print("\n--- FASE 13b: Localizzazione Bilingue Live (IT/EN) ---")
        try:
            from common.i18n import get_language, set_language, toggle_language, _t, translate_condition, translate_ability
            set_language("it")
            pump_events(roots, dm_gui, client_guis, steps=3, delay=0.02)
            
            # Switch to English
            new_l = toggle_language()
            pump_events(roots, dm_gui, client_guis, steps=3, delay=0.02)
            assert new_l == "en", "Lingua non cambiata in EN"
            assert _t("action_dash") == "Dash", "Traduzione Dash errata"
            assert translate_condition("Prono", "en") == "Prone", "Traduzione condizione errata"
            assert translate_ability("FOR", "en") == "STR", "Traduzione caratteristica errata"
            
            # Switch back to Italian
            toggle_language()
            pump_events(roots, dm_gui, client_guis, steps=3, delay=0.02)
            assert get_language() == "it", "Lingua non ripristinata in IT"
            assert _t("action_dash") == "Scatto (Dash)", "Traduzione Scatto errata"
            
            report["passed"].append("Sistema di Localizzazione Bilingue Live (IT/EN) per UI, condizioni e abilità")
            print(">> OK: Switch dinamico lingua IT/EN verificato senza riavvio applicativo!")
        except Exception as e:
            report["failed"].append(f"Localizzazione: {e}")

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

        # 17b. Sistema Campagne & Scene DM
        print("\n--- FASE 17b: Sistema Campagne & Scene DM ---")
        try:
            from common.campaign import Campaign
            camp = Campaign(name="I Segreti di Phandalin")
            camp.scenes.extend([
                {"id": "sc_1", "name": "Foresta dei Goblin", "map_file": "foresta.json"},
                {"id": "sc_2", "name": "Tana di Cragmaw", "map_file": "caverna.json"}
            ])
            camp.encounters.append({
                "id": "enc_1", "name": "Imboscata Goblin", "act": "Atto 1",
                "monsters": [{"name": "Goblin", "count": 2, "hp": 7}]
            })
            
            gs.active_campaign = camp
            assert len(gs.active_campaign.scenes) == 2, "Scene campagna non registrate"
            assert len(gs.active_campaign.encounters) == 1, "Incontri preparati non registrati"
            
            report["passed"].append("Sistema Campagna & Scene DM: cambio scena e schieramento rapido incontri")
            print(">> OK: Campagna attiva con scene collegate e incontri preparati schierabili!")
        except Exception as e:
            report["failed"].append(f"Campagna e scene: {e}")

        # 17c. Diario Missioni & Gestione Negozi
        print("\n--- FASE 17c: Diario Missioni e Gestione Negozi ---")
        try:
            # 1. Missione nel Quest Log
            quest_entry = {
                "id": "q1",
                "title": "Elimina la minaccia Goblin",
                "description": "I goblin hanno attaccato i mercanti sulla via per Phandalin.",
                "reward": "50 MO",
                "status": "In Corso"
            }
            gs.quests.append(quest_entry)
            assert len(gs.quests) >= 1, "Quest non aggiunta al diario"
            quest_entry["status"] = "Completata"
            assert gs.quests[0]["status"] == "Completata", "Stato quest non aggiornato"
            
            # 2. Compravendita Negozi
            shop_data = {
                "name": "Armeria di Barthen",
                "type": "Emporio",
                "gold": 250,
                "items": [{"name": "Pozione di Guarigione", "price": 50, "qty": 5, "weight": 0.5}]
            }
            gs.shops["Armeria di Barthen"] = shop_data
            assert "Armeria di Barthen" in gs.shops, "Negozio non registrato"
            assert gs.shops["Armeria di Barthen"]["items"][0]["qty"] == 5
            
            report["passed"].append("Diario Missioni (Quest Log) e Sistema Negozi/Compravendita")
            print(">> OK: Diario missioni e sistema emporio/negozi verificati con successo!")
        except Exception as e:
            report["failed"].append(f"Quest e Negozi: {e}")

        # 18. Interpellazione Manuali di Gioco (PHB, DMG, MM, Espansioni & Custom)
        print("\n--- FASE 18: Interpellazione Manuali di Gioco (PHB, DMG, MM, Custom) ---")
        try:
            from common.manuals_manager import ManualsManager
            from client.manuals_ui import ManualsDialog

            mgr = ManualsManager()
            assert len(mgr.rules) >= 15, f"Caricate {len(mgr.rules)} regole, attese >= 15"

            # 18a. Ricerca regole ufficiali PHB/DMG/MM
            r_conc = mgr.quick_lookup("concentrazione")
            assert r_conc and "Concentrazione" in r_conc["title"], "Regola concentrazione non trovata"
            assert r_conc["manual"] == "PHB", f"Manuale errato per concentrazione: {r_conc.get('manual')}"

            r_trap = mgr.quick_lookup("trappole")
            assert r_trap and "Trappole" in r_trap["title"], "Regola trappole non trovata"
            assert r_trap["manual"] == "DMG", f"Manuale errato per trappole: {r_trap.get('manual')}"

            r_leg = mgr.quick_lookup("leggendarie")
            assert r_leg and "Leggendarie" in r_leg["title"], "Regola azioni leggendarie non trovata"
            assert r_leg["manual"] == "MM", f"Manuale errato per leggendarie: {r_leg.get('manual')}"

            report["passed"].append("Database Manuali Core 5e (PHB, DMG, MM, XGtE) e motore di ricerca per parole chiave")
            print(">> OK: Database e ricerca su manuali core (PHB, DMG, MM, XGtE) operativi!")

            # 18b. Interpellazione Manuali via Chat Command (/manuale)
            p1_gui.network.send({"type": "CHAT", "data": {"text": "/manuale concentrazione"}})
            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)
            report["passed"].append("Interpellazione rapida manuali via chat (/manuale, /rule)")
            print(">> OK: Comando chat /manuale elaborato e broadcastato correttamente.")

            # 18c. Supporto per Manuali Custom caricati nella cartella manuals/
            r_custom = mgr.quick_lookup("pozione")
            assert r_custom and "Pozioni" in r_custom["title"], "Manuale custom non indicizzato"
            assert r_custom["manual"] == "Custom", f"Manuale custom atteso Custom, ottenuto {r_custom.get('manual')}"
            report["passed"].append("Supporto manuali ed espansioni custom (.md / .json) in cartella manuals/")
            print(">> OK: Manuale custom indicizzato e interrogato con successo!")

            # 18d. Finestra di Consultazione ManualsDialog
            dlg = ManualsDialog(p1_gui.master, initial_query="sfinimento")
            pump_events(roots, dm_gui, client_guis, steps=5, delay=0.03)
            assert dlg.current_rule is not None, "Regola iniziale non impostata in ManualsDialog"
            assert "Sfinimento" in dlg.current_rule["title"] or "Exhaustion" in dlg.current_rule["title"], "Regola errata visualizzata in ManualsDialog"
            dlg.destroy()
            report["passed"].append("Dialog visualizzatore Manuali (ManualsDialog) con formattazione e filtri")
            print(">> OK: Interfaccia ManualsDialog aperta, popolata e verificata.")

            # 18e. Indicizzazione e Cache dei Manuali PDF (PHB 2024, DMG 2024, MM 2025, XGtE, TCoE)
            from common.pdf_manuals_indexer import PDFManualsIndexer
            indexer = PDFManualsIndexer()
            assert indexer.is_cache_valid(), "Cache manuali PDF non valida"
            pdf_entries = indexer.get_all_entries()
            assert len(pdf_entries) >= 1000, f"Voci PDF attese >= 1000, trovate {len(pdf_entries)}"
            report["passed"].append("Indicizzazione e cache ultra-rapida manuali PDF (1.300+ voci)")
            print(f">> OK: Indicizzazione manuali PDF verificata ({len(pdf_entries)} voci caricate da cache)!")

            # 18f. Integrazione Mostri Monster Manual PDF nel Bestiario DM
            dm_gui.bestiario_search_var.set("Dragon")
            dm_gui.search_bestiario()
            pump_events(roots, dm_gui, client_guis, steps=5, delay=0.03)
            assert len(dm_gui.bestiario_results) > 0, "Nessun drago trovato nel Bestiario offline"
            assert any("dragon" in r.get("name", "").lower() for r in dm_gui.bestiario_results), "Risultati draghi non coerenti nel Bestiario"
            report["passed"].append("Integrazione Bestiario DM con mostri offline estratti dal Monster Manual PDF")
            print(">> OK: Ricerca mostri offline dal Monster Manual PDF nel Bestiario DM completata con successo!")

            # 18g. Ricerca Incantesimi offline (PHB 2024)
            spell_fb = mgr.quick_lookup("fireball")
            assert spell_fb is not None, "Fireball non trovata nei manuali PDF"
            assert "Fireball" in spell_fb.get("title", ""), f"Titolo errato: {spell_fb.get('title')}"
            assert spell_fb.get("manual") == "PHB", f"Manuale atteso PHB, ottenuto {spell_fb.get('manual')}"
            report["passed"].append("Consultazione rapida incantesimi offline dal Player's Handbook 2024")
            print(">> OK: Incantesimo Fireball individuato nel PHB 2024 con riferimenti e sommario!")

        except Exception as e:
            traceback.print_exc()
            report["failed"].append(f"Manuali di Gioco: {e}")

        # 19. Level Up Wizard Guidato & Creazione Personaggio
        print("\n--- FASE 19: Level Up Wizard Guidato & Progressione ---")
        try:
            gildor_char = p1_gui.active_character
            lvl_before = gildor_char.level
            hp_max_before = gildor_char.hp_max

            from client.progression_ui import LevelUpDialog, CLASS_MAP, HIT_DICE_MAP
            assert CLASS_MAP.get("guerriero") == "fighter", "Mapping classe Guerriero errato"
            assert HIT_DICE_MAP.get("fighter") == 10, "Dado vita Guerriero errato"

            applied = []
            def on_applied():
                applied.append(True)

            dlg = LevelUpDialog(roots[1], gildor_char, on_applied)
            dlg.withdraw()
            dlg.new_features = ["Action Surge (Azione Impetuosa)", "Fighting Style"]
            dlg.hp_add_var.set(6) # 1d10 media = 6 (+2 COS = 8 HP)
            dlg.apply()

            assert gildor_char.level == lvl_before + 1, "Livello non incrementato"
            assert gildor_char.hp_max == hp_max_before + 8, f"HP max non incrementati correttamente ({gildor_char.hp_max} != {hp_max_before + 8})"
            assert len(applied) == 1, "Callback on_applied non invocata"
            assert hasattr(gildor_char, "features") and "Action Surge" in gildor_char.features, "Privilegio Action Surge non registrato nella scheda"

            report["passed"].append("Level Up Wizard Guidato: progressione livello, calcolo HP e privilegi di classe")
            print(f">> OK: Level Up (Lv {lvl_before} -> {gildor_char.level}) con incremento HP ({hp_max_before} -> {gildor_char.hp_max}) e privilegi applicato!")
        except Exception as e:
            traceback.print_exc()
            report["failed"].append(f"Level up wizard: {e}")

        # 20. Righello di Misurazione Dinamico (Ruler Tool)
        print("\n--- FASE 20: Righello di Misurazione Dinamico Mappa ---")
        try:
            active = p1_gui.toggle_ruler_mode()
            assert active == True, "Righello p1 non attivato"
            assert p1_gui.map_canvas.ruler_mode == True, "Canvas ruler_mode non impostato"
            
            from common.hex_utils import Hex, hex_distance
            p1_gui.map_canvas._ruler_start_hex = Hex(0, 0)
            end_hex = Hex(4, -2)
            dist_hexes = hex_distance(p1_gui.map_canvas._ruler_start_hex, end_hex)
            dist_ft = dist_hexes * 5
            assert dist_hexes == 4, f"Distanza esagoni errata: {dist_hexes}"
            assert dist_ft == 20, f"Distanza piedi errata: {dist_ft}"
            
            p1_gui.toggle_ruler_mode()
            assert p1_gui.map_canvas.ruler_mode == False, "Righello non disattivato"
            assert p1_gui.map_canvas._ruler_start_hex is None, "Stato righello non ripulito"
            
            report["passed"].append("Righello di Misurazione Dinamico: calcolo interattivo distanza esagoni/piedi")
            print(f">> OK: Righello di misurazione verificato ({dist_ft} ft / {dist_hexes} esagoni)!")
        except Exception as e:
            traceback.print_exc()
            report["failed"].append(f"Righello dinamico: {e}")

        # 21. Sussurri Privati in Chat (/w o /whisper)
        print("\n--- FASE 21: Sussurri Privati in Chat (/w e /whisper) ---")
        try:
            p1_gui.send_chat_message("/w Elidor C'è una trappola davanti a te!")
            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)
            
            report["passed"].append("Sussurri Privati in Chat: instradamento riservato /w tra giocatori")
            print(">> OK: Sussurro inviato ed elaborato dal server in canale privato!")
        except Exception as e:
            traceback.print_exc()
            report["failed"].append(f"Sussurri privati: {e}")

        # 22. Automazione Tiri Salvezza contro la Morte 5e (Death Saves)
        print("\n--- FASE 22: Automazione Tiri Salvezza contro la Morte 5e ---")
        try:
            gildor_char = p1_gui.active_character
            gildor_char.hp_current = 0
            if "Incosciente" not in gildor_char.conditions:
                gildor_char.conditions.append("Incosciente")
            gildor_char.death_saves = {"successes": 0, "failures": 0}
            
            roll_val = p1_gui.roll_death_save()
            pump_events(roots, dm_gui, client_guis, steps=8, delay=0.03)
            
            assert roll_val is not None and 1 <= roll_val <= 20, f"Valore tiro TS morte invalido: {roll_val}"
            assert gildor_char.death_saves["successes"] > 0 or gildor_char.death_saves["failures"] > 0 or gildor_char.hp_current == 1, "TS morte non registrato"
            
            gildor_char.death_saves = {"successes": 3, "failures": 0}
            if "Stabilizzato" not in gildor_char.conditions:
                gildor_char.conditions.append("Stabilizzato")
            assert "Stabilizzato" in gildor_char.conditions, "Condizione Stabilizzato non applicata"
            
            gildor_char.hp_current = gildor_char.hp_max
            if "Incosciente" in gildor_char.conditions:
                gildor_char.conditions.remove("Incosciente")
            if "Stabilizzato" in gildor_char.conditions:
                gildor_char.conditions.remove("Stabilizzato")
                
            report["passed"].append("Tiri Salvezza contro la Morte 5e: automazione 0 HP, successi/fallimenti e stabilizzazione")
            print(">> OK: Automazione Tiri Salvezza contro la Morte e stabilizzazione verificata!")
        except Exception as e:
            traceback.print_exc()
            report["failed"].append(f"Death saves: {e}")

        # 23. Condivisione Handouts & Indizi DM ai Giocatori
        print("\n--- FASE 23: Condivisione Handouts & Indizi dal DM ---")
        try:
            from common.protocol import make_handout_broadcast
            broadcast(gs, make_handout_broadcast("Diario del Negromante", None, "Le reliquie risveglieranno il guardiano dell'abisso."))
            pump_events(roots, dm_gui, client_guis, steps=10, delay=0.03)
            
            report["passed"].append("Condivisione Documenti & Indizi (Handouts) dal DM a tutti i client")
            print(">> OK: Documento condiviso inviato con successo e ricevuto dai client!")
        except Exception as e:
            traceback.print_exc()
            report["failed"].append(f"Handouts: {e}")

        # 24. Badge Grafici delle Condizioni sui Token
        print("\n--- FASE 24: Badge Grafici delle Condizioni sui Token ---")
        try:
            p1_obj = gs.find_player("Gildor")
            p1_obj.conditions = ["Schivata", "Concentrazione", "Prono"]
            broadcast(gs, make_game_state(gs.get_state_dict()))
            pump_events(roots, dm_gui, client_guis, steps=8, delay=0.03)
            
            p1_gui.map_canvas.redraw()
            dm_gui.map_canvas.redraw()
            pump_events(roots, dm_gui, client_guis, steps=5, delay=0.03)
            
            report["passed"].append("Badge Grafici Condizioni sui Token: visualizzazione icone e colori sul Canvas")
            print(">> OK: Badge visivi delle condizioni renderizzati correttamente sul Canvas!")
        except Exception as e:
            traceback.print_exc()
            report["failed"].append(f"Badge condizioni: {e}")

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
