# tests/test_raw_5e_advanced_features.py
"""
Test di conformità per le nuove feature D&D 5e RAW:
1. Paladin Divine Smite (Punizione Divina)
2. Druid Wild Shape (Forma Selvatica con assorbimento e riporto danni in eccesso)
3. Sorcerer Flexible Casting & Metamagic (Fonte di Magia & Metamagia)
4. Wizard Arcane Recovery (Recupero Arcano al riposo breve)
5. Reliable Talent (Talento Affidabile Ladro 11+) & Jack of All Trades (Tuttofare Bardo 2+)
6. Expanded Critical Range (Campione 19-20 / 18-20) & Brutal Critical / Savage Attacks
7. Monk Stunning Strike (Colpo Stordente) & Battle Master Superiority Dice
8. Cantrip Damage Scaling (1-4: 1x, 5-10: 2x, 11-16: 3x, 17+: 4x)
9. Prepared Spells Cap Validation
10. Monster Recharge Abilities (Recharge 5-6 al turno)
11. Ongoing Damage & Troll Regeneration (con blocco fuoco/acido)
12. Selectable Automatic XP Distribution (DM Agency toggle)
"""

import unittest
import queue
from unittest.mock import MagicMock
from common.game_state import GameState, Player
from common.character_schema import normalize_character_dict
from client.character_manager import Character
from server.rules.combat import apply_damage, handle_attack_request
from client.sheet_panels.spells_panel import SpellsPanel
from common.dice import roll_dice
from common.encounter_calc import get_xp_for_level, get_level_for_xp, CR_TO_XP


