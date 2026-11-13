# test_campaign_script.py
import tkinter as tk
import unittest

from common.campaign import Campaign
from common.campaign_script import (
    FlowGraph, FlowNode,
    sync_flow_graph_to_campaign, generate_flow_from_campaign,
)


class TestCampaignFlowGraph(unittest.TestCase):
    def _build_sample_graph(self) -> FlowGraph:
        g = FlowGraph()
        g.nodes["n1"] = FlowNode(
            id="n1",
            node_type="scene",
            title="Locanda del Cinghiale",
            x=100,
            y=100,
            data={
                "map_file": "maps/faerun.json",
                "weather": "Nebbia",
                "light": "Notte",
                "music": "Taverna",
                "read_aloud": "Una locanda calda e fumosa nel villaggio di Rovescuro.",
                "secrets": [{"check": "Intuizione CD 12", "text": "Il locandiere e ricattato dal culto."}],
                "rumors": [{"title": "Voce", "text": "La vecchia cripta a nord e profanata."}],
                "handouts": [{"title": "Mappa Cifrata", "file": "mappa_segreta.png"}],
            },
        )
        g.nodes["n2"] = FlowNode(
            id="n2",
            node_type="encounter",
            title="Imboscata Lupi",
            x=380,
            y=180,
            data={
                "monsters": [{"name": "Lupo", "quantity": 3}, {"name": "Lupo Feroce", "quantity": 1}],
                "cr": "2",
                "music": "Combattimento",
                "loot": "Pelli di lupo, 15 mo",
            },
        )
        g.nodes["n3"] = FlowNode(
            id="n3",
            node_type="scene",
            title="Ingresso Cripta",
            x=650,
            y=100,
            data={
                "map_file": "maps/cripta.json",
                "read_aloud": "Due pesanti battenti di pietra consumati dal tempo.",
                "secrets": [{"check": "Arcano CD 14", "text": "Sigillo necromantico inciso sulla pietra."}],
                "traps": [{"check": "Percezione CD 13", "text": "Lastra a pressione."}],
            },
        )
        g.nodes["n4"] = FlowNode(
            id="n4",
            node_type="npc",
            title="Sindaco Roland",
            x=380,
            y=300,
            data={"role": "Sindaco del borgo", "alignment": "Legale Buono", "faction": "Ordine Civico"},
        )
        g.nodes["n5"] = FlowNode(
            id="n5",
            node_type="quest",
            title="Sussurri nella Cripta",
            x=650,
            y=300,
            data={
                "objectives": ["Raggiungi la cripta", "Purifica il santuario"],
                "loot": "100 mo, Pozione di Cura",
                "xp": 300,
            },
        )
        g.add_edge("n1", "n3", label="Se interrogano il locandiere", condition_type="custom")
        g.add_edge("n1", "n2", label="Se escono di notte per investigare", condition_type="custom")
        g.add_edge("n1", "n4", label="Se cercano il sindaco", condition_type="custom")
        g.add_edge("n2", "n3", label="Seguendo le tracce")
        g.add_edge("n4", "n5", label="Accettata la missione")
        g.add_edge("n5", "n3")
        return g

    def test_graph_helpers_and_json_roundtrip(self):
        graph = self._build_sample_graph()
        self.assertEqual(len(graph.nodes), 5)
        self.assertEqual(len(graph.edges), 6)

        # add_edge evita duplicati se allow_duplicate=False
        dup = graph.add_edge("n1", "n3", label="Duplicato")
        self.assertEqual(len(graph.edges), 6)
        self.assertEqual(dup.from_id, "n1")

        # next_node_id genera ID non esistenti
        nid = graph.next_node_id("n")
        self.assertNotIn(nid, graph.nodes)

        # Roundtrip JSON completo
        reloaded = FlowGraph.from_dict(graph.to_dict())
        self.assertEqual(len(reloaded.nodes), len(graph.nodes))
        self.assertEqual(len(reloaded.edges), len(graph.edges))

        re_locanda = reloaded.get_node_by_title("Locanda del Cinghiale")
        self.assertIsNotNone(re_locanda)
        self.assertEqual(re_locanda.data.get("map_file"), "maps/faerun.json")
        self.assertEqual(re_locanda.data.get("secrets")[0]["check"], "Intuizione CD 12")
        self.assertEqual(re_locanda.data.get("handouts")[0]["title"], "Mappa Cifrata")

        # Rimozione edge per indice
        removed = reloaded.remove_edge_at(0)
        self.assertIsNotNone(removed)
        self.assertEqual(len(reloaded.edges), 5)
        self.assertIsNone(reloaded.remove_edge_at(99))

    def test_sync_to_campaign(self):
        graph = self._build_sample_graph()
        camp = Campaign(name="Test Campaign")
        sync_flow_graph_to_campaign(graph, camp)

        scene_names = [s["name"] for s in camp.scenes]
        self.assertIn("Locanda del Cinghiale", scene_names)
        self.assertIn("Ingresso Cripta", scene_names)

        enc_names = [e["name"] for e in camp.encounters]
        self.assertIn("Imboscata Lupi", enc_names)
        self.assertEqual(camp.encounters[0]["loot_currency"]["MO"], 15)

        quest_titles = [q["title"] for q in camp.quests]
        self.assertIn("Sussurri nella Cripta", quest_titles)

        npc_names = [n["name"] for n in camp.npcs]
        self.assertIn("Sindaco Roland", npc_names)
        self.assertTrue(any(f["name"] == "Ordine Civico" for f in camp.factions))
        self.assertTrue(any(h["title"] == "Mappa Cifrata" for h in camp.handouts))

    def test_generate_flow_from_campaign(self):
        camp = Campaign(name="Vecchia Campagna")
        camp.scenes = [{"name": "Piazza", "map_file": "maps/faerun.json", "description": "Una piazza antica."}]
        camp.encounters = [{"name": "Briganti", "description": "3 banditi armati.", "monsters": [{"name": "Bandit", "quantity": 3}]}]
        camp.quests = [{"title": "Salva il borgo", "description": "Sconfiggi i briganti.", "objectives": ["Elimina i capi"]}]

        graph = generate_flow_from_campaign(camp)
        self.assertGreaterEqual(len(graph.nodes), 4)  # Hub + 1 scena + 1 incontro + 1 quest
        self.assertIsNotNone(graph.get_node_by_title("Piazza"))
        self.assertIsNotNone(graph.get_node_by_title("Briganti"))
        self.assertIsNotNone(graph.get_node_by_title("Salva il borgo"))

    def test_conditional_edges_and_expanded_blocks_sync(self):
        graph = FlowGraph()
        graph.nodes["chk"] = FlowNode(
            id="chk",
            node_type="check",
            title="Scassinare Portone",
            data={"ability": "Rapidità di Mano", "cd": 15},
        )
        graph.nodes["sala"] = FlowNode(id="sala", node_type="scene", title="Sala del Tesoro")
        graph.nodes["trp"] = FlowNode(
            id="trp",
            node_type="trap",
            title="Dardi Avvelenati",
            data={"cd": 13, "damage": "2d6 Veleno", "save": "Destrezza"},
        )
        graph.nodes["loot"] = FlowNode(
            id="loot",
            node_type="loot",
            title="Scrigno Segreto",
            data={"gold": "200 mo", "items": ["Anello di Protezione", "Pozione di Volo"]},
        )
        graph.nodes["shop"] = FlowNode(
            id="shop",
            node_type="shop",
            title="La Fucina d'Acciaio",
            data={"merchant": "Gunnar il Fabbro", "shop_type": "Armi e Armature", "items": ["Spada Lunga +1", "Corazza a Strisce"]},
        )
        graph.nodes["puz"] = FlowNode(
            id="puz",
            node_type="puzzle",
            title="Portale delle Rune",
            data={"difficulty": "Difficile", "clue": "Tre fuochi accendono l'aurora", "solution": "Runa del Fuoco in alto"},
        )
        graph.nodes["lore"] = FlowNode(
            id="lore",
            node_type="lore",
            title="Tomo Proibito",
            data={"author": "Arcimago Valthor", "language": "Draconico", "read_aloud": "I segreti per infrangere il sigillo del titano."},
        )
        graph.nodes["ev"] = FlowNode(
            id="ev",
            node_type="event",
            title="Eclissi di Sangue",
            data={"trigger": "Allo scoccare della mezzanotte", "read_aloud": "Il cielo si tinge di rosso scuro."},
        )

        graph.add_edge("chk", "sala", condition_type="success", label="Successo")
        graph.add_edge("chk", "trp", condition_type="failure", label="Fallimento")
        graph.add_edge("sala", "loot", condition_type="check", condition_value="Percezione CD 14")
        graph.add_edge("sala", "shop", condition_type="item", condition_value="Chiave Dorata")
        graph.add_edge("sala", "lore", condition_type="else")

        reloaded = FlowGraph.from_dict(graph.to_dict())
        self.assertEqual(len(reloaded.nodes), 8)
        self.assertEqual(len(reloaded.edges), 5)

        camp = Campaign(name="Test Espansione")
        sync_flow_graph_to_campaign(reloaded, camp)

        shops = getattr(camp, "shops", {})
        self.assertEqual(len(shops), 1)
        gunnar_shop = shops.get("La Fucina d'Acciaio") or list(shops.values())[0]
        self.assertEqual(gunnar_shop["merchant"], "Gunnar il Fabbro")
        self.assertIn("Spada Lunga +1", gunnar_shop["inventory"])

        handouts = getattr(camp, "handouts", [])
        self.assertEqual(len(handouts), 1)
        self.assertEqual(handouts[0]["title"], "Tomo Proibito")
        self.assertIn("sigillo", handouts[0]["description"])

        self.assertIn("ENIGMI & PROVE", camp.dm_notes)
        self.assertIn("Tre fuochi accendono l'aurora", camp.dm_notes)


