import base64
import json
import math
import os
import queue
import tempfile
import tkinter as tk
import unittest
from unittest.mock import MagicMock, patch

from common.game_state import GameState, Player
from common.hex_utils import (
    Hex,
    get_cone_hexes,
    get_cover_between,
    get_cube_hexes,
    get_line_hexes,
    get_sphere_hexes,
    grid_distance,
    has_line_of_sight,
    hex_linedraw,
)
from common.network_utils import broadcast, resolve_map_image_data, sanitize_map_for_players
from common.protocol import (
    make_combat_state_update_broadcast,
    make_fow_update_broadcast,
    make_game_state,
    make_player_joined,
    make_player_move,
    make_player_stats_update,
)
from components.ui_components import HexMapCanvas
from server.rules.character import handle_update_full_sheet_request
from server.rules.map_interaction import (
    handle_create_aoe_request,
    handle_resolve_aoe_request,
    handle_toggle_door_request,
)
from server.rules.movement import _evaluate_creature_space_traversal, handle_move_request


class TestBattlemapFoWLoS(unittest.TestCase):
    """Test di regressione TASK-027 su Battlemap, griglie, LoS/AoE, FoW e segretezza."""

    def test_saving_throw_aoe_los_and_door_blocking(self):
        """Verifica che l'AoE con TS non vada in TypeError (4 argomenti) e rispetti muri e porte chiuse/aperte."""
        gs = GameState(queue.Queue())
        gs.current_map = {
            "grid_type": "square",
            "walls": [[2, 0]],
            "doors": [{"q": 0, "r": 2, "state": "closed", "name": "Porta Est"}],
            "hexes": [[q, r] for q in range(6) for r in range(6)],
        }
        wizard = Player("Mago", conn=object())
        wizard.position = [0, 0]
        wizard.hp = 30
        wizard.is_party_member = True

        goblin_wall = Player("GoblinMuro")
        goblin_wall.position = [3, 0]
        goblin_wall.hp = 12

        goblin_door = Player("GoblinPorta")
        goblin_door.position = [0, 3]
        goblin_door.hp = 12

        goblin_open = Player("GoblinEsposto")
        goblin_open.position = [1, 1]
        goblin_open.hp = 12

        gs.players = [wizard, goblin_wall, goblin_door, goblin_open]

        sent = []
        with patch("server.rules.map_interaction.send_message", side_effect=lambda c, m: sent.append(m)), \
             patch("server.rules.map_interaction.broadcast"):
            # Crea palla di fuoco con TS: goblin dietro muro (3,0) e dietro porta chiusa (0,3) salvati
            handle_create_aoe_request(
                {
                    "aoe_data": {
                        "type": "sfera",
                        "origin": [0, 0],
                        "size": 4,
                        "req_save": True,
                        "stat": "DES",
                        "dc": 15,
                        "dmg": "6d6",
                        "damage_type": "Fuoco",
                    }
                },
                wizard,
                gs,
            )

        # Solo wizard (o escludendo se stesso no, wizard non ha req_save solo per nemici - goblin_open colpito)
        self.assertEqual(goblin_wall.hp, 12, "Goblin dietro muro solido deve essere immune all'AoE")
        self.assertEqual(goblin_door.hp, 12, "Goblin dietro porta chiusa deve avere copertura totale")
        self.assertLess(goblin_open.hp, 12, "Goblin esposto senza ostacoli deve subire l'AoE")

        # Risolvi la stessa AoE dopo aver aperto la porta: ora goblin_door è raggiunto
        gs.current_map["doors"][0]["state"] = "open"
        hp_before = goblin_door.hp
        with patch("server.rules.map_interaction.send_message"), \
             patch("server.rules.map_interaction.broadcast"):
            handle_resolve_aoe_request({"aoe_index": 0}, wizard, gs)
        self.assertLess(goblin_door.hp, hp_before, "Con porta aperta l'AoE deve raggiungere goblin_door")

    def test_grid_geometry_parity_hex_square_and_gridless(self):
        """Verifica sfera circolare gridless, cubo, linee/coni cartesiani e porte diagonali su griglia quadra."""
        # Gridless: cerchio euclideo (3,3) escluso a raggio 3 (hypot=4.24 > 3), (3,0) incluso
        gridless_sphere = get_sphere_hexes(Hex(0, 0), 3, grid_type="none")
        self.assertIn(Hex(3, 0), gridless_sphere)
        self.assertIn(Hex(2, 2), gridless_sphere)  # hypot(2,2)=2.83 <= 3
        self.assertNotIn(Hex(3, 3), gridless_sphere)

        # Square: scatola di Chebyshev 5x5 a raggio 2
        square_sphere = get_sphere_hexes(Hex(0, 0), 2, grid_type="square")
        self.assertEqual(len(square_sphere), 25)

        # Cubo gridless resta quadrato anche se la sfera e' circolare
        gridless_cube = get_cube_hexes(Hex(0, 0), 3, grid_type="none")
        self.assertIn(Hex(3, 3), gridless_cube)

        # Linea su square verso nord-est (3,3) resta sulla diagonale q==r
        sq_line = get_line_hexes(Hex(0, 0), Hex(2, 2), length_in_hexes=4, grid_type="square")
        self.assertEqual([(h.q, h.r) for h in sq_line], [(0, 0), (1, 1), (2, 2), (3, 3)])

        # Cono su square verso destra (5,0) è simmetrico rispetto a r=+k e r=-k
        sq_cone = get_cone_hexes(Hex(0, 0), Hex(5, 0), 4, grid_type="square")
        self.assertIn(Hex(3, 1), sq_cone)
        self.assertIn(Hex(3, -1), sq_cone)

        # hex_linedraw gridless su diagonale lunga non salta passi
        gl_path = hex_linedraw(Hex(0, 0), Hex(3, 2), grid_type="gridless")
        self.assertGreaterEqual(len(gl_path), 4)
        self.assertEqual(gl_path[0], Hex(0, 0))
        self.assertEqual(gl_path[-1], Hex(3, 2))

        # get_cover_between su griglia quadra diagonale
        bonus, _ = get_cover_between(Hex(0, 0), Hex(2, 2), half_cover=[[1, 1]], grid_type="square")
        self.assertEqual(bonus, 2)

        # Porta diagonale a (1,1) interattiva su griglia quadra ma troppo lontana su griglia esagonale
        gs = GameState(queue.Queue())
        actor = Player("Ladro", conn=object())
        actor.position = [0, 0]
        gs.players = [actor]
        gs.current_map = {
            "grid_type": "square",
            "doors": [{"q": 1, "r": 1, "state": "closed", "name": "Porta Diagonale"}],
        }
        errors = []
        with patch("server.rules.map_interaction.send_message", side_effect=lambda c, m: errors.append(m)), \
             patch("server.rules.map_interaction.broadcast"):
            handle_toggle_door_request({"q": 1, "r": 1}, actor, gs)
        self.assertEqual(gs.current_map["doors"][0]["state"], "open")
        self.assertEqual(errors, [])

        gs.current_map = {
            "grid_type": "hex",
            "doors": [{"q": 1, "r": 1, "state": "closed", "name": "Porta Hex Lontana"}],
        }
        with patch("server.rules.map_interaction.send_message", side_effect=lambda c, m: errors.append(m)), \
             patch("server.rules.map_interaction.broadcast"):
            handle_toggle_door_request({"q": 1, "r": 1}, actor, gs)
        self.assertEqual(gs.current_map["doors"][0]["state"], "closed")
        self.assertEqual(len(errors), 1)

    def test_sanitize_map_and_broadcast_secrecy_comprehensive(self):
        """Verifica filtro porte segrete (q,r), trappole secret, loot FoW vuota, teleports/spawn/fow_draft e pocket dimension."""
        raw_map = {
            "grid_type": "hex",
            "walls": [[0, 1]],
            "doors": [
                {"q": 2, "r": 0, "is_secret": True, "discovered": False, "state": "secret"},
                {"q": 2, "r": 1, "is_secret": False, "state": "closed"},
            ],
            "traps": [
                {"q": 3, "r": 0, "hidden": False, "secret": True, "triggered": False, "name": "Segreta Non Scattata"},
                {"q": 4, "r": 0, "hidden": False, "secret": True, "triggered": True, "name": "Segreta Scattata", "dm_notes": "DC 18"},
            ],
            "loots": [{"q": 5, "r": 5, "gold": 999}],
            "teleports": {"6,6": "segreto.json"},
            "spawn_point": [1, 1],
            "fow_enabled": True,
            "fow_revealed": [],
            "fow_draft": [[9, 9]],
        }
        clean = sanitize_map_for_players(raw_map)
        self.assertNotIn("teleports", clean)
        self.assertNotIn("spawn_point", clean)
        self.assertNotIn("fow_draft", clean)
        self.assertEqual(clean["loots"], [], "Con fow_enabled=True e fow_revealed=[] nessun loot deve filtrare")
        self.assertEqual([d.get("q") for d in clean["doors"]], [2])
        self.assertEqual(clean["doors"][0]["r"], 1)
        self.assertIn([2, 0], clean["walls"], "Porta segreta (q,r) deve bloccare LoS/movimento come muro")
        self.assertTrue(has_line_of_sight(Hex(0, 0), Hex(3, 0), clean["walls"]) is False)
        self.assertEqual([t["name"] for t in clean["traps"]], ["Segreta Scattata"])
        self.assertNotIn("secret", clean["traps"][0])
        self.assertNotIn("dm_notes", clean["traps"][0])

        # Verifica broadcast & get_state_dict per pocket_dimension, FoW e FOW_UPDATE_BROADCAST
        gs = GameState(queue.Queue())
        gs.current_map = {
            "grid_type": "hex",
            "fow_enabled": True,
            "fow_revealed": [[0, 0]],
            "fow_draft": [[0, 0], [8, 8]],
            "walls": [],
        }
        hero = Player("Eroe", conn=object())
        hero.position = [0, 0]
        hero.is_party_member = True

        familiar = Player("Gufo")
        familiar.is_party_member = True
        familiar.is_companion = True
        familiar.in_pocket_dimension = True
        familiar.position = [0, 0]

        hidden_orc = Player("OrcoNascosto")
        hidden_orc.position = [8, 8]
        hidden_orc.is_party_member = False

        gs.players = [hero, familiar, hidden_orc]
        gs.combat_active = True
        gs.turn_index = 2  # Turno di hidden_orc

        st_player = gs.get_state_dict(is_dm=False)
        self.assertEqual([p["name"] for p in st_player["players"]], ["Eroe"])
        self.assertEqual(st_player["turn_player_name"], "Sconosciuto")

        delivered = []
        with patch("common.network_utils.send_message", side_effect=lambda c, m: delivered.append(m)):
            broadcast(gs, make_game_state(gs.get_state_dict(is_dm=True)))
            self.assertEqual([p["name"] for p in delivered[-1]["data"]["players"]], ["Eroe"])
            self.assertEqual(delivered[-1]["data"]["turn_player_name"], "Sconosciuto")

            # PLAYER_JOINED, PLAYER_MOVE, PLAYER_STATS_UPDATE su entità in FoW / pocket non devono partire
            n_before = len(delivered)
            broadcast(gs, make_player_joined(hidden_orc.to_dict()))
            broadcast(gs, make_player_move("OrcoNascosto", [8, 8]))
            broadcast(gs, make_player_stats_update("OrcoNascosto", 5, 15, 10, []))
            broadcast(gs, make_player_stats_update("Gufo", 1, 1, 12, []))
            broadcast(gs, make_combat_state_update_broadcast(True, 2, 1, [], "OrcoNascosto"))
            self.assertEqual(len(delivered), n_before + 1)  # Solo COMBAT_STATE_UPDATE mascherato
            self.assertEqual(delivered[-1]["data"]["turn_player_name"], "Sconosciuto")

            # FOW_UPDATE_BROADCAST che svela (8,8) deve azzerare fow_draft e includere l'Orco ora visibile
            broadcast(gs, make_fow_update_broadcast([[0, 0], [8, 8]], [[0, 0], [8, 8], [9, 9]], fow_enabled=True))
            fow_pkt = delivered[-1]["data"]
            self.assertEqual(fow_pkt["fow_draft"], [])
            names = [p["name"] for p in fow_pkt["players"]]
            self.assertIn("OrcoNascosto", names)
            self.assertNotIn("Gufo", names)

    def test_fow_toggle_does_not_publish_draft_and_light_darkvision_sync(self):
        """Verifica che toggle_fow non pubblichi la bozza FoW, propaghi light_radius/color e sincronizzi Darkvision remota."""
        from server.dm_gui import DM_GUI
        from client.client import ClientGUI

        gs = GameState(queue.Queue())
        gs.current_map = {
            "fow_enabled": False,
            "fow_revealed": [[0, 0]],
            "fow_draft": [[0, 0], [1, 0], [2, 0]],
            "walls": [],
        }
        hero = Player("Valen", conn=object())
        hero.position = [0, 0]
        hero.is_party_member = True
        gs.players = [hero]

        mock_dm = MagicMock()
        mock_dm.server.game_state = gs
        mock_dm.fow_enabled_var.get.return_value = True
        sent = []
        with patch("common.network_utils.send_message", side_effect=lambda c, m: sent.append(m)):
            DM_GUI.toggle_fow(mock_dm)

        self.assertTrue(gs.current_map["fow_enabled"])
        self.assertEqual(gs.current_map["fow_revealed"], [[0, 0]], "toggle_fow NON deve pubblicare fow_draft in fow_revealed")
        self.assertEqual(gs.current_map["fow_draft"], [[0, 0], [1, 0], [2, 0]])

        # Verifica stats light_radius + light_color
        stat_pkt = make_player_stats_update("Valen", 20, 20, 2, [], light_radius=8, light_color="#FFAA00")
        c_mock = MagicMock()
        c_mock.name = "Altro"
        c_mock.active_character = None
        c_mock.players_data = {"Valen": {"name": "Valen", "hp": 20, "max_hp": 20}}
        ClientGUI.handle_player_stats_update(c_mock, stat_pkt["data"])
        self.assertEqual(c_mock.players_data["Valen"]["light_radius"], 8)
        self.assertEqual(c_mock.players_data["Valen"]["light_color"], "#FFAA00")
        c_mock.redraw_map_and_players.assert_called()

        # Verifica sincronizzazione remota Scurovisione (UPDATE_FULL_SHEET) + auto_explore_fow
        elf = Player("Elfa", conn=object())
        elf.position = [0, 0]
        elf.vision_radius = 6
        elf.is_party_member = True
        gs.players.append(elf)
        gs.current_map = {
            "grid_type": "hex",
            "fow_enabled": True,
            "fow_revealed": [[0, 0]],
            "fow_draft": [[0, 0]],
            "walls": [],
            "hexes": [[q, r] for q in range(-15, 16) for r in range(-15, 16)],
        }
        with patch("server.rules.character.broadcast"), patch("server.rules.character.send_message"):
            handle_update_full_sheet_request(
                {"character": {"name": "Elfa", "race": "Elfo", "traits": ["Scurovisione 60ft"], "hp_max": 18, "hp_current": 18}},
                elf,
                gs,
            )
        self.assertTrue(elf.has_darkvision)
        self.assertGreaterEqual(elf.vision_radius, 12)
        self.assertIn([10, 0], gs.current_map["fow_revealed"])

    def test_canvas_is_dm_blinded_lights_and_party_visibility(self):
        """Verifica is_dm su canvas disconnesso, cecita' vs vista cieca, luci statiche e visibilita' alleati."""
        root = tk.Tk()
        root.withdraw()
        try:
            canvas = HexMapCanvas(root, width=600, height=400)
            canvas.pack()

            # Client canvas esplicitamente non-DM resta non-DM anche con player_name=None
            canvas.is_dm = False
            canvas.update_data(
                {"grid_type": "square", "fow_enabled": True, "fow_revealed": [[0, 0]], "walls": [], "lights": [{"q": 2, "r": 0, "radius": 3}], "hexes": [[q, r] for q in range(6) for r in range(6)]},
                {"Eroe": {"name": "Eroe", "position": [0, 0], "vision_radius": 6, "is_party_member": True, "conditions": ["Accecato"]}},
                player_name=None,
            )
            self.assertFalse(canvas._effective_is_dm())

            # Accecato senza vista cieca vede solo la propria casella
            canvas.update_data(
                {"grid_type": "square", "fow_enabled": True, "fow_revealed": [[0, 0], [4, 0]], "walls": [], "lights": [{"q": 2, "r": 0, "radius": 3}], "hexes": [[q, r] for q in range(6) for r in range(6)]},
                {"Eroe": {"name": "Eroe", "position": [0, 0], "vision_radius": 6, "is_party_member": True, "conditions": ["Accecato"]}},
                player_name="Eroe",
            )
            self.assertEqual(canvas.visible_hexes, {(0, 0)})

            # Con Vista Cieca 30ft vede fino a 6 celle anche se Accecato
            canvas.update_data(
                {"grid_type": "square", "fow_enabled": True, "fow_revealed": [[0, 0]], "walls": [], "hexes": [[q, r] for q in range(8) for r in range(8)]},
                {"Eroe": {"name": "Eroe", "position": [0, 0], "vision_radius": 6, "is_party_member": True, "conditions": ["Accecato"], "senses": "Vista Cieca 30ft"}},
                player_name="Eroe",
            )
            self.assertIn((5, 0), canvas.visible_hexes)

            # Vedente con Luce Statica sulla mappa a (2,0) svelata (raggio 3 -> illumina (5,0) con raggio 2 se vision=2)
            canvas.update_data(
                {"grid_type": "square", "fow_enabled": True, "fow_revealed": [[0, 0], [2, 0]], "walls": [], "lights": [{"q": 2, "r": 0, "radius": 3}], "hexes": [[q, r] for q in range(8) for r in range(8)]},
                {
                    "Eroe": {"name": "Eroe", "position": [0, 0], "vision_radius": 2, "is_party_member": True, "conditions": []},
                    "Alleato": {"name": "Alleato", "position": [7, 7], "is_party_member": True},
                },
                player_name="Eroe",
            )
            self.assertIn((5, 0), canvas.visible_hexes, "La torcia statica a (2,0) deve illuminare fino a (5,0)")
            # Il token Alleato fuori visible_now viene comunque renderizzato come membro del party
            canvas.redraw()
            drawn_texts = [canvas.itemcget(item, "text") for item in canvas.find_all() if canvas.type(item) == "text"]
            self.assertTrue(any("AL" in t for t in drawn_texts), "Un alleato del party dietro un muro non deve sparire per gli altri giocatori")
        finally:
            root.destroy()

    def test_movement_forced_incapacitated_containers_map_load_and_switch(self):
        """Verifica incapacitated, movimento forzato, peso contenitori, risoluzione immagini e spawn/switch mappa."""
        gs = GameState(queue.Queue())
        gs.combat_active = True
        gs.automation_settings = {"strict_turn_lock": True, "strict_movement_limits": True}
        gs.current_map = {"grid_type": "square", "walls": [], "doors": [], "hexes": [[q, r] for q in range(10) for r in range(10)]}

        p1 = Player("Eroe", conn=object())
        p1.position = [0, 0]
        p1.is_party_member = True
        p1.speed = 30
        p1.in_combat = True
        p1.full_sheet = {
            "attributes": {"FOR": 10},  # 10*15=150 sovraccarico, 10*5=50 ingombrato
            "inventory_grid": [
                {"name": "Statua", "weight": 200.0, "qty": 1, "container": "bag_of_holding"},
                {"name": "ZainoPietre", "weight": 200.0, "qty": 1, "container": "backpack"},
            ],
        }
        p1.backpack_dropped = True  # Con bag_of_holding e zaino posato, carico effettivo = 0 lb

        enemy = Player("Orco")
        enemy.position = [1, 0]
        enemy.hp = 15
        enemy.in_combat = True
        enemy.is_party_member = False
        gs.players = [p1, enemy]
        gs.turn_index = 0  # Turno di p1

        # 1. Movimento forzato di enemy fuori dal suo turno: zero spesa movimento e zero OA su p1
        p1_threat = Player("AlleatoSentinella", conn=object())
        p1_threat.position = [1, 1]
        p1_threat.hp = 20
        p1_threat.is_party_member = True
        gs.players.append(p1_threat)

        alerts = []
        with patch("server.rules.movement.broadcast", side_effect=lambda g, m: alerts.append(m)):
            handle_move_request({"to": [4, 0], "is_forced": True}, enemy, gs)
        self.assertEqual(enemy.position, [4, 0])
        self.assertEqual(enemy.movement_spent_this_turn, 0)
        self.assertFalse(any(m.get("type") == "CHAT_BROADCAST" and "OPPORTUNITÀ" in m.get("data", {}).get("text", "") for m in alerts))

        # 2. P1 con peso in bag_of_holding + zaino posato si muove normalmente senza blocco variant encumbrance
        with patch("server.rules.movement.broadcast"):
            handle_move_request({"to": [2, 0]}, p1, gs)
        self.assertEqual(p1.position, [2, 0])

        # 3. Incapacitated non ostruisce il passaggio come creatura ostile
        incap_enemy = Player("GoblinIncap")
        incap_enemy.position = [3, 0]
        incap_enemy.hp = 7
        incap_enemy.conditions = ["Incapacitated"]
        gs.players.append(incap_enemy)
        blocked, _, _ = _evaluate_creature_space_traversal(p1, Hex(3, 0), is_final_step=False, game_state=gs)
        self.assertFalse(blocked)

        # 4. resolve_map_image_data preferisce bg_image_data embedded ed evita FileNotFoundError
        embedded_b64 = base64.b64encode(b"FAKEPNG").decode("ascii")
        m_emb = {"base_image_path": "C:/non/existent/path/missing_map.png", "bg_image_data": embedded_b64}
        self.assertEqual(resolve_map_image_data(m_emb), embedded_b64)
        self.assertIsNone(resolve_map_image_data({"base_image_path": "C:/non/existent/path/definitely_missing.png"}))

        with tempfile.TemporaryDirectory() as tmpd:
            img_path = os.path.join(tmpd, "arena.png")
            with open(img_path, "wb") as f:
                f.write(b"IMGDATA")
            m_rel = {"base_image_path": "D:/other_pc/assets/arena.png"}
            res = resolve_map_image_data(m_rel, extra_dirs=[tmpd])
            self.assertEqual(base64.b64decode(res), b"IMGDATA")

        # 5. load_map non sovrappone i giocatori su un singolo esagono e switch_map ripulisce AoE/disegni e token murati
        gs.load_map({
            "grid_type": "square",
            "spawn_point": [0, 0],
            "walls": [[1, 0]],
            "hexes": [[q, r] for q in range(4) for r in range(4)],
        })
        positions = [tuple(p.position) for p in gs.players]
        self.assertEqual(len(positions), len(set(positions)), "I token devono essere distribuiti a spirale senza sovrapposizioni allo spawn")
        self.assertNotIn((1, 0), positions)

        gs.active_aoes = [{"origin": [0, 0], "type": "sfera", "size": 2}]
        gs.drawn_lines = [[0, 0, 10, 10, "red"]]
        gs.maps["Mappa2"] = {
            "name": "Mappa2",
            "grid_type": "square",
            "spawn_point": [1, 1],
            "walls": [list(p1.position)],
            "fow_enabled": True,
            "fow_revealed": [[1, 1]],
            "hexes": [[q, r] for q in range(5) for r in range(5)],
        }
        with patch("common.network_utils.broadcast"):
            gs.switch_map("Mappa2")
        self.assertEqual(gs.active_aoes, [])
        self.assertEqual(gs.drawn_lines, [])
        self.assertIn("fow_draft", gs.current_map)
        self.assertNotEqual(p1.position, gs.current_map["walls"][0])


if __name__ == "__main__":
    unittest.main()