class TestRaw5eAdvancedFeatures(unittest.TestCase):

    def setUp(self):
        self.gui_queue = queue.Queue()
        self.game_state = GameState(self.gui_queue)
        self.game_state.combat_active = True

    # 1. Divine Smite
    def test_divine_smite_damage_and_crit(self):
        """Verifica la Punizione Divina del Paladino (PHB p. 85) e il raddoppio su critico."""
        paladin = Player("Paladino")
        paladin.is_party_member = True
        paladin.full_sheet = {
            "char_class": "Paladino",
            "level": 5,
            "spell_slots": {
                "1": {"max": 4, "current": 4},
                "2": {"max": 2, "current": 2}
            }
        }
        zombie = Player("Zombie")
        zombie.hp = 50
        zombie.max_hp = 50
        zombie.full_sheet = {"type": "undead", "cr": "1/4"}
        self.game_state.players = [paladin, zombie]

        # Attacco con slot 1° su Zombie (non morto: 2d8 base + 1d8 non morto = 3d8)
        req_data = {
            "target_name": "Zombie",
            "weapon_name": "Spada Lunga",
            "hit_bonus": 20, # Colpo sicuro
            "damage_formula": "1d8+3",
            "damage_type": "Tagliente",
            "smite_slot": 1
        }
        handle_attack_request(req_data, paladin, self.game_state)
        # Lo slot di 1° cerchio deve essere decrementato
        self.assertEqual(paladin.full_sheet["spell_slots"]["1"]["current"], 3)
        # Zombie deve aver subito danni arma + smite
        self.assertLess(zombie.hp, 50)

    # 2. Druid Wild Shape
    def test_druid_wild_shape_absorption_and_excess_carryover(self):
        """Verifica la Forma Selvatica: assorbimento del pool bestia e riporto dei danni residui (PHB p. 66)."""
        druid = Player("Druido")
        druid.hp = 25
        druid.max_hp = 25
        druid.ac = 14
        druid.speed = 30
        druid.full_sheet = {
            "char_class": "Druido",
            "level": 4,
            "wild_shape": {
                "active": True,
                "beast_name": "Lupo",
                "beast_hp": 11,
                "beast_max_hp": 11,
                "original_hp": 25,
                "original_max_hp": 25,
                "original_ac": 14,
                "original_speed": 30,
                "original_attributes": {"FOR": 10, "DES": 14, "COS": 12}
            }
        }
        druid.hp = 11 # PV Forma Lupo
        self.game_state.players = [druid]

        # Caso A: Danno inferiore ai PV del lupo (es. 6 danni) -> il druido resta trasformato
        final_dmg, note, temp_abs, dmg_hp = apply_damage(druid, 6, "Contundente", self.game_state)
        self.assertEqual(druid.hp, 5)
        self.assertTrue(druid.full_sheet["wild_shape"]["active"])

        # Caso B: Danno superiore ai PV residui del lupo (es. 10 danni su 5 PV)
        # Lupo cede (5 danni assorbiti), 5 danni residui passano ai 25 PV del druido -> PV druido = 20
        final_dmg, note, temp_abs, dmg_hp = apply_damage(druid, 10, "Tagliente", self.game_state)
        self.assertFalse(druid.full_sheet["wild_shape"]["active"])
        self.assertEqual(druid.hp, 20)
        self.assertEqual(druid.max_hp, 25)
        self.assertNotIn("Incosciente", getattr(druid, "conditions", []))

    # 3. Flexible Casting & Metamagic
    def test_sorcerer_flexible_casting_and_metamagic(self):
        """Verifica la Fonte di Magia (Slot <-> Punti) e Metamagia dello Stregone (PHB p. 101)."""
        char = Character("Stregone", char_class="Stregone", level=5)
        char.spell_slots = {
            "1": {"max": 4, "current": 4},
            "2": {"max": 3, "current": 3},
            "3": {"max": 2, "current": 2}
        }
        char.sorcery_points_max = 5
        char.sorcery_points_current = 2

        # 1. Converte slot di 2° cerchio in 2 Punti Stregoneria
        ok, msg = char.convert_slot_to_sorcery_points(2)
        self.assertTrue(ok)
        self.assertEqual(char.sorcery_points_current, 4)
        self.assertEqual(char.spell_slots["2"]["current"], 2)

        # 2. Crea uno slot di 1° cerchio spendendo 2 Punti Stregoneria
        ok, msg = char.convert_sorcery_points_to_slot(1)
        self.assertTrue(ok)
        self.assertEqual(char.sorcery_points_current, 2)
        self.assertEqual(char.spell_slots["1"]["current"], 5) # Slot bonus creato

        # 3. Spende per Metamagia Rapida (2 PE)
        ok, msg = char.use_metamagic("Incantesimo Rapido", 2)
        self.assertTrue(ok)
        self.assertEqual(char.sorcery_points_current, 0)

        # 4. Spesa ulteriore fallisce per mancanza di PE
        ok, msg = char.use_metamagic("Incantesimo Rapido", 2)
        self.assertFalse(ok)

    # 4. Arcane Recovery
    def test_wizard_arcane_recovery(self):
        """Verifica il Recupero Arcano al riposo breve (PHB p. 115)."""
        char = Character("Mago", char_class="Mago", level=6) # Max recupero: ceil(6/2) = 3 livelli
        char.spell_slots = {
            "1": {"max": 4, "current": 2},
            "2": {"max": 3, "current": 1},
            "3": {"max": 3, "current": 0}
        }
        # Tentativo di recuperare 4 livelli (un 3° e un 1°) -> Deve fallire (supera max 3)
        ok, msg = char.arcane_recovery({3: 1, 1: 1})
        self.assertFalse(ok)

        # Recupero di un 2° e un 1° (totale 3 livelli) -> Successo
        ok, msg = char.arcane_recovery({2: 1, 1: 1})
        self.assertTrue(ok)
        self.assertEqual(char.spell_slots["1"]["current"], 3)
        self.assertEqual(char.spell_slots["2"]["current"], 2)
        self.assertTrue(char.arcane_recovery_used)

        # Secondo tentativo nello stesso giorno -> Deve fallire
        ok2, msg2 = char.arcane_recovery({1: 1})
        self.assertFalse(ok2)

        # Riposo Lungo ricarica il Recupero Arcano
        char.long_rest()
        self.assertFalse(char.arcane_recovery_used)

    # 5. Reliable Talent & Jack of All Trades
    def test_reliable_talent_and_jack_of_all_trades(self):
        """Verifica Talento Affidabile (minimo 10 sul d20) e Tuttofare (+PB/2)."""
        rogue = Character("Ladro", char_class="Ladro", level=11)
        self.assertTrue(rogue.has_reliable_talent())

        bard = Character("Bardo", char_class="Bardo", level=4)
        self.assertTrue(bard.has_jack_of_all_trades())

        # Test d20 con reliable_talent=True: nessun tiro può essere < 10
        for _ in range(50):
            res = roll_dice("1d20+5 reliable")
            self.assertGreaterEqual(res["natural_roll"], 10)
            self.assertGreaterEqual(res["total"], 15)

    # 6. Improved Critical & Brutal Critical
    def test_champion_crit_range_and_brutal_critical(self):
        """Verifica il critico migliorato del Campione (19-20) e dadi extra del Barbaro."""
        champ = Character("Guerriero", char_class="Guerriero", subclass="Campione", level=5)
        self.assertEqual(champ.get_crit_threshold(), 19)

        champ15 = Character("Guerriero", char_class="Guerriero", subclass="Campione", level=15)
        self.assertEqual(champ15.get_crit_threshold(), 18)

        barb9 = Character("Barbaro", char_class="Barbaro", race="Mezzorco", level=9)
        # Barbaro 9 = +1 dado Brutale, Mezzorco = +1 dado Selvaggio -> Totale 2 dadi
        self.assertEqual(barb9.get_brutal_critical_dice(), 2)

    # 7. Monk Stunning Strike & Superiority Dice
    def test_stunning_strike_and_superiority_dice(self):
        """Verifica il Colpo Stordente del Monaco e i Dadi di Superiorità del Battle Master."""
        fighter = Character("Fighter", char_class="Guerriero", subclass="Maestro della Battaglia", level=5)
        norm = normalize_character_dict(fighter.to_dict())
        fighter = Character.from_dict(norm)
        self.assertEqual(fighter.superiority_dice_max, 4)
        self.assertEqual(fighter.superiority_dice_current, 4)

        ok, roll_val, msg = fighter.spend_superiority_die()
        self.assertTrue(ok)
        self.assertEqual(fighter.superiority_dice_current, 3)
        self.assertGreaterEqual(roll_val, 1)
        self.assertLessEqual(roll_val, 8)

    # 8. Cantrip Damage Scaling
    def test_cantrip_damage_scaling(self):
        """Verifica la scalatura dei trucchetti a 5°, 11° e 17° livello (PHB p. 201)."""
        # Livello 1-4: 1d10
        self.assertEqual(SpellsPanel.scale_cantrip_formula("1d10", 1), "1d10")
        self.assertEqual(SpellsPanel.scale_cantrip_formula("1d10", 4), "1d10")

        # Livello 5-10: 2d10
        self.assertEqual(SpellsPanel.scale_cantrip_formula("1d10", 5), "2d10")
        self.assertEqual(SpellsPanel.scale_cantrip_formula("1d10", 10), "2d10")

        # Livello 11-16: 3d10
        self.assertEqual(SpellsPanel.scale_cantrip_formula("1d10", 11), "3d10")

        # Livello 17-20: 4d10
        self.assertEqual(SpellsPanel.scale_cantrip_formula("1d10", 17), "4d10")
        self.assertEqual(SpellsPanel.scale_cantrip_formula("1d10", 20), "4d10")

    # 9. Prepared Spells Limit
    def test_prepared_spells_cap(self):
        """Verifica il calcolo del limite di incantesimi preparabili (PHB p. 201)."""
        cleric = Character("Chierico", char_class="Chierico", level=5)
        cleric.attributes["SAG"] = 16 # Mod +3 -> Max preparabili: 5 + 3 = 8
        self.assertEqual(SpellsPanel.get_max_prepared_spells(cleric), 8)

        wizard = Character("Mago", char_class="Mago", level=3)
        wizard.attributes["INT"] = 18 # Mod +4 -> Max preparabili: 3 + 4 = 7
        self.assertEqual(SpellsPanel.get_max_prepared_spells(wizard), 7)

        paladin = Character("Paladino", char_class="Paladino", level=6)
        paladin.attributes["CAR"] = 14 # Mod +2 -> Max: floor(6/2) + 2 = 5
        self.assertEqual(SpellsPanel.get_max_prepared_spells(paladin), 5)

        sorcerer = Character("Stregone", char_class="Stregone", level=5)
        self.assertEqual(SpellsPanel.get_max_prepared_spells(sorcerer), 0) # Spells known

    # 10. Monster Recharge Abilities
    def test_monster_recharge_abilities(self):
        """Verifica la ricarica a inizio turno delle abilità con Recharge 5-6 (MM p. 11)."""
        dragon = Player("Drago Rosso")
        dragon.full_sheet = {
            "actions": [
                {"name": "Soffio di Fuoco (Recharge 5-6)", "expended": True}
            ]
        }
        self.game_state.players = [dragon]
        self.game_state.combat_active = True
        self.game_state.turn_index = 0

        # Esegue next_turn: il drago ha un'abilità spesa con Recharge 5-6
        # Ripetiamo fino a che il d6 non ottiene 5 o 6
        recharged = False
        for _ in range(30):
            dragon.full_sheet["actions"][0]["expended"] = True
            self.game_state.turn_index = 0
            self.game_state.next_turn()
            if not dragon.full_sheet["actions"][0]["expended"]:
                recharged = True
                break
        self.assertTrue(recharged, "L'abilità Recharge 5-6 deve potersi ricaricare all'inizio del turno.")

    # 11. Troll Regeneration & Fire/Acid Inhibition
    def test_troll_regeneration_and_inhibition(self):
        """Verifica la rigenerazione di 10 PV all'inizio del turno e il blocco se colpito da fuoco/acido."""
        troll = Player("Troll")
        troll.hp = 30
        troll.max_hp = 84
        troll.full_sheet = {
            "special_abilities": [
                {"name": "Rigenerazione", "desc": "Il troll recupera 10 punti ferita all'inizio del suo turno."}
            ]
        }
        self.game_state.players = [troll]
        self.game_state.combat_active = True
        self.game_state.turn_index = 0

        # Turno 1: Nessun danno da fuoco -> Rigenera 10 PV (30 -> 40)
        self.game_state.next_turn()
        self.assertEqual(troll.hp, 40)

        # Subisce condizione di danno da fuoco
        troll.conditions.append("Danno da fuoco subito")
        self.game_state.turn_index = 0
        self.game_state.next_turn()
        # Non deve rigenerare
        self.assertEqual(troll.hp, 40)

    # 12. Selectable Automatic XP Distribution (DM Agency)
    def test_selectable_auto_xp_distribution(self):
        """Verifica che la distribuzione automatica di XP avvenga a fine combattimento solo se selezionata dal DM."""
        hero = Player("Eroe")
        hero.is_party_member = True
        hero.hp = 20
        hero.max_hp = 20
        hero.full_sheet = {"exp": 100, "level": 1}

        goblin = Player("Goblin")
        goblin.is_party_member = False
        goblin.hp = 0
        goblin.conditions = ["Morto"]
        goblin.full_sheet = {"cr": "1/4"} # 50 XP (CR_TO_XP['1/4'] = 50)

        self.game_state.players = [hero, goblin]

        # Caso 1: Toggle DISABILITATO dal Master (manuale o setting esplicito)
        self.game_state.automation_settings["auto_distribute_xp"] = False
        self.game_state.end_combat()
        self.assertEqual(hero.full_sheet["exp"], 100, "Con auto_distribute_xp=False l'XP non deve cambiare automaticamente.")

        # Caso 2: Toggle ABILITATO dal Master
        self.game_state.combat_active = True
        self.game_state.automation_settings["auto_distribute_xp"] = True
        self.game_state.end_combat()
        # Il goblin conferisce 50 XP all'eroe: 100 + 50 = 150
        self.assertEqual(hero.full_sheet["exp"], 150, "Con auto_distribute_xp=True l'eroe deve ricevere i 50 XP del Goblin.")

    def test_xp_thresholds_and_level_advancement(self):
        """Verifica le soglie di livello e calcolo XP (PHB p. 15)."""
        self.assertEqual(get_xp_for_level(1), 0)
        self.assertEqual(get_xp_for_level(2), 300)
        self.assertEqual(get_xp_for_level(3), 900)
        self.assertEqual(get_xp_for_level(20), 355000)

        self.assertEqual(get_level_for_xp(0), 1)
        self.assertEqual(get_level_for_xp(299), 1)
        self.assertEqual(get_level_for_xp(300), 2)
        self.assertEqual(get_level_for_xp(899), 2)
        self.assertEqual(get_level_for_xp(900), 3)
        self.assertEqual(get_level_for_xp(355000), 20)


if __name__ == '__main__':
    unittest.main()
