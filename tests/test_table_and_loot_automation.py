import unittest
import queue
from unittest.mock import MagicMock, patch
from common.game_state import GameState, Player
from common.protocol import make_attack_request
from server.rules.combat import (
    _spawn_corpse_loot, recover_expended_ammunition, handle_attack_request
)
from server.rules.inventory import handle_take_loot_request
from server.rules.chat import handle_chat

class TestTableAndLootAutomation(unittest.TestCase):
    def setUp(self):
        self.game_state = GameState(gui_queue=queue.Queue())
        self.game_state.current_map = {
            "grid_type": "hex",
            "hex_size": 30,
            "walls": [],
            "loots": []
        }

        self.player = Player(name="Legolas", conn=MagicMock())
        self.player.hp = 25
        self.player.max_hp = 25
        self.player.position = [0, 0]
        self.player.full_sheet = {
            "class": "Ranger",
            "level": 3,
            "attributes": {"FOR": 10, "DES": 16, "COS": 14, "INT": 12, "SAG": 14, "CAR": 10},
            "inventory_grid": [
                {"name": "Frecce", "qty": 20, "type": "Munizioni", "weight": 1.0},
                None, None, None, None
            ],
            "wallet": {"MO": 10, "MA": 5}
        }

        self.monster = Player(name="Goblin Capo", conn=None)
        self.monster.hp = 0
        self.monster.max_hp = 15
        self.monster.position = [2, 2]
        self.monster.full_sheet = {
            "class": "Mostro",
            "cr": 2,
            "inventory_grid": [
                {"name": "Scimitarra Dentellata", "qty": 1, "type": "Arma", "weight": 3.0}
            ],
            "wallet": {"MO": 15, "MA": 8}
        }

        self.game_state.players = [self.player, self.monster]

    def test_monster_loot_spawn_with_coins_and_items(self):
        """Morte del mostro spawna un forziere con le monete e gli oggetti contenuti (DMG p. 133)."""
        _spawn_corpse_loot(self.monster, self.game_state)
        loots = self.game_state.current_map.get("loots", [])
        self.assertEqual(len(loots), 1)
        loot_obj = loots[0]
        self.assertEqual(loot_obj["q"], 2)
        self.assertEqual(loot_obj["r"], 2)
        self.assertEqual(loot_obj["item"], "Spoglie di Goblin Capo")
        self.assertIn("contents", loot_obj)
        self.assertEqual(loot_obj["contents"]["wallet"]["MO"], 15)
        self.assertEqual(len(loot_obj["contents"]["items"]), 1)
        self.assertEqual(loot_obj["contents"]["items"][0]["name"], "Scimitarra Dentellata")

    def test_loot_pickup_transfers_items_and_gold(self):
        """Raccogliere le spoglie trasferisce le monete e gli oggetti all'inventario del PG."""
        _spawn_corpse_loot(self.monster, self.game_state)
        # Muovi il giocatore sulle spoglie ed effettua il pickup
        self.player.position = [2, 2]
        handle_take_loot_request({"q": 2, "r": 2}, self.player, self.game_state)

        # Monete aggiunte: 10 + 15 = 25 MO, 5 + 8 = 13 MA
        p_wallet = self.player.full_sheet["wallet"]
        self.assertEqual(p_wallet["MO"], 25)
        self.assertEqual(p_wallet["MA"], 13)

        # Oggetto trasferito
        names = [it.get("name") for it in self.player.full_sheet["inventory_grid"] if isinstance(it, dict)]
        self.assertIn("Scimitarra Dentellata", names)
        # Il forziere è stato consumato dalla mappa
        self.assertEqual(len(self.game_state.current_map["loots"]), 0)

    def test_ranged_attack_tracks_expended_ammo(self):
        """Attaccare a distanza con un arco tiene traccia delle munizioni impiegate."""
        with patch("server.rules.combat.broadcast"), patch("random.randint", return_value=12):
            handle_attack_request({
                "target_name": "Goblin Capo",
                "weapon_name": "Arco Lungo",
                "hit_bonus": 5,
                "damage_formula": "1d8+3",
                "is_ranged": True
            }, self.player, self.game_state)

            self.assertTrue(hasattr(self.player, "expended_ammo"))
            self.assertEqual(self.player.expended_ammo.get("Frecce"), 1)

    def test_recover_expended_ammunition_50_percent(self):
        """Recupero munizioni ripristina il 50% arrotondato per difetto (PHB p. 146)."""
        self.player.expended_ammo = {"Frecce": 6}
        recovered = recover_expended_ammunition(self.player, self.game_state)
        self.assertEqual(recovered.get("Frecce"), 3)
        self.assertEqual(self.player.expended_ammo.get("Frecce"), 0)
        # Quantità frecce aggiornata: 20 iniziali + 3 = 23
        arrow_item = next(it for it in self.player.full_sheet["inventory_grid"] if isinstance(it, dict) and it.get("name") == "Frecce")
        self.assertEqual(arrow_item["qty"], 23)

    def test_end_combat_triggers_ammo_recovery(self):
        """Terminare il combattimento avvia automaticamente il recupero munizioni per il party."""
        self.player.expended_ammo = {"Frecce": 8}
        self.game_state.combat_active = True
        self.game_state.end_combat()
        self.assertEqual(self.player.expended_ammo.get("Frecce"), 0)
        arrow_item = next(it for it in self.player.full_sheet["inventory_grid"] if isinstance(it, dict) and it.get("name") == "Frecce")
        self.assertEqual(arrow_item["qty"], 24) # 20 + 4 (50% di 8)

    def test_chat_slash_command_ammo_recovery(self):
        """Il comando chat /recupera_munizioni attiva il recupero 50% RAW."""
        self.player.expended_ammo = {"Frecce": 4}
        handle_chat({"text": "/recupera_munizioni"}, self.player, self.game_state)
        self.assertEqual(self.player.expended_ammo.get("Frecce"), 0)

if __name__ == "__main__":
    unittest.main()
