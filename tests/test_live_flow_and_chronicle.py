# test_live_flow_and_chronicle.py
import unittest
import tkinter as tk
from common.campaign_script import (
    FlowGraph, FlowNode,
    sync_flow_graph_to_campaign
)
from common.session_chronicle import (
    SessionLedger, ChronicleGenerator, integrate_off_track_events_into_flow
)
from common.campaign import Campaign

class TestLiveFlowAndChronicleE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_full_pipeline_flow_to_chronicle(self):
        # 1. Costruzione diretta FlowGraph
        graph = FlowGraph()
        graph.nodes["n1"] = FlowNode(
            id="n1", node_type="scene", title="Taverna del Lupo",
            data={"map_file": "maps/faerun.json", "read_aloud": "Una taverna affollata."},
        )
        graph.nodes["n2"] = FlowNode(
            id="n2", node_type="scene", title="Bosco Oscuro",
            data={"map_file": "maps/bosco.json"},
        )
        graph.nodes["n3"] = FlowNode(id="n3", node_type="scene", title="Cantina Segreta")
        graph.add_edge("n1", "n2", label="Se escono nei boschi")
        graph.add_edge("n1", "n3", label="Se scendono in cantina")
        self.assertEqual(len(graph.nodes), 3)

        # 2. Creazione Campagna
        camp = Campaign(name="Saga del Lupo")
        sync_flow_graph_to_campaign(graph, camp)
        self.assertEqual(len(camp.scenes), 3)

        # 3. Avvio Sessione e Ledger
        ledger = SessionLedger(
            campaign_name=camp.name,
            start_game_date={"year": 1492, "month": 5, "day": 10, "hour": 20}
        )

        # 4. Spostamento nel grafo pianificato
        taverna = graph.get_node_by_title("Taverna del Lupo")
        self.assertIsNotNone(taverna)
        ledger.record_node_visit(taverna.id, taverna.title, "scene")

        # 5. Deviazione FUORI PISTA
        # I giocatori decidono di incendiare il ponte invece di andare nel bosco
        ledger.record_node_visit(
            node_id="off_ponte",
            title="Incendio al Vecchio Ponte",
            node_type="off_track",
            is_off_track=True,
            details="Il party ha dato fuoco al ponte per fermare gli inseguitori"
        )
        ledger.record_combat(
            title="Guardie a Cavallo",
            monsters=[{"name": "Guardia", "quantity": 3}],
            rounds=2,
            victory=True,
            loot="35 mo",
            is_off_track=True
        )

        # 6. Generazione Cronistoria
        md = ChronicleGenerator.generate_markdown(ledger)
        self.assertIn("Saga del Lupo", md)
        self.assertIn("Incendio al Vecchio Ponte", md)
        self.assertIn("Guardie a Cavallo", md)

        discord_recap = ChronicleGenerator.generate_discord_text(ledger)
        self.assertIn("RECAP SESSIONE", discord_recap)
        self.assertIn("Incendio al Vecchio Ponte", discord_recap)

        # 7. Retro-Integrazione del Fuori Pista nel Flusso
        new_nodes = integrate_off_track_events_into_flow(ledger, graph)
        self.assertEqual(len(new_nodes), 2) # Nodo Ponte + Nodo Combattimento Guardie
        self.assertEqual(len(graph.nodes), 5) # 3 originali + 2 nuovi fuori pista

        # 8. Persistenza JSON FlowGraph con nodi fuori pista
        persisted = FlowGraph.from_dict(graph.to_dict())
        titles = [n.title for n in persisted.nodes.values()]
        self.assertIn("Incendio al Vecchio Ponte (Fuori Pista)", titles)
        self.assertIn("Guardie a Cavallo (Fuori Pista)", titles)
        self.assertTrue(any("Deviazione Fuori Pista" in e.label for e in persisted.edges))

if __name__ == '__main__':
    unittest.main()

