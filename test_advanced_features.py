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

if __name__ == "__main__":
    unittest.main()
