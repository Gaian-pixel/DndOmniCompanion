import unittest
from unittest.mock import patch, MagicMock
import queue

from common.game_state import GameState, Player
from common.travel_data import (
    BIOMES, DANGER_LEVELS, TRAVEL_PACES,
    get_biome_presets, get_danger_presets, generate_biome_encounter,
    calculate_effective_sentinel_pp, resolve_night_camp_simulation
)
from common.protocol import (
    make_set_travel_params_request,
    make_set_watch_shifts_request,
    make_resolve_night_camp_request,
    make_generate_encounter_request
)
from server.rules.character import (
    handle_set_travel_params_request,
    handle_set_watch_shifts_request,
    handle_resolve_night_camp_request,
    handle_generate_encounter_request
)

class TestTravelManagerExtended(unittest.TestCase):

    def setUp(self):
        self.q = queue.Queue()
        self.gs = GameState(self.q)
        self.gs.current_map = {"width": 30, "height": 30}

        self.p1 = Player("Gildor")
        self.p1.hp = 20
        self.p1.max_hp = 30
        self.p1.is_party_member = True
        self.p1.conn = MagicMock()
        self.p1.full_sheet = {
            "race": "Elfo dei Boschi",
            "features": ["Trance", "Retaggio Fatato"],
            "attributes": {"FOR": 10, "DES": 16, "COS": 12, "INT": 12, "SAG": 16, "CAR": 10},
            "skills": {"Percezione": 3, "Sopravvivenza": 3},
            "has_darkvision": True
        }

        self.p2 = Player("Torvald")
        self.p2.hp = 25
        self.p2.max_hp = 35
        self.p2.is_party_member = True
        self.p2.conn = MagicMock()
        self.p2.full_sheet = {
            "race": "Umano",
            "attributes": {"FOR": 16, "DES": 10, "COS": 16, "INT": 10, "SAG": 10, "CAR": 10},
            "skills": {"Percezione": 0, "Sopravvivenza": 0},
            "has_darkvision": False
        }

        self.gs.players = [self.p1, self.p2]

    def test_biome_and_danger_presets(self):
        """Verifica i cataloghi dei biomi 5e e dei livelli di pericolo."""
        biomes = get_biome_presets("it")
        self.assertGreaterEqual(len(biomes), 8)
        b_keys = [b["key"] for b in biomes]
        self.assertIn("foresta", b_keys)
        self.assertIn("palude", b_keys)
        self.assertIn("montagna", b_keys)
        self.assertIn("sottosuolo", b_keys)

        dangers = get_danger_presets("it")
        self.assertEqual(len(dangers), 4)
        d_keys = [d["key"] for d in dangers]
        self.assertIn("safe", d_keys)
        self.assertIn("deadly", d_keys)
        self.assertEqual(DANGER_LEVELS["safe"]["encounter_threshold"], 18)
        self.assertEqual(DANGER_LEVELS["deadly"]["encounter_threshold"], 9)

    def test_random_encounter_generation(self):
        """Verifica la generazione di incontri strutturati (Combattimento, Sociale, Scoperta, Pericolo)."""
        enc_combat = generate_biome_encounter("foresta", "dangerous", force_category="combat", lang="it")
        self.assertTrue(enc_combat["occurred"])
        self.assertEqual(enc_combat["category"], "combat")
        self.assertTrue(len(enc_combat["monsters"]) > 0)
        self.assertIn("stealth_dc", enc_combat)
        self.assertIn("dist_hexes", enc_combat)

        enc_social = generate_biome_encounter("pianura", "moderate", force_category="social", lang="it")
        self.assertTrue(enc_social["occurred"])
        self.assertEqual(enc_social["category"], "social")
        self.assertIn("reward", enc_social)

        enc_hazard = generate_biome_encounter("palude", "moderate", force_category="hazard", lang="it")
        self.assertTrue(enc_hazard["occurred"])
        self.assertEqual(enc_hazard["category"], "hazard")
        self.assertIsNotNone(enc_hazard.get("save_stat"))
        self.assertIsNotNone(enc_hazard.get("save_dc"))

    def test_effective_sentinel_pp_and_elf_trance(self):
        """Verifica il calcolo della Percezione Passiva e la Trance Elfica 5e RAW."""
        # Gildor: Elfo con SAG 16 (+3) e Percezione +3 -> Base PP 16, Scurovisione True, Trance True
        st1 = calculate_effective_sentinel_pp(self.p1, has_campfire=True, is_night=True)
        self.assertEqual(st1["base_pp"], 16)
        self.assertEqual(st1["final_pp"], 16)
        self.assertTrue(st1["is_elf_trance"])
        self.assertEqual(st1["max_watch_hours"], 4)

        # Torvald: Umano senza Scurovisione né competenze -> Base PP 10, Trance False
        st2_fire = calculate_effective_sentinel_pp(self.p2, has_campfire=True, is_night=True)
        self.assertEqual(st2_fire["base_pp"], 10)
        self.assertEqual(st2_fire["final_pp"], 10) # Con falò non subisce penalità
        self.assertFalse(st2_fire["is_elf_trance"])
        self.assertEqual(st2_fire["max_watch_hours"], 2)

        # Torvald al buio senza falò -> Svantaggio (-5 PP)
        st2_dark = calculate_effective_sentinel_pp(self.p2, has_campfire=False, is_night=True)
        self.assertEqual(st2_dark["final_pp"], 5)

    def test_night_camp_simulation_peaceful(self):
        """Verifica la simulazione notturna quando non si verificano incontri."""
        shifts = {1: "Gildor", 2: "Torvald", 3: "Gildor", 4: "Nessuno"}
        with patch("common.travel_data.roll_dice", return_value={"total": 2}): # Tiro basso: nessun incontro
            res = resolve_night_camp_simulation(shifts, self.gs.players, "foresta", "safe", has_campfire=True)
        self.assertFalse(res["event_occurred"])
        self.assertFalse(res["ambush"])
        self.assertEqual(len(res["logs"]), 4)

    def test_night_camp_simulation_alert_vs_ambush(self):
        """Verifica che una sentinella attenta allerti il gruppo e una distratta causi imboscata."""
        shifts = {1: "Gildor", 2: "Torvald", 3: "Torvald", 4: "Gildor"}

        # Caso 1: L'incontro avviene nel Turno 1 (Gildor ha PP 16 vs DC 13) -> Allertati!
        mock_enc = {
            "occurred": True, "title": "Lupi", "category": "combat", "stealth_dc": 13
        }
        with patch("common.travel_data.generate_biome_encounter", return_value=mock_enc), \
             patch("random.randint", return_value=1): # Turno 1
            res1 = resolve_night_camp_simulation(shifts, self.gs.players, "foresta", "moderate", has_campfire=True)
        self.assertTrue(res1["alerted"])
        self.assertFalse(res1["ambush"])

        # Caso 2: L'incontro avviene nel Turno 2 (Torvald ha PP 10 vs DC 14) -> Imboscata!
        mock_enc2 = {
            "occurred": True, "title": "Goblin", "category": "combat", "stealth_dc": 14
        }
        with patch("common.travel_data.generate_biome_encounter", return_value=mock_enc2), \
             patch("random.randint", return_value=2): # Turno 2
            res2 = resolve_night_camp_simulation(shifts, self.gs.players, "foresta", "moderate", has_campfire=True)
        self.assertFalse(res2["alerted"])
        self.assertTrue(res2["ambush"])

    def test_handle_set_travel_params_request(self):
        """Verifica l'impostazione dei parametri di viaggio da protocollo."""
        req = make_set_travel_params_request(biome="montagna", danger="deadly", pace="Lenta", terrain="Rocce")
        handle_set_travel_params_request(req, None, self.gs)

        self.assertEqual(self.gs.travel_biome, "montagna")
        self.assertEqual(self.gs.travel_danger, "deadly")
        self.assertEqual(self.gs.travel_pace, "Lenta")
        self.assertEqual(self.gs.travel_terrain, "Rocce")

    def test_handle_set_watch_shifts_request(self):
        """Verifica la configurazione dei turni di guardia notturna da protocollo."""
        req = make_set_watch_shifts_request(
            shifts={"1": "Gildor", "2": "Torvald", "3": "Gildor", "4": "Torvald"},
            has_campfire=False
        )
        handle_set_watch_shifts_request(req, None, self.gs)

        self.assertEqual(self.gs.camp_watch_shifts.get("1"), "Gildor")
        self.assertFalse(self.gs.camp_has_campfire)

    def test_handle_resolve_night_camp_peaceful(self):
        """Verifica l'applicazione del Riposo Lungo notturno sereno sul server."""
        self.gs.time_hour = 22
        self.gs.travel_hours_today = 6
        self.gs.travel_miles_today = 18
        self.p1.exhaustion_level = 1

        with patch("common.travel_data.resolve_night_camp_simulation", return_value={"ambush": False, "logs": ["Notte serena"], "sentinel_name": "Gildor"}):
            handle_resolve_night_camp_request({}, None, self.gs)

        # L'ora deve avanzare di 8 ore (22 + 8 = 30 -> 6:00 del giorno dopo)
        self.assertEqual(self.gs.time_hour, 6)
        self.assertEqual(self.gs.travel_hours_today, 0)
        self.assertEqual(self.gs.travel_miles_today, 0)

        # Ripristino completo HP e rimozione di 1 livello di Sfinimento
        self.assertEqual(self.p1.hp, self.p1.max_hp)
        self.assertEqual(self.p1.exhaustion_level, 0)

    def test_handle_resolve_night_camp_ambush(self):
        """Verifica che un'imboscata notturna applichi le condizioni Incosciente e Prono ai dormienti."""
        self.gs.camp_watch_shifts = {1: "Gildor", 2: "Nessuno", 3: "Nessuno", 4: "Nessuno"}

        with patch("common.travel_data.resolve_night_camp_simulation", return_value={"ambush": True, "logs": ["Imboscata!"], "sentinel_name": "Gildor"}):
            handle_resolve_night_camp_request({}, None, self.gs)

        # Torvald stava dormendo: deve avere Incosciente e Prono
        self.assertIn("Incosciente", self.p2.conditions)
        self.assertIn("Prono", self.p2.conditions)
        # Gildor era la sentinella: non è Incosciente
        self.assertNotIn("Incosciente", self.p1.conditions)

    def test_travel_pace_mechanics(self):
        """Verifica le statistiche e penalità delle andature 5e RAW."""
        slow = TRAVEL_PACES["Lenta"]
        self.assertEqual(slow["speed_mph"], 2)
        self.assertEqual(slow["pp_modifier"], 5)
        self.assertTrue(slow["stealth_allowed"])

        fast = TRAVEL_PACES["Veloce"]
        self.assertEqual(fast["speed_mph"], 4)
        self.assertEqual(fast["pp_modifier"], -5)
        self.assertFalse(fast["forage_allowed"])

if __name__ == "__main__":
    unittest.main()
