import unittest
import os
import sys
import queue
import random

os.environ["DND_MOCK_AUDIO"] = "1"

from common.game_state import GameState, Player
from common.hex_utils import Hex
from common.protocol import *
from client.character_manager import Character, LIGHT_PRESETS
from server.rules.combat import (
    handle_attack_request,
    _process_save_result,
    handle_save_result_request,
    handle_spend_legendary_action_request,
    handle_end_turn_request,
)
from server.rules.character import handle_update_stats_request
from server.rules.map_interaction import (
    handle_quest_action_request,
    handle_handout_share_request,
)
from components.ui_components import HexMapCanvas

class TestAdvanced5eFeatures(unittest.TestCase):
    def setUp(self):
        self.game_state = GameState(gui_queue=queue.Queue())
        self.game_state.current_map = {
            "name": "Arena 5e",
            "hexes": [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1], [0, 2], [1, 2], [2, 2]],
            "walls": [],
            "doors": [],
            "room_pins": [],
            "fow_enabled": True,
            "fow_revealed": [[0, 0]],
            "fow_draft": []
        }

    def tearDown(self):
        random.seed(None)

    # -------------------------------------------------------------
    # 1. SORGENTI DI LUCE & ILLUMINAZIONE DINAMICA
    # -------------------------------------------------------------
    def test_dynamic_lighting_presets_and_toggle(self):
        char = Character(name="Eroe della Luce")
        self.assertIsNone(char.active_light)
        self.assertEqual(char.get_light_specs(), (0, "#FFD700"))

        # Accensione Torcia
        active, status, preset = char.toggle_light("torch")
        self.assertTrue(active)
        self.assertEqual(status, "accesa")
        self.assertEqual(preset["id"], "torch")
        radius, color = char.get_light_specs()
        self.assertEqual(radius, 8)
        self.assertEqual(color, "#FFD700")

        # Spegnimento
        active, status, old = char.toggle_light("torch")
        self.assertFalse(active)
        self.assertEqual(status, "spenta")
        self.assertEqual(char.get_light_specs(), (0, "#FFD700"))

        # Accensione Incantesimo Luce
        active, status, preset = char.toggle_light("light_spell")
        self.assertTrue(active)
        self.assertEqual(preset["id"], "light_spell")
        self.assertEqual(char.get_light_specs(), (8, "#66D9E8"))

        # Accensione Lanterna Schermata (Fascio Ristretto / Dim)
        char.toggle_light() # Spegne
        active, status, preset = char.toggle_light("dim_hooded")
        self.assertTrue(active)
        self.assertEqual(char.get_light_specs(), (1, "#FF8C00"))

    def test_light_update_stats_and_fow_exploration(self):
        player = Player("Guerriero")
        player.position = [0, 0]
        player.vision_radius = 2
        player.light_radius = 0
        self.game_state.players = [player]

        # Invia aggiornamento con raggio di luce 6
        data = {
            "name": player.name,
            "hp": 20,
            "max_hp": 20,
            "initiative": 10,
            "conditions": [],
            "light_radius": 6,
            "light_color": "#FFA500"
        }
        handle_update_stats_request(data, player, self.game_state)
        self.assertEqual(player.light_radius, 6)
        self.assertEqual(player.light_color, "#FFA500")
        # FoW deve aver rivelato un'area più ampia grazie a max(vision_radius, light_radius)
        revealed = self.game_state.current_map.get("fow_revealed", [])
        self.assertIn([1, 0], revealed)
        self.assertIn([0, 1], revealed)

    # -------------------------------------------------------------
    # 2. COPERTURA TATTICA 5e RAW & TS DESTREZZA
    # -------------------------------------------------------------
    def test_attack_explicit_cover(self):
        attacker = Player("Arciere")
        attacker.position = [0, 0]
        attacker.full_sheet = {"ac": 12, "attributes": {"DES": 16}}

        target = Player("Bersaglio")
        target.position = [2, 0]
        target.hp = 30
        target.max_hp = 30
        target.full_sheet = {"ac": 10}

        self.game_state.players = [attacker, target]

        # Mock del d20 per test deterministico
        random.seed(42)

        # 1. Nessuna copertura: CA target = 10
        # Inviamo un attacco con bonus +0
        data_no_cover = {
            "target_name": target.name,
            "weapon_name": "Arco",
            "hit_bonus": 0,
            "damage_formula": "1d6",
            "damage_type": "Perforante",
            "cover": "none"
        }
        handle_attack_request(data_no_cover, attacker, self.game_state)

        # 2. Mezza Copertura (+2 CA): CA target diventa 12
        data_half_cover = {
            "target_name": target.name,
            "weapon_name": "Arco",
            "hit_bonus": 0,
            "damage_formula": "1d6",
            "damage_type": "Perforante",
            "cover": "half"
        }
        handle_attack_request(data_half_cover, attacker, self.game_state)

        # 3. 3/4 Copertura (+5 CA): CA target diventa 15
        data_34_cover = {
            "target_name": target.name,
            "weapon_name": "Arco",
            "hit_bonus": 0,
            "damage_formula": "1d6",
            "damage_type": "Perforante",
            "cover": "three_quarters"
        }
        handle_attack_request(data_34_cover, attacker, self.game_state)

        # 4. Copertura Totale: colpo sempre bloccato
        target.hp = 30
        data_total_cover = {
            "target_name": target.name,
            "weapon_name": "Arco",
            "hit_bonus": 20, # anche con +20 colpo sicuro
            "damage_formula": "1d6",
            "damage_type": "Perforante",
            "cover": "total"
        }
        handle_attack_request(data_total_cover, attacker, self.game_state)
        # Il bersaglio non subisce danni da copertura totale
        self.assertEqual(target.hp, 30)

    def test_save_result_dex_cover(self):
        target = Player("Ladro")
        target.hp = 20
        target.max_hp = 20
        target.full_sheet = {"attributes": {"DES": 14}}
        self.game_state.players = [target]

        # TS su DES CD 15 con tiro base 11 (fallirebbe normalmente)
        # Senza copertura: 11 < 15 -> fallimento
        _process_save_result(target.name, "DES", 11, False, False, 15, "2d6", True, "Mago", self.game_state, "Fuoco", cover="none")
        self.assertLess(target.hp, 20)

        # Ripristina HP
        target.hp = 20
        # Con 3/4 di copertura (+5 al tiro): 11 + 5 = 16 >= 15 -> successo!
        # Se ha successo, half_on_success=False significa 0 danni
        _process_save_result(target.name, "DES", 11, False, False, 15, "2d6", False, "Mago", self.game_state, "Fuoco", cover="three_quarters")
        self.assertEqual(target.hp, 20)

    # -------------------------------------------------------------
    # 3. SPESA DADI VITA NEL RIPOSO BREVE
    # -------------------------------------------------------------
    def test_spend_hit_die_single_and_long_rest(self):
        char = Character(name="Barbaro")
        char.hp_max = 30
        char.hp_current = 10
        char.attributes["COS"] = 16 # Mod +3
        char.hit_dice_total = 4
        char.hit_dice_current = 4
        char.hit_dice_type = "d12"

        # Spende 1 dado vita
        res = char.spend_hit_die_single()
        self.assertTrue(res["success"])
        self.assertEqual(res["die"], "1d12")
        self.assertEqual(res["con_mod"], 3)
        self.assertGreaterEqual(res["roll"], 1)
        self.assertLessEqual(res["roll"], 12)
        self.assertEqual(res["healed"], res["roll"] + 3)
        self.assertEqual(char.hit_dice_current, 3)
        self.assertEqual(char.hp_current, 10 + res["actual_gain"])

        # Esaurimento dadi vita
        char.hit_dice_current = 0
        fail_res = char.spend_hit_die_single()
        self.assertFalse(fail_res["success"])
        self.assertEqual(fail_res["reason"], "Nessun Dado Vita rimasto")

        # Riposo Lungo: recupera fino a metà dei dadi vita totali (min 1)
        char.long_rest()
        self.assertEqual(char.hp_current, char.hp_max)
        self.assertEqual(char.hit_dice_current, 2) # 4 // 2 = 2

    # -------------------------------------------------------------
    # 4. CONCENTRAZIONE RIGOROSA
    # -------------------------------------------------------------
    def test_concentration_spell_replacement(self):
        player = Player("Chierico")
        player.conditions = ["Concentrazione"]
        self.game_state.players = [player]

        # Verifichiamo che il protocollo gestisca lo stato di concentrazione
        self.assertIn("Concentrazione", player.conditions)
        
        # Se subisce danno e fallisce il tiro salvezza su Costituzione, la concentrazione cade
        _process_save_result(player.name, "COS", 5, False, False, 10, None, False, "Sistema (Concentrazione)", self.game_state, "Contundente")
        self.assertNotIn("Concentrazione", player.conditions)

    # -------------------------------------------------------------
    # 5. AZIONI LEGGENDARIE & AZIONI DI TANA PER BOSS
    # -------------------------------------------------------------
    def test_boss_legendary_and_lair_actions(self):
        boss = Player("Drago Rosso Antico")
        boss.role = "Monster"
        boss.hp = 300
        boss.max_hp = 300
        boss.initiative = 20
        boss.has_lair_actions = True
        boss.legendary_actions_max = 3
        boss.legendary_actions_current = 3

        hero = Player("Eroe")
        hero.initiative = 15

        self.game_state.players = [boss, hero]
        self.game_state.combat_active = True
        self.game_state.turn_index = 0
        self.game_state.round_number = 1

        # 1. Spesa Azione Leggendaria
        dm_player = Player("DM")
        dm_player.role = "DM"

        data_leg = {
            "boss_name": boss.name,
            "action_name": "Colpo d'Ala",
            "cost": 2
        }
        handle_spend_legendary_action_request(data_leg, dm_player, self.game_state)
        self.assertEqual(boss.legendary_actions_current, 1)

        # 2. Spesa fallita se non ha abbastanza cariche
        data_leg_fail = {
            "boss_name": boss.name,
            "action_name": "Sguardo Terrorizzante",
            "cost": 2 # Rimasta solo 1 carica!
        }
        handle_spend_legendary_action_request(data_leg_fail, dm_player, self.game_state)
        self.assertEqual(boss.legendary_actions_current, 1) # Invariata

        # 3. Fine turno dell'eroe -> reset azioni leggendarie del boss all'inizio del suo turno
        self.game_state.turn_index = 1 # Turno dell'eroe
        handle_end_turn_request({}, hero, self.game_state)
        # Ora il turno torna al boss (turn_index 0)
        self.assertEqual(boss.legendary_actions_current, 3) # Ricaricate a 3!

    # -------------------------------------------------------------
    # 6. REGISTRO MISSIONI & DOCUMENTI CONDIVISI (HANDOUTS)
    # -------------------------------------------------------------
    def test_quest_log_and_handouts_system(self):
        # 1. Aggiungi missione
        quest_data = {
            "action": "add",
            "quest": {
                "id": "q1",
                "title": "Salva la principessa",
                "desc": "Trova la principessa nel dungeon oscuro",
                "giver": "Re Alistair",
                "reward": "500 MO",
                "completed": False
            }
        }
        handle_quest_action_request(quest_data, None, self.game_state)
        self.assertEqual(len(self.game_state.quests), 1)
        self.assertEqual(self.game_state.quests[0]["title"], "Salva la principessa")

        # 2. Completa missione
        complete_data = {
            "action": "complete",
            "quest": {"id": "q1"}
        }
        handle_quest_action_request(complete_data, None, self.game_state)
        self.assertTrue(self.game_state.quests[0]["completed"])

        # 3. Condividi Handout (Pergamena/Lettera)
        handout_data = {
            "title": "Lettera Sigillata",
            "content": "Incontraci alla taverna della luna calante a mezzanotte.",
            "image_path": "",
            "sender": "Dungeon Master"
        }
        handle_handout_share_request(handout_data, None, self.game_state)
        self.assertEqual(len(self.game_state.handouts), 1)
        self.assertEqual(self.game_state.handouts[0]["title"], "Lettera Sigillata")

        # 4. Verifica serializzazione nel GameState
        state_dict = self.game_state.get_state_dict()
        self.assertIn("handouts", state_dict)
        self.assertEqual(len(state_dict["handouts"]), 1)

        # 5. Cancella missione
        delete_data = {
            "action": "delete",
            "quest": {"id": "q1"}
        }
        handle_quest_action_request(delete_data, None, self.game_state)
        self.assertEqual(len(self.game_state.quests), 0)

    # -------------------------------------------------------------
    # 7. BADGE VISIVI DELLE CONDIZIONI (BILINGUE)
    # -------------------------------------------------------------
    def test_condition_badges_mapping(self):
        # Verifica che il dizionario cond_badge_map in HexMapCanvas copra tutte le condizioni bilingue
        badge_map = HexMapCanvas.cond_badge_map
        self.assertIn("Concentrazione", badge_map)
        self.assertIn("Concentrating", badge_map)
        self.assertEqual(badge_map["Concentrazione"][1], "🧠")
        self.assertIn("Schivata", badge_map)
        self.assertIn("Dodge", badge_map)
        self.assertEqual(badge_map["Schivata"][1], "🛡️")
        self.assertIn("Prono", badge_map)
        self.assertIn("Prone", badge_map)
        self.assertEqual(badge_map["Prono"][1], "🧎")
        self.assertIn("Invisibile", badge_map)
        self.assertIn("Invisible", badge_map)
        self.assertEqual(badge_map["Invisibile"][1], "👻")
        self.assertIn("Morto", badge_map)
        self.assertIn("Dead", badge_map)
        self.assertEqual(badge_map["Morto"][1], "💀")
        self.assertIn("Avvelenato", badge_map)
        self.assertIn("Poisoned", badge_map)
        self.assertEqual(badge_map["Avvelenato"][1], "🟢")

    # -------------------------------------------------------------
    # 8. VERIFICHE CODE REVIEW & REGRESSION TESTS
    # -------------------------------------------------------------
    def test_instant_death_drops_concentration_and_cleans_aoes(self):
        from server.rules.combat import apply_damage, drop_concentration
        wizard = Player("Mago")
        wizard.hp = 10
        wizard.max_hp = 10
        wizard.conditions = ["Concentrazione"]
        class MockConn:
            def sendall(self, b): pass
        wizard.conn = MockConn() # Giocatore reale connesso
        self.game_state.players = [wizard]
        self.game_state.active_aoes = [{
            "caster": "Mago",
            "concentration": True,
            "origin": [1, 1],
            "size": 3,
            "type": "circle"
        }]

        # 1. Morte istantanea da danno massiccio (25 danni >= 10 HP attuali + 10 max HP)
        apply_damage(wizard, 25, "Fuoco", self.game_state)
        self.assertEqual(wizard.hp, 0)
        self.assertIn("Morto", wizard.conditions)
        self.assertNotIn("Concentrazione", wizard.conditions, "Concentrazione rimossa in caso di morte istantanea")
        self.assertEqual(len(self.game_state.active_aoes), 0, "AoE a concentrazione del mago rimossa alla morte")

    def test_spell_slots_list_recovery_on_long_rest(self):
        char = Character(name="Stregone")
        # Formato lista legacy [current, max]
        char.spell_slots = {"1": [0, 4], "2": [1, 3]}
        char.long_rest()
        self.assertEqual(char.spell_slots["1"][0], 4, "Slot di 1° livello ripristinati a 4")
        self.assertEqual(char.spell_slots["2"][0], 3, "Slot di 2° livello ripristinati a 3")

    def test_network_gm_layer_filtered_for_player_state(self):
        gm_token = Player("PNG Segreto")
        gm_token.layer = "gm"
        pc_token = Player("Guerriero")
        pc_token.layer = "token"
        self.game_state.players = [gm_token, pc_token]

        state_dm = self.game_state.get_state_dict(is_dm=True)
        state_player = self.game_state.get_state_dict(is_dm=False)

        dm_names = [p["name"] for p in state_dm["players"]]
        player_names = [p["name"] for p in state_player["players"]]

        self.assertIn("PNG Segreto", dm_names)
        self.assertNotIn("PNG Segreto", player_names, "Il layer GM deve essere escluso per i client giocatori")
        self.assertIn("Guerriero", player_names)

    def test_theme_font_regular_alias(self):
        from common.theme import FONT_REGULAR, FONT_MAIN
        self.assertEqual(FONT_REGULAR, FONT_MAIN)

    def test_dm_generators_typing_optional_present(self):
        import server.dm_generators as dmg
        self.assertTrue(hasattr(dmg, "Optional"), "server.dm_generators deve importare Optional da typing")

    def test_menubar_no_duplicate_campaign_entries(self):
        import ast
        with open("server/dm_gui.py", "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
        
        # Estrai la definizione di setup_menubar
        setup_fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "setup_menubar"), None)
        self.assertIsNotNone(setup_fn, "setup_menubar deve essere definita in server/dm_gui.py")
        
        # Verifica comandi in tools_menu vs file_menu
        tools_commands = []
        file_commands = []
        for node in ast.walk(setup_fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_command":
                caller = getattr(node.func.value, "id", "")
                label_kw = next((kw.value for kw in node.keywords if kw.arg == "label"), None)
                if label_kw and isinstance(label_kw, ast.Call) and getattr(label_kw.func, "id", "") == "_t":
                    arg = label_kw.args[0].value if label_kw.args and isinstance(label_kw.args[0], ast.Constant) else None
                    if caller == "tools_menu":
                        tools_commands.append(arg)
                    elif caller == "file_menu":
                        file_commands.append(arg)
                        
        self.assertNotIn("menu_new_campaign", tools_commands, "tools_menu non deve duplicare 'menu_new_campaign'")
        self.assertIn("menu_new_campaign", file_commands, "file_menu deve contenere 'menu_new_campaign'")
        self.assertIn("menu_encounter_builder", tools_commands, "tools_menu deve contenere 'menu_encounter_builder'")
        self.assertIn("menu_close_campaign", file_commands, "file_menu deve contenere 'menu_close_campaign'")

    def test_outdoor_day_night_cycle_overlays(self):
        """Verifica le fasi del ciclo solare per le mappe all'aperto (Alba, Giorno, Tramonto, Notte)."""
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        try:
            canvas = HexMapCanvas(root, width=400, height=300)
            map_data = {"hexes": [[0, 0]], "hex_size": 30, "outdoor": True}

            # 1. Giorno Pieno (12:00) -> Nessun overlay oscurante solare
            canvas.update_data(map_data, {}, time_hour=12, weather="Sereno")
            root.update()
            day_overlays = canvas.find_withtag("night_overlay")
            self.assertEqual(len(day_overlays), 0, "A mezzogiorno all'aperto c'è piena luce solare, nessun filtro oscurante")

            # 2. Alba (07:00) -> Tinta ambrata del primo mattino
            canvas.update_data(map_data, {}, time_hour=7, weather="Sereno")
            root.update()
            dawn_overlays = canvas.find_withtag("night_overlay")
            self.assertGreaterEqual(len(dawn_overlays), 1, "All'alba all'aperto deve essere applicato il filtro ambrato")

            # 3. Tramonto (19:00) -> Tinta crepuscolare arancio
            canvas.update_data(map_data, {}, time_hour=19, weather="Sereno")
            root.update()
            dusk_overlays = canvas.find_withtag("night_overlay")
            self.assertGreaterEqual(len(dusk_overlays), 1, "Al tramonto all'aperto deve essere applicato il filtro crepuscolare")

            # 4. Notte (23:00) -> Filtro notte scuro + stelle notturne
            canvas.update_data(map_data, {}, time_hour=23, weather="Sereno")
            root.update()
            night_overlays = canvas.find_withtag("night_overlay")
            self.assertGreater(len(night_overlays), 5, "Di notte all'aperto devono essere presenti il filtro notturno e le stelle")
        finally:
            root.destroy()

    def test_indoor_dungeon_no_solar_overlay(self):
        """Verifica che le mappe al chiuso / dungeon NON subiscano il ciclo solare giorno/notte."""
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        try:
            canvas = HexMapCanvas(root, width=400, height=300)
            dungeon_map = {"name": "Dungeon dei Non Morti", "hexes": [[0, 0]], "hex_size": 30, "outdoor": False}

            # Anche alle 23:00, in un dungeon non cala la notte solare all'aperto
            canvas.update_data(dungeon_map, {}, time_hour=23, weather="Sereno")
            root.update()
            indoor_night_overlays = canvas.find_withtag("night_overlay")
            self.assertEqual(len(indoor_night_overlays), 0, "In un dungeon/al chiuso non deve essere applicato l'overlay della notte solare")

            # E nemmeno all'alba alle 07:00
            canvas.update_data(dungeon_map, {}, time_hour=7, weather="Sereno")
            root.update()
            indoor_dawn_overlays = canvas.find_withtag("night_overlay")
            self.assertEqual(len(indoor_dawn_overlays), 0, "In un dungeon/al chiuso non deve essere applicato l'overlay dell'alba solare")
        finally:
            root.destroy()

    def test_outdoor_night_light_sources_pierce_darkness(self):
        """Verifica che di notte all'aperto le sorgenti di luce attive (torce) taglino l'oscurità notturna."""
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        try:
            canvas = HexMapCanvas(root, width=400, height=300)
            map_data = {"hexes": [[0, 0]], "hex_size": 30, "outdoor": True}
            players_data = {
                "Guerriero": {
                    "position": [0, 0],
                    "light_radius": 8,  # Torcia accesa
                    "light_color": "#FFD700"
                }
            }

            canvas.update_data(map_data, players_data, time_hour=23, weather="Sereno")
            root.update()
            night_items = canvas.find_withtag("night_overlay")
            # Deve contenere il rettangolo notturno, le stelle e gli aloni di luce della torcia
            self.assertGreater(len(night_items), 10, "La torcia deve creare aloni di luce radiante che forano la notte all'aperto")
        finally:
            root.destroy()

    def test_game_state_time_minute_serialization(self):
        """Verifica che GameState gestisca e serializzi time_minute e time_second."""
        self.game_state.time_hour = 14
        self.game_state.time_minute = 0
        self.game_state.advance_game_time(minutes=35, seconds=40)
        self.assertEqual(self.game_state.time_hour, 14)
        self.assertEqual(self.game_state.time_minute, 35)
        self.assertEqual(self.game_state.time_second, 40)

        state_dict = self.game_state.get_state_dict()
        self.assertEqual(state_dict["time_minute"], 35)
        self.assertEqual(state_dict["time_second"], 40)

        # Ripristino da load_session
        import tempfile
        from common.file_utils import atomic_save_json
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name
        try:
            self.game_state.save_session(temp_path)
            new_state = GameState(gui_queue=queue.Queue())
            new_state.load_session(temp_path)
            self.assertEqual(new_state.time_hour, 14)
            self.assertEqual(new_state.time_minute, 35)
            self.assertEqual(new_state.time_second, 40)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_toggle_map_outdoor_dm_gui(self):
        """Verifica il toggle dell'ambiente outdoor/indoor e l'aggiornamento della pillola del DM."""
        from unittest.mock import MagicMock
        from server.dm_gui import DM_GUI
        
        gui = MagicMock(spec=DM_GUI)
        gui.server = MagicMock()
        gui.server.game_state = self.game_state
        gui.top_status_env_lbl = MagicMock()
        gui.log_to_chat = MagicMock()
        gui.update_canvas = MagicMock()
        
        self.game_state.current_map["outdoor"] = True
        
        # Primo toggle: da all'aperto a dungeon/chiuso
        DM_GUI.toggle_map_outdoor(gui)
        self.assertFalse(self.game_state.current_map["outdoor"])
        gui.log_to_chat.assert_called()
        gui.update_canvas.assert_called()
        
        # Secondo toggle: torna all'aperto
        DM_GUI.toggle_map_outdoor(gui)
        self.assertTrue(self.game_state.current_map["outdoor"])

    def test_automation_settings_day_night_cycle_toggle(self):
        """Verifica che la disattivazione del ciclo giorno/notte nel profilo mantenga la mappa pulita."""
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        try:
            canvas = HexMapCanvas(root, width=400, height=300)
            map_data = {"hexes": [[0, 0]], "hex_size": 30, "outdoor": True}

            # 1. Ciclo giorno/notte attivo -> di notte filtro notturno presente
            canvas.update_data(map_data, {}, time_hour=23, weather="Sereno", auto_day_night=True)
            root.update()
            self.assertGreater(len(canvas.find_withtag("night_overlay")), 0)

            # 2. Ciclo giorno/notte disattivato dal profilo -> nessun filtro notturno
            canvas.update_data(map_data, {}, time_hour=23, weather="Sereno", auto_day_night=False)
            root.update()
            self.assertEqual(len(canvas.find_withtag("night_overlay")), 0, "Se auto_day_night_cycle è False, nessun filtro solare/notturno deve essere applicato")
        finally:
            root.destroy()

    def test_automation_settings_advance_time_toggle(self):
        """Verifica che auto_advance_time abiliti o disabiliti lo scorrimento del tempo (+6s) a ogni round."""
        p = Player("Guerriero")
        p.position = [0, 0]
        p.in_combat = True
        self.game_state.players = [p]
        self.game_state.combat_active = True
        self.game_state.turn_index = 0
        self.game_state.time_second = 0

        # Con auto_advance_time = False, il round avanza ma l'orologio resta fermo
        self.game_state.automation_settings["auto_advance_time"] = False
        self.game_state.next_turn() # turn_index torna a 0, round_number = 2
        self.assertEqual(self.game_state.round_number, 2)
        self.assertEqual(self.game_state.time_second, 0, "Con auto_advance_time=False il tempo non deve scorrere automaticamente al cambio round")

        # Con auto_advance_time = True, il tempo avanza di 6 secondi
        self.game_state.automation_settings["auto_advance_time"] = True
        self.game_state.next_turn() # round_number = 3
        self.assertEqual(self.game_state.round_number, 3)
        self.assertEqual(self.game_state.time_second, 6, "Con auto_advance_time=True il tempo deve avanzare di 6s per round")

    def test_ancient_blue_dragon_attributes_extraction(self):
        """Verifica che l'Ancient Blue Dragon abbia le corrette caratteristiche 5e (FOR 29, COS 27, INT 18, etc.) e non tutti 10."""
        from common.srd_offline import extract_and_normalize_attributes, search_monsters_offline, get_monster_offline
        
        # 1. Verifica SRD offline
        hits = search_monsters_offline("Ancient Blue Dragon")
        self.assertGreater(len(hits), 0, "Ancient Blue Dragon deve essere trovato nei dati SRD offline")
        mdata = hits[0]["monster_data"]
        attrs = mdata.get("attributes", {})
        self.assertEqual(attrs.get("FOR"), 29, "Ancient Blue Dragon deve avere FOR 29")
        self.assertEqual(attrs.get("STR"), 29)
        self.assertEqual(attrs.get("DES"), 10, "Ancient Blue Dragon deve avere DES 10")
        self.assertEqual(attrs.get("COS"), 27, "Ancient Blue Dragon deve avere COS 27")
        self.assertEqual(attrs.get("INT"), 18, "Ancient Blue Dragon deve avere INT 18")
        self.assertEqual(attrs.get("SAG"), 17, "Ancient Blue Dragon deve avere SAG 17")
        self.assertEqual(attrs.get("CAR"), 21, "Ancient Blue Dragon deve avere CAR 21")
        self.assertEqual(mdata.get("ac"), 22, "Ancient Blue Dragon deve avere CA 22")
        self.assertEqual(mdata.get("hp"), 481, "Ancient Blue Dragon deve avere HP 481")

        # 2. Verifica anche ricerca in lingua italiana
        attrs_it = extract_and_normalize_attributes(None, "Drago Blu Antico")
        self.assertEqual(attrs_it.get("FOR"), 29)
        self.assertEqual(attrs_it.get("COS"), 27)

    def test_pdf_indexer_monster_cache_enrichment(self):
        """Verifica che il PDFManualsIndexer arricchisca le voci mostro in cache con gli attributi e CA corretti."""
        from common.pdf_manuals_indexer import PDFManualsIndexer
        indexer = PDFManualsIndexer()
        monsters = indexer.get_monsters()
        self.assertGreater(len(monsters), 0)
        
        abd_entries = [m for m in monsters if "ancient blue dragon" in m.get("title", "").lower()]
        if abd_entries:
            mdata = abd_entries[0].get("monster_data", {})
            attrs = mdata.get("attributes", {})
            self.assertEqual(attrs.get("FOR"), 29, "L'Ancient Blue Dragon indicizzato da PDF deve avere FOR 29 e non 10")
            self.assertEqual(attrs.get("COS"), 27)
            self.assertEqual(attrs.get("CAR"), 21)
            self.assertEqual(mdata.get("ac"), 22, "L'Ancient Blue Dragon indicizzato da PDF deve avere CA 22")

    def test_bestiary_spawn_populates_full_sheet_attributes(self):
        """Verifica che lo spawning da DMBestiaryPanel popoli npc.full_sheet['attributes'] e calcoli l'iniziativa corretta."""
        from unittest.mock import MagicMock
        from server.dm_bestiary_panel import DMBestiaryPanel
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:
            mock_dm = MagicMock()
            mock_dm.master = root
            mock_dm.server.game_state = self.game_state
            mock_dm.map_canvas = MagicMock()
            mock_dm.map_canvas._last_clicked_hex = None

            panel = DMBestiaryPanel(root, mock_dm)
            
            # Simuliamo la selezione di un mostro tipo Ancient Blue Dragon
            panel.bestiario_results = [{
                "name": "Ancient Blue Dragon",
                "monster_data": {
                    "name": "Ancient Blue Dragon",
                    "hp": 481,
                    "ac": 22,
                    "cr": "23",
                    "attributes": {"FOR": 29, "DES": 10, "COS": 27, "INT": 18, "SAG": 17, "CAR": 21}
                }
            }]
            panel.bestiario_listbox.insert(0, "Ancient Blue Dragon")
            panel.bestiario_listbox.selection_set(0)

            # Esegui spawn
            panel.spawn_bestiario()

            spawned = self.game_state.find_player("Ancient Blue Dragon")
            self.assertIsNotNone(spawned, "Il mostro deve essere stato aggiunto al game_state")
            self.assertIn("attributes", spawned.full_sheet, "full_sheet deve contenere la chiave 'attributes'")
            self.assertEqual(spawned.full_sheet["attributes"]["FOR"], 29, "FOR deve essere 29 e non 10")
            self.assertEqual(spawned.full_sheet["attributes"]["COS"], 27)
            self.assertEqual(spawned.full_sheet["ac"], 22)
            self.assertEqual(spawned.initiative, 0, "Iniziativa da DES 10 deve essere 0")
        finally:
            root.destroy()

    def test_encounter_builder_spawn_populates_attributes(self):
        """Verifica che l'EncounterBuilder schieri i mostri con caratteristiche complete nel full_sheet."""
        from unittest.mock import MagicMock
        from server.dm_gui import DM_GUI
        
        gui = MagicMock(spec=DM_GUI)
        gui.server = MagicMock()
        gui.server.game_state = self.game_state
        gui.log_to_chat = MagicMock()
        
        monsters = [{
            "name": "Goblin",
            "hp": 7,
            "ac": 15,
            "count": 1,
            "initiative": None,
            "attributes": {"FOR": 8, "DES": 14, "COS": 10, "INT": 10, "SAG": 8, "CAR": 8}
        }]
        
        DM_GUI.handle_encounter_start(gui, monsters)
        
        goblin = self.game_state.find_player("Goblin")
        self.assertIsNotNone(goblin)
        self.assertEqual(goblin.full_sheet["attributes"]["DES"], 14)
        self.assertEqual(goblin.full_sheet["attributes"]["FOR"], 8)
        self.assertEqual(goblin.initiative, 2, "Iniziativa calcolata dal modificatore di DES 14 (+2)")

    def test_format_monster_action_tooltip_details(self):
        """Verifica che il tooltip dell'azione formatti e mostri le caratteristiche corrette: TpC, dadi/danni, gittata, TS."""
        from common.srd_offline import format_monster_action_tooltip, get_monster_offline

        abd = get_monster_offline("Ancient Blue Dragon")
        self.assertIsNotNone(abd)
        actions = abd.get("actions", [])
        
        # 1. Morso (Bite)
        bite = next((a for a in actions if a.get("name") == "Bite"), None)
        self.assertIsNotNone(bite)
        bite_tip = format_monster_action_tooltip(bite, "Ancient Blue Dragon")
        self.assertIn("TpC: +16", bite_tip, "Il tooltip deve mostrare il Tiro per Colpire +16")
        self.assertIn("Danno", bite_tip, "Il tooltip deve mostrare l'intestazione Danno")
        self.assertIn("2d10", bite_tip, "Il tooltip deve mostrare i dadi di danno")
        self.assertIn("reach 15 ft", bite_tip.lower(), "Il tooltip deve mostrare la portata di 15 ft")

        # 2. Soffio di Fulmine (Lightning Breath)
        breath = next((a for a in actions if "lightning breath" in a.get("name", "").lower()), None)
        self.assertIsNotNone(breath)
        breath_tip = format_monster_action_tooltip(breath, "Ancient Blue Dragon")
        self.assertIn("CD 23", breath_tip, "Il tooltip deve mostrare la Classe Difficoltà del Tiro Salvezza CD 23")
        self.assertIn("16d10", breath_tip, "Il tooltip deve mostrare i dadi del danno da fulmine")

        # 3. Goblin Scimitar
        goblin = get_monster_offline("Goblin")
        self.assertIsNotNone(goblin)
        scimitar = next((a for a in goblin.get("actions", []) if a.get("name") == "Scimitar"), None)
        self.assertIsNotNone(scimitar)
        scim_tip = format_monster_action_tooltip(scimitar, "Goblin")
        self.assertIn("TpC: +4", scim_tip)
        self.assertIn("1d6", scim_tip)

    def test_monster_actions_hover_tooltips_gui(self):
        """Verifica che la selezione di un mostro in dm_gui generi bottoni azione equipaggiati con ToolTip."""
        import tkinter as tk
        from tkinter import ttk
        from server.dm_gui import DM_GUI
        from unittest.mock import MagicMock
        from common.game_state import Player

        root = tk.Tk()
        root.withdraw()
        try:
            gui = MagicMock(spec=DM_GUI)
            gui.server = MagicMock()
            gui.server.game_state = self.game_state
            gui.npc_actions_frame = ttk.Frame(root)
            gui.player_listbox = tk.Listbox(root)

            # Aggiungiamo un mostro Ancient Blue Dragon
            dragon = Player("Ancient Blue Dragon")
            dragon.full_sheet = {
                "name": "Ancient Blue Dragon",
                "actions": [
                    {"name": "Bite", "desc": "Melee Weapon Attack: +16 to hit, reach 15 ft. Hit: 20 (2d10 + 9) piercing.", "attack_bonus": 16, "damage_dice": "2d10"}
                ]
            }
            self.game_state.players = [dragon]

            gui.player_listbox.insert(0, "Ancient Blue Dragon (HP: 481/481)")
            gui.player_listbox.selection_set(0)

            # Invochiamo on_player_selected
            DM_GUI.on_player_selected(gui, None)

            # Verifichiamo che il bottone dell'azione sia stato creato
            children = gui.npc_actions_frame.winfo_children()
            self.assertEqual(len(children), 1)
            btn = children[0]
            self.assertEqual(btn.cget("text"), "Bite")
        finally:
            root.destroy()

    def test_normalize_ac_value(self):
        """Verifica la normalizzazione robusta della Classe Armatura da qualsiasi formato o anomalie API."""
        from common.srd_offline import normalize_ac_value

        # 1. Lista di dict tipica di dnd5eapi.co
        self.assertEqual(normalize_ac_value([{"type": "natural", "value": 22}]), 22)
        self.assertEqual(normalize_ac_value([{"type": "armor", "value": 18, "armor": [{"name": "Plate"}]}]), 18)

        # 2. Casi limite anomali o parziali con parentesi '[{}]'
        self.assertEqual(normalize_ac_value([{}]), 10)
        self.assertEqual(normalize_ac_value("[]"), 10)
        self.assertEqual(normalize_ac_value("[{}]"), 10)
        self.assertEqual(normalize_ac_value("[{'value': 22}]"), 22)

        # 3. Formati stringa complessi da manuali o Open5e
        self.assertEqual(normalize_ac_value("18 (natural armor)"), 18)
        self.assertEqual(normalize_ac_value("16 (chain mail, shield)"), 16)
        self.assertEqual(normalize_ac_value("22"), 22)

        # 4. Numeri primitivi e dizionari
        self.assertEqual(normalize_ac_value(17), 17)
        self.assertEqual(normalize_ac_value(19.0), 19)
        self.assertEqual(normalize_ac_value({"value": 15}), 15)
        self.assertEqual(normalize_ac_value({"ac": 14}), 14)

        # 5. None e valori non validi -> fallback a default
        self.assertEqual(normalize_ac_value(None, default=12), 12)
        self.assertEqual(normalize_ac_value("Nessuna CA", default=10), 10)

    def test_normalize_speed_value(self):
        """Verifica la normalizzazione e formattazione elegante della Velocità (Speed) senza '[{}]'."""
        from common.srd_offline import normalize_speed_value

        # 1. Dizionario con movimenti multipli da dnd5eapi.co
        s_val, s_disp, s_u = normalize_speed_value({"walk": "40 ft.", "burrow": "40 ft.", "fly": "80 ft."})
        self.assertEqual(s_val, 40)
        self.assertEqual(s_u, "ft")
        self.assertIn("40 ft", s_disp)
        self.assertIn("Volo 80 ft", s_disp)
        self.assertIn("Scavo 40 ft", s_disp)
        self.assertNotIn("{", s_disp)
        self.assertNotIn("[", s_disp)

        # 2. Casi limite con dict o stringhe grezze '[{}]'
        s_val, s_disp, s_u = normalize_speed_value([{}])
        self.assertEqual(s_val, 30)
        self.assertEqual(s_disp, "30 ft")
        self.assertNotIn("{", s_disp)

        s_val, s_disp, s_u = normalize_speed_value("[{}]")
        self.assertEqual(s_val, 30)
        self.assertEqual(s_disp, "30 ft")

        s_val, s_disp, s_u = normalize_speed_value("{}")
        self.assertEqual(s_val, 30)
        self.assertEqual(s_disp, "30 ft")

        # 3. Stringa con movimenti multipli da Tome of Beasts / Open5e
        tob_speed = "10 ft., swim 40 ft., fly 40 ft. (ethereal only, hover)"
        s_val, s_disp, s_u = normalize_speed_value(tob_speed)
        self.assertEqual(s_val, 10)
        self.assertIn("Nuoto 40 ft", s_disp)
        self.assertIn("Volo 40 ft", s_disp)
        self.assertIn("(ethereal only, hover)", s_disp)

        # 4. Numeri primitivi e metri
        self.assertEqual(normalize_speed_value(30), (30, "30 ft", "ft"))
        self.assertEqual(normalize_speed_value(9, default_unit="m"), (9, "9 m", "m"))

    def test_speed_to_hexes_with_complex_speed(self):
        """Verifica che speed_to_hexes accetti anche strutture dict o list senza andare in errore."""
        from common.i18n import speed_to_hexes

        # 40 ft // 5 = 8 esagoni
        self.assertEqual(speed_to_hexes({"walk": "40 ft.", "fly": "80 ft."}), 8)
        self.assertEqual(speed_to_hexes("40 ft., fly 80 ft."), 8)
        # Fallback se vuoto o '[{}]'
        self.assertEqual(speed_to_hexes([{}]), 6)  # 30 ft // 5 = 6

    def test_dm_player_sheet_viewer_no_raw_formatting(self):
        """Verifica che DMPlayerSheetViewer non mostri stringhe grezze '[{}]' per CA e Velocità."""
        import tkinter as tk
        from tkinter import ttk
        from server.dm_dialogs import DMPlayerSheetViewer

        root = tk.Tk()
        root.withdraw()
        try:
            # Scheda simulata con formattazione non normalizzata da API grezza
            raw_sheet = {
                "name": "Ancient Blue Dragon",
                "char_class": "Mostro/NPC",
                "level": 1,
                "hp_current": 481,
                "hp_max": 481,
                "ac": [{"type": "natural", "value": 22}],
                "speed": {"walk": "40 ft.", "burrow": "40 ft.", "fly": "80 ft."},
                "attributes": {"FOR": 29, "DES": 10, "COS": 27, "INT": 18, "SAG": 17, "CAR": 21},
                "actions": [{"name": "Bite", "desc": "Melee Weapon Attack"}]
            }

            viewer = DMPlayerSheetViewer(root, player_name="Ancient Blue Dragon", sheet=raw_sheet)

            # Raccogliamo tutti i testi delle Label create nella finestra
            def collect_texts(widget):
                texts = []
                if isinstance(widget, (ttk.Label, tk.Label)):
                    texts.append(widget.cget("text"))
                for child in widget.winfo_children():
                    texts.extend(collect_texts(child))
                return texts

            all_labels = collect_texts(viewer)
            # Nessuna etichetta deve contenere la formattazione grezza [{}]
            for t in all_labels:
                self.assertNotIn("[{", t, f"Trovata formattazione grezza in label: {t}")
                self.assertNotIn("{'walk'", t, f"Trovata sintassi dict grezza in label: {t}")

            # Deve contenere '22' come CA e '40 ft' come velocità
            self.assertIn("22", all_labels, "La CA deve essere visualizzata come 22 pulito")
            self.assertTrue(any("40 ft" in t for t in all_labels), "La velocità base deve essere 40 ft")

            viewer.destroy()
        finally:
            root.destroy()

    def test_match_monster_cr_and_type(self):
        """Verifica i filtri di precisione per Grado di Sfida (CR) e Tipo Creatura."""
        from common.srd_offline import match_monster_cr, match_monster_type

        # CR test
        self.assertTrue(match_monster_cr("1/4", "CR 0 - 1/2"))
        self.assertTrue(match_monster_cr(3, "CR 1 - 4"))
        self.assertFalse(match_monster_cr(10, "CR 1 - 4"))
        self.assertTrue(match_monster_cr("23", "CR 20+"))
        self.assertTrue(match_monster_cr(5, "Tutti i CR"))

        # Tipo creatura test (bilingue)
        self.assertTrue(match_monster_type("dragon", "Drago"))
        self.assertTrue(match_monster_type("medium undead", "Non Morto"))
        self.assertTrue(match_monster_type("humanoid (elf)", "Umanoide"))
        self.assertFalse(match_monster_type("fiend (devil)", "Bestia"))
        self.assertTrue(match_monster_type("beast", "Tutti i Tipi"))

    def test_match_item_rarity_and_type(self):
        """Verifica i filtri per Rarità e Tipo di Oggetto."""
        from common.srd_offline import match_item_rarity, match_item_type

        # Rarità test
        self.assertTrue(match_item_rarity("rare", "Raro"))
        self.assertTrue(match_item_rarity("very rare", "Molto raro"))
        self.assertTrue(match_item_rarity("legendary", "Leggendario"))
        self.assertFalse(match_item_rarity("common", "Raro"))
        self.assertTrue(match_item_rarity("uncommon", "Tutte le Rarità"))

        # Tipo test
        self.assertTrue(match_item_type("Weapon (longsword)", "Arma"))
        self.assertTrue(match_item_type("Armor (plate)", "Armatura"))
        self.assertTrue(match_item_type("Potion of Healing", "Pozione"))
        self.assertTrue(match_item_type("Wondrous item", "Meraviglia"))

    def test_statblock_card_view_rendering(self):
        """Verifica il rendering della StatblockCardView per mostri, oggetti e incantesimi."""
        import tkinter as tk
        from tkinter import ttk
        from components.statblock_view import StatblockCardView

        root = tk.Tk()
        root.withdraw()
        try:
            view = StatblockCardView(root)

            # 1. Mostro
            monster = {
                "name": "Adult Red Dragon",
                "size": "Huge",
                "type": "dragon",
                "alignment": "chaotic evil",
                "armor_class": 19,
                "hit_points": 256,
                "challenge_rating": "17",
                "speed": {"walk": "40 ft.", "fly": "80 ft."},
                "attributes": {"FOR": 27, "DES": 10, "COS": 25, "INT": 16, "SAG": 13, "CAR": 21},
                "actions": [
                    {"name": "Multiattack", "desc": "The dragon can use its Frightful Presence."},
                    {"name": "Bite", "desc": "Melee Weapon Attack: +14 to hit, reach 10 ft. Hit: 19 (2d10 + 8) piercing.", "attack_bonus": 14}
                ]
            }
            view.show_monster(monster)

            def get_text(widget):
                txts = []
                if isinstance(widget, (ttk.Label, tk.Label)):
                    txts.append(widget.cget("text"))
                for c in widget.winfo_children():
                    txts.extend(get_text(c))
                return txts

            texts = get_text(view)
            self.assertTrue(any("Adult Red Dragon" in t for t in texts))
            self.assertTrue(any("CR 17" in t for t in texts))
            self.assertTrue(any("19" in t for t in texts))  # CA
            self.assertTrue(any("40 ft" in t for t in texts))  # Speed

            # 2. Oggetto Magico
            item = {
                "name": "Flame Tongue",
                "type": "Weapon (any sword)",
                "rarity": "rare",
                "desc": "You can use a bonus action to speak this magic sword's command word."
            }
            view.show_magic_item(item)
            texts_item = get_text(view)
            self.assertTrue(any("Flame Tongue" in t for t in texts_item))
            self.assertTrue(any("Rare" in t or "Raro" in t for t in texts_item))

            # 3. Incantesimo
            spell = {
                "name": "Fireball",
                "level": 3,
                "school": "Evocation",
                "casting_time": "1 action",
                "range": "150 feet",
                "desc": "A bright streak flashes from your pointing finger..."
            }
            view.show_spell(spell)
            texts_spell = get_text(view)
            self.assertTrue(any("Fireball" in t for t in texts_spell))
            self.assertTrue(any("Livello 3" in t for t in texts_spell))

            view.destroy()
        finally:
            root.destroy()

    def test_compendium_dialog_split_view(self):
        """Verifica che CompendiumDialog si apra in modalità Split View con filtri rapidi."""
        import tkinter as tk
        from server.compendium_ui import CompendiumDialog

        root = tk.Tk()
        root.withdraw()
        try:
            dlg = CompendiumDialog(root, is_dm=True)
            self.assertTrue(hasattr(dlg, "paned"), "CompendiumDialog deve avere un PanedWindow per la split view")
            self.assertTrue(hasattr(dlg, "statblock_view"), "CompendiumDialog deve avere uno StatblockCardView integrato")
            self.assertTrue(hasattr(dlg, "filter_frame"), "CompendiumDialog deve avere il container dei filtri rapidi")
            dlg.destroy()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()