class TestCampaignStudioRegression(unittest.TestCase):
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

    def test_rearrange_and_move_does_not_multiply_nodes(self):
        from server.campaign_studio_ui import CampaignStudioFrame

        camp = Campaign(name="Campagna Studio Test")
        studio = CampaignStudioFrame(self.root, camp)
        self.assertFalse(hasattr(studio, "txt_script"))

        initial_nodes = len(studio.graph.nodes)
        initial_edges = len(studio.graph.edges)

        for _ in range(4):
            studio.rearrange_flow_layout()
            node = next(iter(studio.graph.nodes.values()))
            node.x += 25.0
            node.y += 15.0
            studio._on_canvas_modified()
            self.assertEqual(len(studio.graph.nodes), initial_nodes)
            self.assertEqual(len(studio.graph.edges), initial_edges)

        moved = next(iter(studio.graph.nodes.values()))
        self.assertAlmostEqual(moved.x, 125.0)
        self.assertAlmostEqual(moved.y, 95.0)
        studio.destroy()

    def test_double_check_creates_distinct_outcomes_and_links_selected_node(self):
        from server.campaign_studio_ui import CampaignStudioFrame

        camp = Campaign(name="Campagna Check Test")
        studio = CampaignStudioFrame(self.root, camp)

        ingresso = studio.graph.get_node_by_title("Ingresso Cripta")
        self.assertIsNotNone(ingresso)
        studio.flow_canvas.select_node(ingresso.id, notify=True)

        studio.add_block("check")
        studio.add_block("check")

        # La selezione rimane sul nodo di partenza scelto dal DM
        self.assertEqual(studio.flow_canvas.selected_node_id, ingresso.id)

        checks = [n for n in studio.graph.nodes.values() if n.node_type == "check"]
        self.assertEqual(len(checks), 2)
        self.assertEqual([c.title for c in checks], ["Scassinare il Portone", "Scassinare il Portone 2"])

        success_ids = set()
        failure_ids = set()
        for chk in checks:
            self.assertTrue(
                any(e.from_id == ingresso.id and e.to_id == chk.id for e in studio.graph.edges),
                f"Manca collegamento dal nodo selezionato verso {chk.title}"
            )
            succ = [e.to_id for e in studio.graph.edges if e.from_id == chk.id and e.condition_type == "success"]
            fail = [e.to_id for e in studio.graph.edges if e.from_id == chk.id and e.condition_type == "failure"]
            self.assertEqual(len(succ), 1)
            self.assertEqual(len(fail), 1)
            success_ids.add(succ[0])
            failure_ids.add(fail[0])
        self.assertEqual(len(success_ids), 2)
        self.assertEqual(len(failure_ids), 2)

        # Senza nodo selezionato, due clic su Prova creano comunque blocchi ed esiti indipendenti
        studio2 = CampaignStudioFrame(self.root, Campaign(name="Campagna Unselected"))
        studio2.flow_canvas.selected_node_id = None
        studio2.add_block("check")
        studio2.add_block("check")
        checks2 = [n for n in studio2.graph.nodes.values() if n.node_type == "check"]
        self.assertEqual(len(checks2), 2)
        outs2 = {e.to_id for c in checks2 for e in studio2.graph.edges if e.from_id == c.id}
        self.assertEqual(len(outs2), 4)
        studio.destroy()
        studio2.destroy()

    def test_visual_inspector_edits_nodes_and_edges(self):
        from server.campaign_studio_ui import CampaignStudioFrame

        camp = Campaign(name="Ispettore Visuale Test")
        studio = CampaignStudioFrame(self.root, camp)

        # Entra nella prima scena ed edita un nodo via Ispettore sinistro
        studio.enter_scene("Locanda del Cinghiale")
        roland = studio.graph.get_node_by_title("Sindaco Roland")
        self.assertIsNotNone(roland)
        studio.flow_canvas.select_node(roland.id, notify=True)

        w_title = studio._inspector_widgets["_title"]
        w_title.delete(0, tk.END)
        w_title.insert(0, "Borgomastro Roland")
        w_ra = studio._inspector_widgets["_read_aloud"]
        w_ra.delete("1.0", tk.END)
        w_ra.insert("1.0", "Un anziano nobile preoccupato per le sorti del villaggio.")
        _, w_faction = studio._inspector_widgets["_fields"]["faction"]
        w_faction.set("Consiglio di Waterdeep")
        studio._commit_inspector_edits()

        self.assertEqual(roland.title, "Borgomastro Roland")
        self.assertEqual(roland.data.get("faction"), "Consiglio di Waterdeep")
        self.assertIn("Consiglio di Waterdeep", [f["name"] for f in camp.factions])

        # Seleziona e modifica visivamente un arco / condizione
        self.assertGreater(len(studio.graph.edges), 0)
        studio.flow_canvas.select_edge(0, notify=True)
        w_cond = studio._inspector_widgets["_edge_cond"]
        w_val = studio._inspector_widgets["_edge_val"]
        w_lbl = studio._inspector_widgets["_edge_lbl"]
        w_cond.set("check")
        w_val.delete(0, tk.END)
        w_val.insert(0, "Persuasione CD 14")
        w_lbl.delete(0, tk.END)
        w_lbl.insert(0, "Se convincono l'oste")
        studio._commit_inspector_edits()

        self.assertEqual(studio.graph.edges[0].condition_type, "check")
        self.assertEqual(studio.graph.edges[0].condition_value, "Persuasione CD 14")
        self.assertEqual(studio.graph.edges[0].label, "Se convincono l'oste")

        edges_before = len(studio.graph.edges)
        studio._delete_edge_from_inspector(0)
        self.assertEqual(len(studio.graph.edges), edges_before - 1)
        studio.destroy()

    def test_inspector_weather_dropdown_and_secrets_crud(self):
        from tkinter import ttk
        from server.campaign_studio_ui import CampaignStudioFrame
        from server.campaign_editor_ui import CampaignEditorFrame

        camp = Campaign(name="Meteo e Segreti Test")
        camp.add_scene("Piazza del Mercato", "maps/piazza.json", description="Cuore della cittadina.")
        camp.add_encounter("Ombre sul Sagrato", [{"name": "Ombra", "count": 2}], act="Atto 1", scene="Piazza del Mercato")

        studio = CampaignStudioFrame(self.root, camp)

        # 1. Il campo Meteo sul nodo scena è una Combobox readonly con valori canonici
        scene_node = next(n for n in studio.graph.nodes.values() if n.node_type == "scene")
        studio.flow_canvas.select_node(scene_node.id, notify=True)

        ftype, w_weather = studio._inspector_widgets["_fields"]["weather"]
        self.assertEqual(ftype, "readonly_combo")
        self.assertIsInstance(w_weather, ttk.Combobox)
        self.assertEqual(str(w_weather.cget("state")), "readonly")
        self.assertEqual(
            list(w_weather.cget("values")),
            ["", "Sereno", "Pioggia", "Tempesta", "Neve", "Nebbia", "Oscurità"],
        )

        # Imposta meteo e verifica propagazione alla scena
        w_weather.set("Tempesta")
        studio._commit_inspector_edits()
        self.assertEqual(scene_node.data.get("weather"), "Tempesta")
        scene_entry = next(s for s in camp.scenes if s.get("name") == scene_node.title)
        self.assertEqual(scene_entry.get("weather"), "Tempesta")

        # Svuota meteo e verifica rimozione dalla scena
        w_weather.set("")
        studio._commit_inspector_edits()
        self.assertFalse(scene_node.data.get("weather"))
        scene_entry_after = next(s for s in camp.scenes if s.get("name") == scene_node.title)
        self.assertNotIn("weather", scene_entry_after)

        # 2. Segreti & Indizi DM guidati: selezione non sporca il nodo, controlli guidati + flush e rimozione pulita
        from server.campaign_studio_ui import _parse_secret_check, _format_secret_check
        self.assertEqual(_parse_secret_check("Arcano CD 14"), ("Arcano", "14"))
        self.assertEqual(_parse_secret_check(""), ("Nessuna (Automatico)", ""))
        self.assertEqual(_format_secret_check("Percezione", "13"), "Percezione CD 13")
        self.assertEqual(_format_secret_check("Nessuna (Automatico)", "13"), "")

        studio.enter_scene(scene_node.title)
        target_node = next(iter(studio.graph.nodes.values()))
        had_secrets_key = "secrets" in target_node.data
        studio.flow_canvas.select_node(target_node.id, notify=True)
        if not had_secrets_key:
            self.assertNotIn("secrets", target_node.data)

        p_form = studio._inspector_widgets["_pending_secret_form"]
        self.assertIsInstance(p_form["type_combo"], ttk.Combobox)
        self.assertEqual(str(p_form["type_combo"].cget("state")), "readonly")
        self.assertEqual(list(p_form["type_combo"].cget("values")), ["SEGRETO", "INDIZIO", "TRAPPOLA", "PASSAGGIO"])
        self.assertIsInstance(p_form["check_combo"], ttk.Combobox)
        self.assertEqual(str(p_form["check_combo"].cget("state")), "readonly")
        self.assertEqual(p_form["check_combo"].get(), "Nessuna (Automatico)")
        self.assertEqual(str(p_form["cd_spin"].cget("state")), "disabled")

        # Aggiunta guidata con Tipo + Prova + CD
        p_form["type_combo"].set("INDIZIO")
        p_form["check_combo"].set("Indagare")
        p_form["check_combo"].event_generate("<<ComboboxSelected>>")
        self.assertEqual(str(p_form["cd_spin"].cget("state")), "normal")
        p_form["cd_spin"].set("15")
        p_form["txt_entry"].insert(0, "La fontana cela una botola.")
        studio._commit_inspector_edits()

        self.assertEqual(
            target_node.data.get("secrets"),
            [{"type": "INDIZIO", "check": "Indagare CD 15", "text": "La fontana cela una botola."}],
        )
        self.assertEqual(p_form["txt_entry"].get(), "")
        self.assertEqual(p_form["type_combo"].get(), "SEGRETO")
        self.assertEqual(p_form["check_combo"].get(), "Nessuna (Automatico)")
        self.assertEqual(str(p_form["cd_spin"].cget("state")), "disabled")
        self.assertIn("=== ENIGMI & PROVE DELLA CAMPAGNA ===", camp.dm_notes)
        self.assertIn("INDIZIO [Indagare CD 15]: La fontana cela una botola.", camp.dm_notes)

        # Aggiunta guidata automatica (Nessuna prova)
        p_form["type_combo"].set("PASSAGGIO")
        p_form["txt_entry"].insert(0, "Porta segreta dietro l'arazzo.")
        studio._commit_inspector_edits()
        self.assertEqual(
            target_node.data.get("secrets")[-1],
            {"type": "PASSAGGIO", "check": "", "text": "Porta segreta dietro l'arazzo."},
        )

        # Modifica inline guidata via pulsante '✏️' -> '✓'
        def _walk_widgets(root):
            out = []
            for ch in root.winfo_children():
                out.append(ch)
                out.extend(_walk_widgets(ch))
            return out

        edit_btns = [w for w in _walk_widgets(studio.inspector_panel) if isinstance(w, ttk.Button) and w.cget("text") == "✏️"]
        self.assertEqual(len(edit_btns), 2)
        edit_btns[0].invoke()

        # L'editing del primo segreto mostra Combobox + Spinbox popolati con i valori correnti
        save_btns = [w for w in _walk_widgets(studio.inspector_panel) if isinstance(w, ttk.Button) and w.cget("text") == "✓"]
        self.assertEqual(len(save_btns), 1)
        edit_box = save_btns[0].master.master
        ed_combos = [w for w in _walk_widgets(edit_box) if isinstance(w, ttk.Combobox)]
        ed_spins = [w for w in _walk_widgets(edit_box) if isinstance(w, ttk.Spinbox)]
        self.assertEqual(ed_combos[0].get(), "INDIZIO")
        self.assertEqual(ed_combos[1].get(), "Indagare")
        self.assertEqual(ed_spins[0].get(), "15")
        ed_combos[0].set("TRAPPOLA")
        ed_combos[1].set("Percezione")
        ed_combos[1].event_generate("<<ComboboxSelected>>")
        ed_spins[0].set("14")
        save_btns[0].invoke()
        self.assertEqual(
            target_node.data.get("secrets")[0],
            {"type": "TRAPPOLA", "check": "Percezione CD 14", "text": "La fontana cela una botola."},
        )

        # Rimuovendo tutti i segreti sparisce la sezione generata da dm_notes
        studio._remove_node_secret(target_node, 1)
        studio._remove_node_secret(target_node, 0)
        self.assertNotIn("secrets", target_node.data)
        self.assertNotIn("=== ENIGMI & PROVE DELLA CAMPAGNA ===", camp.dm_notes)
        studio.destroy()

        # 3. CampaignEditorFrame.sync_campaign_data preserva note manuali + segreti dello Studio
        camp2 = Campaign(name="Editor DM Notes Sync")
        camp2.add_scene("Cripta", "maps/cripta.json", description="Antica cripta.")
        camp2.add_encounter("Guardiano", [{"name": "Scheletro", "count": 2}], act="Atto 1", scene="Cripta")
        editor = CampaignEditorFrame(self.root, campaign=camp2)

        editor.txt_dm_notes.delete("1.0", tk.END)
        editor.txt_dm_notes.insert("1.0", "Appunto manuale del Master.")

        ed_scene = next(n for n in editor.studio_frame.graph.nodes.values() if n.node_type == "scene")
        editor.studio_frame.enter_scene(ed_scene.title)
        ed_node = next(iter(editor.studio_frame.graph.nodes.values()))
        editor.studio_frame.flow_canvas.select_node(ed_node.id, notify=True)
        ed_form = editor.studio_frame._inspector_widgets["_pending_secret_form"]
        ed_form["type_combo"].set("SEGRETO")
        ed_form["check_combo"].set("Percezione")
        ed_form["check_combo"].event_generate("<<ComboboxSelected>>")
        ed_form["cd_spin"].set("12")
        ed_form["txt_entry"].insert(0, "Graffi dietro l'altare.")

        editor.sync_campaign_data()
        self.assertIn("Appunto manuale del Master.", camp2.dm_notes)
        self.assertIn("=== ENIGMI & PROVE DELLA CAMPAGNA ===", camp2.dm_notes)
        self.assertIn("Graffi dietro l'altare.", camp2.dm_notes)
        self.assertIn("Percezione CD 12", camp2.dm_notes)
        self.assertIn("Graffi dietro l'altare.", editor.txt_dm_notes.get("1.0", tk.END))

        editor.studio_frame._remove_node_secret(ed_node, 0)
        editor.sync_campaign_data()
        self.assertIn("Appunto manuale del Master.", camp2.dm_notes)
        self.assertNotIn("=== ENIGMI & PROVE DELLA CAMPAGNA ===", camp2.dm_notes)
        self.assertNotIn("Graffi dietro l'altare.", editor.txt_dm_notes.get("1.0", tk.END))
        editor.destroy()


if __name__ == '__main__':
    unittest.main()
