"""
tests/test_missing_5e_features.py - Test completi per le meccaniche D&D 5e RAW avanzate:
1. Fortuna dell'Halfling (reroll 1 naturale sul d20) & Combattere con Armi Possenti (reroll 1 e 2 sui dadi danno)
2. Multiclasse (prerequisiti min 13, progressione livelli e Tabella Slot Incantesimo Multiclasse PHB p. 165)
3. Oggetti Magici a Cariche (consumo cariche, ricarica all'alba, regola DMG p. 141 ultima carica)
4. Portento (Mago Divinatore 2d20/3d20) e Talento Fortunato (3 Punti Fortuna al Riposo Lungo)
5. Talenti Marziali (-5 TxC / +10 Danni per GWM/Sharpshooter) e Combattere con Due Armi (Off-Hand Bonus Action)
6. Magia: Lancio a Livello Superiore (Upcasting automatico formula danni/cure) & Rituali
7. Combattimento Tattico Server:
   - Aura di Protezione del Paladino (+Mod CAR ai TS degli alleati entro 10 ft / 30 ft al liv. 18)
   - Spiriti Guardiani (TS SAG e 3d8 danni radiosi a inizio turno nemico entro 15 ft)
   - Tenacia Implacabile (Mezzorco) e Protezione contro la Morte (Death Ward) a 0 PF -> 1 PF
   - Azione Preparare (Ready Action con concentrazione su incantesimi e innesco tramite Reazione)
   - Reazioni Difensive Avanzate (Assorbire Elementi, Controincantesimo, Deflettere Missili)
"""

import queue
import unittest
from unittest.mock import patch

from common.dice import roll_dice
from common.character_schema import (
    check_multiclass_prerequisites,
    calculate_multiclass_spell_slots,
    normalize_character_dict,
)
from common.item_modifiers import (
    detect_item_charges_defaults,
    use_item_charge_dict,
    recharge_item_dict,
)
from client.character_manager import Character
from client.sheet_panels.combat_panel import CombatPanel
from client.sheet_panels.spells_panel import SpellsPanel
from common.game_state import GameState, Player
from server.rules.combat import (
    apply_damage,
    get_paladin_aura_save_bonus,
    _process_save_result,
    advance_combat_turn,
    handle_ready_action_request,
    handle_trigger_readied_action_request,
    handle_reaction_response,
)


