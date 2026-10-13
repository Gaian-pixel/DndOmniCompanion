# server/rules/audio.py
import base64
import threading

from common.protocol import make_audio_track_chunk, make_error_reply
from common.network_utils import send_message


def handle_audio_track_request(data, player, game_state):
    """Un client non ha la traccia in cache: gliela inviamo a blocchi in un thread separato."""
    track_id = data.get("track_id")
    library = getattr(game_state, "audio_library", None)
    if not track_id or library is None or not library.get(track_id):
        send_message(player.conn, make_error_reply("Traccia audio non disponibile sul server."))
        return

    conn = player.conn
    t_info = library.get(track_id)
    ext = t_info.get("ext", ".mp3") if t_info else ".mp3"

    def _send():
        for index, total, chunk in library.iter_chunks(track_id):
            if conn is None or player.conn is not conn:
                return  # il giocatore si è disconnesso durante il trasferimento
            send_message(conn, make_audio_track_chunk(track_id, index, total, base64.b64encode(chunk).decode("ascii"), ext=ext))

    threading.Thread(target=_send, daemon=True).start()

