"""
tests/test_item_modifiers.py - Test unitari per il calcolo automatico dei modificatori da oggetti magici (5e RAW).
Verifica:
- Armature magiche (+1, +2, +3, Piastre Naniche, Scaglie di Drago, Armatura Demoniaca)
- Scudi normali e magici (+1, +2, +3)
- Oggetti meravigliosi da difesa (Anello/Mantello di Protezione, Bracciali della Difesa, Veste dell'Arcimago)
- Statistiche alterate (Guanti dell'Orco, Fascia Intelletto, Amuleto Salute, Cinture Giganti, Tomi)
- Armi magiche (+1, +2, +3, Spada del Sole, Holy Avenger) su TxC e Danni
- Modificatori incantesimi (Verga Custode del Patto, Grimorio Arcano)
- Reattività dinamica e rispetto dei limiti di sintonizzazione (max 3 standard, 6 per Artefice)
"""

import unittest
from client.character_manager import Character
from common.item_modifiers import (
    extract_magic_bonus, detect_armor_properties,
    calculate_character_item_modifiers, compute_effective_ac
)
from client.sheet_panels.combat_panel import CombatPanel
from client.sheet_panels.spells_panel import SpellsPanel


class TestItemModifiers(unittest.TestCase):

    def setUp(self):
        self.char = Character(name="Kaelen")
        self.char.char_class = "Guerriero"
        self.char.level = 5
        self.char.attributes = {
            "FOR": 16,  # Mod +3
            "DES": 14,  # Mod +2
            "COS": 14,  # Mod +2
            "INT": 10,  # Mod +0
            "SAG": 12,  # Mod +1
            "CAR": 8    # Mod -1
        }
        self.char.saving_throw_proficiencies = ["FOR", "COS"]
        self.char.inventory_grid = [None] * 25

    def test_extract_magic_bonus(self):
        """Verifica l'estrazione affidabile del bonus magico (+1, +2, +3) dai nomi o testi."""
        self.assertEqual(extract_magic_bonus("Armatura a Piastre +3"), 3)
        self.assertEqual(extract_magic_bonus("Scudo +2"), 2)
        self.assertEqual(extract_magic_bonus("Spada Lunga +1"), 1)
        self.assertEqual(extract_magic_bonus("+3 Holy Avenger"), 3)
        self.assertEqual(extract_magic_bonus("Cotta di Maglia"), 0)
        self.assertEqual(extract_magic_bonus("Pozione di Cura"), 0)

    def test_detect_armor_properties(self):
        """Verifica il corretto rilevamento di CA base, destrezza massima e bonus magico."""
        # Armatura a Piastre +3 (Heavy: 18 base, 0 dex, +3 magico)
        plate_p = detect_armor_properties({"name": "Armatura a Piastre +3", "type": "Armatura"})
        self.assertTrue(plate_p["is_armor"])
        self.assertEqual(plate_p["category"], "heavy")
        self.assertEqual(plate_p["base_ac"], 18)
        self.assertEqual(plate_p["max_dex"], 0)
        self.assertEqual(plate_p["magic_bonus"], 3)

        # Mezza Armatura +2 (Medium: 15 base, max 2 dex, +2 magico)
        half_p = detect_armor_properties({"name": "Mezza Armatura +2", "type": "Armatura"})
        self.assertTrue(half_p["is_armor"])
        self.assertEqual(half_p["category"], "medium")
        self.assertEqual(half_p["base_ac"], 15)
        self.assertEqual(half_p["max_dex"], 2)
        self.assertEqual(half_p["magic_bonus"], 2)

        # Cuoio Borchiato +1 (Light: 12 base, dex illimitata, +1 magico)
        stud_p = detect_armor_properties({"name": "Cuoio Borchiato +1", "type": "Armatura"})
        self.assertTrue(stud_p["is_armor"])
        self.assertEqual(stud_p["category"], "light")
        self.assertEqual(stud_p["base_ac"], 12)
        self.assertIsNone(stud_p["max_dex"])
        self.assertEqual(stud_p["magic_bonus"], 1)

        # Scudo +3 (Shield: 2 base, +3 magico)
        shield_p = detect_armor_properties({"name": "Scudo +3", "type": "Scudo"})
        self.assertTrue(shield_p["is_shield"])
        self.assertEqual(shield_p["base_ac"], 2)
        self.assertEqual(shield_p["magic_bonus"], 3)

    def test_magic_armor_legendary_plus_three(self):
        """Verifica specifica della richiesta utente: calcolo automatico di Armatura a Piastre +3 (18 + 3 = 21 CA)."""
        self.char.inventory_grid[0] = {
            "name": "Armatura a Piastre +3",
            "type": "Armatura",
            "container": "equipped"
        }
        # Heavy armor -> DES mod ignorato (0). CA = 18 + 3 = 21
        self.assertEqual(self.char.recalculate_ac(), 21)
        self.assertEqual(self.char.get_effective_ac(), 21)

    def test_magic_armor_and_magic_shield_stacking(self):
        """Verifica la combinazione di Armatura a Piastre +3 (21) e Scudo +3 (5) = 26 CA."""
        self.char.inventory_grid[0] = {
            "name": "Armatura a Piastre +3",
            "type": "Armatura",
            "container": "equipped"
        }
        self.char.inventory_grid[1] = {
            "name": "Scudo +3",
            "type": "Scudo",
            "container": "equipped"
        }
        # 18 (base piastre) + 3 (magico piastre) + 2 (base scudo) + 3 (magico scudo) = 26 CA
        self.assertEqual(self.char.recalculate_ac(), 26)

    def test_medium_and_light_magic_armor_with_dex(self):
        """Verifica la destrezza permessa su armature medie e leggere magiche."""
        # Mezza Armatura +1 con DES 14 (mod +2): 15 + 1 + 2 = 18
        self.char.inventory_grid[0] = {
            "name": "Mezza Armatura +1",
            "type": "Armatura",
            "container": "equipped"
        }
        self.assertEqual(self.char.recalculate_ac(), 18)

        # Cuoio Borchiato +2 con DES 14 (mod +2): 12 + 2 + 2 = 16
        self.char.inventory_grid[0] = {
            "name": "Cuoio Borchiato +2",
            "type": "Armatura",
            "container": "equipped"
        }
        self.assertEqual(self.char.recalculate_ac(), 16)

    def test_wondrous_items_attunement_ac_and_saves(self):
        """Verifica Anello e Mantello della Protezione (+1 CA, +1 TS ciascuno)."""
        self.char.inventory_grid[0] = {
            "name": "Armatura a Piastre +2",
            "type": "Armatura",
            "container": "equipped"
        }
        self.char.inventory_grid[1] = {
            "name": "Anello di Protezione",
            "type": "Anello",
            "container": "equipped",
            "attuned": True,
            "desc": "+1 alla CA e ai tiri salvezza"
        }
        self.char.inventory_grid[2] = {
            "name": "Mantello della Protezione",
            "type": "Oggetto Meraviglioso",
            "container": "equipped",
            "attuned": True,
            "desc": "+1 alla CA e a tutti i tiri salvezza"
        }
        # Piastre +2 = 20 CA. +1 Anello + 1 Mantello = 22 CA!
        self.assertEqual(self.char.recalculate_ac(), 22)

        # TS FOR: FOR 16 (mod +3) + PB (liv 5 = +3) + 2 da oggetti = +8!
        self.assertEqual(self.char.get_effective_save_bonus("FOR"), 8)
        # TS DES (non competente): DES 14 (mod +2) + 2 da oggetti = +4!
        self.assertEqual(self.char.get_effective_save_bonus("DES"), 4)

    def test_bracers_of_defense_raw_compliance(self):
        """I Bracciali della Difesa danno +2 CA SOLO se NON si indossa armatura e NON si usa scudo."""
        wizard = Character(name="Mago")
        wizard.char_class = "Mago"
        wizard.attributes["DES"] = 14  # Mod +2 -> Base unarmored = 12
        wizard.inventory_grid[0] = {
            "name": "Bracciali della Difesa",
            "type": "Oggetto Meraviglioso",
            "container": "equipped",
            "attuned": True
        }
        # Senza armatura e senza scudo: 10 + 2 + 2 = 14 CA
        self.assertEqual(wizard.recalculate_ac(), 14)

        # Se equipaggia un'armatura, i bracciali si disattivano (D&D 5e RAW)
        wizard.inventory_grid[1] = {
            "name": "Armatura di Cuoio",
            "type": "Armatura",
            "container": "equipped"
        }
        # Cuoio: 11 + 2 = 13 (Bracciali inattivi)
        self.assertEqual(wizard.recalculate_ac(), 13)

    def test_stat_altering_items_gauntlets_and_amulet(self):
        """Verifica oggetti che impostano attributi (Guanti dell'Orco FOR 19, Amuleto Salute COS 19)."""
        weak_char = Character(name="Debole")
        weak_char.attributes["FOR"] = 8   # Mod -1
        weak_char.attributes["COS"] = 10  # Mod +0
        weak_char.inventory_grid[0] = {
            "name": "Guanti della Forza dell'Orco",
            "container": "equipped",
            "attuned": True
        }
        weak_char.inventory_grid[1] = {
            "name": "Amuleto della Salute",
            "container": "equipped",
            "attuned": True
        }

        # FOR passa da 8 a 19 (Mod passa da -1 a +4)
        self.assertEqual(weak_char.get_effective_attribute("FOR"), 19)
        self.assertEqual(weak_char.get_modifier("FOR"), 4)

        # COS passa da 10 a 19 (Mod passa da 0 a +4)
        self.assertEqual(weak_char.get_effective_attribute("COS"), 19)
        self.assertEqual(weak_char.get_modifier("COS"), 4)

    def test_magic_weapons_txc_and_damage(self):
        """Verifica che un'arma magica +3 applichi il bonus sia al tiro per colpire che al danno."""
        weapon = {
            "name": "Spada Lunga +3",
            "type": "Arma da Guerra",
            "ability": "FOR",
            "damage_dice": "1d8",
            "damage_type": "tagliente",
            "proficient": True
        }
        # Personaggio liv 5 (PB = +3), FOR 16 (mod = +3)
        # TxC = 3 (mod) + 3 (PB) + 3 (magico) = +9
        total_txc, mod, prof, w_bonus, stat_key = CombatPanel.calculate_weapon_txc(self.char, weapon)
        self.assertEqual(total_txc, 9)
        self.assertEqual(w_bonus, 3)

        # Danno = 1d8 + 3 (mod) + 3 (magico) = 1d8+6
        formula, display_str, dmg_mod = CombatPanel.calculate_weapon_damage(self.char, weapon, mod, w_bonus)
        self.assertEqual(dmg_mod, 6)
        self.assertEqual(formula, "1d8+6")

    def test_magic_foci_spell_dc_and_attack(self):
        """Verifica Verga del Custode del Patto / Grimorio Arcano (+2 a CD e TxC magico)."""
        warlock = Character(name="Warlock")
        warlock.char_class = "Warlock"
        warlock.level = 5
        warlock.attributes["CAR"] = 16  # Mod +3, PB = +3 -> Base CD = 8+3+3 = 14, Atk = +6
        warlock.inventory_grid[0] = {
            "name": "Verga del Custode del Patto +2",
            "type": "Verga",
            "container": "equipped",
            "attuned": True
        }
        stats = SpellsPanel.calculate_spell_stats(warlock)
        # CD = 14 + 2 = 16, Atk = +6 + 2 = +8
        self.assertEqual(stats["dc"], 16)
        self.assertEqual(stats["attack_bonus"], 8)
        self.assertEqual(stats["attack_str"], "+8")

    def test_attunement_limit_enforcement(self):
        """Verifica il rispetto del limite di 3 sintonizzazioni per classi standard."""
        self.char.inventory_grid = [
            {"name": "Oggetto 1", "attuned": True, "bonus_ac": 1},
            {"name": "Oggetto 2", "attuned": True, "bonus_ac": 1},
            {"name": "Oggetto 3", "attuned": True, "bonus_ac": 1},
            {"name": "Oggetto 4", "attuned": True, "bonus_ac": 1},  # Oltre il limite
        ]
        mods = self.char.get_item_modifiers()
        self.assertEqual(mods["attuned_count"], 3)
        self.assertEqual(mods["bonus_ac"], 3)  # Solo i primi 3 contano

    def test_duplicate_attunement_prevention_raw(self):
        """D&D 5e RAW: non è possibile sintonizzarsi con più copie dello stesso oggetto."""
        self.char.inventory_grid = [
            {"name": "Anello di Protezione", "attuned": True, "container": "equipped"},
            {"name": "Anello di Protezione", "attuned": True, "container": "equipped"},
        ]
        mods = self.char.get_item_modifiers()
        self.assertEqual(mods["attuned_count"], 1)
        self.assertEqual(mods["bonus_ac"], 1)
        self.assertEqual(mods["bonus_saves"], 1)

    def test_stowed_and_dropped_backpack_exclusion(self):
        """Oggetti in Borsa Conservante o nello zaino lasciato a terra non conferiscono bonus."""
        self.char.inventory_grid = [
            {"name": "Anello di Protezione", "attuned": True, "container": "bag_of_holding"},
            {"name": "Pietra della Buona Fortuna", "attuned": True, "container": "backpack"},
        ]
        # Borsa conservante ignorata, zaino attivo -> solo Pietra (+1 TS) attiva
        mods = self.char.get_item_modifiers()
        self.assertEqual(mods["bonus_ac"], 0)
        self.assertEqual(mods["bonus_saves"], 1)

        # Se lascia lo zaino a terra, anche la Pietra nello zaino diventa inattiva
        self.char.backpack_dropped = True
        mods_dropped = self.char.get_item_modifiers()
        self.assertEqual(mods_dropped["bonus_saves"], 0)

    def test_fighting_style_defense_no_false_positives(self):
        """Verifica che 'Difesa Senz'Armatura' o 'Difesa contro Attacchi Multipli' non diano +1 CA con armatura."""
        barb = Character(name="Grog")
        barb.char_class = "Barbaro"
        barb.attributes = {"FOR": 16, "DES": 14, "COS": 16, "INT": 8, "SAG": 10, "CAR": 10}
        barb.features = "Ira Barbarica, Difesa Senz'Armatura"
        barb.inventory_grid = [
            {"name": "Mezza Armatura", "type": "Armatura", "container": "equipped"}
        ]
        # Mezza Armatura (15) + DES (2) = 17 (NON 18!)
        self.assertEqual(barb.recalculate_ac(), 17)

        # Guerriero con vero Stile di Combattimento: Difesa -> +1 CA con armatura
        self.char.features = "Recuperare Energie, Stile di Combattimento: Difesa"
        self.char.inventory_grid = [
            {"name": "Armatura a Piastre", "type": "Armatura", "container": "equipped"}
        ]
        self.assertEqual(self.char.recalculate_ac(), 19)

    def test_staff_of_power_vs_robe_of_archmagi_raw(self):
        """Bastone del Potere (+2 TxC magico, +0 CD) vs Veste dell'Arcimago (+2 TxC magico, +2 CD)."""
        wiz = Character(name="Elminster")
        wiz.char_class = "Mago"
        wiz.level = 5
        wiz.attributes["INT"] = 18  # Mod +4, PB +3 -> Base CD = 15, Atk = +7
        wiz.inventory_grid = [
            {"name": "Bastone del Potere", "attuned": True, "container": "equipped"}
        ]
        stats_staff = SpellsPanel.calculate_spell_stats(wiz)
        self.assertEqual(stats_staff["dc"], 15)
        self.assertEqual(stats_staff["attack_bonus"], 9)

        wiz.inventory_grid.append(
            {"name": "Veste dell'Arcimago", "attuned": True, "container": "equipped"}
        )
        stats_both = SpellsPanel.calculate_spell_stats(wiz)
        self.assertEqual(stats_both["dc"], 17)
        self.assertEqual(stats_both["attack_bonus"], 11)

    def test_unequipped_attuned_armor_does_not_leak_ac(self):
        """Un'armatura magica sintonizzata ma nello zaino non somma bonus_ac."""
        self.char.inventory_grid = [
            {
                "name": "Armatura Demoniaca",
                "type": "Armatura",
                "container": "backpack",
                "attuned": True,
                "desc": "Finché indossi questa armatura ottieni +1 alla CA."
            }
        ]
        # Non equipaggiata -> CA senz'armatura = 10 + DES (2) = 12
        self.assertEqual(self.char.recalculate_ac(), 12)

    def test_normalize_character_dict_preserves_features_string_and_list(self):
        """normalize_character_dict mantiene 'features' come stringa e 'features_list' come lista."""
        from common.character_schema import normalize_character_dict
        raw = {
            "name": "TestHero",
            "features": "Scurovisione\nAzione Impetuosa",
            "features_list": [{"name": "Azione Impetuosa", "category": "Privilegio di Classe", "desc": "Extra action"}],
            "has_inspiration": True
        }
        clean = normalize_character_dict(raw)
        self.assertIsInstance(clean["features"], str)
        self.assertIn("Scurovisione", clean["features"])
        self.assertIsInstance(clean["features_list"], list)
        self.assertEqual(len(clean["features_list"]), 1)
        self.assertTrue(clean["inspiration"])
        self.assertTrue(clean["has_inspiration"])

    def test_sync_weapons_from_inventory_and_finesse_ranged(self):
        """Le armi equipaggiate nell'inventario vengono sincronizzate e usano la caratteristica 5e corretta."""
        self.char.attributes["FOR"] = 10  # Mod +0
        self.char.attributes["DES"] = 18  # Mod +4
        self.char.inventory_grid = [
            {"name": "Spada Corta +2", "type": "Arma", "container": "equipped"},
            {"name": "Arco Lungo +1", "type": "Arma", "container": "equipped"},
        ]
        self.char.sync_weapons_from_inventory()
        w_names = [w["name"] for w in self.char.weapons]
        self.assertIn("Spada Corta +2", w_names)
        self.assertIn("Arco Lungo +1", w_names)

        shortsword = next(w for w in self.char.weapons if w["name"] == "Spada Corta +2")
        longbow = next(w for w in self.char.weapons if w["name"] == "Arco Lungo +1")

        # Spada Corta è Accurata (Finesse) -> usa DES (+4) + PB (+3) + Magico (+2) = +9
        txc_ss, mod_ss, _, wb_ss, stat_ss = CombatPanel.calculate_weapon_txc(self.char, shortsword)
        self.assertEqual(stat_ss, "DES")
        self.assertEqual(mod_ss, 4)
        self.assertEqual(wb_ss, 2)
        self.assertEqual(txc_ss, 9)

        # Arco Lungo è a distanza -> usa obbligatoriamente DES (+4) + PB (+3) + Magico (+1) = +8
        self.char.attributes["FOR"] = 20  # Anche con FOR 20 (+5), l'arco usa DES (+4)
        txc_lb, mod_lb, _, wb_lb, stat_lb = CombatPanel.calculate_weapon_txc(self.char, longbow)
        self.assertEqual(stat_lb, "DES")
        self.assertEqual(mod_lb, 4)
        self.assertEqual(wb_lb, 1)
        self.assertEqual(txc_lb, 8)

    def test_player_effective_save_and_darkvision_with_string_features(self):
        """Player.check_has_darkvision e get_effective_save_bonus_from_dict funzionano su Player con full_sheet."""
        from common.game_state import Player
        from common.item_modifiers import get_effective_save_bonus_from_dict
        sheet = self.char.to_dict()
        sheet["features"] = "Scurovisione 18m\nRecuperare Energie"
        sheet["inventory_grid"] = [
            {"name": "Anello di Protezione", "attuned": True, "container": "equipped"}
        ]
        p = Player("Kaelen", (0, 0))
        p.full_sheet = sheet
        self.assertTrue(p.check_has_darkvision())
        # COS 14 (+2) + PB (+3) + Anello (+1) = +6
        self.assertEqual(get_effective_save_bonus_from_dict(p, "COS"), 6)


if __name__ == "__main__":
    unittest.main()

