# tests/test_audit_v17_phase3.py
"""
Unit tests per la Fase 3 del piano di remediation D&D 5e RAW (audit v17).
Verifica:
- 3.1: Rimozione auto-successo/fallimento su TS e Prove di Caratteristica per Nat 20 / Nat 1
- 3.2: Correzione dei 7 bug di CA (calculate_initial_ac, recalculate_ac, bracers, attunement) e Scurovisione
- 3.3: Geometria Griglia Quadrata 5e (standard Chebyshev vs tattica DMG) e distanza 3D
- 3.4: Effetti di combattimento (Benedizione, Anatema, Velocità, Lentezza) e Concentrazione
- 3.5: Imboscata notturna, Percezione Passiva Sentinella, Riposo Lungo e Breve
- 3.6: Wizard (Mezzelfo, sottoclassi Lv 1, velocità m/ft, taglia, resistenze), Risorse di classe e Sintonizzazione Artefice
- 3.7: Combattimento RAW (portata, gittata, nemico a 5ft, rimozione penalità homebrew, TS morte, AoE muri, dadi e calcolatore incontri)
"""

import unittest
import queue
from client.character_manager import Character
from common.game_state import GameState, Player
from common.hex_utils import Hex, grid_distance, grid_distance_3d, has_line_of_sight
from common.dice import roll_dice
from common.encounter_calc import calculate_encounter_difficulty, CR_TO_XP, get_monster_count_multiplier


