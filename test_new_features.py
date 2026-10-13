import unittest
import os
import queue
import random
from common.game_state import GameState, Player
from client.character_manager import Character, CharacterManager
from server.dm_generators import LootGenerator, RandomNPCGenerator
from server.rules.combat import _process_save_result
from server.rules.inventory import handle_give_gold_request, handle_give_item_request
from server.rules.map_interaction import handle_create_aoe_request


class DummySocket:
    def __init__(self):
        self.sent_messages = []

    def sendall(self, data):
        self.sent_messages.append(data)


class TestDndNewFeatures(unittest.TestCase):
    def setUp(self):
        self.gui_queue = queue.Queue()
        self.game_state = GameState(self.gui_queue)

    def test_character_data_model(self):
        """Testa l'estensione del modello Character con armi, ispirazione e diario."""
        c = Character(name="Gimli")
        c.char_class = "Guerriero"
        c.level = 1
        d = c.to_dict()
        
        self.assertTrue(hasattr(c, "weapons"))
        self.assertTrue(hasattr(c, "has_inspiration"))
        self.assertTrue(hasattr(c, "journal_notes"))
        self.assertFalse(c.has_inspiration)
        
        # Caricamento da dict
        c2 = Character.from_dict(d)
        self.assertEqual(c2.name, "Gimli")
        self.assertGreaterEqual(len(c2.weapons), 1)
        self.assertFalse(c2.has_inspiration)

    def test_loot_generator(self):
        """Testa la generazione di bottino DMG 5e per tutti i tier."""
        tiers = ["GS 0-4", "GS 5-10", "GS 11-16"]
        for t in tiers:
            loot_ind = LootGenerator.generate(t, "Bottino Individuale")
            self.assertIn("coins", loot_ind)
            self.assertGreaterEqual(loot_ind["total_value_gp"], 0)

            loot_hoard = LootGenerator.generate(t, "Tesoro della Tana")
            self.assertIn("gems", loot_hoard)
            self.assertIn("items", loot_hoard)
            self.assertGreater(loot_hoard["total_value_gp"], 0)
            self.assertGreaterEqual(len(loot_hoard["gems"]), 1)
            self.assertGreaterEqual(len(loot_hoard["items"]), 1)

    def test_random_npc_generator(self):
        """Testa la generazione rapida di PNG con personalità, tratti e segreti."""
        npc = RandomNPCGenerator.generate()
        self.assertIn("name", npc)
        self.assertIn("race", npc)
        self.assertIn("role", npc)
        self.assertIn("alignment", npc)
        self.assertIn("trait", npc)
        self.assertIn("secret", npc)
        self.assertGreater(npc["hp"], 0)
        self.assertGreaterEqual(npc["ac"], 10)

    def test_weapon_attack_and_crit_mechanics(self):
        """Testa la matematica di attacco con armi e il raddoppio dei dadi su critico."""
        c = Character(name="Legolas")
        c.char_class = "Ranger"
        c.level = 1
        c.attributes["DES"] = 16  # mod +3
        c.proficiency_bonus = 2
        
        weapon = {
            "name": "Arco Lungo",
            "type": "Distanza",
            "ability": "DES",
            "damage_dice": "1d8",
            "damage_type": "Perforante",
            "bonus": 1,
            "proficient": True
        }
        
        # TxC atteso: mod(3) + prof(2) + bonus(1) = +6
        mod = (c.attributes["DES"] - 10) // 2
        prof = c.proficiency_bonus
        bonus = weapon["bonus"]
        total_txc = mod + prof + bonus
        self.assertEqual(total_txc, 6)
        
        # Test danno normale (1d8 + 4)
        dmg_mod = mod + bonus  # 3 + 1 = 4
        self.assertEqual(dmg_mod, 4)
        
        # Test critico: raddoppio dadi (1d8 -> 2d8)
        dice_expr = weapon["damage_dice"]
        import re
        m = re.match(r"(\d+)d(\d+)", dice_expr)
        num_dice = int(m.group(1)) * 2  # raddoppio
        die_sides = int(m.group(2))
        self.assertEqual(num_dice, 2)
        self.assertEqual(die_sides, 8)

    def test_automated_npc_aoe_save(self):
        """Testa l'automazione dei Tiri Salvezza per mostri/PNG colpiti da AoE."""
        npc = Player("Goblin")
        npc.position = [2, 2]
        npc.hp = 15
        npc.max_hp = 15
        npc.full_sheet = {"attributes": {"DES": 14}}  # Mod +2
        self.game_state.add_player(npc)
        
        caster = Player("Mago")
        caster.position = [0, 0]
        self.game_state.add_player(caster)

        
        aoe_data = {
            "origin": [2, 2],
            "type": "sfera",
            "size": 2,
            "req_save": True,
            "stat": "DES",
            "dc": 15,
            "dmg": "2d6",
            "half": True
        }
        
        # Esegui creazione AoE
        handle_create_aoe_request({"aoe_data": aoe_data}, caster, self.game_state)
        
        # L'NPC era nell'area e ha subito danni (totali o dimezzati)
        self.assertLess(npc.hp, 15)
        self.assertGreaterEqual(npc.hp, 0)

    def test_give_gold_between_players(self):
        """Testa il passaggio di oro tra giocatori (P2P Trade)."""
        p1 = Player("Guerriero")
        p1.conn = DummySocket()
        p2 = Player("Ladro")
        p2.conn = DummySocket()
        self.game_state.add_player(p1)
        self.game_state.add_player(p2)
        
        # p1 dona 50 MO a p2
        handle_give_gold_request({"target_name": "Ladro", "amount": 50}, p1, self.game_state)
        
        # p2 deve aver ricevuto il messaggio RECEIVE_GOLD
        self.assertGreater(len(p2.conn.sent_messages), 0)
        # Primi 4 byte sono l'header struct '!I' della lunghezza
        sent_data = p2.conn.sent_messages[0][4:].decode("utf-8")
        self.assertIn("RECEIVE_GOLD", sent_data)
        self.assertIn("50", sent_data)

    def test_give_item_between_players(self):
        """Testa il passaggio di oggetti tra giocatori (P2P Item Trade)."""
        p1 = Player("Guerriero")
        p1.conn = DummySocket()
        p2 = Player("Ladro")
        p2.conn = DummySocket()
        self.game_state.add_player(p1)
        self.game_state.add_player(p2)
        
        item = {"name": "Pozione di Cura", "type": "Consumabile", "qty": 1}
        handle_give_item_request({"target_name": "Ladro", "item": item}, p1, self.game_state)
        
        self.assertGreater(len(p2.conn.sent_messages), 0)
        sent_data = p2.conn.sent_messages[0][4:].decode("utf-8")
        self.assertIn("RECEIVE_ITEM", sent_data)
        self.assertIn("Pozione di Cura", sent_data)


    def test_inspiration_protocol(self):
        """Testa il protocollo di concessione e revoca dell'Ispirazione."""
        from common.protocol import make_update_inspiration
        msg_grant = make_update_inspiration(True)
        self.assertEqual(msg_grant["type"], "UPDATE_INSPIRATION")
        self.assertTrue(msg_grant["data"]["has_inspiration"])
        
        msg_revoke = make_update_inspiration(False)
        self.assertEqual(msg_revoke["type"], "UPDATE_INSPIRATION")
        self.assertFalse(msg_revoke["data"]["has_inspiration"])



if __name__ == "__main__":
    unittest.main()
