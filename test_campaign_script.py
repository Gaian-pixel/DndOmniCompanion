# test_campaign_script.py
import unittest
from common.campaign_script import (
    DndScriptParser, DndScriptSerializer, FlowGraph, FlowNode, FlowEdge,
    sync_flow_graph_to_campaign, generate_flow_from_campaign
)
from common.campaign import Campaign

class TestCampaignScript(unittest.TestCase):
    def setUp(self):
        self.sample_script = """
# SCENA: Locanda del Cinghiale
mappa: "maps/faerun.json"
meteo: "Nebbia"
luce: "Notte"
musica: "Taverna"
narra: "Una locanda calda e fumosa nel villaggio di Rovescuro."

* SEGRETO [Intuizione CD 12]: "Il locandiere e ricattato dal culto."
* VOCE: "La vecchia cripta a nord e profanata."
* HANDOUT: "mappa_segreta.png" [titolo: "Mappa Cifrata"]

-> "Se interrogano il locandiere" -> SCENA: Ingresso Cripta
-> "Se escono di notte per investigare" -> INCONTRO: Imboscata Lupi
-> "Se cercano il sindaco" -> PNG: Sindaco Roland


# INCONTRO: Imboscata Lupi
mostri: 3x "Lupo", 1x "Lupo Feroce"
cr: "2"
musica: "Combattimento"
loot: "Pelli di lupo, 15 mo"

-> "Seguendo le tracce" -> SCENA: Ingresso Cripta


# SCENA: Ingresso Cripta
mappa: "maps/cripta.json"
narra: "Due pesanti battenti di pietra consumati dal tempo."

* SEGRETO [Arcano CD 14]: "Sigillo necromantico inciso sulla pietra."
* TRAPPOLA [Percezione CD 13]: "Lastra a pressione."

-> "Se aprono la porta" -> SCENA: Tomba dei Re


# PNG: Sindaco Roland
ruolo: "Sindaco del borgo"
allineamento: "Legale Buono"

-> "Accettata la missione" -> QUEST: Sussurri nella Cripta


# QUEST: Sussurri nella Cripta
obiettivi: "Raggiungi la cripta", "Purifica il santuario"
loot: "100 mo, Pozione di Cura"
xp: 300

-> SCENA: Ingresso Cripta
"""

    def test_parse_nodes_and_edges(self):
        parser = DndScriptParser()
        graph = parser.parse(self.sample_script)

        # Verifica nodi creati
        self.assertGreaterEqual(len(graph.nodes), 5)
        
        # Verifica Locanda
        locanda = graph.get_node_by_title("Locanda del Cinghiale")
        self.assertIsNotNone(locanda)
        self.assertEqual(locanda.node_type, "scene")
        self.assertEqual(locanda.data.get("map_file"), "maps/faerun.json")
        self.assertEqual(locanda.data.get("weather"), "Nebbia")
        self.assertEqual(locanda.data.get("music"), "Taverna")
        self.assertIn("calda e fumosa", locanda.data.get("read_aloud", ""))

        # Verifica segreti e voci
        secrets = locanda.data.get("secrets", [])
        self.assertEqual(len(secrets), 1)
        self.assertEqual(secrets[0]["check"], "Intuizione CD 12")
        self.assertIn("ricattato", secrets[0]["text"])

        rumors = locanda.data.get("rumors", [])
        self.assertEqual(len(rumors), 1)
        self.assertIn("cripta", rumors[0]["text"])

        # Verifica Incontro Lupi
        lupi = graph.get_node_by_title("Imboscata Lupi")
        self.assertIsNotNone(lupi)
        self.assertEqual(lupi.node_type, "encounter")
        self.assertEqual(lupi.data.get("cr"), "2")
        monsters = lupi.data.get("monsters", [])
        self.assertEqual(len(monsters), 2)
        self.assertEqual(monsters[0]["name"], "Lupo")
        self.assertEqual(monsters[0]["quantity"], 3)
        self.assertEqual(monsters[1]["name"], "Lupo Feroce")
        self.assertEqual(monsters[1]["quantity"], 1)

        # Verifica Quest
        quest = graph.get_node_by_title("Sussurri nella Cripta")
        self.assertIsNotNone(quest)
        self.assertEqual(quest.node_type, "quest")
        self.assertEqual(quest.data.get("xp"), 300)
        self.assertEqual(len(quest.data.get("objectives", [])), 2)

        # Verifica Edges
        self.assertGreaterEqual(len(graph.edges), 5)
        # Controlla freccia Locanda -> Incontro Lupi
        found_edge = False
        for e in graph.edges:
            if e.from_id == locanda.id and e.to_id == lupi.id:
                self.assertIn("escono di notte", e.label)
                found_edge = True
                break
        self.assertTrue(found_edge)

    def test_bidirectional_serialization(self):
        parser = DndScriptParser()
        graph = parser.parse(self.sample_script)

        serializer = DndScriptSerializer()
        generated_code = serializer.serialize(graph)

        # Ricarica il codice generato
        reparsed_graph = parser.parse(generated_code)

        # Verifica equivalenza nodi
        self.assertEqual(len(graph.nodes), len(reparsed_graph.nodes))
        self.assertEqual(len(graph.edges), len(reparsed_graph.edges))

        re_locanda = reparsed_graph.get_node_by_title("Locanda del Cinghiale")
        self.assertIsNotNone(re_locanda)
        self.assertEqual(re_locanda.data.get("map_file"), "maps/faerun.json")

    def test_sync_to_campaign(self):
        parser = DndScriptParser()
        graph = parser.parse(self.sample_script)

        camp = Campaign(name="Test Campaign")
        sync_flow_graph_to_campaign(graph, camp)

        # Verifica sincronizzazione con gli oggetti Campaign
        scene_names = [s["name"] for s in camp.scenes]
        self.assertIn("Locanda del Cinghiale", scene_names)
        self.assertIn("Ingresso Cripta", scene_names)

        enc_names = [e["name"] for e in camp.encounters]
        self.assertIn("Imboscata Lupi", enc_names)

        quest_titles = [q["title"] for q in camp.quests]
        self.assertIn("Sussurri nella Cripta", quest_titles)

        npc_names = [n["name"] for n in camp.npcs]
        self.assertIn("Sindaco Roland", npc_names)

    def test_generate_flow_from_campaign(self):
        camp = Campaign(name="Vecchia Campagna")
        camp.scenes = [{"name": "Piazza", "map_file": "maps/faerun.json", "description": "Una piazza antica."}]
        camp.encounters = [{"name": "Briganti", "description": "3 banditi armati.", "monsters": [{"name": "Bandit", "quantity": 3}]}]
        camp.quests = [{"title": "Salva il borgo", "description": "Sconfiggi i briganti.", "objectives": ["Elimina i capi"]}]

        graph = generate_flow_from_campaign(camp)
        self.assertGreaterEqual(len(graph.nodes), 4) # Hub + 1 scena + 1 incontro + 1 quest

        serializer = DndScriptSerializer()
        script = serializer.serialize(graph)
        self.assertIn("# SCENA: Piazza", script)
        self.assertIn("# INCONTRO: Briganti", script)
        self.assertIn("# QUEST: Salva il borgo", script)

if __name__ == '__main__':
    unittest.main()
