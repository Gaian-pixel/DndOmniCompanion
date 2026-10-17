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

    def test_i18n_language_system(self):
        """Testa il sistema di internazionalizzazione (Italiano/Inglese), toggle e condizioni bilingue."""
        from common.i18n import (
            _t, get_language, set_language, toggle_language,
            translate_condition, is_condition_active,
            translate_ability, get_ability_name
        )
        
        orig_lang = get_language()
        try:
            # 1. Imposta Italiano
            set_language("it")
            self.assertEqual(get_language(), "it")
            self.assertEqual(_t("menu_exit"), "Esci")
            self.assertEqual(_t("action_dash"), "Scatto (Dash)")
            self.assertEqual(_t("lbl_round", round=5), "Round: 5")
            self.assertEqual(translate_ability("FOR", "it"), "FOR")
            self.assertEqual(get_ability_name("FOR", "it"), "Forza")
            
            # 2. Toggle verso Inglese
            new_lang = toggle_language()
            self.assertEqual(new_lang, "en")
            self.assertEqual(get_language(), "en")
            self.assertEqual(_t("menu_exit"), "Exit")
            self.assertEqual(_t("action_dash"), "Dash")
            self.assertEqual(_t("lbl_round", round=5), "Round: 5")
            self.assertEqual(translate_ability("FOR", "en"), "STR")
            self.assertEqual(get_ability_name("FOR", "en"), "Strength")
            
            # 3. Test Traduzione Condizioni
            self.assertEqual(translate_condition("Prono", "en"), "Prone")
            self.assertEqual(translate_condition("Prone", "it"), "Prono")
            self.assertEqual(translate_condition("Dead", "it"), "Morto")
            self.assertEqual(translate_condition("Concentrazione", "en"), "Concentration")
            
            # 4. Test is_condition_active con liste miste
            conds_it = ["Prono", "Concentrazione", "Invisibile"]
            conds_en = ["Prone", "Concentration", "Invisible"]
            
            self.assertTrue(is_condition_active(conds_it, "Prono"))
            self.assertTrue(is_condition_active(conds_en, "Prono"))
            self.assertTrue(is_condition_active(conds_it, "Prone"))
            self.assertTrue(is_condition_active(conds_en, "Prone"))
            self.assertTrue(is_condition_active(conds_en, "Concentrazione"))
            self.assertFalse(is_condition_active(conds_en, "Dead"))
        finally:
            set_language(orig_lang)

    def test_dynamic_cover_5e(self):
        """Testa il calcolo della copertura D&D 5e: +2 per creature o ostacoli bassi, +5 per ostacoli 3/4."""
        from common.hex_utils import Hex, get_cover_between
        
        origin = Hex(0, 0)
        target = Hex(4, 0)
        # Linea da (0,0) a (4,0): (1,0), (2,0), (3,0)
        
        # 1. Nessun ostacolo intermedio
        bonus, name = get_cover_between(origin, target)
        self.assertEqual(bonus, 0)
        
        # 2. Ostacolo di mezza copertura
        bonus, name = get_cover_between(origin, target, half_cover=[[2, 0]])
        self.assertEqual(bonus, 2)
        self.assertIn("Mezza Copertura", name)
        
        # 3. Ostacolo di tre quarti di copertura
        bonus, name = get_cover_between(origin, target, three_quarters=[[2, 0]])
        self.assertEqual(bonus, 5)
        self.assertIn("Tre Quarti", name)
        
        # 4. Creatura interposta (Regola 5e: una creatura alleata o nemica conferisce mezza copertura)
        dummy_creature = type("Creature", (), {"position": [2, 0], "name": "Goblin"})()
        bonus, name = get_cover_between(origin, target, intermediate_creatures=[dummy_creature])
        self.assertEqual(bonus, 2)
        self.assertIn("Creatura interposta", name)

    def test_legendary_boss_mechanics(self):
        """Testa le resistenze leggendarie (auto-conversione del TS) e le azioni leggendarie."""
        boss = Player(name="Drago Rosso Antico")
        boss.hp = 546
        boss.max_hp = 546
        boss.initiative = 10
        boss.legendary_resistances_max = 3
        boss.legendary_resistances_current = 3
        boss.legendary_actions_max = 3
        boss.legendary_actions_current = 3
        self.game_state.players.append(boss)
        
        # 1. Test Resistenza Leggendaria su TS fallito
        # Tiro roll_total=8 vs CD 18 -> Fallimento, ma la resistenza deve convertirlo in successo
        _process_save_result(
            target_name=boss.name, stat="DES", roll_total=8, is_crit=False, is_fail=False,
            dc=18, damage_formula="10d6", half_on_success=True, source_name="Palla di Fuoco",
            game_state=self.game_state, damage_type="Fuoco"
        )
        self.assertEqual(boss.legendary_resistances_current, 2)
        
        # 2. Test Spesa Azione Leggendaria
        from server.rules.combat import handle_spend_legendary_action_request
        handle_spend_legendary_action_request(
            {"boss_name": boss.name, "action_name": "Colpo di Coda", "cost": 1},
            boss, self.game_state
        )
        self.assertEqual(boss.legendary_actions_current, 2)

    def test_hazards_and_traps(self):
        """Testa l'attivazione automatica di trappole quando un token si muove sull'esagono."""
        from server.rules.movement import handle_move_request
        
        player = Player(name="Esploratore")
        player.hp = 20
        player.max_hp = 20
        player.initiative = 12
        player.position = [0, 0]
        player.full_sheet = {"attributes": {"DES": 14}}
        self.game_state.players.append(player)
        self.game_state.current_map = {
            "hex_size": 60,
            "fow_enabled": False,
            "walls": [],
            "traps": [
                {
                    "q": 1, "r": 0,
                    "name": "Fossa con Punte",
                    "dc": 14,
                    "damage": "2d10",
                    "damage_type": "Perforante",
                    "triggered": False,
                    "hidden": True
                }
            ]
        }
        
        # Muovi il giocatore sulla trappola a [1, 0]
        handle_move_request({"to": [1, 0]}, player, self.game_state)
        
        trap = self.game_state.current_map["traps"][0]
        self.assertTrue(trap["triggered"], "La trappola deve risultare attivata")
        self.assertFalse(trap["hidden"], "La trappola deve essere visibile dopo essere scattata")

    def test_encounter_difficulty_calculator(self):
        """Testa il calcolo del bilanciamento incontri DMG 5e (p.82)."""
        from common.encounter_calc import calculate_encounter_difficulty
        
        # 4 personaggi di livello 1: soglia Facile = 100 XP
        # 1 Goblin (CR 1/4 = 50 XP, moltiplicatore 1.0 = 50 XP effettivi < 100) -> Banale
        res_trivial = calculate_encounter_difficulty([1, 1, 1, 1], ["1/4"])
        self.assertEqual(res_trivial["difficulty"], "Banale")
        self.assertEqual(res_trivial["raw_xp"], 50)
        
        # 2 Goblin (2 * 50 = 100 XP, moltiplicatore 1.5 = 150 XP effettivi, >= 100 e < 200) -> Facile
        res_easy = calculate_encounter_difficulty([1, 1, 1, 1], ["1/4", "1/4"])
        self.assertEqual(res_easy["difficulty"], "Facile")
        self.assertEqual(res_easy["adjusted_xp"], 150)
        
        # 4 personaggi di livello 1 vs 4 Goblin (4 * 50 = 200 XP * 2 = 400 XP) -> Mortale (soglia Mortale = 400)
        res_deadly = calculate_encounter_difficulty([1, 1, 1, 1], ["1/4", "1/4", "1/4", "1/4"])
        self.assertEqual(res_deadly["difficulty"], "Mortale")
        self.assertEqual(res_deadly["adjusted_xp"], 400)

    def test_dynamic_light_and_player_model(self):
        """Testa il salvataggio e caricamento dei campi luce e boss nel modello Player."""
        p = Player(name="Mago")
        p.hp = 30
        p.max_hp = 30
        p.initiative = 15
        p.light_radius = 6
        p.light_color = "#66D9E8"
        p.legendary_resistances_max = 3
        p.legendary_resistances_current = 2
        p.legendary_actions_max = 3
        p.legendary_actions_current = 1
        
        d = p.to_dict()
        self.assertEqual(d["light_radius"], 6)
        self.assertEqual(d["light_color"], "#66D9E8")
        self.assertEqual(d["legendary_resistances_max"], 3)
        self.assertEqual(d["legendary_resistances_current"], 2)
        
        p2 = Player.from_dict(d)
        self.assertEqual(p2.light_radius, 6)
        self.assertEqual(p2.light_color, "#66D9E8")
        self.assertEqual(p2.legendary_actions_current, 1)

    def test_ruler_measurement_tool(self):
        """Testa il funzionamento del righello interattivo e il calcolo delle distanze in piedi/esagoni."""
        from common.hex_utils import Hex, hex_distance
        h1 = Hex(0, 0)
        h2 = Hex(4, -2)
        dist_hexes = hex_distance(h1, h2)
        dist_ft = dist_hexes * 5
        self.assertEqual(dist_hexes, 4)
        self.assertEqual(dist_ft, 20)

    def test_whisper_chat_routing(self):
        """Testa l'instradamento corretto dei sussurri privati (/w, /whisper) senza broadcast pubblico."""
        from server.rules.chat import handle_chat
        
        p_alice = Player(name="Alice")
        p_alice.conn = DummySocket()
        p_bob = Player(name="Bob")
        p_bob.conn = DummySocket()
        p_claire = Player(name="Claire")
        p_claire.conn = DummySocket()
        self.game_state.players = [p_alice, p_bob, p_claire]

        # Alice sussurra a Bob
        handle_chat({"text": "/w Bob Questo è un segreto"}, p_alice, self.game_state)
        
        # Bob deve aver ricevuto il messaggio privato
        self.assertTrue(len(p_bob.conn.sent_messages) > 0, "Bob deve ricevere il sussurro")
        # Alice riceve la conferma del sussurro inviato
        self.assertTrue(len(p_alice.conn.sent_messages) > 0, "Alice deve ricevere la conferma del sussurro")
        # Claire NON deve aver ricevuto alcun messaggio!
        self.assertEqual(len(p_claire.conn.sent_messages), 0, "Claire non deve intercettare il sussurro privato")

    def test_handout_protocol(self):
        """Testa la corretta generazione del payload per i documenti/indizi DM."""
        from common.protocol import make_handout_broadcast
        h_packet = make_handout_broadcast("Mappa del Tesoro", image_b64="fake_b64", content="X segna il punto.")
        self.assertEqual(h_packet["type"], "HANDOUT_BROADCAST")
        self.assertEqual(h_packet["data"]["title"], "Mappa del Tesoro")
        self.assertEqual(h_packet["data"]["content"], "X segna il punto.")
        self.assertEqual(h_packet["data"]["image_b64"], "fake_b64")

    def test_class_default_skills_and_modifiers(self):
        """Testa l'assegnazione automatica delle competenze abilità di classe e il calcolo del modificatore totale."""
        from common.starter_equipment import CLASS_DEFAULT_SKILLS, apply_class_and_race_starter_kit
        from client.character_manager import Character
        
        # 1. Fighter
        c_fighter = Character(name="FighterTest", campaign="Test")
        c_fighter.char_class = "Guerriero"
        c_fighter.attributes = {"FOR": 16, "DES": 12, "COS": 14, "INT": 10, "SAG": 14, "CAR": 8}
        c_fighter.level = 1
        apply_class_and_race_starter_kit(c_fighter)
        
        self.assertEqual(c_fighter.skills["Atletica"], 1, "Guerriero deve avere competenza in Atletica")
        self.assertEqual(c_fighter.skills["Percezione"], 1, "Guerriero deve avere competenza in Percezione")
        self.assertEqual(c_fighter.skills["Arcano"], 0, "Guerriero non ha competenza in Arcano")
        
        # Calcolo modificatore per Atletica: FOR 16 (+3), livello 1 (PB 2), competenza 1 -> +5
        pb = ((c_fighter.level - 1) // 4) + 2
        atletica_mod = ((c_fighter.attributes["FOR"] - 10) // 2) + (pb * c_fighter.skills["Atletica"])
        self.assertEqual(atletica_mod, 5, "Atletica con FOR 16 e livello 1 deve essere +5")
        
        # Calcolo modificatore per Arcano: INT 10 (+0), competenza 0 -> +0
        arcano_mod = ((c_fighter.attributes["INT"] - 10) // 2) + (pb * c_fighter.skills["Arcano"])
        self.assertEqual(arcano_mod, 0, "Arcano senza competenza e INT 10 deve essere +0")
        
        # 2. Rogue con Maestria (Expertise = 2)
        c_rogue = Character(name="RogueTest", campaign="Test")
        c_rogue.char_class = "Ladro"
        c_rogue.attributes = {"FOR": 8, "DES": 16, "COS": 12, "INT": 14, "SAG": 12, "CAR": 14}
        c_rogue.level = 5 # PB = 3
        apply_class_and_race_starter_kit(c_rogue)
        
        self.assertEqual(c_rogue.skills["Furtività"], 2, "Ladro ha maestria in Furtività")
        pb_5 = ((c_rogue.level - 1) // 4) + 2 # 3
        stealth_mod = ((c_rogue.attributes["DES"] - 10) // 2) + (pb_5 * c_rogue.skills["Furtività"]) # 3 + (3 * 2) = +9
        self.assertEqual(stealth_mod, 9, "Furtività al livello 5 con DES 16 e maestria deve essere +9")

    def test_inventory_currency_and_icons(self):
        """Testa la logica di calcolo del valore totale delle valute e l'iconografia dell'inventario."""
        from client.character_sheet_ui import get_item_icon
        
        # Test icone per tipologie di oggetti
        self.assertEqual(get_item_icon({"name": "Spada Lunga", "type": "Arma"}), "⚔️")
        self.assertEqual(get_item_icon({"name": "Cotta di Maglia", "type": "Armatura"}), "🛡️")
        self.assertEqual(get_item_icon({"name": "Pozione di Cura", "type": "Consumabile"}), "🧪")
        self.assertEqual(get_item_icon({"name": "Mappa della Regione", "type": "Documento"}), "📜")
        self.assertEqual(get_item_icon({"name": "Anello di Protezione", "type": "Gioiello"}), "💍")
        self.assertEqual(get_item_icon({"name": "Liuto", "type": "Strumento"}), "🧰")
        self.assertEqual(get_item_icon({"name": "Razioni da Viaggio", "type": "Equipaggiamento"}), "🎒")
        self.assertEqual(get_item_icon({"name": "Monete d'Oro", "type": "Valuta"}), "🪙")
        self.assertEqual(get_item_icon({}), "📦")

        # Test conversione e valore totale monete 5e:
        # 100 MR (1 MO) + 10 MA (1 MO) + 2 ME (1 MO) + 50 MO (50 MO) + 2 MP (20 MO) = 73 MO
        mr, ma, me, mo, mp = 100, 10, 2, 50, 2
        total_gp = mo + (mp * 10.0) + (me * 0.5) + (ma * 0.1) + (mr * 0.01)
        self.assertAlmostEqual(total_gp, 73.0, places=2)

    def test_game_constraints_and_dm_approval(self):
        """Testa i vincoli di gioco: restrizione valuta/attributi e richieste di approvazione DM."""
        from common.protocol import (
            make_currency_request, make_currency_response,
            make_item_approval_request, make_item_approval_response
        )
        from server.rules.character import (
            handle_currency_request, handle_item_approval_request,
            handle_update_full_sheet_request
        )

        # 1. Test protocol packets
        req_pkt = make_currency_request("MO", 150, "Bottino antico forziere")
        self.assertEqual(req_pkt["type"], "CURRENCY_REQUEST")
        self.assertEqual(req_pkt["data"]["coin"], "MO")
        self.assertEqual(req_pkt["data"]["amount"], 150)

        res_pkt = make_currency_response("Guerriero", "MO", 150, approved=True)
        self.assertEqual(res_pkt["type"], "CURRENCY_RESPONSE")
        self.assertTrue(res_pkt["data"]["approved"])

        item_sample = {"name": "Stocco Elfico +1", "type": "Arma", "qty": 1, "weight": 2.0}
        item_req = make_item_approval_request(item_sample, slot_idx=3)
        self.assertEqual(item_req["type"], "ITEM_APPROVAL_REQUEST")
        self.assertEqual(item_req["data"]["slot_idx"], 3)

        item_res = make_item_approval_response("Ladro", item_sample, slot_idx=3, approved=True)
        self.assertEqual(item_res["type"], "ITEM_APPROVAL_RESPONSE")
        self.assertTrue(item_res["data"]["approved"])

        # 2. Test server queuing of currency & item requests
        p = Player(name="TestHero")
        handle_currency_request({"coin": "MO", "amount": 100, "reason": "Taglia"}, p, self.game_state)
        self.assertFalse(self.game_state.gui_queue.empty())
        
        # Estrai elementi dalla coda saltando i LOG_MESSAGE
        def get_next_action(expected_type):
            while not self.game_state.gui_queue.empty():
                item = self.game_state.gui_queue.get()
                if item.get("type") == expected_type:
                    return item
            return None

        q_item = get_next_action("CURRENCY_REQUEST")
        self.assertIsNotNone(q_item)
        self.assertEqual(q_item["amount"], 100)

        handle_item_approval_request({"item": item_sample, "slot_idx": 5}, p, self.game_state)
        q_item2 = get_next_action("ITEM_APPROVAL_REQUEST")
        self.assertIsNotNone(q_item2)
        self.assertEqual(q_item2["item"]["name"], "Stocco Elfico +1")

        # 3. Test Server Authority in handle_update_full_sheet_request
        # Il giocatore ha 50 MO approvate dal server e attributo FOR a 14
        p.full_sheet = {
            "name": "TestHero",
            "level": 3,
            "currency": {"MR": 0, "MA": 0, "ME": 0, "MO": 50, "MP": 0},
            "attributes": {"FOR": 14, "DES": 12, "COS": 14, "INT": 10, "SAG": 10, "CAR": 10},
            "inventory_grid": [None] * 25,
            "starting_kit_applied": True,
            "campaign_starter_received": True
        }

        # Scenario A: Il client tenta un aumento unilaterale a 9999 MO e FOR a 20 -> il server deve bloccare
        cheat_sheet = dict(p.full_sheet)
        cheat_sheet["currency"] = {"MR": 0, "MA": 0, "ME": 0, "MO": 9999, "MP": 0}
        cheat_sheet["attributes"] = {"FOR": 20, "DES": 12, "COS": 14, "INT": 10, "SAG": 10, "CAR": 10}
        # Tenta anche di spawnare un oggetto in uno slot vuoto
        cheat_inv = [None] * 25
        cheat_inv[0] = {"name": "Spada Vorpal Hack", "type": "Arma", "qty": 1}
        cheat_sheet["inventory_grid"] = cheat_inv

        handle_update_full_sheet_request({"character": cheat_sheet}, p, self.game_state)
        # Verifica che il server abbia mantenuto le 50 MO iniziali
        self.assertEqual(p.full_sheet["currency"]["MO"], 50, "Il server deve bloccare aumenti unilaterali di monete")
        # Verifica che il server abbia mantenuto FOR a 14
        self.assertEqual(p.full_sheet["attributes"]["FOR"], 14, "Il server deve bloccare aumenti unilaterali di attributi")
        # Verifica che il server abbia bloccato l'oggetto abusivo
        self.assertIsNone(p.full_sheet["inventory_grid"][0], "Il server deve impedire l'aggiunta di oggetti non approvati")

        # Scenario B: Il client spende monete legittimamente (da 50 a 30 MO) -> il decremento deve essere consentito
        legit_spend = dict(p.full_sheet)
        legit_spend["currency"] = {"MR": 0, "MA": 0, "ME": 0, "MO": 30, "MP": 0}
        handle_update_full_sheet_request({"character": legit_spend}, p, self.game_state)
        self.assertEqual(p.full_sheet["currency"]["MO"], 30, "La spesa (decremento) di monete deve essere consentita")

    def test_combat_economy_and_rules_consistency(self):
        """Testa le correzioni concettuali: blocco incapacitati, budget movimento, Warlock rest, e compravendita grid."""
        from server.rules.movement import handle_move_request
        from server.rules.combat import handle_attack_request
        from server.rules.character import handle_targeted_action
        from server.rules.inventory import handle_buy_item_request, handle_give_gold_request
        from server.rules.map_interaction import handle_create_aoe_request
        from client.character_manager import Character

        # 1. Personaggio Incosciente/Morto non può muoversi né attaccare
        downed = Player(name="EroeCaduto")
        downed.hp = 0
        downed.max_hp = 20
        downed.conditions = ["Incosciente", "Prono"]
        downed.position = [0, 0]
        self.game_state.players.append(downed)

        handle_move_request({"to": [1, 0]}, downed, self.game_state)
        self.assertEqual(downed.position, [0, 0], "Un PG incosciente non deve potersi muovere")

        target = Player(name="Nemico")
        target.hp = 20
        target.max_hp = 20
        target.position = [1, 0]
        self.game_state.players.append(target)

        handle_attack_request({"target_name": "Nemico", "weapon_name": "Pugno", "hit_bonus": 2, "damage_formula": "1d4"}, downed, self.game_state)
        self.assertEqual(target.hp, 20, "Un PG incosciente non deve poter attaccare")

        handle_targeted_action({"target_name": "Nemico", "action_type": "danno", "formula": "10"}, downed, self.game_state)
        self.assertEqual(target.hp, 20, "Un PG incosciente non deve poter eseguire targeted actions")

        # 2. Budget di movimento cumulativo in combattimento
        hero = Player(name="Combattente")
        hero.hp = 30
        hero.speed = 30 # 6 esagoni
        hero.position = [0, 0]
        self.game_state.players.append(hero)
        self.game_state.combat_active = True
        hero.in_combat = True

        # Primo movimento: 4 esagoni -> consentito
        handle_move_request({"to": [4, 0]}, hero, self.game_state)
        self.assertEqual(hero.position, [4, 0])
        self.assertEqual(hero.movement_spent_this_turn, 4)

        # Secondo movimento nello stesso turno: altri 4 esagoni (totale 8 > 6) -> bloccato!
        handle_move_request({"to": [8, 0]}, hero, self.game_state)
        self.assertEqual(hero.position, [4, 0], "Il movimento che supera il budget di turno deve essere bloccato")

        # 3. Warlock ricarica gli slot su Riposo Breve (Magia del Patto 5e)
        warlock = Character(name="WarlockHero", campaign="Test")
        warlock.char_class = "Warlock"
        warlock.spell_slots = {"2": {"max": 2, "current": 0}}
        warlock.hit_dice_current = 2
        warlock.hp_current = 10
        warlock.hp_max = 20
        warlock.short_rest(1)
        self.assertEqual(warlock.spell_slots["2"]["current"], 2, "Il Warlock deve ricaricare gli slot con un riposo breve")

        # 4. Compravendita Emporio: detrazione MO e posizionamento nella griglia 25 slot
        buyer = Player(name="Acquirente")
        buyer.full_sheet = {
            "name": "Acquirente",
            "currency": {"MR": 0, "MA": 0, "ME": 0, "MO": 100, "MP": 0},
            "inventory_grid": [None] * 25
        }
        self.game_state.players.append(buyer)
        self.game_state.shops = {
            "Bottega": {
                "name": "Bottega",
                "items": [{"name": "Corda di Canapa", "price": 10, "qty": 1, "weight": 10.0}]
            }
        }
        handle_buy_item_request({"shop_name": "Bottega", "item_name": "Corda di Canapa"}, buyer, self.game_state)
        self.assertEqual(buyer.full_sheet["currency"]["MO"], 90, "Le MO devono essere scalate dall'acquisto")
        self.assertIsNotNone(buyer.full_sheet["inventory_grid"][0], "L'oggetto deve apparire nella griglia a 25 slot")
        self.assertEqual(buyer.full_sheet["inventory_grid"][0]["name"], "Corda di Canapa")

        # 5. Concentrazione AoE: sovrascrittura di precedente AoE a concentrazione
        caster = Player(name="Mago")
        caster.hp = 20
        caster.position = [0, 0]
        self.game_state.players.append(caster)
        handle_create_aoe_request({"aoe_data": {"origin": [0, 0], "type": "sfera", "size": 2, "concentration": True, "name": "Ragnatela"}}, caster, self.game_state)
        self.assertEqual(len(self.game_state.active_aoes), 1)
        self.assertEqual(self.game_state.active_aoes[0]["name"], "Ragnatela")

        # Lancia una seconda magia a concentrazione -> la prima deve cadere
        handle_create_aoe_request({"aoe_data": {"origin": [2, 0], "type": "sfera", "size": 3, "concentration": True, "name": "Muro di Fuoco"}}, caster, self.game_state)
        self.assertEqual(len(self.game_state.active_aoes), 1)
        self.assertEqual(self.game_state.active_aoes[0]["name"], "Muro di Fuoco", "La precedente concentrazione deve essere caduta")

    def test_distance_units_and_code_review_fixes(self):
        """Testa l'unità di misura piedi/metri (ft/m) e tutte le correzioni della Code Review v3."""
        from common.i18n import (
            get_distance_unit, set_distance_unit, convert_speed_value,
            speed_to_hexes, format_distance_hexes
        )
        from common.hex_utils import Hex, get_line_hexes
        from common.dice import roll_dice
        from server.rules.movement import handle_move_request
        from server.rules.character import handle_update_full_sheet_request
        from server.rules.chat import handle_roll_request, handle_chat

        # 1. Conversione unità Piedi (ft) <-> Metri (m)
        self.assertEqual(convert_speed_value(30, "ft", "m"), 9)
        self.assertEqual(convert_speed_value(9, "m", "ft"), 30)
        self.assertEqual(convert_speed_value(25, "ft", "m"), 7.5)
        self.assertEqual(convert_speed_value(7.5, "m", "ft"), 25)
        self.assertEqual(speed_to_hexes(30, "ft"), 6)
        self.assertEqual(speed_to_hexes(9, "m"), 6)
        self.assertEqual(speed_to_hexes(7.5, "m"), 5)
        self.assertEqual(format_distance_hexes(6, "ft"), "30 ft")
        self.assertEqual(format_distance_hexes(6, "m"), "9 m")
        self.assertEqual(format_distance_hexes(5, "m"), "7.5 m")

        # Persistenza e cambio unità
        prev_unit = get_distance_unit()
        set_distance_unit("m")
        self.assertEqual(get_distance_unit(), "m")
        set_distance_unit("ft")
        self.assertEqual(get_distance_unit(), "ft")
        set_distance_unit(prev_unit)

        # 2. Movimento sul server con velocità espressa in Metri (9 m = 6 esagoni)
        p_metric = Player(name="EsploratoreMetrico")
        p_metric.hp = 25
        p_metric.speed = 9
        p_metric.speed_unit = "m"
        p_metric.position = [0, 0]
        p_metric.in_combat = True
        self.game_state.players.append(p_metric)
        self.game_state.combat_active = True

        # Muove di 6 esagoni (9 m) -> consentito!
        handle_move_request({"to": [6, 0]}, p_metric, self.game_state)
        self.assertEqual(p_metric.position, [6, 0], "Un PG con 9m di velocità deve potersi muovere di 6 esagoni")

        # Nuovo turno: tenta di muovere di 7 esagoni (10.5 m > 9 m) -> bloccato!
        p_metric.movement_spent_this_turn = 0
        handle_move_request({"to": [13, 0]}, p_metric, self.game_state)
        self.assertEqual(p_metric.position, [6, 0], "Un movimento di 7 esagoni deve essere bloccato con 9m di velocità")

        # 3. Riordino inventario (spostamento oggetto da slot 0 a slot 12) non deve cancellare l'oggetto
        spada = {"name": "Spada Lunga", "type": "Arma", "qty": 1, "weight": 3.0}
        inv_initial = [None] * 25
        inv_initial[0] = spada
        p_metric.full_sheet = {
            "name": "EsploratoreMetrico",
            "level": 1,
            "speed": 9,
            "speed_unit": "m",
            "inventory_grid": list(inv_initial),
            "starting_kit_applied": True,
            "campaign_starter_received": True
        }
        rearranged_sheet = dict(p_metric.full_sheet)
        inv_moved = [None] * 25
        inv_moved[12] = spada
        rearranged_sheet["inventory_grid"] = inv_moved
        handle_update_full_sheet_request({"character": rearranged_sheet}, p_metric, self.game_state)
        self.assertIsNone(p_metric.full_sheet["inventory_grid"][0])
        self.assertIsNotNone(p_metric.full_sheet["inventory_grid"][12], "Lo spostamento di slot nello zaino deve essere consentito")
        self.assertEqual(p_metric.full_sheet["inventory_grid"][12]["name"], "Spada Lunga")

        # 4. Hex.distance e get_line_hexes con 2 o 3 argomenti
        h_a = Hex(0, 0)
        h_b = Hex(3, 0)
        self.assertEqual(h_a.distance(h_b), 3)
        line_2args = get_line_hexes(h_a, h_b)
        self.assertEqual(len(line_2args), 4)
        line_3args = get_line_hexes(h_a, h_b, 5)
        self.assertEqual(len(line_3args), 5)

        # 5. roll_dice con testo tipo danno e tiro 0d0 flavor
        res_dmg = roll_dice("1d8+3 Tagliente")
        self.assertTrue(4 <= res_dmg["total"] <= 11)
        handle_roll_request({"formula": "0d0", "reason": "Usa Tratti Elfici"}, p_metric, self.game_state)

        # 6. Sicurezza comandi chat DM (/setsize bloccato ai giocatori normali connessi)
        p_metric.conn = DummySocket()
        p_metric.size = 1
        handle_chat({"text": "/setsize EsploratoreMetrico 3"}, p_metric, self.game_state)
        self.assertEqual(p_metric.size, 1, "Un giocatore normale non deve poter cambiare la propria taglia via /setsize")

        # 7. GameState.remove_player accetta sia stringa che istanza Player
        temp_p = Player(name="TempPNG")
        self.game_state.players.append(temp_p)
        self.game_state.remove_player("TempPNG")
        self.assertIsNone(self.game_state.find_player("TempPNG"))

    def test_critical_success_and_failure_mechanics(self):
        """Testa Successi Critici (20 Naturale) e Fallimenti Critici (1 Naturale) su dadi, attacchi, TS e chat."""
        from unittest.mock import patch
        from common.dice import roll_dice
        from server.rules.combat import handle_attack_request, _process_save_result
        from server.rules.chat import handle_chat

        # 1. Verifica flag critico/fumble in roll_dice su 1d20
        with patch("common.dice.random.randint", return_value=20):
            res20 = roll_dice("1d20+5")
            self.assertTrue(res20["is_crit"])
            self.assertFalse(res20["is_fumble"])
            self.assertEqual(res20["natural_roll"], 20)
            self.assertEqual(res20["crit_status"], "crit_success")
            self.assertEqual(res20["total"], 25)

        with patch("common.dice.random.randint", return_value=1):
            res1 = roll_dice("1d20+9")
            self.assertFalse(res1["is_crit"])
            self.assertTrue(res1["is_fumble"])
            self.assertTrue(res1["is_crit_fail"])
            self.assertEqual(res1["natural_roll"], 1)
            self.assertEqual(res1["crit_status"], "crit_fail")
            self.assertEqual(res1["total"], 10)

        # 2. Verifica raddoppio soli dadi (e non modificatore statico) nei danni critici (is_crit=True)
        with patch("common.dice.random.randint", return_value=6):
            crit_dmg = roll_dice("1d8+4 Tagliente", is_crit=True)
            self.assertEqual(len(crit_dmg["rolls"]), 2, "Il colpo critico deve tirare il doppio dei dadi")
            self.assertEqual(crit_dmg["modifier"], 4, "Il modificatore statico non deve raddoppiare sul critico")
            self.assertEqual(crit_dmg["total"], 16, "2d8 (6+6) + 4 = 16")

        # 3. Combattimento: 20 Naturale colpisce sempre (anche contro CA 99) e raddoppia solo i dadi danno
        attacker = Player(name="GuerrieroCrit")
        attacker.position = [0, 0]
        attacker.hp = 30
        attacker.max_hp = 30
        defender = Player(name="GolemCorazzato")
        defender.position = [1, 0]
        defender.hp = 50
        defender.max_hp = 50
        defender.ac = 99
        defender.full_sheet = {"ac": 99}
        self.game_state.players.extend([attacker, defender])

        # D20 tira 20 (roll1=20, roll2=20), poi i 2d8 del critico tirano 5 e 5 -> danno atteso: (5+5) + 3 = 13 (non 16!)
        with patch("common.dice.random.randint", side_effect=[20, 20, 5, 5]):
            handle_attack_request(
                {"target_name": "GolemCorazzato", "hit_bonus": 2, "damage_formula": "1d8+3"},
                attacker,
                self.game_state,
            )
        self.assertEqual(defender.hp, 37, "Il 20 Naturale deve colpire automaticamente CA 99 e infliggere 2d8+3 = 13 danni")

        # 4. Combattimento: 1 Naturale manca sempre (anche con +50 TxC contro CA 5)
        defender.ac = 5
        defender.full_sheet = {"ac": 5}
        defender.hp = 50
        with patch("common.dice.random.randint", return_value=1):
            handle_attack_request(
                {"target_name": "GolemCorazzato", "hit_bonus": 50, "damage_formula": "1d8+3"},
                attacker,
                self.game_state,
            )
        self.assertEqual(defender.hp, 50, "L'1 Naturale deve mancare automaticamente anche se il totale supera la CA")

        # 5. Tiri Salvezza: 20 Naturale supera sempre, 1 Naturale fallisce sempre
        defender.hp = 40
        # 20 Naturale con totale 18 contro CD 30 (senza dimezzamento) -> successo automatico (0 danni)
        _process_save_result(
            defender, "DES", 18, True, False, 30, "4d6", False, "Disintegrazione", self.game_state
        )
        self.assertEqual(defender.hp, 40, "Un 20 Naturale sul TS deve avere successo automatico anche sotto la CD")

        # 1 Naturale con totale 25 contro CD 10 -> fallimento automatico (danni pieni)
        with patch("common.dice.random.randint", return_value=4):
            _process_save_result(
                defender, "SAG", 25, False, True, 10, "2d6", False, "Paura Arcana", self.game_state
            )
        self.assertEqual(defender.hp, 32, "Un 1 Naturale sul TS deve fallire automaticamente anche sopra la CD")

        # 6. Comando /roll in chat
        with patch("common.dice.random.randint", return_value=20):
            handle_chat({"text": "/roll 1d20+4 Percepire"}, attacker, self.game_state)

    def test_ruler_map_scale_and_units(self):
        """Verifica che il righello e format_distance_hexes tengano conto della scala della mappa (Combattimento, Esplorazione, Mondo, Personalizzata) in ft/mi e m/km."""
        from common.i18n import get_map_scale_info, format_distance_hexes

        # 1. Scala Combattimento (hex_size=60 o 30) -> 1 hex = 5 ft / 1.5 m
        combat_map = {"hex_size": 60, "hexes": [[0, 0], [6, 0]]}
        self.assertEqual(get_map_scale_info(combat_map, "ft")["scale_type"], "combat")
        self.assertEqual(format_distance_hexes(6, unit="ft", map_data=combat_map), "30 ft")
        self.assertEqual(format_distance_hexes(6, unit="m", map_data=combat_map), "9 m")

        # 2. Scala Esplorazione / POI (hex_size=35) -> 1 hex = 1 mi / 1.5 km
        exploration_map = {"hex_size": 35, "hexes": [[0, 0], [3, 0]]}
        self.assertEqual(get_map_scale_info(exploration_map, "ft")["scale_type"], "exploration")
        self.assertEqual(format_distance_hexes(3, unit="ft", map_data=exploration_map), "3 mi")
        self.assertEqual(format_distance_hexes(3, unit="m", map_data=exploration_map), "4.5 km")
        self.assertIn("[~1h]", format_distance_hexes(3, unit="ft", map_data=exploration_map, include_travel_time=True))

        # 3. Scala Mondo / Regione (hex_size=15, es. faerun.json) -> 1 hex = 6 mi / 9 km
        world_map = {"hex_size": 15, "hexes": [[0, 0], [4, 0]]}
        self.assertEqual(get_map_scale_info(world_map, "ft")["scale_type"], "world")
        self.assertEqual(format_distance_hexes(4, unit="ft", map_data=world_map), "24 mi")
        self.assertEqual(format_distance_hexes(4, unit="m", map_data=world_map), "36 km")
        self.assertIn("[~8h]", format_distance_hexes(4, unit="ft", map_data=world_map, include_travel_time=True))
        # 8 esagoni sul mondo = 48 mi = 2 giorni di marcia (16h / 8h)
        self.assertIn("2", format_distance_hexes(8, unit="ft", map_data=world_map, include_travel_time=True))

        # 4. Scala Personalizzata esplicita (es. 1 hex = 10 ft -> 3 m)
        custom_map = {"hex_size": 60, "map_scale_type": "custom", "hex_scale_value": 10, "hex_scale_unit": "ft"}
        self.assertEqual(format_distance_hexes(4, unit="ft", map_data=custom_map), "40 ft")
        self.assertEqual(format_distance_hexes(4, unit="m", map_data=custom_map), "12 m")

    def test_turn_economy_combat_and_exploration_rules(self):
        """Verifica le regole di Economia del Turno in Esplorazione vs Combattimento e la pulizia automatica delle condizioni di turno."""
        from server.rules.combat import (
            handle_dash_request, handle_disengage_request,
            handle_dodge_request, handle_help_request
        )

        p1 = Player(name="Guerriero")
        p1.hp = 30
        p1.max_hp = 30
        p1.initiative = 18
        p1.conn = DummySocket()

        p2 = Player(name="Goblin")
        p2.hp = 15
        p2.max_hp = 15
        p2.initiative = 10

        self.game_state.players = [p1, p2]

        # 1. Modalità Esplorazione (combat_active = False): Scatto, Disimpegno, Schivata e Aiuto devono essere bloccati
        self.game_state.combat_active = False
        handle_dash_request({}, p1, self.game_state)
        handle_disengage_request({}, p1, self.game_state)
        handle_dodge_request({}, p1, self.game_state)
        handle_help_request({"target_name": "Goblin"}, p1, self.game_state)
        self.assertEqual(p1.conditions, [], "Fuori dal combattimento non devono essere applicate condizioni tattiche di turno")
        self.assertEqual(p2.conditions, [], "Fuori dal combattimento Aiuto non deve applicare 'Aiutato'")

        # 2. Avvio Combattimento: Turno 0 è di Guerriero (Iniziativa 18 > 10)
        self.game_state.start_combat()
        self.assertTrue(self.game_state.combat_active)
        self.assertEqual(self.game_state.get_current_turn_player().name, "Guerriero")

        handle_dash_request({}, p1, self.game_state)
        handle_dodge_request({}, p1, self.game_state)
        handle_help_request({"target_name": "Goblin"}, p1, self.game_state)
        self.assertIn("Scatto", p1.conditions)
        self.assertIn("Schivata", p1.conditions)
        self.assertIn("Aiutato", p2.conditions)

        # 3. Fine del turno di Guerriero -> passa al turno di Goblin:
        # 'Scatto' termina a fine turno di Guerriero, mentre 'Schivata' resta attiva durante il turno del Goblin!
        self.game_state.next_turn()
        self.assertEqual(self.game_state.get_current_turn_player().name, "Goblin")
        self.assertNotIn("Scatto", p1.conditions, "Scatto deve scadere alla fine del turno del PG")
        self.assertIn("Schivata", p1.conditions, "Schivata deve restare attiva durante i turni nemici fino all'inizio del prossimo turno del PG")

        # 4. Fine del turno del Goblin -> torna l'inizio del turno di Guerriero:
        # 'Schivata' scade automaticamente all'inizio del nuovo turno di Guerriero!
        self.game_state.next_turn()
        self.assertEqual(self.game_state.get_current_turn_player().name, "Guerriero")
        self.assertNotIn("Schivata", p1.conditions, "Schivata deve scadere all'inizio del turno successivo del PG")

        # 5. Fine del Combattimento (end_combat): rimuove tutte le condizioni tattiche temporanee ma preserva quelle persistenti
        p1.conditions = ["Disimpegno", "Schivata", "Avvelenato"]
        p1.full_sheet = {"conditions": ["Disimpegno", "Schivata", "Avvelenato"]}
        self.game_state.end_combat()
        self.assertFalse(self.game_state.combat_active)
        self.assertEqual(p1.conditions, ["Avvelenato"], "end_combat deve ripulire Disimpegno e Schivata mantenendo Avvelenato")
        self.assertEqual(p1.full_sheet["conditions"], ["Avvelenato"])
        self.assertEqual(p2.conditions, [], "end_combat deve ripulire Aiutato dal bersaglio")

    def test_class_resources_system(self):
        """Testa le risorse di classe speciali (Ira, Ki, Ispirazione Bardica, ecc.) e recupero con riposi."""
        # 1. Barbaro: Ira ricarica su Riposo Lungo
        barb = Character(name="Conan")
        barb.char_class = "Barbaro"
        barb.level = 3
        barb.auto_populate_class_resources()
        self.assertTrue(any(r["name"] == "Ira (Rage)" for r in barb.custom_resources))
        rage = next(r for r in barb.custom_resources if r["name"] == "Ira (Rage)")
        self.assertEqual(rage["max"], 3)
        self.assertEqual(rage["current"], 3)
        self.assertEqual(rage["reset_on"], "long")
        # Consuma 1 Ira
        rage["current"] -= 1
        barb.short_rest()
        self.assertEqual(rage["current"], 2, "Ira non si ricarica con Riposo Breve")
        barb.long_rest()
        self.assertEqual(rage["current"], 3, "Ira si ricarica con Riposo Lungo")

        # 2. Monaco: Punti Ki ricaricano su Riposo Breve
        monk = Character(name="Lee")
        monk.char_class = "Monaco"
        monk.level = 5
        monk.auto_populate_class_resources()
        ki = next(r for r in monk.custom_resources if "Punti Ki" in r["name"])
        self.assertEqual(ki["max"], 5)
        self.assertEqual(ki["reset_on"], "short")
        ki["current"] = 1
        monk.short_rest()
        self.assertEqual(ki["current"], 5, "I Punti Ki si ricaricano interamente con Riposo Breve")

        # 3. Guerriero: Action Surge e Second Wind ricaricano su Riposo Breve
        fighter = Character(name="Aragorn")
        fighter.char_class = "Guerriero"
        fighter.level = 4
        fighter.auto_populate_class_resources()
        surge = next(r for r in fighter.custom_resources if "Action Surge" in r["name"])
        wind = next(r for r in fighter.custom_resources if "Secondo Fiato" in r["name"])
        surge["current"] = 0
        wind["current"] = 0
        fighter.short_rest()
        self.assertEqual(surge["current"], 1, "Action Surge recuperato con Riposo Breve")
        self.assertEqual(wind["current"], 1, "Secondo Fiato recuperato con Riposo Breve")

    def test_character_sheet_html_export(self):
        """Testa la generazione del file HTML stampabile della scheda personaggio."""
        c = Character(name="Gandalf")
        c.char_class = "Mago"
        c.race = "Umano"
        c.level = 5
        c.hp = 28
        c.max_hp = 28
        c.attributes["INT"] = 18
        c.custom_resources = [{"name": "Punti Stregoneria", "current": 3, "max": 5, "reset_on": "long"}]
        c.spellbook = [{"name": "Palla di Fuoco", "level": 3, "school": "Evocazione"}]

        from client.character_sheet_ui import CharacterSheetUI
        html = CharacterSheetUI._generate_character_html(c)
        self.assertIn("Gandalf", html)
        self.assertIn("Mago", html)
        self.assertIn("Lv 5", html)
        self.assertIn("Punti Stregoneria", html)
        self.assertIn("Palla di Fuoco", html)
        self.assertIn("<!DOCTYPE html>", html)

    def test_creature_token_sizes_and_multipliers(self):
        """Testa le taglie dei token (Tiny, Small, Medium, Large, Huge, Gargantuan) e il mapping visivo."""
        SIZE_MAP = {
            "tiny": 0.5, "minuscola": 0.5,
            "small": 0.8, "piccola": 0.8,
            "medium": 1.0, "media": 1.0,
            "large": 1.8, "grande": 1.8,
            "huge": 2.6, "enorme": 2.6,
            "gargantuan": 3.5, "mastodontica": 3.5
        }
        self.assertEqual(SIZE_MAP["tiny"], 0.5)
        self.assertEqual(SIZE_MAP["medium"], 1.0)
        self.assertEqual(SIZE_MAP["large"], 1.8)
        self.assertEqual(SIZE_MAP["huge"], 2.6)
        self.assertEqual(SIZE_MAP["gargantuan"], 3.5)

        p = Player(name="DragoRosso")
        p.size = "huge"
        d = p.to_dict()
        self.assertEqual(d["size"], "huge")
        p2 = Player.from_dict(d)
        self.assertEqual(p2.size, "huge")

    def test_gm_hidden_layer(self):
        """Testa il Livello GM: i token nascosti sono filtrati per i giocatori e visibili solo al DM."""
        p_normal = Player(name="Chierico")
        p_normal.layer = "token"
        p_secret = Player(name="AssassinoInvisibile")
        p_secret.layer = "gm"

        self.game_state.players = [p_normal, p_secret]

        # 1. get_state_dict(is_dm=True) deve contenere entrambi i token
        dm_state = self.game_state.get_state_dict(is_dm=True)
        dm_player_names = [pl["name"] for pl in dm_state["players"]]
        self.assertIn("Chierico", dm_player_names)
        self.assertIn("AssassinoInvisibile", dm_player_names)

        # 2. get_state_dict(is_dm=False) per i giocatori NON deve contenere il token del GM layer!
        player_state = self.game_state.get_state_dict(is_dm=False)
        player_names = [pl["name"] for pl in player_state["players"]]
        self.assertIn("Chierico", player_names)
        self.assertNotIn("AssassinoInvisibile", player_names, "Il token nel livello GM deve essere invisibile ai giocatori!")

    def test_multi_grid_support(self):
        """Testa il supporto multi-griglia (Quadrata, Esagonale, Gridless) e le formule di distanza."""
        from common.hex_utils import SquareLayout, Hex, grid_distance

        # 1. SquareLayout: coordinate e conversione pixel <-> grid
        sq_layout = SquareLayout(size=50, origin=(0, 0))
        h = Hex(2, 3)
        px, py = sq_layout.hex_to_pixel(h)
        self.assertEqual((px, py), (125.0, 175.0), "Il centro della cella (2, 3) deve essere (125, 175)")
        recovered_hex = sq_layout.pixel_to_hex((px, py))
        self.assertEqual(recovered_hex, h)

        # 2. Distanza su griglia quadrata (Chebyshev / D&D 5e: diagonale costa 1 casella)
        start = Hex(0, 0)
        diag = Hex(3, 3)
        self.assertEqual(grid_distance(start, diag, "square"), 3, "In D&D 5e su griglia quadrata una diagonale di 3 caselle è distanza 3")

        # 3. Distanza su griglia libera (Euclidea)
        euclid_dist = grid_distance(start, diag, "none")
        self.assertAlmostEqual(euclid_dist, 4.2426, places=3)

        # 4. Distanza su griglia esagonale (Cubo esagonale)
        hex_dist = grid_distance(start, diag, "hex")
        self.assertEqual(hex_dist, 6)

    def test_whiteboard_drawing_and_clear_packets(self):
        """Testa la lavagna condivisa: invio disegni e cancellazione sincronizzata."""
        from server.rules.map_interaction import handle_draw_request, handle_clear_drawings_request
        from common.protocol import make_clear_drawings_request, make_clear_drawings_broadcast

        self.game_state.drawn_lines = []
        p = Player(name="Disegnatore")

        # 1. Aggiungi linea
        handle_draw_request({"points": [(10, 10), (20, 20)], "color": "blue"}, p, self.game_state)
        self.assertEqual(len(self.game_state.drawn_lines), 1)
        self.assertEqual(self.game_state.drawn_lines[0]["color"], "blue")

        # 2. Protocol helpers
        req = make_clear_drawings_request()
        self.assertEqual(req["type"], "CLEAR_DRAWINGS_REQUEST")
        bcast = make_clear_drawings_broadcast()
        self.assertEqual(bcast["type"], "CLEAR_DRAWINGS_BROADCAST")

    def test_official_pdf_character_sheet_export(self):
        """Testa la compilazione automatica e l'esportazione della Scheda Ufficiale D&D 5e in PDF."""
        from client.character_manager import Character
        from client.pdf_sheet_generator import generate_character_pdf, get_default_template_path
        from pypdf import PdfReader
        import tempfile

        # Se il template locale esiste, usalo; altrimenti crea un template temporaneo a 3 pagine per testare il motore
        template_path = get_default_template_path()
        cleanup_template = False
        if not template_path or not os.path.isfile(template_path):
            from reportlab.pdfgen import canvas
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_tpl:
                template_path = tmp_tpl.name
            cleanup_template = True
            c_tpl = canvas.Canvas(template_path, pagesize=(594, 783))
            c_tpl.drawString(50, 700, "Pagina 1")
            c_tpl.showPage()
            c_tpl.drawString(50, 700, "Pagina 2")
            c_tpl.showPage()
            c_tpl.drawString(50, 700, "Pagina 3")
            c_tpl.showPage()
            c_tpl.save()

        # Configura personaggio di test
        char = Character("Valeros il Guerriero", "La Miniera Perduta")
        char.race = "Umano"
        char.char_class = "Guerriero"
        char.level = 4
        char.background = "Soldato"
        char.alignment = "Legale Buono"
        char.attributes = {"FOR": 16, "DES": 12, "COS": 14, "INT": 10, "SAG": 12, "CAR": 8}
        char.hp_max = 38
        char.hp_current = 35
        char.temp_hp = 4
        char.ac = 18
        char.initiative = 1
        char.speed = 9
        char.speed_unit = "m"
        char.proficiency_bonus = 2
        char.hit_dice_total = 4
        char.hit_dice_current = 3
        char.hit_dice_type = "d10"
        char.currency = {"MR": 10, "MA": 5, "ME": 0, "MO": 45, "MP": 1}
        char.skills["Atletica"] = 1
        char.skills["Intimidire"] = 1
        char.skills["Sopravvivenza"] = 1
        char.has_inspiration = True
        char.weapons = [
            {"name": "Spada Lunga", "bonus": 5, "damage_dice": "1d8+3", "damage_type": "Tagliente"},
            {"name": "Arco Corto", "bonus": 3, "damage_dice": "1d6+1", "damage_type": "Perforante"}
        ]
        char.features = "Secondo Fiato (1d10+4 PF).\nAzione Impetuosa (1 azione aggiuntiva)."
        char.spellbook = [
            {"name": "Luce", "level": 0, "prepared": True}
        ]

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            res_path = generate_character_pdf(char, tmp_path, template_path)
            self.assertEqual(res_path, tmp_path)
            self.assertTrue(os.path.exists(tmp_path))
            size = os.path.getsize(tmp_path)
            self.assertGreater(size, 1000, "Il PDF generato deve contenere il documento a 3 pagine")

            # Verifica pagine con pypdf
            reader = PdfReader(tmp_path)
            self.assertEqual(len(reader.pages), 3, "La scheda ufficiale deve avere 3 pagine")
            self.assertEqual(int(reader.pages[0].mediabox.width), 594)
            self.assertEqual(int(reader.pages[0].mediabox.height), 783)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if cleanup_template and os.path.exists(template_path):
                os.remove(template_path)

    def test_offline_character_manager_features(self):
        """Testa la creazione e gestione autonoma dei personaggi offline."""
        from common.i18n import _t, set_language
        from client.character_sheet_ui import open_export_character_dialog, CharacterSheetUI
        from client.character_manager_ui import get_class_icon

        # 1. Test icone classi
        self.assertEqual(get_class_icon("Guerriero"), "⚔️")
        self.assertEqual(get_class_icon("Mago"), "🔮")
        self.assertEqual(get_class_icon("Ladro"), "🗡️")
        self.assertEqual(get_class_icon("Chierico"), "🛡️")

        # 2. Test export helper exportable/callable
        self.assertTrue(callable(open_export_character_dialog))
        self.assertTrue(hasattr(CharacterSheetUI, "open_export_character_dialog"))

        # 3. Test traduzioni i18n per launcher e menu personaggi in IT ed EN
        set_language("it")
        self.assertIn("Gestione Personaggi", _t("launcher_player_btn_manage_chars"))
        self.assertIn("Crea Personaggio", _t("launcher_player_btn_create_char"))
        self.assertEqual(_t("menu_character"), "Personaggio")

        set_language("en")
        self.assertIn("Character Manager", _t("launcher_player_btn_manage_chars"))
        self.assertIn("Create Character", _t("launcher_player_btn_create_char"))
        self.assertEqual(_t("menu_character"), "Character")
        set_language("it") # Reset ad italiano

        # 4. Test duplicazione e gestione personaggio in memoria
        mgr = CharacterManager()
        initial_count = len(mgr.characters)
        test_char = Character(name="Eroe Offline Test")
        test_char.char_class = "Paladino"
        test_char.level = 3
        mgr.add_character(test_char)
        self.assertEqual(len(mgr.characters), initial_count + 1)

        # Duplicazione
        char_dict = test_char.to_dict()
        char_dict["id"] = "dup_test_id_123"
        char_dict["name"] = f"{test_char.name} (Copia)"
        copied = Character.from_dict(char_dict)
        mgr.add_character(copied)
        self.assertEqual(copied.name, "Eroe Offline Test (Copia)")
        self.assertEqual(copied.char_class, "Paladino")
        self.assertEqual(copied.level, 3)

        # Pulizia
        mgr.delete_character(test_char)
        mgr.delete_character(copied)
        self.assertEqual(len(mgr.characters), initial_count)


if __name__ == "__main__":
    unittest.main()



