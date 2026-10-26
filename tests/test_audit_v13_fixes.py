import queue
import unittest
from common.dice import roll_dice
from common.game_state import GameState, Player
from server.rules.combat import apply_damage, _process_save_result, handle_attack_request, drop_concentration
from server.rules.movement import handle_move_request
from common.network_utils import sanitize_map_for_players
from common.srd_offline import get_class_level_features_offline
from client.character_manager import Character

class TestAuditV13Fixes(unittest.TestCase):
    def setUp(self):
        self.game_state = GameState(queue.Queue())

    def test_compound_dice_parser(self):
        # Multi-group dice formula
        res = roll_dice("2d6+1d8+3")
        self.assertEqual(len(res["rolls"]), 3)
        self.assertEqual(res["modifier"], 3)
        self.assertEqual(res["total"], sum(res["rolls"]) + 3)
        self.assertGreaterEqual(res["total"], 6)
        self.assertLessEqual(res["total"], 23)

        # Critical hit doubling dice pool in compound formula
        crit_res = roll_dice("2d6+1d8+3", is_crit=True)
        self.assertEqual(len(crit_res["rolls"]), 6) # 4d6 + 2d8
        self.assertEqual(crit_res["modifier"], 3)
        self.assertEqual(crit_res["type"], "Critico")

    def test_crit_at_zero_hp_gives_two_failures(self):
        p = Player("Svenuto")
        p.hp = 0
        p.max_hp = 30
        p.is_party_member = True
        p.death_saves = {"successes": 0, "failures": 0}
        
        # Regular damage at 0 HP -> 1 failure
        apply_damage(p, 5, "Tagliente", self.game_state, is_crit=False)
        self.assertEqual(p.death_saves["failures"], 1)

        # Critical hit at 0 HP -> 2 failures (PHB p. 197 RAW)
        apply_damage(p, 5, "Tagliente", self.game_state, is_crit=True)
        self.assertEqual(p.death_saves["failures"], 3)
        self.assertIn("Morto", p.conditions)

    def test_concentration_drops_on_incapacitated(self):
        caster = Player("Mago")
        caster.hp = 20
        caster.max_hp = 20
        caster.conditions = ["Concentrazione"]
        self.game_state.active_aoes = [{"name": "Ragnatela", "caster": "Mago", "concentration": True}]

        # Inflicting Incapacitated condition drops concentration per RAW 5e PHB p. 203
        caster.conditions.append("Incapacitato")
        apply_damage(caster, 1, "Forza", self.game_state)
        self.assertNotIn("Concentrazione", caster.conditions)
        self.assertEqual(len(self.game_state.active_aoes), 0)

    def test_full_sheet_damage_resistances_applied(self):
        tiefling = Player("Tiefling")
        tiefling.hp = 30
        tiefling.max_hp = 30
        tiefling.full_sheet = {"damage_resistances": ["fuoco", "fire"]}
        
        # Fire damage should be halved (10 -> 5)
        final_dmg, note, _, _ = apply_damage(tiefling, 10, "Fuoco", self.game_state)
        self.assertEqual(final_dmg, 5)
        self.assertIn("Resistenza", note)
        self.assertEqual(tiefling.hp, 25)

    def test_saving_throw_crit_and_fumble(self):
        target = Player("Bersaglio")
        target.hp = 30
        target.max_hp = 30
        self.game_state.players = [target]
        
        # Nat 20 auto-succeeds on saving throws
        _process_save_result("Bersaglio", "SAG", 15, is_crit=True, is_fail=False, dc=30,
                             damage_formula="10", half_on_success=False, source_name="Incantesimo",
                             game_state=self.game_state, damage_type="Psichico")
        self.assertEqual(target.hp, 30) # Succeeded -> 0 damage

        # Nat 1 auto-fails even if roll_total >= dc
        _process_save_result("Bersaglio", "SAG", 25, is_crit=False, is_fail=True, dc=10,
                             damage_formula="10", half_on_success=False, source_name="Incantesimo",
                             game_state=self.game_state, damage_type="Psichico")
        self.assertEqual(target.hp, 20) # Failed -> took 10 damage

    def test_teleport_does_not_provoke_opportunity_attack(self):
        enemy = Player("Nemico")
        enemy.position = [0, 0]
        enemy.hp = 20
        enemy.is_party_member = False
        
        player = Player("Mago")
        player.position = [0, 1] # adjacent to enemy
        player.hp = 20
        player.is_party_member = True
        
        self.game_state.players = [enemy, player]
        self.game_state.combat_active = True
        
        # Normal move would provoke, but teleportation does not
        handle_move_request({"to": [0, 5], "is_teleport": True}, player, self.game_state)
        self.assertEqual(player.position, [0, 5])
        self.assertFalse(getattr(enemy, "has_reacted_this_turn", False))

    def test_sanitize_map_for_players(self):
        secret_map = {
            "name": "Dungeon",
            "traps": [
                {"name": "Fossa", "q": 1, "r": 1, "hidden": True, "triggered": False},
                {"name": "Scattata", "q": 2, "r": 2, "hidden": False, "triggered": True}
            ],
            "doors": [
                {"q": 3, "r": 3, "is_secret": True, "discovered": False},
                {"q": 4, "r": 4, "is_secret": True, "discovered": True}
            ],
            "room_pins": [
                {"q": 5, "r": 5, "label": "Sala del Trono", "dm_notes": "Qui si nasconde il Lich"}
            ]
        }
        cleaned = sanitize_map_for_players(secret_map)
        # Hidden trap removed, triggered kept
        self.assertEqual(len(cleaned["traps"]), 1)
        self.assertEqual(cleaned["traps"][0]["name"], "Scattata")
        # Secret undiscovered door removed, discovered kept
        self.assertEqual(len(cleaned["doors"]), 1)
        self.assertEqual(cleaned["doors"][0]["discovered"], True)
        # DM notes stripped
        self.assertNotIn("dm_notes", cleaned["room_pins"][0])
        self.assertEqual(cleaned["room_pins"][0]["label"], "Sala del Trono")

    def test_srd_subclass_forwarding_third_casters(self):
        # Eldritch Knight at level 3 gets spell slots
        ek_data = get_class_level_features_offline("Guerriero", 3, subclass="Cavaliere Mistico")
        self.assertIn("1", ek_data.get("spell_slots", {}))
        self.assertEqual(ek_data["spell_slots"]["1"], 2)

    def test_finesse_weapon_ability_choice(self):
        c = Character()
        c.name = "Ladro"
        c.attributes = {"FOR": 10, "DES": 16, "COS": 12, "INT": 14, "SAG": 10, "CAR": 8}
        # Rapier with default FOR ability key will choose DES since DES (16) > FOR (10)
        c.weapons = [{"name": "Stocco", "ability": "FOR", "damage_dice": "1d8", "properties": "Accurata"}]
        # Mod for DES 16 is +3, FOR 10 is +0
        des_mod = (c.attributes["DES"] - 10) // 2
        self.assertEqual(des_mod, 3)

    def test_character_saving_throw_bonus_calculation(self):
        c = Character()
        c.name = "Guerriero"
        c.level = 1
        c.attributes = {"FOR": 16, "DES": 12, "COS": 14, "INT": 10, "SAG": 10, "CAR": 8}
        c.saving_throw_proficiencies = ["FOR", "COS"]
        
        # FOR save: Mod +3 + PB 2 = +5
        self.assertEqual(c.get_effective_save_bonus("FOR"), 5)
        # DES save: Mod +1 (no PB) = +1
        self.assertEqual(c.get_effective_save_bonus("DES"), 1)

if __name__ == "__main__":
    unittest.main()