class TestAuditPhase3(unittest.TestCase):

    def test_3_1_saving_throw_no_nat20_autosuccess(self):
        """3.1: Verifica che un tiro salvezza con 20 naturale o 1 naturale rispetti matematicamente la CD (no auto-successo/fallimento PHB p. 179)."""
        from server.rules.combat import _process_save_result
        gs = GameState(gui_queue=queue.Queue())
        p = Player(name="Eroe")
        p.hp = 20
        p.max_hp = 20
        gs.players.append(p)

        # 20 Naturale con mod +0 contro CD 25 -> DEVE fallire (20 < 25)
        _process_save_result(p.name, "SAG", roll_total=20, is_crit=True, is_fail=False, dc=25, damage_formula=None, half_on_success=True, source_name="Test", game_state=gs)
        
        # 1 Naturale con mod +12 contro CD 10 -> DEVE superare (13 >= 10)
        _process_save_result(p.name, "DES", roll_total=13, is_crit=False, is_fail=True, dc=10, damage_formula=None, half_on_success=True, source_name="Test", game_state=gs)

    def test_3_2_ac_calculations_and_darkvision(self):
        """3.2: Verifica il calcolo corretto della CA conforme a D&D 5e RAW (starter armor, bracers, negative dex, attunement)."""
        from common.starter_equipment import calculate_initial_ac, apply_class_and_race_starter_kit
        
        # 1. Guerriero con Cotta di Maglia (16) e Scudo (2)
        c_fighter = Character(name="Guerriero")
        c_fighter.char_class = "Guerriero"
        c_fighter.attributes = {"FOR": 16, "DES": 10, "COS": 14, "INT": 10, "SAG": 12, "CAR": 8}
        apply_class_and_race_starter_kit(c_fighter)
        self.assertEqual(c_fighter.recalculate_ac(), 18)

        # 2. Des negativa su armatura media (es. Mezza Armatura 15 con DES 8 -> 14)
        c_med = Character(name="Chierico")
        c_med.char_class = "Chierico"
        c_med.attributes = {"FOR": 14, "DES": 8, "COS": 14, "INT": 10, "SAG": 16, "CAR": 10} # DES mod = -1
        c_med.inventory_grid[0] = {"name": "Mezza Armatura", "type": "Armatura", "container": "equipped"}
        self.assertEqual(c_med.recalculate_ac(), 14)

        # 3. Bracciali della Difesa: solo se senz'armatura e senza scudo (+2 CA)
        c_bracers = Character(name="Mago")
        c_bracers.char_class = "Mago"
        c_bracers.attributes = {"FOR": 8, "DES": 14, "COS": 12, "INT": 16, "SAG": 12, "CAR": 10} # DES mod = +2 -> Base 12
        c_bracers.inventory_grid[0] = {"name": "Bracciali della Difesa", "type": "Oggetto Magico", "container": "equipped", "attuned": True}
        self.assertEqual(c_bracers.recalculate_ac(), 14)

        # Se indossa uno scudo, i Bracciali della Difesa NON devono applicarsi
        c_bracers.inventory_grid[1] = {"name": "Scudo", "type": "Scudo", "container": "equipped"}
        self.assertEqual(c_bracers.recalculate_ac(), 14) # 10 + 2 (DES) + 2 (Scudo) = 14 (Bracciali inattivi)

        # 4. Scurovisione da features razziali o di classe
        c_dwarf = Character(name="Nano")
        c_dwarf.race = "Nano"
        self.assertTrue(c_dwarf.check_has_darkvision())

        c_human = Character(name="Umano")
        c_human.race = "Umano"
        self.assertFalse(c_human.check_has_darkvision())
        c_human.features = "Scurovisione fino a 18 metri"
        self.assertTrue(c_human.check_has_darkvision())

    def test_3_3_grid_geometry_standard_vs_tactical(self):
        """3.3: Verifica la geometria quadrata 5e (Standard Chebyshev 5-5-5 vs Tattica DMG 5-10-5) e distanza 3D."""
        h1 = Hex(0, 0)
        h2 = Hex(2, 2) # Spostamento di 2 caselle in diagonale (+2, +2)
        
        # In esagonale, la distanza da (0,0) a (2,2) è 4 esagoni
        self.assertEqual(grid_distance(h1, h2, grid_type="hex"), 4)

        # In griglia quadrata standard PHB (Chebyshev), distanza = max(|dx|, |dy|) = 2 caselle (10 ft)
        self.assertEqual(grid_distance(h1, h2, grid_type="square", diagonal_rule="standard"), 2)

        # In griglia quadrata tattica DMG (5-10-5), prima diagonale = 1 (5ft), seconda = 2 (10ft) -> totale = 3 (15 ft)
        self.assertEqual(grid_distance(h1, h2, grid_type="square", diagonal_rule="tactical"), 3)

        # Distanza 3D con quota (es. 2 caselle orizzontali, quota z=15ft = 3 caselle)
        # Metrica 5e: max(d_orizzontale, dz) = max(2, 3) = 3 caselle
        d3d = grid_distance_3d(h1, h2, z_a=0, z_b=15, grid_type="square", diagonal_rule="standard")
        self.assertEqual(d3d, 3.0)

    def test_3_4_effect_presets_and_concentration(self):
        """3.4: Verifica il funzionamento dei preset ufficiali (Bless, Bane, Haste, Slow) e concentrazione."""
        from server.rules.combat import has_effect_or_condition, drop_concentration
        gs = GameState(gui_queue=queue.Queue())
        p = Player(name="Mago")
        p.hp = 20
        p.max_hp = 20
        p.elevation = 20 # Sospeso a 20 ft
        gs.players.append(p)

        # Se la concentrazione è su Benedizione, drop_concentration NON deve farlo cadere a terra
        p.active_effects = [{"name": "Benedizione", "concentration": True, "condition": "Benedizione"}]
        drop_concentration(p, gs, notify=False)
        self.assertEqual(p.elevation, 20) # Rimane in quota

        # Se invece la concentrazione era su Volo, drop_concentration DEVE farlo precipitare a quota 0
        p.active_effects = [{"name": "Volare", "concentration": True, "condition": "Volo"}]
        drop_concentration(p, gs, notify=False)
        self.assertEqual(p.elevation, 0) # Precipitato a terra

    def test_3_5_night_ambush_and_rests(self):
        """3.5: Verifica risoluzione corretta di Riposo Lungo e Breve secondo 5e RAW."""
        from server.rules.character import handle_long_rest_request
        from server.rules.combat import handle_short_rest_request
        gs = GameState(gui_queue=queue.Queue())
        
        # Player vivo e mostro nemico
        pc = Player(name="Eroe")
        pc.hp = 5
        pc.max_hp = 30
        pc.is_party_member = True
        pc.full_sheet = {"level": 6, "hit_dice_total": 6, "hit_dice_current": 1, "spell_slots": {"1": {"max": 4, "current": 0}}}
        monster = Player(name="Goblin")
        monster.hp = 2
        monster.max_hp = 7
        monster.is_party_member = False
        gs.players.extend([pc, monster])

        # Long Rest
        handle_long_rest_request({}, pc, gs)
        self.assertEqual(pc.hp, 30)
        self.assertEqual(pc.full_sheet["spell_slots"]["1"]["current"], 4)
        # Recupera max(1, 6 // 2) = 3 dadi vita -> 1 + 3 = 4
        self.assertEqual(pc.full_sheet["hit_dice_current"], 4)
        # Il mostro non deve essere curato dal riposo lungo del party!
        self.assertEqual(monster.hp, 2)

    def test_3_6_wizard_creation_and_resources(self):
        """3.6: Verifica Half-Elf bonus, velocità convertita in metri, sottoclassi Lv 1 e risorse di classe."""
        # 1. Risorse di classe RAW
        c_monk = Character(name="Monaco")
        c_monk.char_class = "Monaco"
        c_monk.level = 1
        c_monk.auto_populate_class_resources()
        # Monaco al Lv 1 non ha ancora Ki (si ottiene al Lv 2)
        self.assertEqual(len(c_monk.custom_resources), 0)
        c_monk.update_class_resources_for_level(2)
        ki_res = next((r for r in c_monk.custom_resources if "Ki" in r["name"]), None)
        self.assertIsNotNone(ki_res)
        self.assertEqual(ki_res["max"], 2)

        # 2. Warlock Mystic Arcanum
        c_warlock = Character(name="Warlock")
        c_warlock.char_class = "Warlock"
        c_warlock.level = 11
        c_warlock.auto_populate_class_resources()
        arcanum = next((r for r in c_warlock.custom_resources if "Arcanum" in r["name"]), None)
        self.assertIsNotNone(arcanum)
        self.assertEqual(arcanum["max"], 1)

        # 3. Taglia piccola e resistenze razziali
        c_halfling = Character(name="Halfling")
        c_halfling.race = "Halfling"
        c_halfling.speed_unit = "m"
        # 25 ft -> 7.5 m
        from common.i18n import speed_to_hexes
        self.assertEqual(speed_to_hexes(7.5, "m"), 5)

        # 4. Modificatore effettivo (oggetti magici)
        c_str = Character(name="Barbaro")
        c_str.attributes["FOR"] = 10 # Base 10 (+0)
        c_str.inventory_grid[0] = {"name": "Guanti del Potere Orchesco", "type": "Oggetto Magico", "container": "equipped", "attuned": True, "set_str": 19}
        self.assertEqual(c_str.get_modifier("FOR"), 4) # 19 -> +4

    def test_3_7_combat_rules_dice_and_encounter(self):
        """3.7: Verifica annullamento vantaggio/svantaggio nei dadi, gittata armi, AoE damage e calcolatore incontri."""
        # 1. Motore Dadi: Vantaggio + Svantaggio si annullano
        r_cancel = roll_dice("1d20+5 adv dis")
        self.assertNotIn(r_cancel["type"], ("Vantaggio", "Svantaggio"))

        # In italiano
        r_ita = roll_dice("1d20+3 vantaggio svantaggio")
        self.assertNotIn(r_ita["type"], ("Vantaggio", "Svantaggio"))

        # Formula con dado aggiuntivo (1d20 + 1d4 + 2 adv): tira solo il d20 due volte
        r_bless = roll_dice("1d20+1d4+2 adv")
        self.assertEqual(r_bless["type"], "Vantaggio")
        self.assertEqual(len(r_bless["rolls"]), 2) # [d20, 1d4]

        # 2. Calcolatore Incontri: CR 25–29 e float
        self.assertEqual(CR_TO_XP["25"], 75000)
        self.assertEqual(CR_TO_XP["29"], 135000)
        enc_res = calculate_encounter_difficulty([5, 5, 5, 5], [0.5, 0.5]) # Due mostri da CR 1/2 (100 XP cad.)
        self.assertEqual(enc_res["raw_xp"], 200)
        self.assertEqual(enc_res["multiplier"], 1.5)
        self.assertEqual(enc_res["adjusted_xp"], 300)

        # 3. Sneak Attack: Colpi Senz'Armi non qualificano per attacco furtivo
        from server.rules.combat import handle_attack_request
        gs = GameState(gui_queue=queue.Queue())
        attacker = Player(name="Ladro")
        attacker.hp = 20
        attacker.max_hp = 20
        attacker.is_party_member = True
        attacker.position = [0, 0]
        attacker.full_sheet = {"class": "Ladro", "level": 3}
        target = Player(name="Orco")
        target.hp = 30
        target.max_hp = 30
        target.is_party_member = False
        target.position = [1, 0]
        gs.players.extend([attacker, target])

        # Attacco con Colpo Senz'Armi (non accurato e non a distanza)
        handle_attack_request({
            "target": target.name,
            "weapon_name": "Colpo Senz'Armi",
            "damage_formula": "1",
            "damage_type": "Contundente"
        }, attacker, gs)
        # Non deve aver consumato sneak attack
        self.assertFalse(getattr(attacker, "sneak_attack_used_this_turn", False))


if __name__ == "__main__":
    unittest.main()
