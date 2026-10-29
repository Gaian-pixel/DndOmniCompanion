import unittest
from common.campaign_journal import (
    CampaignJournal, JournalSession, JournalEvent, format_game_date
)

class TestCampaignJournal(unittest.TestCase):
    def setUp(self):
        self.journal = CampaignJournal(campaign_name="Le Cronache di Rovescuro")

    def test_initial_session_creation(self):
        """Il diario crea automaticamente la Sessione 1 se vuoto."""
        sess = self.journal.get_active_session()
        self.assertEqual(sess.session_number, 1)
        self.assertEqual(len(self.journal.sessions), 1)
        self.assertFalse(sess.is_concluded)

    def test_multi_session_continuity(self):
        """Iniziare una nuova sessione archivia la precedente preservando la storia."""
        sess1 = self.journal.get_active_session()
        sess1.title = "La Notte delle Ossa"
        self.journal.record_event("combat", "Agguato degli Scheletri", "Il party ha affrontato 3 scheletri arcieri.", actor="Party")
        
        # Avvia Sessione 2
        sess2 = self.journal.start_new_session(title="La Discesa nella Cripta", location="Catacombe Profonde")
        self.assertEqual(len(self.journal.sessions), 2)
        self.assertTrue(sess1.is_concluded)
        self.assertFalse(sess2.is_concluded)
        self.assertEqual(sess2.session_number, 2)
        self.assertEqual(self.journal.active_session_index, 1)
        self.assertEqual(self.journal.get_active_session().title, "La Discesa nella Cripta")

    def test_prose_synthesis_italian(self):
        """La sintesi in italiano genera prosa fluida senza jargon di sistema né rime bardiche."""
        sess = self.journal.get_active_session()
        sess.location = "Rovescuro"
        sess.weather = "Pioggia"
        sess.game_date = {"year": 1492, "month": 3, "day": 14, "hour": 21, "minute": 0}

        self.journal.record_event("door", "Grata delle Catacombe", "Legolas ha scassinato la serratura arrugginita con successo.", actor="Legolas")
        self.journal.record_event("trap", "Dardo Avvelenato", "Thorin ha notato il meccanismo disattivandolo.", actor="Thorin")
        self.journal.record_event("combat", "Scontro con gli Spettri", "Due spettri guardiani sono emersi dall'ombra.", actor="Party")
        self.journal.record_event("combat", "Spettro Eliminato", "Lo spettro guardiano è stato abbattuto e dissolto.", actor="Gildor")
        self.journal.record_event("loot", "Spoglie della Cripta", "45 monete d'oro e una chiave d'argento.", actor="Legolas")
        self.journal.record_event("rest", "Riposo Breve", "Il party ha barricato l'anticamera medicando le ferite.", actor="Il gruppo")

        prose = self.journal.synthesize_prose(language="it")
        self.assertIn("Rovescuro", prose)
        self.assertIn("Pioggia", prose)
        self.assertIn("Esplorazione & Percorso", prose)
        self.assertIn("Legolas", prose)
        self.assertIn("Pericoli & Trappole", prose)
        self.assertIn("Fatti d'Arme & Combattimenti", prose)
        self.assertIn("Spoglie & Tesori", prose)
        self.assertIn("Bivacco & Riposo", prose)

    def test_prose_synthesis_english(self):
        """La sintesi in inglese genera prosa fluida equivalente."""
        sess = self.journal.get_active_session()
        sess.location = "Shadowdale"
        sess.weather = "Storm"
        sess.game_date = {"year": 1492, "month": 5, "day": 10, "hour": 14, "minute": 30}

        self.journal.record_event("door", "Iron Gate", "picked the rusty lock.", actor="Legolas")
        self.journal.record_event("combat", "Ambush", "defeated goblin scouts.", actor="Thorin")
        self.journal.record_event("loot", "Goblin Cache", "30 gold coins and a gem.", actor="Party")

        prose = self.journal.synthesize_prose(language="en")
        self.assertIn("Shadowdale", prose)
        self.assertIn("Exploration & Journey", prose)
        self.assertIn("Battles & Skirmishes", prose)
        self.assertIn("Spoils & Treasure", prose)

    def test_sanitize_for_players(self):
        """La sanitizzazione per i giocatori rimuove rigorosamente le note riservate del DM."""
        sess = self.journal.get_active_session()
        sess.prose = "Il gruppo ha varcato la soglia."
        sess.dm_notes = "ATTENZIONE: Padre Lucian è in realtà il cultista sotto mentite spoglie!"

        clean_dict = self.journal.sanitize_for_players()
        clean_sess = clean_dict["sessions"][0]
        self.assertEqual(clean_sess["prose"], "Il gruppo ha varcato la soglia.")
        self.assertEqual(clean_sess["dm_notes"], "")

    def test_export_formats(self):
        """Esportazione Markdown, Discord e HTML pergamena funzionano correttamente."""
        sess = self.journal.get_active_session()
        sess.title = "La Prima Notte"
        self.journal.record_event("discovery", "Iscrizione Antica", "Testo scolpito nella pietra.", actor="Gildor")
        sess.prose = self.journal.synthesize_prose(language="it")

        # Markdown completo
        md = self.journal.export_full_markdown(language="it")
        self.assertIn("Cronache di Campagna", md)
        self.assertIn("La Prima Notte", md)

        # Discord
        discord_txt = self.journal.export_discord(language="it")
        self.assertIn("La Prima Notte", discord_txt)
        self.assertIn("────────", discord_txt)

        # HTML
        html_doc = self.journal.export_html(language="it")
        self.assertIn("<!DOCTYPE html>", html_doc)
        self.assertIn("Cronache di Campagna", html_doc)
        self.assertIn("La Prima Notte", html_doc)
        self.assertIn(".parchment", html_doc)

    def test_serialization_roundtrip(self):
        """Serializzazione e deserializzazione preservano perfettamente tutte le sessioni ed eventi."""
        sess1 = self.journal.get_active_session()
        sess1.title = "Sessione Alpha"
        sess1.dm_notes = "Segreto 1"
        self.journal.record_event("combat", "Lotta", "Desc", actor="Thorin")
        
        self.journal.start_new_session(title="Sessione Beta")
        self.journal.record_event("loot", "Oro", "100 MO", actor="Legolas")

        data = self.journal.to_dict()
        restored = CampaignJournal.from_dict(data)

        self.assertEqual(restored.campaign_name, "Le Cronache di Rovescuro")
        self.assertEqual(len(restored.sessions), 2)
        self.assertEqual(restored.sessions[0].title, "Sessione Alpha")
        self.assertEqual(restored.sessions[0].dm_notes, "Segreto 1")
        self.assertEqual(len(restored.sessions[0].events), 1)
        self.assertEqual(restored.sessions[1].title, "Sessione Beta")
        self.assertEqual(len(restored.sessions[1].events), 1)

    def test_game_state_journal_integration(self):
        """GameState registra gli eventi nel CampaignJournal e sanitizza per i giocatori."""
        import queue
        from common.game_state import GameState
        gs = GameState(gui_queue=queue.Queue())
        self.assertIsNotNone(gs.campaign_journal)

        gs.record_journal_event("combat", "Inizio Incontro", "I goblin attaccano il carretto.", actor="Goblin")
        sess = gs.campaign_journal.get_active_session()
        self.assertEqual(len(sess.events), 1)
        self.assertEqual(sess.events[0].title, "Inizio Incontro")

        # Verifica get_state_dict anti-metagame
        sess.dm_notes = "Il Goblin Sciamano possiede una mappa segreta."
        dm_state = gs.get_state_dict(is_dm=True)
        player_state = gs.get_state_dict(is_dm=False)

        self.assertIn("campaign_journal", dm_state)
        self.assertIn("campaign_journal", player_state)
        self.assertEqual(dm_state["campaign_journal"]["sessions"][0]["dm_notes"], "Il Goblin Sciamano possiede una mappa segreta.")
        self.assertEqual(player_state["campaign_journal"]["sessions"][0]["dm_notes"], "")

    def test_protocol_and_server_handlers(self):
        """Messaggi di protocollo e server handler per il diario di campagna."""
        import queue
        from common.game_state import GameState
        from common.protocol import (
            make_journal_sync, make_journal_update_request,
            make_new_journal_session_request, make_conclude_journal_session_request
        )
        from server.rules.journal import (
            handle_journal_update_request,
            handle_new_journal_session_request,
            handle_conclude_journal_session_request
        )

        msg_update = make_journal_update_request(0, title="Nuovo Titolo", prose="Prosa aggiornata")
        self.assertEqual(msg_update["type"], "JOURNAL_UPDATE_REQUEST")
        self.assertEqual(msg_update["data"]["title"], "Nuovo Titolo")

        msg_new = make_new_journal_session_request("Sessione 2")
        self.assertEqual(msg_new["type"], "NEW_JOURNAL_SESSION_REQUEST")
        self.assertEqual(msg_new["data"]["title"], "Sessione 2")

        msg_conclude = make_conclude_journal_session_request()
        self.assertEqual(msg_conclude["type"], "CONCLUDE_JOURNAL_SESSION_REQUEST")

        class MockPlayer:
            def __init__(self):
                self.role = "DM"
                self.conn = None

        mock_player = MockPlayer()
        game_state = GameState(gui_queue=queue.Queue())

        # Test update request handler
        handle_journal_update_request({
            "session_index": 0,
            "title": "La Torre del Mago",
            "prose": "Il gruppo scala la torre.",
            "dm_notes": "Trappola al terzo piano."
        }, mock_player, game_state)
        sess = game_state.campaign_journal.get_active_session()
        self.assertEqual(sess.title, "La Torre del Mago")
        self.assertEqual(sess.prose, "Il gruppo scala la torre.")
        self.assertEqual(sess.dm_notes, "Trappola al terzo piano.")

        # Test new session handler
        handle_new_journal_session_request({
            "title": "La Cripta Sotto la Torre",
            "location": "Cripta"
        }, mock_player, game_state)
        self.assertEqual(len(game_state.campaign_journal.sessions), 2)
        self.assertEqual(game_state.campaign_journal.get_active_session().title, "La Cripta Sotto la Torre")

        # Test conclude session handler
        handle_conclude_journal_session_request({}, mock_player, game_state)
        self.assertTrue(game_state.campaign_journal.sessions[1].is_concluded)

if __name__ == "__main__":
    unittest.main()
