import sys
import os
import threading
import time
import tkinter as tk
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from server.server import DM_GUI
from client.client import ClientGUI
from client.character_manager import Character
from common.hex_utils import Hex

def test_flow():
    print("1. Avvio test E2E GUI...")
    root_server = tk.Tk()
    root_client = tk.Tk()
    
    # Hide windows during test
    root_server.withdraw()
    root_client.withdraw()
    
    server_gui = DM_GUI(root_server)
    client_gui = ClientGUI(root_client)
    
    root_server.update()
    root_client.update()
    
    dummy_char = Character("TestHero", "Guerriero")
    dummy_char.hp_max = 20
    dummy_char.hp_current = 20
    dummy_char.initiative = 10
    
    time.sleep(0.3)
    
    print("2. Eseguo connessione tramite mocking del LoginDialog...")
    with patch('client.client.LoginDialog') as MockDialog:
        instance = MockDialog.return_value
        # When wait_window is called, we just immediately set the result and return
        def fake_wait(window):
            instance.result = ("127.0.0.1", dummy_char)
            
        with patch.object(root_client, 'wait_window', fake_wait):
            client_gui.connect_to_server()
            
    for _ in range(20):
        root_server.update()
        root_client.update()
        if client_gui.is_connected and server_gui.server.game_state.find_player("TestHero"):
            break
        time.sleep(0.1)
        
    if client_gui.is_connected and server_gui.server.game_state.find_player("TestHero"):
        print("OK: Client connesso con successo")
    else:
        print("ERR: Client NON connesso o non registrato")
        sys.exit(1)
        
    print("3. Simulo avvio combattimento dal Server...")
    # Bypass the blocking dialog for E2E testing
    server_gui.server.game_state.start_combat()
    from common.protocol import make_chat_broadcast, make_game_state
    from common.network_utils import broadcast
    broadcast(server_gui.server.game_state, make_chat_broadcast("Sistema", "Inizio Combattimento! Roll Iniziativa!"))
    broadcast(server_gui.server.game_state, make_game_state(server_gui.server.game_state.get_state_dict()))
    
    for _ in range(5):
        root_server.update()
        root_client.update()
        time.sleep(0.1)
        
    if server_gui.server.game_state.combat_active:
        print("OK: Combattimento avviato sul Server")
        
    print("4. Simulo piazzamento AoE dal Client...")
    client_gui.aoe_mode = True
    client_gui.aoe_params = {"type": "sfera", "size": 3, "color": "red"}
    
    with patch('common.messagebox.messagebox.showinfo'):
        try:
            client_gui.on_hex_click(Hex(5, 5))
        except Exception as e:
            print(f'ECCEZIONE: {e}')
            client_gui.on_hex_click(Hex(5, 5))
        except Exception as e:
            print(f'ECCEZIONE IN ON_HEX_CLICK: {e}')
    
    for _ in range(10):
        root_server.update()
        root_client.update()
        time.sleep(0.1)
        
    print('Giocatori sul server:', [p.name for p in server_gui.server.game_state.players])
    aoes = server_gui.server.game_state.active_aoes
    if any(aoe["type"] == "sfera" and aoe["origin"] == [5, 5] for aoe in aoes):
        print("OK: AoE ricevuta e processata dal Server")
    else:
        print("ERR: AoE NON trovata nello stato del server! aoes=", aoes)
        sys.exit(1)
        
    print("5. Test movimento del giocatore...")
    client_gui.on_hex_click(Hex(2, 2))
    for _ in range(5):
        root_server.update()
        root_client.update()
        time.sleep(0.1)
        
    p = server_gui.server.game_state.find_player("TestHero")
    if p and p.position == [2, 2]:
        print("OK: Giocatore spostato correttamente a [2, 2]")
    else:
        print("ERR: Spostamento fallito")
        sys.exit(1)
        
    print("6. Test pulizia AoE (Pulsante DM)...")
    server_gui.btn_clear_aoe.invoke()
    for _ in range(5):
        root_server.update()
        root_client.update()
        time.sleep(0.1)
        
    if len(server_gui.server.game_state.active_aoes) == 0:
        print("OK: AoE pulita con successo dal Server e Client notificati")
    else:
        print("ERR: AoE non pulita!")
        sys.exit(1)
        
    print("7. Chiusura pulita delle socket...")
    if hasattr(client_gui, 'voice_client') and client_gui.voice_client:
        try: client_gui.voice_client.stop()
        except Exception: pass
    if hasattr(server_gui, 'voice_client') and server_gui.voice_client:
        try: server_gui.voice_client.stop()
        except Exception: pass
    if hasattr(client_gui, 'client_socket') and client_gui.client_socket:
        try: client_gui.client_socket.close()
        except Exception: pass
    server_gui.server.stop()
    
    root_client.destroy()
    root_server.destroy()
    print("\n[SUCCESSO] TUTTI I TEST PASSATI SENZA ERRORI!")
    os._exit(0)

if __name__ == "__main__":
    test_flow()

