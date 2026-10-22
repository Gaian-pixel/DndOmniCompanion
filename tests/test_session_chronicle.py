# test_session_chronicle.py
import unittest
from common.session_chronicle import (
    SessionLedger, SessionEvent, ChronicleGenerator,
    integrate_off_track_events_into_flow
)
from common.campaign_script import FlowGraph, FlowNode

class TestSessionChronicle(unittest.TestCase):
    def setUp(self):
        self.ledger = SessionLedger(
            session_id="20261021_215000",
            campaign_name="La Cripta dei Sussurri",
            start_game_date={"year": 1492, "month": 10, "day": 13, "hour": 20},
            current_game_date={"year": 1492, "month": 10, "day": 14, "hour": 2},
            current_weather="Nebbia"
        )

    def test_record_events_and_recap(self):
        # 1. Registra nodo ufficiale
        self.ledger.record_node_visit("node_1", "Locanda del Cinghiale", "scene")
        
        # 2. Registra deviazione fuori pista
        self.ledger.record_node_visit("node_off_1", "Fuga nella Palude", "off_track", is_off_track=True, details="I PG sono fuggiti dalla finestra")

        # 3. Registra combattimento improvvisato
        self.ledger.record_combat("Coccatrice Errante", [{"name": "Cockatrice", "quantity": 1}], rounds=3, victory=True, loot="Piuma magica", xp=100, is_off_track=True)

        # 4. Registra segreto svelato
        self.ledger.record_secret("Statua del Drago", "Intuizione CD 14", "La statua punta verso est")

        # 5. Registra tiro epico
        self.ledger.record_dice_crit("Gildor", "1d20+5", is_nat20=True)

        # 6. Registra nota DM
        self.ledger.record_dm_note("Il party deve ancora pagare il conto alla locanda!")

        self.assertEqual(len(self.ledger.events), 6)
        self.assertEqual(len(self.ledger.visited_node_ids), 2)

        # Verifica generazione Markdown
        md = ChronicleGenerator.generate_markdown(self.ledger)
        self.assertIn("La Cripta dei Sussurri", md)
        self.assertIn("Locanda del Cinghiale", md)
        self.assertIn("FUORI PISTA", md)
        self.assertIn("Fuga nella Palude", md)
        self.assertIn("Coccatrice Errante", md)
        self.assertIn("Statua del Drago", md)
        self.assertIn("Gildor", md)

        # Verifica generazione Discord text
        disc = ChronicleGenerator.generate_discord_text(self.ledger)
        self.assertIn("RECAP SESSIONE", disc)
        self.assertIn("Coccatrice Errante", disc)

        # Verifica generazione HTML
        html = ChronicleGenerator.generate_html(self.ledger)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("La Cripta dei Sussurri", html)

    def test_integrate_off_track_into_flow(self):
        # Prepara un FlowGraph iniziale con 1 solo nodo ufficiale
        graph = FlowGraph()
        node_locanda = FlowNode(id="node_locanda", node_type="scene", title="Locanda", x=100.0, y=100.0)
        graph.nodes["node_locanda"] = node_locanda

        # Registra percorso: prima Locanda, poi fuori pista
        self.ledger.record_node_visit("node_locanda", "Locanda", "scene")
        self.ledger.record_node_visit("off_bosco", "Bosco dei Sussurri", "off_track", is_off_track=True, details="Deviazione improvvisata nel bosco")
        self.ledger.record_combat("Banditi", [{"name": "Bandit", "quantity": 2}], is_off_track=True)

        # Esegui retro-integrazione nel FlowGraph
        new_nodes = integrate_off_track_events_into_flow(self.ledger, graph)
        self.assertEqual(len(new_nodes), 2)

        # Verifica che i nuovi nodi siano stati inseriti nel grafo
        self.assertEqual(len(graph.nodes), 3) # Locanda + Bosco + Banditi
        
        # Verifica che ci sia un edge che collega Locanda al primo fuori pista
        connected_edges = [e for e in graph.edges if e.from_id == "node_locanda"]
        self.assertGreaterEqual(len(connected_edges), 1)
        self.assertIn("Deviazione Fuori Pista", connected_edges[0].label)

if __name__ == '__main__':
    unittest.main()

