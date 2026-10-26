import unittest
from unittest.mock import MagicMock
from queue import Queue
from common.dice import roll_dice
from common.game_state import GameState, Player
from common.network_utils import sanitize_map_for_players, broadcast
from server.rules.combat import handle_attack_request, _process_save_result
from server.rules.inventory import handle_give_item_request, handle_take_loot_request
from client.character_manager import Character

class TestAuditV14Fixes(unittest.TestCase):
    def setUp(self):
        self.game_state = GameState(Queue())
        self.game_state.current_map = {
            "walls": [],
            "doors": [],
            "traps": [],
            "loots": [],
            "fow_enabled": False,
            "hex_size": 60
        }

    def test_dice_damage_modifier_with_letter_d_preserved(self):
        """[Audit v14] Formule danni con 'd' nel nome descrittivo (freddo, contundente, acido, fendente)."""
        r_cold = roll_dice("1d8+4 freddo")
        self.assertEqual(r_cold["modifier"], 4)
        self.assertGreaterEqual(r_cold["total"], 5)
        self.assertLessEqual(r_cold["total"], 12)

        r_blunt = roll_dice("2d6+3 contundente")
        self.assertEqual(r_blunt["modifier"], 3)
        self.assertGreaterEqual(r_blunt["total"], 5)
        self.assertLessEqual(r_blunt["total"], 15)

        r_acid = roll_dice("1d4+2 acido")
        self.assertEqual(r_acid["modifier"], 2)

        r_slash = roll_dice("1d10+5 fendente")
        self.assertEqual(r_slash["modifier"], 5)

    def test_dice_constant_damage_formula(self):
        """[Audit v14] Formule a danno fisso o costante descrittiva senza dadi."""
        r_const = roll_dice("5 contundente")
        self.assertEqual(r_const["total"], 5)
        self.assertEqual(r_const["modifier"], 5)
        self.assertFalse(r_const["is_crit"])

        r_sum = roll_dice("5+2")
        self.assertEqual(r_sum["total"], 7)
        self.assertEqual(r_sum["modifier"], 7)

    def test_dice_bless_d20_detection(self):
        """[Audit v14] Presenza di 1d4 (Benedizione) non disabilita il d20 per colpi critici/fallimenti."""
        res = roll_dice("1d20+1d4+3")
        self.assertEqual(res["modifier"], 3)
        self.assertIn("natural_roll", res)
        self.assertGreaterEqual(res["natural_roll"], 1)
        self.assertLessEqual(res["natural_roll"], 20)

    def test_dodge_invalidated_by_incapacitated_or_zero_speed(self):
        """[Audit v14 RAW] Schivata decade se la creatura è incapacitata o ha velocità 0."""
        target = Player("Bersaglio")
        target.conditions = ["Schivata", "Incapacitato"]
        target.speed = 30
        target.hp = 20
        target.max_hp = 20

        attacker = Player("Attaccante")
        attacker.conditions = []
        attacker.hp = 20
        attacker.max_hp = 20

        self.game_state.players = [target, attacker]
        
        # Con bersaglio incapacitato, non deve ricevere svantaggio da Schivata
        # Eseguiamo un attacco simulato
        data = {
            "target_name": "Bersaglio",
            "weapon_name": "Stocco",
            "hit_bonus": 5,
            "damage_formula": "1d8+3",
            "damage_type": "Perforante"
        }
        # Non deve lanciare eccezioni
        handle_attack_request(data, attacker, self.game_state)

    def test_sneak_attack_weapon_restriction(self):
        """[Audit v14 RAW] Attacco Furtivo richiede arma accurata o a distanza."""
        rogue = Player("Ladro")
        rogue.char_class = "Ladro"
        rogue.level = 3
        rogue.full_sheet = {"class": "Ladro", "level": 3, "features": ["Attacco Furtivo"]}
        rogue.position = [0, 0]
        rogue.hp = 20
        rogue.max_hp = 20

        target = Player("Bersaglio")
        target.position = [1, 0]
        target.hp = 50
        target.max_hp = 50
        target.is_party_member = False

        ally = Player("Guerriero")
        ally.position = [1, 1]
        ally.hp = 30
        ally.max_hp = 30
        ally.is_party_member = True

        self.game_state.players = [rogue, target, ally]
        self.game_state.combat_active = True

        # Attacco con arma NON accurata (es. Spadone pesante a due mani)
        data_heavy = {
            "target_name": "Bersaglio",
            "weapon_name": "Spadone",
            "hit_bonus": 5,
            "damage_formula": "2d6",
            "damage_type": "Tagliente"
        }
        handle_attack_request(data_heavy, rogue, self.game_state)
        # Attacco furtivo NON deve essere stato consumato
        self.assertFalse(getattr(rogue, "sneak_attack_used_this_turn", False))

        # Attacco con arma accurata (Stocco)
        data_finesse = {
            "target_name": "Bersaglio",
            "weapon_name": "Stocco",
            "hit_bonus": 5,
            "damage_formula": "1d8",
            "damage_type": "Perforante"
        }
        handle_attack_request(data_finesse, rogue, self.game_state)
        self.assertTrue(getattr(rogue, "sneak_attack_used_this_turn", False))

    def test_sneak_attack_resets_on_turn_change(self):
        """[Audit v14 RAW] Attacco furtivo è una volta per turno, azzerato ad ogni cambio turno."""
        rogue = Player("Ladro")
        rogue.sneak_attack_used_this_turn = True
        self.game_state.players = [rogue]
        self.game_state.combat_active = True
        self.game_state.turn_order = ["Ladro"]
        self.game_state.turn_index = 0

        self.game_state.next_turn()
        self.assertFalse(rogue.sneak_attack_used_this_turn)

    def test_barbarian_rage_damage_bonus_and_scaling(self):
        """[Audit v14 RAW] Bonus danno Ira Barbarica solo per mischia e scalato per livello."""
        barb = Player("Barbaro")
        barb.conditions = ["Ira"]
        barb.full_sheet = {"class": "Barbaro", "level": 9}
        barb.position = [0, 0]
        barb.hp = 50
        barb.max_hp = 50

        target = Player("Orco")
        target.position = [1, 0]
        target.hp = 100
        target.max_hp = 100
        self.game_state.players = [barb, target]

        # Arco (a distanza) non riceve il bonus Ira
        data_ranged = {
            "target_name": "Orco",
            "weapon_name": "Arco Corto",
            "is_ranged": True,
            "hit_bonus": 10,
            "damage_formula": "1d6",
            "damage_type": "Perforante"
        }
        handle_attack_request(data_ranged, barb, self.game_state)
        # Livello 9 in mischia: riceve +3 bonus
        data_melee = {
            "target_name": "Orco",
            "weapon_name": "Ascia da Battaglia",
            "hit_bonus": 10,
            "damage_formula": "1d8",
            "damage_type": "Tagliente"
        }
        handle_attack_request(data_melee, barb, self.game_state)

    def test_inventory_give_stack_quantity_subtraction(self):
        """[Audit v14] Donazione di oggetti da stack sottrae solo la quantità donata."""
        sender = Player("Mittente")
        sender.full_sheet = {
            "inventory_grid": [
                {"name": "Freccia", "qty": 20, "weight": 0.05},
                None
            ]
        }
        sender.conn = MagicMock()

        recip = Player("Destinatario")
        recip.full_sheet = {
            "inventory_grid": [None, None]
        }
        recip.conn = MagicMock()

        self.game_state.players = [sender, recip]

        handle_give_item_request({"target_name": "Destinatario", "item": {"name": "Freccia", "qty": 5}}, sender, self.game_state)

        # Il mittente conserva 15 frecce nello slot 0
        sender_slot = sender.full_sheet["inventory_grid"][0]
        self.assertIsNotNone(sender_slot)
        self.assertEqual(sender_slot["qty"], 15)

        # Il destinatario riceve 5 frecce nello slot 0
        recip_slot = recip.full_sheet["inventory_grid"][0]
        self.assertIsNotNone(recip_slot)
        self.assertEqual(recip_slot["qty"], 5)

    def test_loot_chest_not_removed_if_inventory_full(self):
        """[Audit v14] Loot dalla mappa non viene cancellato se l'inventario del giocatore è pieno."""
        player = Player("Avventuriero")
        player.position = [2, 2]
        player.full_sheet = {
            "inventory_grid": [{"name": f"Oggetto {i}", "qty": 1} for i in range(25)]
        }
        player.conn = MagicMock()

        self.game_state.players = [player]
        self.game_state.current_map["loots"] = [
            {"q": 2, "r": 2, "item": "Gemma Preziosa", "qty": 1}
        ]

        handle_take_loot_request({"q": 2, "r": 2}, player, self.game_state)

        # Il forziere DEVE essere ancora presente sulla mappa!
        self.assertEqual(len(self.game_state.current_map["loots"]), 1)
        self.assertEqual(self.game_state.current_map["loots"][0]["item"], "Gemma Preziosa")

    def test_secret_doors_with_state_secret_sanitized(self):
        """[Audit v14 Sicurezza] Porte segrete con state == 'secret' rimosse per i giocatori."""
        raw_map = {
            "doors": [
                {"q": 1, "r": 1, "state": "secret", "is_secret": False, "discovered": False},
                {"q": 2, "r": 2, "state": "closed", "is_secret": False},
                {"q": 3, "r": 3, "state": "open", "is_secret": False}
            ],
            "traps": [
                {"q": 4, "r": 4, "hidden": True, "triggered": False}
            ]
        }
        clean = sanitize_map_for_players(raw_map)
        # La porta segreta con state == 'secret' deve essere filtrata
        self.assertEqual(len(clean["doors"]), 2)
        self.assertTrue(all(d.get("state") != "secret" for d in clean["doors"]))
        # La trappola nascosta deve essere filtrata
        self.assertEqual(len(clean["traps"]), 0)

    def test_character_bilingual_save_bonus(self):
        """[Audit v14] Normalizzazione multilingue attributi per Tiri Salvezza (DEX -> DES, STR -> FOR)."""
        char = Character("LadroAgile")
        char.level = 1 # PB = +2
        char.attributes = {"FOR": 10, "DES": 16, "COS": 12, "INT": 14, "SAG": 10, "CAR": 8}
        char.saving_throw_proficiencies = ["DES", "INT"]

        # Richiesta in inglese DEX
        dex_save = char.get_effective_save_bonus("DEX")
        # DES 16 -> mod +3, competente (+2) -> totale +5
        self.assertEqual(dex_save, 5)

        # Richiesta in inglese STR (non competente, FOR 10 -> +0)
        str_save = char.get_effective_save_bonus("STR")
        self.assertEqual(str_save, 0)

    def test_character_recalculate_ac(self):
        """[Audit v14 RAW] Ricalcolo dinamico CA con armature, scudo e destrezza."""
        char = Character("GuerrieroArmato")
        char.attributes = {"DES": 14, "COS": 14, "SAG": 10} # DES mod = +2
        
        # Senz'armatura: 10 + 2 = 12
        char.inventory_grid = []
        ac = char.recalculate_ac()
        self.assertEqual(ac, 12)

        # Equipaggia Giaco di Maglia (Media: base 13 + min(2, DES) = 15)
        char.inventory_grid = [
            {"name": "Giaco di Maglia", "type": "Armatura", "container": "equipped", "ac_base": 13}
        ]
        ac = char.recalculate_ac()
        self.assertEqual(ac, 15)

        # Equipaggia anche uno Scudo (+2 -> 17)
        char.inventory_grid.append(
            {"name": "Scudo di Ferro", "type": "Scudo", "container": "equipped"}
        )
        ac = char.recalculate_ac()
        self.assertEqual(ac, 17)

    def test_warlock_short_rest_pact_slots_only(self):
        """[Audit v14 RAW] Riposo breve del Warlock ricarica solo gli slot del Patto (cerchi <= 5)."""
        char = Character("WarlockPotente")
        char.char_class = "Warlock"
        char.spell_slots = {
            "3": {"current": 0, "max": 2},
            "6": {"current": 0, "max": 1} # Arcano Misterioso di 6° cerchio
        }
        char.short_rest(hd_to_spend=0)

        # Lo slot di 3° cerchio è ricaricato
        self.assertEqual(char.spell_slots["3"]["current"], 2)
        # Lo slot di 6° cerchio NON è ricaricato dal riposo breve!
        self.assertEqual(char.spell_slots["6"]["current"], 0)

if __name__ == "__main__":
    unittest.main()
