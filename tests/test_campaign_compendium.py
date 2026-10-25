# test_campaign_compendium.py
"""
Test di integrazione per l'aggiunta di elementi dal compendio 5e e dai manuali PDF in 'Crea Campagna':
- Importazione equipaggiamento nello Starter Kit
- Importazione mostri/PNG dal compendio e manuali PDF nei PNG chiave della campagna
- Importazione magie/oggetti/lore dai manuali PDF negli Handouts della campagna
- Categorie e filtri per manuali PDF (Monster Manual, PHB 2024, DMG 2024, TCoE, XGtE)
- Consultazione globale dal compendio con routing intelligente dei tab
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import tkinter as tk
import queue

from common.theme import setup_theme
from common.campaign import Campaign
from common.game_state import GameState
from server.campaign_editor_ui import CampaignEditorDialog
from server.compendium_ui import CompendiumDialog

class TestCampaignCompendiumIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
            setup_theme(cls.root)
        except (tk.TclError, Exception):
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root:
            try:
                cls.root.destroy()
            except Exception:
                pass

    def setUp(self):
        if not self.root:
            self.skipTest("Tkinter not available in headless environment")
        self.camp = Campaign(name="Campagna Compendium Test")
        self.q = queue.Queue()
        self.gs = GameState(self.q)
        self.editor = CampaignEditorDialog(self.root, campaign=self.camp, game_state=self.gs)

    def tearDown(self):
        if hasattr(self, "editor") and self.editor:
            try:
                self.editor.destroy()
            except Exception:
                pass

    def test_compendium_dialog_params(self):
        """Verifica che CompendiumDialog accetti initial_category e action_label."""
        with patch.object(CompendiumDialog, "fetch_list"):
            dlg = CompendiumDialog(
                self.root,
                on_import_callback=lambda d, c: None,
                is_dm=True,
                initial_category="Equipaggiamento",
                action_label="➕ Aggiungi al Kit"
            )
            self.assertEqual(dlg.initial_category, "Equipaggiamento")
            self.assertEqual(dlg.action_label, "➕ Aggiungi al Kit")
            self.assertEqual(dlg.category_var.get(), "Equipaggiamento")
            dlg.destroy()

    def test_compendium_dialog_includes_pdf_manual_categories(self):
        """Verifica che CompendiumDialog elenchi le categorie dei manuali PDF."""
        with patch.object(CompendiumDialog, "fetch_list"):
            dlg = CompendiumDialog(self.root, is_dm=True)
            values = dlg.category_cb["values"]
            self.assertTrue(any("Monster Manual" in v for v in values))
            self.assertTrue(any("Player's Handbook" in v for v in values))
            self.assertTrue(any("Dungeon Master's Guide" in v for v in values))
            self.assertTrue(any("Tutti i Manuali" in v for v in values))
            dlg.destroy()

    def test_import_starter_kit_from_compendium_data(self):
        """Verifica parsing e inserimento di un'arma nello starter kit della campagna."""
        initial_count = len(self.camp.starter_kit)
        weapon_data = {
            "name": "Arco Lungo",
            "equipment_category": {"name": "Weapon"},
            "damage": {"damage_dice": "1d8", "damage_type": {"name": "Piercing"}},
            "properties": [{"name": "Due mani"}, {"name": "Pesante"}],
            "weight": 2.0,
            "desc": "Arco lungo in legno di tasso."
        }
        self.editor._import_starter_kit_data(weapon_data, "Equipaggiamento")
        self.assertEqual(len(self.camp.starter_kit), initial_count + 1)
        added = self.camp.starter_kit[-1]
        self.assertEqual(added["name"], "Arco Lungo")
        self.assertEqual(added["type"], "Arma")
        self.assertEqual(added["weight"], 2.0)
        self.assertIn("1d8", added["desc"])
        self.assertIn("Due mani", added["desc"])

    def test_import_npc_from_compendium_data(self):
        """Verifica parsing e inserimento di una creatura/PNG dal compendio."""
        initial_count = len(self.camp.npcs)
        monster_data = {
            "name": "Cultista Fanatico",
            "type": "humanoid",
            "subtype": "human",
            "hit_points": 33,
            "armor_class": 13,
            "alignment": "medium humanoid, lawful evil",
            "challenge_rating": 2,
            "senses": "Percezione passiva 11",
            "languages": "Comune",
            "actions": [{"name": "Pugnale Sacrificale"}, {"name": "Lancio Incantesimi"}]
        }
        self.editor._import_npc_data(monster_data, "Mostri")
        self.assertEqual(len(self.camp.npcs), initial_count + 1)
        added = self.camp.npcs[-1]
        self.assertEqual(added["name"], "Cultista Fanatico")
        self.assertEqual(added["hp"], 33)
        self.assertEqual(added["ac"], 13)
        self.assertIn("humanoid", added["role"])
        self.assertIn("lawful evil", added["notes"])
        self.assertIn("Pugnale Sacrificale", added["notes"])

    def test_import_handout_from_compendium_data(self):
        """Verifica parsing e inserimento di un oggetto magico/documento negli handouts."""
        initial_count = len(self.camp.handouts)
        magic_item_data = {
            "name": "Tomo dei Pensieri Limpidi",
            "rarity": "Molto Raro",
            "type": "Libro Magico",
            "desc": "Questo libro contiene esercizi per la memoria e la logica. Leggerlo aumenta l'Intelligenza di 2."
        }
        self.editor._import_handout_data(magic_item_data, "Oggetti Magici")
        self.assertEqual(len(self.camp.handouts), initial_count + 1)
        added = self.camp.handouts[-1]
        self.assertEqual(added["title"], "Tomo dei Pensieri Limpidi")
        self.assertIn("Molto Raro", added["content"])
        self.assertIn("Intelligenza di 2", added["content"])

    @patch("server.compendium_ui.messagebox.showinfo")
    def test_compendium_import_pdf_monster_entry(self, mock_info):
        """Verifica che una voce mostro estratta da un manuale PDF venga importata con statistiche corrette."""
        imported_item = {}
        imported_cat = ""
        def cb(item, cat):
            nonlocal imported_item, imported_cat
            imported_item = item
            imported_cat = cat

        with patch.object(CompendiumDialog, "fetch_list"):
            dlg = CompendiumDialog(self.root, on_import_callback=cb, is_dm=True)
            dlg.category_var.set("📖 [PDF] Monster Manual (Mostri)")

            pdf_monster = {
                "title": "Beholder Tyrant",
                "manual": "MM",
                "manual_name": "Monster Manual",
                "category": "Mostri & PNG",
                "page_ref": "Pag. 36",
                "content": "A spherical floating horror with ten eyestalks and a central eye.",
                "monster_data": {
                    "hp": 180,
                    "ac": 18,
                    "cr": "13",
                    "attributes": {"FOR": 10, "DES": 14, "COS": 18, "INT": 17, "SAG": 15, "CAR": 17}
                }
            }

            dlg._on_statblock_action(pdf_monster, "Mostri")
            dlg.destroy()

        self.assertEqual(imported_cat, "Mostri")
        self.assertEqual(imported_item.get("name"), "Beholder Tyrant")
        self.assertEqual(imported_item.get("hp"), 180)
        self.assertEqual(imported_item.get("ac"), 18)
        self.assertEqual(imported_item.get("cr"), "13")
        self.assertIn("spherical floating", imported_item.get("desc"))

        # Ora testiamo l'inserimento di questo mostro PDF nei PNG della campagna
        self.editor._import_npc_data(imported_item, "Mostri")
        npc = self.camp.npcs[-1]
        self.assertEqual(npc["name"], "Beholder Tyrant")
        self.assertEqual(npc["hp"], 180)
        self.assertEqual(npc["ac"], 18)
        self.assertEqual(npc["attributes"]["INT"], 17)

    @patch("server.compendium_ui.messagebox.showinfo")
    def test_compendium_import_pdf_rule_or_item_entry(self, mock_info):
        """Verifica che una regola o oggetto estratto da un PDF venga importato con fonte manuale."""
        imported_item = {}
        imported_cat = ""
        def cb(item, cat):
            nonlocal imported_item, imported_cat
            imported_item = item
            imported_cat = cat

        with patch.object(CompendiumDialog, "fetch_list"):
            dlg = CompendiumDialog(self.root, on_import_callback=cb, is_dm=True)
            dlg.category_var.set("📖 [PDF] Dungeon Master's Guide (DMG 2024)")

            pdf_rule = {
                "title": "Creating Magic Items",
                "manual": "DMG",
                "manual_name": "Dungeon Master's Guide 2024",
                "category": "Equipaggiamento & Tesori",
                "page_ref": "Pag. 71",
                "content": "Crafting a magic item requires a formula, rare ingredients, and focused spellcasting."
            }

            dlg._on_statblock_action(pdf_rule, "Equipaggiamento")
            dlg.destroy()

        self.assertEqual(imported_cat, "Equipaggiamento")
        self.assertEqual(imported_item.get("name"), "Creating Magic Items")

        # Importiamo come handout nella campagna
        self.editor._import_handout_data(imported_item, "Regole")
        handout = self.camp.handouts[-1]
        self.assertEqual(handout["title"], "Creating Magic Items")
        self.assertIn("Dungeon Master's Guide 2024", handout["content"])
        self.assertIn("Pag. 71", handout["content"])
        self.assertIn("Crafting a magic item", handout["content"])

    @patch("server.compendium_ui.CompendiumDialog")
    def test_open_global_compendium_modal(self, mock_comp_dialog):
        """Verifica apertura del compendio globale dalla toolbar della campagna."""
        captured_cb = None
        def mock_init(master, on_import_callback=None, is_dm=True, initial_category=None, action_label=None):
            nonlocal captured_cb
            captured_cb = on_import_callback
            return MagicMock()

        mock_comp_dialog.side_effect = mock_init
        self.editor.open_global_compendium()
        self.assertIsNotNone(captured_cb)

        # Selezioniamo il tab PNG
        tab_idx = None
        for i in range(self.editor.notebook.index("end")):
            if "png" in self.editor.notebook.tab(i, "text").lower():
                tab_idx = i
                break
        if tab_idx is not None:
            self.editor.notebook.select(tab_idx)

        npc_data = {
            "name": "Guardia Cittadina",
            "type": "humanoid",
            "hit_points": 11,
            "armor_class": 16
        }
        captured_cb(npc_data, "Mostri")
        self.assertTrue(any(n["name"] == "Guardia Cittadina" for n in self.camp.npcs))

    def test_compendium_bilingual_offline_sorting_favorites_and_dice(self):
        """Verifica ricerca bilingue IT/EN, caricamento offline 0ms, ordinamento colonne, preferiti, tiri di dado e quantità."""
        imported_calls = []
        dlg = CompendiumDialog(
            self.root,
            on_import_callback=lambda item, cat: imported_calls.append((item.get("name"), cat)),
            is_dm=True,
            initial_category="Incantesimi",
        )

        # 1. Ricerca bilingue Italiano -> Inglese su Incantesimi (es. 'palla di fuoco' -> 'Fireball')
        dlg.search_var.set("palla di fuoco")
        names_found = [it.get("name", "").lower() for it in dlg.displayed_items]
        self.assertIn("fireball", names_found)

        # 2. Ricerca bilingue su Oggetti Magici ('borsa conservante' -> 'Bag of Holding')
        dlg.search_var.set("")
        dlg.category_var.set("Oggetti Magici")
        dlg._on_category_changed()
        dlg.search_var.set("borsa conservante")
        item_names = [it.get("name", "").lower() for it in dlg.displayed_items]
        self.assertIn("bag of holding", item_names)

        # 3. Ordinamento per colonna Dettaglio (CR) su Mostri
        dlg.search_var.set("")
        dlg.category_var.set("Mostri")
        dlg._on_category_changed()
        self.assertGreater(len(dlg.displayed_items), 50)
        dlg._on_sort_column("detail")  # Crescente
        dlg._on_sort_column("detail")  # Decrescente (CR più alti in cima)
        first_cr = dlg.displayed_items[0].get("challenge_rating", dlg.displayed_items[0].get("cr", 0))
        self.assertGreaterEqual(float(str(first_cr).split("/")[0]), 20.0)

        # 4. Preferiti & Recenti
        sample_monster = dlg.displayed_items[0]
        now_fav = dlg._on_toggle_favorite(sample_monster, "Mostri")
        self.assertTrue(now_fav)
        self.assertTrue(dlg.compendium_manager.is_favorite(sample_monster))
        # Rimuoviamo il preferito di test per lasciare pulito il file
        dlg._on_toggle_favorite(sample_monster, "Mostri")
        self.assertFalse(dlg.compendium_manager.is_favorite(sample_monster))

        # 5. Lancio dadi interattivo nello Statblock & Selettore Quantità
        roll_res = dlg.statblock_view.roll_dice_formula("8d6+4", "Soffio di Fuoco")
        self.assertGreaterEqual(roll_res["total"], 12)
        self.assertLessEqual(roll_res["total"], 52)
        self.assertEqual(len(roll_res["rolls"]), 8)

        with patch("server.compendium_ui.messagebox.showinfo"):
            dlg.statblock_view.quantity_var.set(3)
            dlg.statblock_view._trigger_primary_action({"name": "Goblin Arciere", "hp": 7, "ac": 15}, "Mostri")
        self.assertEqual(len(imported_calls), 3)
        dlg.destroy()

    def test_compendium_expanded_classes_and_progression_1_to_20(self):
        """Verifica che tutte le 13 classi abbiano progressione 1-20, sottoclassi e slot incantesimi."""
        from common.srd_offline import (
            get_all_classes_offline,
            get_class_level_features_offline,
            get_all_traits_offline,
        )
        classes = get_all_classes_offline()
        self.assertEqual(len(classes), 13)
        class_names = [c["name"].lower() for c in classes]
        for expected in ["guerriero", "barbaro", "ladro", "mago", "chierico", "paladino", "bardo", "druido", "monaco", "ranger", "stregone", "warlock", "artefice"]:
            self.assertTrue(any(expected in cn for cn in class_names), f"Classe mancante: {expected}")

        # Verifica progressione 1-20 e sottoclassi
        warlock_feats = get_class_level_features_offline("warlock", 5)
        self.assertEqual(warlock_feats["level"], 5)
        self.assertIn("3", warlock_feats["spell_slots"])  # Slot di 3° livello su riposo breve
        self.assertGreater(len(warlock_feats["subclasses"]), 3)

        paladin_feats = get_class_level_features_offline("paladino", 5)
        self.assertEqual(paladin_feats["hit_die"], 10)
        self.assertIn("2", paladin_feats["spell_slots"])  # Half-caster slot 2° liv

        artificer_feats = get_class_level_features_offline("artefice", 3)
        self.assertEqual(artificer_feats["hit_die"], 8)
        self.assertGreater(len(artificer_feats["subclasses"]), 2)

        # Tratti di classe + raziali
        traits = get_all_traits_offline()
        self.assertGreater(len(traits), 150)

    def test_compendium_feats_and_backgrounds(self):
        """Verifica cataloghi di Talenti (Feats) e Backgrounds 5e."""
        from common.srd_offline import (
            get_all_feats_offline,
            get_all_backgrounds_offline,
        )
        feats = get_all_feats_offline()
        self.assertGreaterEqual(len(feats), 40)
        feat_names = [f["name"].lower() for f in feats]
        self.assertTrue(any("great weapon master" in fn or "armi possenti" in fn for fn in feat_names))
        self.assertTrue(any("sharpshooter" in fn or "tiratore scelto" in fn for fn in feat_names))
        self.assertTrue(any("sentinel" in fn or "sentinella" in fn for fn in feat_names))
        self.assertTrue(any("war caster" in fn or "incantatore da guerra" in fn for fn in feat_names))
        self.assertTrue(any("fey touched" in fn or "toccato dalle fate" in fn for fn in feat_names))

        backgrounds = get_all_backgrounds_offline()
        self.assertGreaterEqual(len(backgrounds), 18)
        bg_names = [b["name"].lower() for b in backgrounds]
        self.assertTrue(any("accolito" in bn or "acolyte" in bn for bn in bg_names))
        self.assertTrue(any("nobile" in bn or "noble" in bn for bn in bg_names))
        self.assertTrue(any("soldato" in bn or "soldier" in bn for bn in bg_names))
        self.assertTrue(any("pirata" in bn or "pirate" in bn for bn in bg_names))

        # CompendiumDialog categorie
        dlg = CompendiumDialog(self.root, is_dm=True, initial_category="Talenti")
        self.assertIn("Talenti", dlg.category_cb["values"])
        self.assertIn("Background", dlg.category_cb["values"])
        self.assertGreaterEqual(len(dlg.displayed_items), 40)
        dlg.category_var.set("Background")
        dlg._on_category_changed()
        self.assertGreaterEqual(len(dlg.displayed_items), 18)
        dlg.destroy()

    def test_compendium_iconic_non_srd_monsters_and_spells(self):
        """Verifica mostri iconici non-SRD (Beholder, Mind Flayer, etc.) e magie iconiche (Hex, Booming Blade, etc.)."""
        from common.srd_offline import (
            get_monster_offline,
            search_monsters_offline,
            search_spells_offline,
            get_all_monsters_offline,
            get_all_spells_offline,
        )
        # Mostri non-SRD
        beholder = get_monster_offline("beholder")
        self.assertIsNotNone(beholder)
        self.assertEqual(int(beholder.get("armor_class", 0)), 18)
        self.assertEqual(int(beholder.get("hit_points", 0)), 180)

        beholder_it = get_monster_offline("osservatore")
        self.assertIsNotNone(beholder_it)
        self.assertEqual(beholder_it.get("name"), "Beholder")

        mind_flayer = get_monster_offline("mind flayer")
        self.assertIsNotNone(mind_flayer)
        self.assertEqual(mind_flayer.get("challenge_rating"), "7")

        displacer = get_monster_offline("belva distorcente")
        self.assertIsNotNone(displacer)

        death_knight = get_monster_offline("cavaliere della morte")
        self.assertIsNotNone(death_knight)

        # Magie non-SRD
        hex_spells = search_spells_offline("hex")
        self.assertTrue(any(s["name"] == "Hex" for s in hex_spells))

        sortilegio_spells = search_spells_offline("sortilegio")
        self.assertTrue(any(s["name"] == "Hex" for s in sortilegio_spells))

        booming_blade = search_spells_offline("booming blade")
        self.assertTrue(any("booming blade" in s["name"].lower() for s in booming_blade))

        silvery_barbs = search_spells_offline("stoccata argentea")
        self.assertTrue(any("silvery barbs" in s["name"].lower() for s in silvery_barbs))

    def test_compendium_expanded_rules_and_dm_tables(self):
        """Verifica le tabelle e regole avanzate del DM (veleni, trappole, alloggi, follia, CR/XP)."""
        from common.srd_offline import get_all_rules_offline
        rules = get_all_rules_offline()
        self.assertGreaterEqual(len(rules), 14)
        rule_names = [r["name"].lower() for r in rules]
        self.assertTrue(any("veleni" in rn for rn in rule_names))
        self.assertTrue(any("trappole" in rn for rn in rule_names))
        self.assertTrue(any("alloggio" in rn or "vitto" in rn for rn in rule_names))
        self.assertTrue(any("grado di sfida" in rn or "xp" in rn for rn in rule_names))
        self.assertTrue(any("follia" in rn for rn in rule_names))
        self.assertTrue(any("oggetti" in rn and "ca" in rn for rn in rule_names))
        self.assertTrue(any("indebolimento" in rn or "exhaustion" in rn for rn in rule_names))

    def test_compendium_100_percent_official_coverage(self):
        """Verifica la copertura al 100% di tutti i manuali ufficiali D&D 5e: 500+ incantesimi, 1120+ mostri, 117 sottoclassi, 37 razze, 800+ tratti."""
        from common.srd_offline import (
            get_all_spells_offline,
            get_all_monsters_offline,
            get_all_magic_items_offline,
            get_all_subclasses_offline,
            get_all_races_offline,
            get_all_traits_offline,
            get_all_rules_offline,
            get_magic_item_offline,
            get_monster_offline,
        )
        # 1. 500+ Incantesimi
        spells = get_all_spells_offline()
        self.assertGreaterEqual(len(spells), 500)

        # 2. 1,120+ Mostri (inclusi WotC copyright monsters)
        monsters = get_all_monsters_offline()
        self.assertGreaterEqual(len(monsters), 1120)
        spectator = get_monster_offline("spectator")
        self.assertIsNotNone(spectator)
        elder_brain = get_monster_offline("elder brain")
        self.assertIsNotNone(elder_brain)

        # 3. 250+ Oggetti Magici & Artefatti DMG
        items = get_all_magic_items_offline()
        self.assertGreaterEqual(len(items), 250)
        vecna_eye = get_magic_item_offline("eye of vecna")
        self.assertIsNotNone(vecna_eye)
        bandore = get_magic_item_offline("fochlucan bandore")
        self.assertIsNotNone(bandore)

        # 4. Tutte le 117 Sottoclassi ufficiali per tutte le 13 classi
        subclasses = get_all_subclasses_offline()
        self.assertEqual(len(subclasses), 117)
        classes_represented = {s.get("class_name") for s in subclasses}
        self.assertEqual(len(classes_represented), 13)

        # 5. Tutte le 37+ Razze giocabili (9 PHB + 28+ Esotiche)
        races = get_all_races_offline()
        self.assertGreaterEqual(len(races), 37)
        race_names = [r["name"].lower() for r in races]
        self.assertIn("aasimar", race_names)
        self.assertIn("goliath", race_names)
        self.assertIn("tabaxi", race_names)
        self.assertIn("forgiato", race_names)

        # 6. 800+ Tratti con descrizioni complete
        traits = get_all_traits_offline()
        self.assertGreaterEqual(len(traits), 800)

        # 7. Tabelle di Bottino DMG A-I nelle regole
        rules = get_all_rules_offline()
        rule_names = [r["name"].lower() for r in rules]
        self.assertTrue(any("tabella bottino dmg: table a" in rn for rn in rule_names))
        self.assertTrue(any("tabella bottino dmg: table i" in rn for rn in rule_names))

if __name__ == '__main__':
    unittest.main()
