import unittest
from unittest.mock import patch, MagicMock
import queue

from common.game_state import GameState, Player
from common.companions_data import (
    FAMILIAR_FORMS, BEAST_COMPANIONS, SUMMON_TEMPLATES,
    get_companion_presets, scale_beast_companion_stats,
    create_companion_player_dict
)
from common.protocol import (
    make_summon_companion_request,
    make_dismiss_familiar_request,
    make_deliver_touch_spell_request,
    make_attack_request
)
from server.rules.combat import (
    handle_summon_companion_request,
    handle_dismiss_familiar_request,
    handle_deliver_touch_spell_request,
    handle_attack_request,
    drop_concentration,
    _spawn_corpse_loot
)

class TestCompanionsFamiliarsSummons(unittest.TestCase):

    def setUp(self):
        self.q = queue.Queue()
        self.gs = GameState(self.q)
        self.gs.current_map = {"width": 30, "height": 30, "loots": []}

        self.master = Player("Gildor")
        self.master.hp = 25
        self.master.max_hp = 25
        self.master.position = [5, 5]
        self.master.is_party_member = True
        self.master.conn = MagicMock()
        self.master.full_sheet = {
            "attributes": {"FOR": 10, "DES": 16, "COS": 12, "INT": 14, "SAG": 16, "CAR": 10},
            "level": 5,
            "proficiency_bonus": 3
        }

        self.target = Player("Goblin")
        self.target.hp = 15
        self.target.max_hp = 15
        self.target.position = [6, 5] # Adiacente
        self.target.is_party_member = False
        self.target.conn = MagicMock()

        self.gs.players = [self.master, self.target]

    def test_presets_content_and_traits(self):
        """Verifica i cataloghi dei preset per famigli, compagni ranger ed evocazioni."""
        familiars = get_companion_presets("familiar", lang="it")
        self.assertGreaterEqual(len(familiars), 8)
        fam_keys = [f["key"] for f in familiars]
        self.assertIn("owl", fam_keys)
        self.assertIn("bat", fam_keys)
        self.assertIn("imp", fam_keys)

        owl = FAMILIAR_FORMS["owl"]
        self.assertFalse(owl["can_attack"])
        self.assertTrue(any("Flyby" in t for t in owl["traits"]))
        self.assertEqual(owl["vision_radius"], 24)

        bat = FAMILIAR_FORMS["bat"]
        self.assertFalse(bat["can_attack"])
        self.assertEqual(bat["blindsight"], 12)

        imp = FAMILIAR_FORMS["imp"]
        self.assertTrue(imp["can_attack"])
        self.assertIn("attack", imp)

        beasts = get_companion_presets("beast", lang="it")
        beast_keys = [b["key"] for b in beasts]
        self.assertIn("wolf", beast_keys)
        self.assertIn("panther", beast_keys)
        self.assertIn("giant_snake", beast_keys)

        summons = get_companion_presets("summon", lang="it")
        sum_keys = [s["key"] for s in summons]
        self.assertIn("skeleton", sum_keys)
        self.assertIn("conjured_wolf", sum_keys)
        self.assertIn("fey_spirit", sum_keys)
        self.assertTrue(SUMMON_TEMPLATES["conjured_wolf"]["concentration"])

    def test_beast_companion_scaling(self):
        """Verifica lo scaling 5e RAW del compagno animale del Ranger in base a livello e PB."""
        wolf_base = BEAST_COMPANIONS["wolf"]
        # Livello 3 Ranger, PB +2
        scaled_lvl3 = scale_beast_companion_stats(wolf_base, ranger_level=3, ranger_pb=2)
        self.assertEqual(scaled_lvl3["ac"], 13 + 2) # 15
        self.assertEqual(scaled_lvl3["max_hp"], max(11, 4 * 3)) # 12
        self.assertEqual(scaled_lvl3["attack"]["hit"], "+6")

        # Livello 8 Ranger, PB +3
        scaled_lvl8 = scale_beast_companion_stats(wolf_base, ranger_level=8, ranger_pb=3)
        self.assertEqual(scaled_lvl8["ac"], 13 + 3) # 16
        self.assertEqual(scaled_lvl8["max_hp"], max(11, 4 * 8)) # 32
        self.assertEqual(scaled_lvl8["attack"]["hit"], "+7")

    def test_create_companion_dict(self):
        """Verifica la generazione corretta del payload per istanziare un Player compagno."""
        comp_dict = create_companion_player_dict(
            companion_type="familiar",
            template_key="owl",
            master_player=self.master,
            custom_name="Edwige"
        )
        self.assertEqual(comp_dict["name"], "Edwige")
        self.assertEqual(comp_dict["master_name"], "Gildor")
        self.assertEqual(comp_dict["owner"], "Gildor")
        self.assertEqual(comp_dict["companion_type"], "familiar")
        self.assertTrue(comp_dict["is_companion"])
        self.assertFalse(comp_dict["can_attack"])
        self.assertEqual(comp_dict["position"], [6, 5])

    def test_handle_summon_companion_request(self):
        """Verifica l'evocazione via handler server e il vincolo di 1 solo famiglio attivo."""
        req1 = make_summon_companion_request(
            companion_type="familiar",
            template_key="owl",
            custom_name="Edwige"
        )
        handle_summon_companion_request(req1, self.master, self.gs)
        
        fam = self.gs.find_player("Edwige")
        self.assertIsNotNone(fam)
        self.assertEqual(fam.companion_type, "familiar")
        self.assertEqual(fam.master_name, "Gildor")
        self.assertIn(fam, self.gs.players)

        # Evoca un secondo famiglio: PHB p. 240 dice che il precedente svanisce
        req2 = make_summon_companion_request(
            companion_type="familiar",
            template_key="bat",
            custom_name="Shadow"
        )
        handle_summon_companion_request(req2, self.master, self.gs)
        self.assertIsNone(self.gs.find_player("Edwige"))
        new_fam = self.gs.find_player("Shadow")
        self.assertIsNotNone(new_fam)
        self.assertEqual(new_fam.companion_type, "familiar")

    def test_pocket_dimension_and_recall(self):
        """Verifica congedo temporaneo in tasca dimensionale e successivo richiamo."""
        req = make_summon_companion_request(
            companion_type="familiar",
            template_key="owl",
            custom_name="Edwige"
        )
        handle_summon_companion_request(req, self.master, self.gs)
        fam = self.gs.find_player("Edwige")

        # Congedo nella tasca dimensionale
        pocket_req = make_dismiss_familiar_request("Edwige", action="pocket")
        handle_dismiss_familiar_request(pocket_req, self.master, self.gs)
        self.assertTrue(fam.in_pocket_dimension)
        self.assertTrue(fam.is_hidden)

        # Richiamo dalla tasca dimensionale
        recall_req = make_dismiss_familiar_request("Edwige", action="recall")
        handle_dismiss_familiar_request(recall_req, self.master, self.gs)
        self.assertFalse(fam.in_pocket_dimension)
        self.assertFalse(fam.is_hidden)
        self.assertEqual(fam.position, [self.master.position[0] + 1, self.master.position[1]])

        # Congedo permanente
        dismiss_req = make_dismiss_familiar_request("Edwige", action="dismiss")
        handle_dismiss_familiar_request(dismiss_req, self.master, self.gs)
        self.assertNotIn(fam, self.gs.players)

    def test_deliver_touch_spell_success(self):
        """Verifica erogazione incantesimo a contatto 5e RAW tramite famiglio."""
        req = make_summon_companion_request(
            companion_type="familiar",
            template_key="owl",
            custom_name="Edwige"
        )
        handle_summon_companion_request(req, self.master, self.gs)
        fam = self.gs.find_player("Edwige")
        fam.position = [6, 5]
        self.target.position = [7, 5] # Distanza 1 dal famiglio, entro 20 dal padrone [5, 5]

        touch_req = make_deliver_touch_spell_request(
            familiar_name="Edwige",
            target_name="Goblin",
            spell_name="Stretta Folgorante",
            action_type="damage",
            formula="1d8",
            damage_type="Fulmine"
        )

        with patch("server.rules.combat.roll_dice", return_value={"total": 6, "rolls": [6]}):
            handle_deliver_touch_spell_request(touch_req, self.master, self.gs)

        self.assertTrue(getattr(fam, "has_reacted_this_turn", False))
        self.assertEqual(self.target.hp, 9) # 15 - 6

    def test_deliver_touch_spell_range_and_pocket_restrictions(self):
        """Verifica restrizioni di raggio e tasca dimensionale per incantesimi a contatto."""
        req = make_summon_companion_request(
            companion_type="familiar",
            template_key="owl",
            custom_name="Edwige"
        )
        handle_summon_companion_request(req, self.master, self.gs)
        fam = self.gs.find_player("Edwige")

        # 1. Troppo lontano dal padrone (> 20 esagoni / 100 ft)
        fam.position = [30, 30]
        self.target.position = [31, 30]
        touch_req = make_deliver_touch_spell_request("Edwige", "Goblin", "Stretta Folgorante", "damage", "1d8", "Fulmine")
        handle_deliver_touch_spell_request(touch_req, self.master, self.gs)
        self.assertEqual(self.target.hp, 15) # Nessun danno subito

        # 2. Famiglio vicino al padrone ma bersaglio non a portata di contatto (> 1 esagono dal famiglio)
        fam.position = [6, 5]
        self.target.position = [10, 5] # Distanza > 1
        handle_deliver_touch_spell_request(touch_req, self.master, self.gs)
        self.assertEqual(self.target.hp, 15)

        # 3. Famiglio nella tasca dimensionale
        self.target.position = [7, 5]
        fam.in_pocket_dimension = True
        handle_deliver_touch_spell_request(touch_req, self.master, self.gs)
        self.assertEqual(self.target.hp, 15)

    def test_familiar_attack_restrictions(self):
        """Verifica che i famigli standard non possano attaccare, mentre i famigli da Patto della Catena sì."""
        # Famiglio standard (Gufo)
        req_owl = make_summon_companion_request("familiar", "owl", "Edwige")
        handle_summon_companion_request(req_owl, self.master, self.gs)
        owl = self.gs.find_player("Edwige")

        owl_atk_req = make_attack_request(
            target_name="Goblin",
            weapon_name="Graffio",
            hit_bonus=3,
            damage_formula="1d4",
            damage_type="Tagliente"
        )
        handle_attack_request(owl_atk_req, owl, self.gs)
        self.assertEqual(self.target.hp, 15) # Bloccato dal server

        # Famiglio Patto della Catena (Imp)
        req_imp = make_summon_companion_request("familiar", "imp", "Pazuzu")
        handle_summon_companion_request(req_imp, self.master, self.gs)
        imp = self.gs.find_player("Pazuzu")
        self.assertTrue(imp.can_attack)

        imp_atk_req = make_attack_request(
            target_name="Goblin",
            weapon_name="Pungiglione",
            hit_bonus=5,
            damage_formula="1d4+3",
            damage_type="Perforante"
        )
        with patch("random.randint", return_value=15), patch("server.rules.combat.roll_dice", return_value={"total": 5, "rolls": [2]}):
            handle_attack_request(imp_atk_req, imp, self.gs)
        self.assertLess(self.target.hp, 15)

    def test_drop_concentration_dissolves_summons(self):
        """Verifica che l'interruzione della concentrazione dissolva solo le creature evocate, non i famigli."""
        self.master.conditions.append("Concentrazione")

        # Evoca un famiglio (permanente)
        req_fam = make_summon_companion_request("familiar", "owl", "Edwige")
        handle_summon_companion_request(req_fam, self.master, self.gs)

        # Evoca uno spirito fatato (evocazione legata a concentrazione)
        req_sum = make_summon_companion_request("summon", "fey_spirit", "Spirito Fatato")
        handle_summon_companion_request(req_sum, self.master, self.gs)

        self.assertIsNotNone(self.gs.find_player("Edwige"))
        self.assertIsNotNone(self.gs.find_player("Spirito Fatato"))

        # Il master perde la concentrazione
        drop_concentration(self.master, self.gs, notify=True)

        # Spirito fatato deve essere dissolto, il famiglio deve rimanere
        self.assertIsNone(self.gs.find_player("Spirito Fatato"))
        self.assertIsNotNone(self.gs.find_player("Edwige"))

    def test_corpse_loot_bypass_for_companions(self):
        """Verifica che la morte di compagni/famigli non generi forzieri di loot sulla mappa."""
        req_fam = make_summon_companion_request("familiar", "owl", "Edwige")
        handle_summon_companion_request(req_fam, self.master, self.gs)
        fam = self.gs.find_player("Edwige")

        _spawn_corpse_loot(fam, self.gs)
        self.assertEqual(len(self.gs.current_map.get("loots", [])), 0)

        # Mostro normale genera invece loot
        _spawn_corpse_loot(self.target, self.gs)
        self.assertEqual(len(self.gs.current_map.get("loots", [])), 1)

if __name__ == "__main__":
    unittest.main()
