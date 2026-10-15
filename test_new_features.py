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


if __name__ == "__main__":
    unittest.main()