class TestMissing5eFeatures(unittest.TestCase):

    def test_halfling_luck_rerolls_natural_one(self):
        """Fortuna dell'Halfling (PHB p. 28): ritira l'1 naturale sul d20 una sola volta."""
        with patch("common.dice.random.randint", side_effect=[1, 14]):
            res = roll_dice("1d20+3", reroll_ones_d20=True)
            self.assertEqual(res["rolls"], [14])
            self.assertEqual(res["total"], 17)
            self.assertTrue(any("Halfling" in n for n in res["rerolled_notes"]))

    def test_great_weapon_fighting_rerolls_1_and_2(self):
        """Combattere con Armi Possenti (PHB p. 72): ritira 1 e 2 sui dadi danno."""
        with patch("common.dice.random.randint", side_effect=[1, 5, 2, 6]):
            res = roll_dice("2d6+4", gwf_reroll=True)
            self.assertEqual(res["rolls"], [5, 6])
            self.assertEqual(res["total"], 15)
            self.assertEqual(len(res["rerolled_notes"]), 2)

    def test_multiclass_prerequisites_and_spell_slots(self):
        """Multiclasse (PHB p. 163-165): verifica requisito 13 e calcolo slot incantatore multiclasse."""
        c = Character(name="Elminster", char_class="Guerriero", level=5)
        c.attributes = {"FOR": 16, "DES": 12, "COS": 14, "INT": 10, "SAG": 10, "CAR": 10}

        # INT 10 < 13: non può multiclassare in Mago
        ok_wiz, _ = check_multiclass_prerequisites(c, "Mago")
        self.assertFalse(ok_wiz)

        # Portiamo INT a 14: ora soddisfa sia Guerriero (FOR 16 >= 13) sia Mago (INT 14 >= 13)
        c.attributes["INT"] = 14
        ok_wiz2, _ = check_multiclass_prerequisites(c, "Mago")
        self.assertTrue(ok_wiz2)

        # Aggiungiamo 3 livelli da Mago e 4 da Chierico -> Livello incantatore 3 + 4 = 7 (slot di 4° livello)
        slots = calculate_multiclass_spell_slots({"Mago": 3, "Chierico": 4})
        self.assertEqual(slots["1"]["max"], 4)
        self.assertEqual(slots["2"]["max"], 3)
        self.assertEqual(slots["3"]["max"], 3)
        self.assertEqual(slots["4"]["max"], 1)
        self.assertEqual(slots["5"]["max"], 0)

        # Paladino 2 (mezzo incantatore = 1) + Mago 3 = livello 4 (4, 3, 0...)
        slots_pal_wiz = calculate_multiclass_spell_slots({"Paladino": 2, "Mago": 3})
        self.assertEqual(slots_pal_wiz["1"]["max"], 4)
        self.assertEqual(slots_pal_wiz["2"]["max"], 3)
        self.assertEqual(slots_pal_wiz["3"]["max"], 0)

    def test_magic_item_charges_and_long_rest_recharge(self):
        """Oggetti Magici a Cariche (DMG p. 141): rilevamento, consumo, controllo d20 su 0 cariche e ricarica."""
        wand = {"name": "Bacchetta delle Palle di Fuoco", "type": "Bacchetta", "attuned": True}
        detect_item_charges_defaults(wand)
        self.assertEqual(wand["charges_max"], 7)
        self.assertEqual(wand["charges_current"], 7)

        # Spendi 6 cariche (rimane 1 carica)
        ok1, msg1 = use_item_charge_dict(wand, cost=6)
        self.assertTrue(ok1)
        self.assertEqual(wand["charges_current"], 1)

        # Spendi l'ultima carica con d20 = 12 (non si distrugge)
        with patch("common.dice.random.randint", return_value=12):
            ok2, msg2 = use_item_charge_dict(wand, cost=1)
            self.assertTrue(ok2)
            self.assertEqual(wand["charges_current"], 0)
            self.assertIn("1d20 = 12", msg2)

        # Ricarica all'alba
        with patch("common.dice.random.randint", return_value=4):
            rec_msg = recharge_item_dict(wand)
            self.assertIsNotNone(rec_msg)
            self.assertEqual(wand["charges_current"], 5)  # 1d6(4) + 1 = 5

    def test_portent_and_lucky_on_long_rest(self):
        """Portento (Mago Divinatore) e Talento Fortunato si ricaricano al Riposo Lungo."""
        c = Character(name="Gale", char_class="Mago", subclass="Scuola di Divinazione", level=6)
        c.features = "Talento: Fortunato\nPortento"
        c.long_rest()

        self.assertEqual(len(c.portent_dice), 2)
        self.assertEqual(c.lucky_points, 3)

        used_p = c.use_portent_die(0)
        self.assertIsNotNone(used_p)
        self.assertEqual(len(c.portent_dice), 1)

        self.assertTrue(c.use_lucky_point())
        self.assertEqual(c.lucky_points, 2)

    def test_power_attack_and_two_weapon_fighting(self):
        """Maestro d'Armi Possenti / Tiratore Scelto (-5 TxC / +10 Danni) e Combattere con Due Armi."""
        c = Character(name="Conan", char_class="Guerriero", level=5)
        c.attributes["FOR"] = 18  # mod +4, pb +3 -> base TxC +7
        weapon = {"name": "Spadone", "ability": "FOR", "damage_dice": "2d6", "bonus": 1, "proficient": True}

        normal_txc = CombatPanel.calculate_weapon_txc(c, weapon, power_attack=False)
        power_txc = CombatPanel.calculate_weapon_txc(c, weapon, power_attack=True)
        self.assertEqual(normal_txc[0], 8)  # +4 FOR + 3 PB + 1 magic
        self.assertEqual(power_txc[0], 3)   # 8 - 5 = 3

        normal_dmg = CombatPanel.calculate_weapon_damage(c, weapon, power_attack=False, is_offhand=False)
        power_dmg = CombatPanel.calculate_weapon_damage(c, weapon, power_attack=True, is_offhand=False)
        self.assertEqual(normal_dmg[2], 5)    # +4 FOR + 1 magic
        self.assertEqual(power_dmg[2], 15)    # 5 + 10 = 15

        # Mano secondaria senza Stile Combattere con Due Armi: non somma il +4 di FOR positivo
        offhand_no_style = CombatPanel.calculate_weapon_damage(c, weapon, power_attack=False, is_offhand=True)
        self.assertEqual(offhand_no_style[2], 1)  # 0 mod + 1 magic

        # Con Stile di Combattimento: Combattere con Due Armi somma anche il +4 di FOR
        c.features = "Stile di Combattimento: Combattere con Due Armi"
        offhand_with_style = CombatPanel.calculate_weapon_damage(c, weapon, power_attack=False, is_offhand=True)
        self.assertEqual(offhand_with_style[2], 5)

    def test_spell_upcasting_and_ritual_detection(self):
        """Upcasting automatico (PHB p. 201) e rilevamento Rituali."""
        # Palla di Fuoco (base 8d6 al 3° liv -> 10d6 al 5° liv)
        scaled_fb = SpellsPanel.scale_spell_formula_for_upcast("8d6", 3, 5, "Palla di Fuoco")
        self.assertEqual(scaled_fb, "10d6")

        # Cura Ferite (base 1d8+3 al 1° liv -> 3d8+3 al 3° liv)
        scaled_cw = SpellsPanel.scale_spell_formula_for_upcast("1d8+3", 1, 3, "Cura Ferite")
        self.assertEqual(scaled_cw, "3d8+3")

        self.assertTrue(SpellsPanel.is_ritual_spell({"name": "Individuazione del Magico", "level": 1}))
        self.assertFalse(SpellsPanel.is_ritual_spell({"name": "Palla di Fuoco", "level": 3}))

    def test_paladin_aura_of_protection_and_spirit_guardians(self):
        """Aura di Protezione del Paladino (+Mod CAR entro 10 ft) e Spiriti Guardiani (3d8 a inizio turno)."""
        gs = GameState(queue.Queue())
        gs.current_map = {"grid_type": "hex", "walls": []}

        paladin = Player("Artorius", (0, 0))
        paladin.is_party_member = True
        paladin.hp = 50
        paladin.max_hp = 50
        paladin.full_sheet = {
            "char_class": "Paladino",
            "level": 6,
            "attributes": {"FOR": 16, "DES": 10, "COS": 14, "INT": 10, "SAG": 12, "CAR": 18},  # CAR 18 -> +4
        }

        ally = Player("Lyra", (1, 0))  # Distanza 1 esagono (5 ft <= 10 ft)
        ally.is_party_member = True
        ally.hp = 30
        ally.max_hp = 30
        ally.position = [1, 0]
        paladin.position = [0, 0]

        gs.players = [paladin, ally]

        bonus, pal_name = get_paladin_aura_save_bonus(ally, gs)
        self.assertEqual(bonus, 4)
        self.assertEqual(pal_name, "Artorius")

        # Se Lyra si allontana a 4 esagoni (20 ft > 10 ft per Paladino liv 6), bonus = 0
        ally.position = [4, 0]
        bonus_far, _ = get_paladin_aura_save_bonus(ally, gs)
        self.assertEqual(bonus_far, 0)

        # Al livello 18 l'aura si espande a 30 ft (6 esagoni)
        paladin.full_sheet["level"] = 18
        bonus_lvl18, _ = get_paladin_aura_save_bonus(ally, gs)
        self.assertEqual(bonus_lvl18, 4)

    def test_relentless_endurance_and_death_ward_prevent_0_hp(self):
        """Tenacia Implacabile (Mezzorco) e Protezione contro la Morte lasciano a 1 PF invece di 0 PF."""
        gs = GameState(queue.Queue())

        orc = Player("Grommash", (0, 0))
        orc.is_party_member = True
        orc.hp = 10
        orc.max_hp = 40
        orc.full_sheet = {"race": "Mezzorco", "relentless_endurance_used": False}

        # Subisce 15 danni (andrebbe a -5, non è morte istantanea perché 5 < 40) -> resta a 1 PF!
        apply_damage(orc, 15, "Tagliente", gs)
        self.assertEqual(orc.hp, 1)
        self.assertTrue(orc.relentless_endurance_used)

        # Un secondo colpo letale prima del riposo lungo lo manda a 0 PF
        apply_damage(orc, 10, "Tagliente", gs)
        self.assertEqual(orc.hp, 0)

        # Protezione contro la Morte (Death Ward)
        cleric = Player("Kyra", (0, 0))
        cleric.is_party_member = True
        cleric.hp = 8
        cleric.max_hp = 35
        cleric.conditions = ["Protezione contro la Morte"]
        apply_damage(cleric, 20, "Necrotico", gs)
        self.assertEqual(cleric.hp, 1)
        self.assertNotIn("Protezione contro la Morte", cleric.conditions)

    def test_ready_action_and_advanced_reactions(self):
        """Azione Preparare (Ready Action) e Reazioni Difensive (Assorbire Elementi, Deflettere Missili)."""
        gs = GameState(queue.Queue())
        p = Player("Kaelen", (0, 0))
        p.is_party_member = True
        p.hp = 25
        p.max_hp = 30
        p.conditions = []
        gs.players = [p]

        # Prepara un incantesimo -> attiva "Azione Preparata" e "Concentrazione"
        handle_ready_action_request(
            {"trigger_text": "Il drago atterra", "readied_action": "Dardo Incantato", "is_spell": True},
            p,
            gs,
        )
        self.assertIn("Azione Preparata", p.conditions)
        self.assertIn("Concentrazione", p.conditions)
        self.assertTrue(p.has_acted_this_turn)

        # Innesca l'azione preparata -> consuma la Reazione e rimuove "Azione Preparata"
        handle_trigger_readied_action_request({"target_name": "Drago Rosso"}, p, gs)
        self.assertTrue(p.has_reacted_this_turn)
        self.assertNotIn("Azione Preparata", p.conditions)

        # Reset reazione e test Assorbire Elementi
        p.has_reacted_this_turn = False
        handle_reaction_response(
            {"reaction_type": "ABSORB_ELEMENTS", "accepted": True, "details": {"damage_type": "Fuoco"}},
            p,
            gs,
        )
        self.assertTrue(p.has_reacted_this_turn)
        self.assertIn("Fuoco", p.damage_resistances)
        self.assertIn("Assorbire Elementi (Fuoco)", p.conditions)


if __name__ == "__main__":
    unittest.main()
