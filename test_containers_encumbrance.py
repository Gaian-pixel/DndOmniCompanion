import unittest
from client.character_manager import Character, CONTAINERS


class TestContainersAndEncumbrance(unittest.TestCase):
    def setUp(self):
        self.char = Character(name="Kragmor", campaign="Lost Mines")
        self.char.attributes["FOR"] = 10 # STR 10 -> normal <= 50 lbs, encumbered <= 100 lbs, heavily <= 150 lbs, overloaded > 150 lbs
        self.char.speed = 30
        self.char.speed_unit = "ft"
        self.char.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
        self.char.inventory_grid = [None] * 25
        self.char.backpack_dropped = False

    def test_coin_weight_calculation(self):
        # 50 coins = 1 lb (PHB p. 143)
        self.char.currency["MO"] = 100
        self.assertEqual(self.char.get_carried_weight(), 2.0)

        self.char.currency["MR"] = 150
        # 250 coins total = 5.0 lbs
        self.assertEqual(self.char.get_carried_weight(), 5.0)

    def test_container_weight_distribution(self):
        # Item 1: Equipped sword (3 lbs)
        self.char.inventory_grid[0] = {
            "name": "Spada Lunga",
            "type": "Arma",
            "qty": 1,
            "weight": 3.0,
            "container": "equipped"
        }
        # Item 2: Backpack rations (10 lbs)
        self.char.inventory_grid[1] = {
            "name": "Razioni da Viaggio",
            "type": "Equipaggiamento",
            "qty": 5,
            "weight": 2.0,
            "container": "backpack"
        }
        # Item 3: Bag of Holding heavy chest (200 lbs)
        self.char.inventory_grid[2] = {
            "name": "Forziere Pesante",
            "type": "Altro",
            "qty": 1,
            "weight": 200.0,
            "container": "bag_of_holding"
        }
        # Item 4: Haversack spell components (15 lbs)
        self.char.inventory_grid[3] = {
            "name": "Componenti Magiche",
            "type": "Altro",
            "qty": 1,
            "weight": 15.0,
            "container": "haversack"
        }
        # Item 5: Mount tent (20 lbs)
        self.char.inventory_grid[4] = {
            "name": "Tenda da Campo",
            "type": "Equipaggiamento",
            "qty": 1,
            "weight": 20.0,
            "container": "mount"
        }

        # Carried should ONLY include equipped (3 lbs) + backpack (10 lbs) = 13.0 lbs
        self.assertEqual(self.char.get_carried_weight(), 13.0)

        # Check container contents tracking
        self.assertEqual(self.char.get_container_contents_weight("bag_of_holding"), 200.0)
        self.assertEqual(self.char.get_container_contents_weight("haversack"), 15.0)
        self.assertEqual(self.char.get_container_contents_weight("mount"), 20.0)
        self.assertEqual(self.char.get_container_contents_weight("backpack"), 10.0)
        self.assertEqual(self.char.get_container_contents_weight("equipped"), 3.0)

    def test_tactical_drop_backpack(self):
        # Equipped armor (40 lbs) + Backpack gear (30 lbs)
        self.char.inventory_grid[0] = {
            "name": "Corazza a Strisce",
            "type": "Armatura",
            "qty": 1,
            "weight": 40.0,
            "container": "equipped"
        }
        self.char.inventory_grid[1] = {
            "name": "Attrezzi da Scalatore",
            "type": "Attrezzi",
            "qty": 1,
            "weight": 30.0,
            "container": "backpack"
        }

        # Total carried with backpack worn = 70.0 lbs
        self.assertFalse(self.char.backpack_dropped)
        self.assertEqual(self.char.get_carried_weight(), 70.0)

        # Drop backpack on ground!
        dropped = self.char.toggle_drop_backpack()
        self.assertTrue(dropped)
        self.assertTrue(self.char.backpack_dropped)

        # Weight should now ONLY be the equipped armor (40.0 lbs)
        self.assertEqual(self.char.get_carried_weight(), 40.0)

        # Pick up backpack again!
        picked_up = self.char.toggle_drop_backpack()
        self.assertFalse(picked_up)
        self.assertFalse(self.char.backpack_dropped)
        self.assertEqual(self.char.get_carried_weight(), 70.0)

    def test_encumbrance_tiers_and_speed_penalty(self):
        # STR 10:
        # <= 50 lbs: Normal (speed 30, no penalty)
        # 51 - 100 lbs: Encumbered (-10 ft penalty -> speed 20)
        # 101 - 150 lbs: Heavily Encumbered (-20 ft penalty -> speed 10, Disadvantage)
        # > 150 lbs: Overloaded (speed 0)
        
        # 1. Normal (40 lbs)
        self.char.inventory_grid[0] = {"name": "Test", "type": "Arma", "qty": 1, "weight": 40.0, "container": "equipped"}
        enc = self.char.get_encumbrance_status()
        self.assertEqual(enc["tier"], "normal")
        self.assertEqual(enc["speed_penalty_ft"], 0)
        self.assertFalse(enc["disadvantage"])
        self.assertEqual(self.char.get_effective_speed(), 30)

        # 2. Encumbered (70 lbs)
        self.char.inventory_grid[0]["weight"] = 70.0
        enc = self.char.get_encumbrance_status()
        self.assertEqual(enc["tier"], "encumbered")
        self.assertEqual(enc["speed_penalty_ft"], 10)
        self.assertFalse(enc["disadvantage"])
        self.assertEqual(self.char.get_effective_speed(), 20)

        # 3. Heavily Encumbered (120 lbs)
        self.char.inventory_grid[0]["weight"] = 120.0
        enc = self.char.get_encumbrance_status()
        self.assertEqual(enc["tier"], "heavily_encumbered")
        self.assertEqual(enc["speed_penalty_ft"], 20)
        self.assertTrue(enc["disadvantage"])
        self.assertEqual(self.char.get_effective_speed(), 10)

        # 4. Overloaded (180 lbs)
        self.char.inventory_grid[0]["weight"] = 180.0
        enc = self.char.get_encumbrance_status()
        self.assertEqual(enc["tier"], "overloaded")
        self.assertEqual(self.char.get_effective_speed(), 0)

    def test_metric_speed_encumbrance(self):
        # In metric units (meters), base speed 9m
        self.char.speed = 9.0
        self.char.speed_unit = "m"
        
        # Encumbered -> -3.0 m penalty (speed becomes 6.0 m)
        self.char.inventory_grid[0] = {"name": "Test", "type": "Arma", "qty": 1, "weight": 80.0, "container": "equipped"}
        self.assertEqual(self.char.get_effective_speed(), 6.0)

        # Heavily Encumbered -> -6.0 m penalty (speed becomes 3.0 m)
        self.char.inventory_grid[0]["weight"] = 130.0
        self.assertEqual(self.char.get_effective_speed(), 3.0)

        # Overloaded -> speed becomes 0.0 m
        self.char.inventory_grid[0]["weight"] = 200.0
        self.assertEqual(self.char.get_effective_speed(), 0.0)

    def test_dropping_backpack_recovers_speed(self):
        # Character is heavily encumbered due to heavy backpack gear
        self.char.inventory_grid[0] = {"name": "Arma Leggera", "type": "Arma", "qty": 1, "weight": 10.0, "container": "equipped"}
        self.char.inventory_grid[1] = {"name": "Bottino Pesante", "type": "Equipaggiamento", "qty": 1, "weight": 120.0, "container": "backpack"}

        # Total carried = 130 lbs -> Heavily Encumbered, speed 10 ft
        self.assertEqual(self.char.get_encumbrance_status()["tier"], "heavily_encumbered")
        self.assertEqual(self.char.get_effective_speed(), 10)

        # Combat action: Sfila lo zaino a terra!
        self.char.toggle_drop_backpack()

        # Total carried is now only 10 lbs -> Normal tier, speed fully recovered to 30 ft!
        self.assertEqual(self.char.get_encumbrance_status()["tier"], "normal")
        self.assertEqual(self.char.get_effective_speed(), 30)

    def test_serialization_and_retrocompatibility(self):
        self.char.backpack_dropped = True
        self.char.inventory_grid[0] = {
            "name": "Spada Antica",
            "type": "Arma",
            "qty": 1,
            "weight": 3.5,
            "container": "equipped"
        }
        data = self.char.to_dict()
        self.assertTrue(data["backpack_dropped"])

        loaded = Character.from_dict(data)
        self.assertTrue(loaded.backpack_dropped)
        self.assertEqual(loaded.inventory_grid[0]["container"], "equipped")
        self.assertEqual(loaded.get_carried_weight(), 3.5)

        # Test legacy character without backpack_dropped field
        legacy_data = {"name": "OldHero", "level": 3, "attributes": {"FOR": 12}}
        legacy_char = Character.from_dict(legacy_data)
        self.assertFalse(legacy_char.backpack_dropped)
        self.assertEqual(legacy_char.get_carried_weight(), 0.0)


if __name__ == "__main__":
    unittest.main()

