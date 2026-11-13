# tests/test_campaign_hierarchy.py
import os
import tempfile
import unittest
import tkinter as tk
from unittest.mock import MagicMock, patch

from common.campaign import Campaign, create_sample_starter_campaign
from common.campaign_script import (
    FlowGraph,
    FlowNode,
    ensure_hierarchical_campaign_flows,
    get_scene_subflow_graph,
    summarize_subflow,
)


class TestCampaignHierarchyData(unittest.TestCase):
    def test_factions_and_subflow_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            camp = Campaign(name="Fazioni & Gerarchia", folder_path=tmpdir)
            camp.add_scene("Piazza Centrale", "maps/faerun.json", "Cuore del borgo")
            camp.add_faction(
                name="Gilda delle Ombre",
                alignment="Neutrale Malvagio",
                description="Spie e contrabbandieri.",
                headquarters="Piazza Centrale",
                reputation=-1,
            )
            ensure_hierarchical_campaign_flows(camp)
            camp.save(tmpdir)

            loaded = Campaign.load(tmpdir)
            self.assertEqual(len(loaded.factions), 1)
            self.assertEqual(loaded.factions[0]["name"], "Gilda delle Ombre")
            self.assertEqual(loaded.factions[0]["reputation"], -1)
            self.assertEqual(len(loaded.scenes), 1)
            self.assertTrue(loaded.flow_graph.get("nodes"))

    def test_legacy_flat_flow_graph_auto_migrates_cleanly_and_idempotently(self):
        flat = FlowGraph()
        flat.nodes["s1"] = FlowNode(id="s1", node_type="scene", title="Villaggio di Rovescuro", data={"map_file": "maps/faerun.json"})
        flat.nodes["e1"] = FlowNode(id="e1", node_type="encounter", title="Imboscata Goblin", data={"monsters": [{"name": "Goblin", "quantity": 2}]})
        flat.nodes["n1"] = FlowNode(id="n1", node_type="npc", title="Sindaco Brent", data={"role": "Sindaco", "faction": "Ordine Civico"})
        flat.nodes["s2"] = FlowNode(id="s2", node_type="scene", title="Caverne Oscure", data={"map_file": "maps/cripta.json"})
        flat.add_edge("s1", "e1", label="Al limitare")
        flat.add_edge("s1", "n1", label="Parlando col sindaco")
        flat.add_edge("e1", "s2", label="Seguendo le tracce")

        camp = Campaign(name="Legacy Flat")
        camp.flow_graph = flat.to_dict()

        macro = ensure_hierarchical_campaign_flows(camp)

        # Livello 1 deve contenere solo le 2 Scene + collegamento tra Villaggio e Caverne
        macro_types = {n.node_type for n in macro.nodes.values()}
        self.assertEqual(macro_types, {"scene"})
        self.assertEqual(len(macro.nodes), 2)

        v_node = macro.get_node_by_title("Villaggio di Rovescuro")
        c_node = macro.get_node_by_title("Caverne Oscure")
        self.assertIsNotNone(v_node)
        self.assertIsNotNone(c_node)
        self.assertTrue(any(e.from_id == v_node.id and e.to_id == c_node.id for e in macro.edges))

        # Entita' interne migrate nel sotto-flusso di Villaggio di Rovescuro
        v_scene = camp.get_scene_by_name("Villaggio di Rovescuro")
        self.assertIsNotNone(v_scene)
        v_sub = get_scene_subflow_graph(v_scene)
        self.assertIsNotNone(v_sub.get_node_by_title("Imboscata Goblin"))
        self.assertIsNotNone(v_sub.get_node_by_title("Sindaco Brent"))
        self.assertIsNotNone(v_sub.get_node_by_title("Caverne Oscure"))  # nodo uscita

        # Entita' globali sincronizzate con riferimento alla scena + auto-registrazione fazione
        self.assertEqual(len(camp.encounters), 1)
        self.assertEqual(camp.encounters[0].get("scene"), "Villaggio di Rovescuro")
        self.assertEqual(len(camp.npcs), 1)
        self.assertEqual(camp.npcs[0].get("faction"), "Ordine Civico")
        self.assertTrue(any(f["name"] == "Ordine Civico" for f in camp.factions))

        # Seconda esecuzione strettamente idempotente
        macro_again = ensure_hierarchical_campaign_flows(camp)
        self.assertEqual(len(macro_again.nodes), len(macro.nodes))
        self.assertEqual(len(camp.encounters), 1)
        self.assertEqual(len(camp.npcs), 1)

    def test_sample_starter_campaign_has_hierarchical_flows_and_factions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            camp = create_sample_starter_campaign(target_dir=tmpdir)
            self.assertGreaterEqual(len(camp.scenes), 2)
            self.assertGreaterEqual(len(camp.factions), 2)
            self.assertTrue(camp.flow_graph.get("nodes"))
            catacombe = camp.get_scene_by_name("Ingresso Catacombe")
            self.assertIsNotNone(catacombe)
            summary = summarize_subflow(get_scene_subflow_graph(catacombe))
            self.assertGreater(summary["total"], 0)


class TestCampaignHierarchyUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except tk.TclError:
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
            self.skipTest("Tkinter GUI not available in headless environment")

    def test_studio_drilldown_scoped_flows_and_macro_drag_stability(self):
        from server.campaign_studio_ui import CampaignStudioFrame

        camp = Campaign(name="Gerarchia Studio UI")
        studio = CampaignStudioFrame(self.root, camp)

        # Livello 1: Macro Scene (pure FlowGraph senza editor testuale)
        self.assertIsNone(studio.active_scene_name)
        self.assertFalse(hasattr(studio, "txt_script"))
        self.assertTrue(all(n.node_type == "scene" for n in studio.graph.nodes.values()))
        macro_count_before = len(studio.graph.nodes)

        # Drill-down nella prima Scena
        locanda_node = studio.graph.get_node_by_title("Locanda del Cinghiale")
        self.assertIsNotNone(locanda_node)
        studio._on_node_drilldown(locanda_node)

        self.assertEqual(studio.active_scene_name, "Locanda del Cinghiale")
        self.assertIsNone(studio.graph.get_node_by_title("Locanda del Cinghiale"))
        self.assertIsNotNone(studio.graph.get_node_by_title("Sindaco Roland"))

        # Aggiungi una Prova interna alla Scena tramite tavolozza visuale
        roland = studio.graph.get_node_by_title("Sindaco Roland")
        studio.flow_canvas.select_node(roland.id, notify=True)
        studio.add_block("check")
        self.assertGreaterEqual(len([n for n in studio.graph.nodes.values() if n.node_type == "check"]), 1)

        # Torna al Livello 1 (Macro Scene)
        studio.exit_to_campaign()
        self.assertIsNone(studio.active_scene_name)
        locanda_macro = studio.graph.get_node_by_title("Locanda del Cinghiale")
        self.assertIsNotNone(locanda_macro)
        self.assertIn("🎲1", locanda_macro.data.get("subflow_summary_text", ""))

        # Drag del nodo macro non deve moltiplicare nodi o archi
        locanda_macro.x += 40.0
        studio._on_canvas_modified()
        self.assertEqual(len(studio.graph.nodes), macro_count_before)
        self.assertNotIn("flow_script", camp.to_dict())
        studio.destroy()

    def test_campaign_editor_collapsed_two_tabs_factions_and_inject(self):
        from server.campaign_editor_ui import CampaignEditorFrame

        camp = Campaign(name="Editor Collassato")
        camp.add_scene("Porto Ventoso", "maps/faerun.json", "Molo principale")
        camp.add_encounter("Rissa al Molo", [{"name": "Bandito", "count": 3, "hp": 11}], act="Atto 1")
        camp.add_faction("Guardia Costiera", alignment="Legale Buono", headquarters="Porto Ventoso", reputation=2)

        editor = CampaignEditorFrame(self.root, campaign=camp)
        # Solo 2 tab principali: Studio + Generale
        self.assertEqual(editor.notebook.index("end"), 2)
        self.assertTrue(hasattr(editor, "tree_scenes"))
        self.assertTrue(hasattr(editor, "tree_enc"))
        self.assertTrue(hasattr(editor, "tree_quests"))
        self.assertTrue(hasattr(editor, "tree_npcs"))
        self.assertTrue(hasattr(editor, "tree_factions"))
        self.assertTrue(hasattr(editor, "tree_handouts"))

        self.assertEqual(len(editor.tree_factions.get_children()), 1)

        # Inietta incontro selezionato direttamente nella Scena nello Studio
        editor.tree_enc.selection_set("0")
        editor.inject_selected_encounter_to_flow()
        self.assertEqual(editor.studio_frame.active_scene_name, "Porto Ventoso")
        self.assertIsNotNone(editor.studio_frame.graph.get_node_by_title("Rissa al Molo"))

        editor.sync_campaign_data()
        porto = camp.get_scene_by_name("Porto Ventoso")
        self.assertIsNotNone(get_scene_subflow_graph(porto).get_node_by_title("Rissa al Molo"))
        editor.destroy()

    @patch("server.dm_live_flow.messagebox")
    def test_live_flow_two_level_drilldown_and_encounter_spawn(self, mock_mb):
        import queue
        from common.game_state import GameState
        from common.session_chronicle import SessionLedger
        from server.dm_live_flow import DMLiveFlowDialog

        camp = Campaign(name="Live Flow 2-Livelli")
        camp.add_scene("Piazza", "maps/faerun.json", "Centro cittadino")
        camp.add_scene("Torre", "maps/faerun.json", "Torre abbandonata")
        camp.add_encounter("Guardie Corrotte", [{"name": "Goblin", "count": 2, "hp": 7}], scene="Torre")
        ensure_hierarchical_campaign_flows(camp)

        gs = GameState(gui_queue=queue.Queue())
        camp.apply_to_game_state(gs)
        ledger = SessionLedger(campaign_name=camp.name, start_game_date=camp.start_date)

        mock_gui = MagicMock()
        mock_gui.master = self.root
        mock_gui.server = MagicMock(game_state=gs)

        dlg = DMLiveFlowDialog(mock_gui, gs, ledger)
        try:
            self.assertIsNone(dlg._current_scene_name)
            self.assertTrue(all(n.node_type == "scene" for n in dlg.graph.nodes.values()))

            # Entra nella Scena Torre
            dlg.enter_scene_subflow("Torre")
            self.assertEqual(dlg._current_scene_name, "Torre")
            enc_node = dlg.graph.get_node_by_title("Guardie Corrotte")
            self.assertIsNotNone(enc_node)

            # Lancia incontro sul VTT (verifica fix precedente NameError su `cr`)
            dlg.activate_encounter_on_vtt(enc_node)
            mock_mb.showerror.assert_not_called()
            self.assertTrue(any("Goblin" in p.name for p in gs.players))

            # Torna al macro-flusso Scene
            dlg.exit_to_macro_flow()
            self.assertIsNone(dlg._current_scene_name)
            self.assertIsNotNone(dlg.graph.get_node_by_title("Torre"))
        finally:
            dlg.destroy()


if __name__ == "__main__":
    unittest.main()
