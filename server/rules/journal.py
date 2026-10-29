# server/rules/journal.py
"""
Handler per le richieste di aggiornamento e sincronizzazione del Diario di Campagna.
"""

from common.network_utils import broadcast
from common.protocol import make_journal_sync, make_chat_broadcast


def handle_journal_update_request(data, player, game_state):
    """Aggiorna titolo, prosa o note riservate di una specifica sessione del diario."""
    is_dm = (player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if not is_dm:
        return

    session_index = data.get("session_index", -1)
    title = data.get("title")
    prose = data.get("prose")
    dm_notes = data.get("dm_notes")

    with game_state.lock:
        if not hasattr(game_state, "campaign_journal") or not game_state.campaign_journal:
            return

        journal = game_state.campaign_journal
        if not journal.sessions:
            journal.get_active_session()

        if 0 <= session_index < len(journal.sessions):
            sess = journal.sessions[session_index]
            if title is not None:
                sess.title = title
            if prose is not None:
                sess.prose = prose
            if dm_notes is not None:
                sess.dm_notes = dm_notes

        if getattr(game_state, "active_campaign", None):
            game_state.active_campaign.journal = journal

    # Trasmetti la versione sanitizzata ai giocatori
    sanitized = game_state.campaign_journal.sanitize_for_players()
    broadcast(game_state, make_journal_sync(sanitized))
    game_state._trigger_gui_update()


def handle_new_journal_session_request(data, player, game_state):
    """Inizia una nuova sessione all'interno del Diario Continuativo di Campagna."""
    is_dm = (player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if not is_dm:
        return

    title = data.get("title", "")
    with game_state.lock:
        if not hasattr(game_state, "campaign_journal") or not game_state.campaign_journal:
            from common.campaign_journal import CampaignJournal
            camp_name = getattr(game_state.active_campaign, "name", "Campagna") if getattr(game_state, "active_campaign", None) else "Campagna"
            game_state.campaign_journal = CampaignJournal(campaign_name=camp_name)

        weather = getattr(game_state, "weather", "Sereno")
        loc = getattr(game_state.current_map, "get", lambda k, d: d)("name", "Mappa Tattica") if getattr(game_state, "current_map", None) else "Faerûn"
        game_date = {
            "year": getattr(game_state, "time_year", 1492),
            "month": getattr(game_state, "time_month", 1),
            "day": getattr(game_state, "time_day", 1),
            "hour": getattr(game_state, "time_hour", 8),
            "minute": getattr(game_state, "time_minute", 0)
        }
        new_sess = game_state.campaign_journal.start_new_session(
            title=title,
            weather=weather,
            location=loc,
            game_date=game_date
        )

        if getattr(game_state, "active_campaign", None):
            game_state.active_campaign.journal = game_state.campaign_journal

    sanitized = game_state.campaign_journal.sanitize_for_players()
    broadcast(game_state, make_journal_sync(sanitized))
    sess_title = new_sess.title if new_sess else "Nuova Sessione"
    broadcast(game_state, make_chat_broadcast("Sistema", f"📖 Il DM ha aperto una nuova sessione nel Diario: {sess_title}"))
    game_state._trigger_gui_update()


def handle_conclude_journal_session_request(data, player, game_state):
    """Archivia la sessione attiva generando la sintesi se non presente."""
    is_dm = (player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if not is_dm:
        return

    with game_state.lock:
        if not hasattr(game_state, "campaign_journal") or not game_state.campaign_journal:
            return
        concluded = game_state.campaign_journal.conclude_active_session()

        if getattr(game_state, "active_campaign", None):
            game_state.active_campaign.journal = game_state.campaign_journal

    sanitized = game_state.campaign_journal.sanitize_for_players()
    broadcast(game_state, make_journal_sync(sanitized))
    concluded_title = concluded.title if concluded else "Sessione"
    broadcast(game_state, make_chat_broadcast("Sistema", f"🏁 Sessione {concluded_title} conclusa ed archiviata nel Diario."))
    game_state._trigger_gui_update()
